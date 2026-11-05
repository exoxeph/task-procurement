"""Fixed workflow: read PDF -> extract -> validate -> check rules -> report/handoff."""

import argparse
from dataclasses import replace
import math
import json
import os
from pathlib import Path
from time import perf_counter

from procurement.shared.evaluation import evaluate_fields, evaluate_samples
from procurement.shared.env import load_env
from procurement.shared.extraction import FACT_NAMES, parse_json, validate_fields
from procurement.shared.human_review import apply_corrections
from procurement.approach1.extractor import extract_document as extract_baseline
from procurement.shared.pdf_text import PdfReadError, read_pdf
from procurement.shared.references import PROJECT_ROOT, SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.report import render_comparison, render_report
from procurement.shared.rules import check_rules
from procurement.shared.runs import read_run, stamp_run, write_run


def document_level_issues(issues):
    """Keep run issues about the document or whole run; drop one-fact ("quantity: ...") issues."""
    return tuple(issue for issue in issues if issue.split(': ', 1)[0] not in FACT_NAMES)


def review_document(path, items, policy, *, approach='approach1', model=None,
                    endpoint='http://localhost:11434', timeout=600.0, artifact_dir=None,
                    source_run=None, review_response=None, provider='ollama'):
    started = perf_counter()
    document = read_pdf(path)
    if (source_run is None) != (review_response is None):
        raise ValueError('A correction requires both source_run and review_response.')
    if source_run is not None:
        original = read_run(source_run, document)
        response = parse_json(Path(review_response).read_text(encoding='utf-8'))
        run = apply_corrections(original, document, response)
    elif approach == 'approach1':
        run = extract_baseline(document)
        run = replace(run, metadata={**run.metadata, 'status': 'needs_review' if run.issues else 'completed',
                                     'elapsed_seconds': perf_counter() - started})
    elif approach == 'approach2' and provider == 'gemini':
        from procurement.approach2.gemini import extract_document as extract_gemini
        run = extract_gemini(document, model=model, timeout=timeout)
    elif approach == 'approach2' and provider == 'openrouter':
        from procurement.approach2.openrouter import extract_document as extract_openrouter
        run = extract_openrouter(document, model=model, timeout=timeout)
    elif approach == 'approach2':
        from procurement.approach2.extractor import extract_document as extract_ai
        run = extract_ai(document, model=model or 'qwen3:14b', endpoint=endpoint, timeout=timeout)
    elif approach == 'approach3' and provider == 'openrouter':
        from procurement.approach3.openrouter import extract_document as extract_openrouter3
        run = extract_openrouter3(document, model=model, timeout=timeout)
    elif approach == 'approach4':
        from procurement.approach4.extractor import extract_document as extract_ai4
        run = extract_ai4(document, model=model, timeout=timeout, provider=provider, endpoint=endpoint)
    elif approach == 'approach3':
        from procurement.approach3.extractor import extract_document as extract_ai3
        run = extract_ai3(document, model=model or 'qwen2.5:7b', endpoint=endpoint, timeout=timeout)
    else:
        raise ValueError(f'Unknown extraction approach: {approach}')
    if approach != 'approach4':
        # Approach 4 keeps the extractor's facts and carries code warnings instead of erasing values.
        validation = validate_fields(run.fields, document)
        run = replace(run, fields=validation.fields,
                      issues=tuple(dict.fromkeys(run.issues + validation.issues)))
    run = stamp_run(run, document)
    # pdf_issue is for problems with the document or the whole run (unreadable page,
    # several items, a failed model call). A problem with one fact ("quantity: ...") is
    # already shown by that fact's own finding, so it is not repeated as a pdf_issue.
    document_level = document_level_issues(run.issues)
    checked_document = replace(document, issues=tuple(dict.fromkeys(document.issues + document_level)))
    decision = None
    if approach == 'approach4' and run.metadata.get('status') != 'failed':
        # The judge checks the facts against the source and applies the company rules, alone.
        from procurement.approach4.judge import judge
        # Same service as the extractor. On OpenRouter the judge model may differ (OPENROUTER_JUDGE_MODEL).
        judge_model = run.metadata.get('model')
        if provider == 'openrouter':
            judge_model = (os.environ.get('OPENROUTER_JUDGE_MODEL') or os.environ.get('OPENROUTER_DECIDER_MODEL')
                           or judge_model)
        decision, decision_meta = judge(checked_document, run, items, policy, model=judge_model,
                                        key=os.environ.get('OPENROUTER_API_KEY', '') if provider == 'openrouter' else '',
                                        timeout=timeout, provider=provider, endpoint=endpoint)
        metadata = {**run.metadata, 'judge': decision_meta,
                    'elapsed_seconds': (run.metadata.get('elapsed_seconds') or 0) + decision_meta['elapsed_seconds']}
        if decision_meta['status'] == 'failed':
            metadata['status'] = 'failed'
        run = replace(run, metadata=metadata)
    if artifact_dir is not None:
        artifact_path = write_run(run, document, artifact_dir)
        run = replace(run, metadata={**run.metadata, 'artifact_path': str(artifact_path.resolve())})
    result = decision if decision is not None else check_rules(checked_document, run.fields, items, policy)
    extraction_status = (run.metadata.get('source_status') if run.metadata.get('assisted')
                         else run.metadata.get('status'))
    steps = (
        {'name': 'Read PDF', 'status': 'needs_review' if document.issues else 'completed'},
        {'name': 'Extract facts', 'status': extraction_status or 'completed'},
        {'name': 'Validate facts', 'status': 'needs_review' if run.issues or any(
            fact.status in ('ambiguous', 'unrecognized') for fact in run.fields.values()) else 'completed'},
        {'name': 'Check purchase request and company rules',
         'status': 'needs_review' if any(f.severity == 'Needs a person to check' for f in result.findings) else 'completed'},
        {'name': 'Report decision and human handoff',
         'status': 'needs_review' if result.verdict == 'Needs a person to check' else 'completed'},
    )
    if approach == 'approach4':
        steps = (
            {'name': 'Read PDF', 'status': 'needs_review' if document.issues else 'completed'},
            {'name': 'Agent 1: extract facts step by step', 'status': extraction_status or 'completed'},
            {'name': 'Code: annotate quote and format warnings (nothing erased)',
             'status': 'needs_review' if run.metadata.get('warnings') else 'completed'},
            {'name': 'Agent 2: check facts against the source and apply the rules',
             'status': 'needs_review' if result.verdict == 'Needs a person to check' else 'completed'},
            {'name': 'Report decision and human handoff',
             'status': 'needs_review' if result.verdict == 'Needs a person to check' else 'completed'},
        )
    return replace(result, extraction_run=run, steps=steps)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path, help='Defaults to the ten supplied PDFs.')
    parser.add_argument('--output', type=Path, default=Path('reports/procurement-review.html'))
    parser.add_argument('--check-labels',action='store_true',help='Exit 1 if development results differ from manual labels.')
    parser.add_argument('--approach', choices=('approach1', 'approach2', 'approach3', 'approach4', 'both'), default='approach1')
    parser.add_argument('--provider', choices=('ollama', 'gemini', 'openrouter'), default='ollama',
                        help='Model service for approach2. gemini and openrouter send document text to a hosted service '
                             'and need GEMINI_API_KEY / OPENROUTER_API_KEY in .env.')
    parser.add_argument('--model', help='Installed local Ollama model (Approach 2 defaults to qwen3:14b), '
                                        'a Gemini model (GEMINI_MODEL) or an OpenRouter slug (OPENROUTER_MODEL) from .env.')
    parser.add_argument('--ollama-url', default='http://localhost:11434')
    parser.add_argument('--timeout', type=float, default=600.0, help='Seconds per extraction call.')
    parser.add_argument('--artifacts', type=Path, default=Path('reports/runs'))
    parser.add_argument('--source-run', type=Path, help='Saved extraction JSON to correct; does not call AI again.')
    parser.add_argument('--review-response', type=Path, help='Attributed, source-backed corrections JSON.')
    load_env()
    arguments = parser.parse_args()
    if arguments.provider != 'ollama' and arguments.approach == 'approach1':
        parser.error('--provider gemini/openrouter applies to approach2, approach3 or approach4')
    if arguments.provider == 'gemini' and arguments.approach in ('approach3', 'approach4'):
        parser.error('approach3 and approach4 support --provider ollama (default) or openrouter, not gemini')
    if bool(arguments.source_run) != bool(arguments.review_response):
        parser.error('--source-run and --review-response must be supplied together')
    if arguments.review_response and (len(arguments.paths) != 1 or arguments.approach == 'both'):
        parser.error('Human corrections require exactly one explicit PDF and cannot use --approach both')
    if arguments.output.suffix.lower() != '.html':
        parser.error('--output must be an .html report path')
    if not math.isfinite(arguments.timeout) or arguments.timeout <= 0:
        parser.error('--timeout must be a positive finite number')
    try:
        items = load_purchase_request()
        policy = load_company_rules()
        fact_labels = parse_json((PROJECT_ROOT / 'config/manual-facts.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot load references: {error}\n')
    paths = arguments.paths or sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))
    if not paths:
        parser.exit(1, 'No supplier PDFs found.\n')
    approaches = ('approach1', 'approach2') if arguments.approach == 'both' else (arguments.approach,)
    failed = False
    groups, report_paths = {}, {}
    for approach in approaches:
        results, errors = [], []
        for path in paths:
            label = 'human-assisted' if arguments.review_response else approach
            print(f'{label}: reading {path.name}...', flush=True)
            try:
                result = review_document(path, items, policy, approach=approach, model=arguments.model,
                                         provider=arguments.provider, endpoint=arguments.ollama_url, timeout=arguments.timeout,
                                         artifact_dir=arguments.artifacts, source_run=arguments.source_run,
                                         review_response=arguments.review_response)
                results.append(result)
                print(f'{path.name}: {result.verdict}', flush=True)
            except (PdfReadError, OSError, ValueError) as error:
                errors.append((str(path), str(error)))
                print(f'{path.name}: Needs a person to check - {error}', flush=True)
        # Failed human corrections also stay outside unassisted extraction scores.
        evaluation = evaluate_samples(results, () if arguments.review_response else errors)
        evaluation['fields'] = evaluate_fields(results, fact_labels, () if arguments.review_response else errors)
        groups[approach] = evaluation
        print_evaluation(evaluation)
        output = arguments.output
        if arguments.approach == 'both':
            output = output.with_name(f'{output.stem}-{approach}{output.suffix}')
        report_paths[approach] = output.name
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_report(results, errors, evaluation), encoding='utf-8')
        except OSError as error:
            parser.exit(1, f'Cannot write report: {error}\n')
        print(f'Report: {output.resolve()}')
        execution_error = bool(errors) or any(r.extraction_run.metadata.get('status') == 'failed' for r in results)
        mismatch = evaluation['verdict_matches'] != evaluation['total'] or evaluation['rule_matches'] != evaluation['total']
        failed |= execution_error or (arguments.check_labels and mismatch)
    try:
        arguments.output.with_suffix('.json').write_text(json.dumps(groups, indent=2), encoding='utf-8')
        if arguments.approach == 'both':
            arguments.output.write_text(render_comparison(groups, report_paths), encoding='utf-8')
            print(f'Comparison: {arguments.output.resolve()}')
    except OSError as error:
        parser.exit(1, f'Cannot write comparison metrics: {error}\n')
    return int(failed)


def print_evaluation(evaluation):
    """Keep console metrics consistent for each approach."""
    if evaluation.get('assisted_excluded'):
        print(f"Assisted runs excluded: {evaluation['assisted_excluded']}")
    if evaluation['total']:
        print(f"Development samples - Verdicts: {evaluation['verdict_matches']}/{evaluation['total']}; "
              f"Rule sets: {evaluation['rule_matches']}/{evaluation['total']}")
        print(f"Automatic decisions: {evaluation['automatic_decisions']}/{evaluation['total']}; "
              f"Conservative escalations: {evaluation['conservative_escalations']}; "
              f"Unsafe approvals: {evaluation['unsafe_approvals']}")
        print(f"Input failures: {evaluation['input_failures']}; Extraction failures: {evaluation['extraction_failures']}")


if __name__ == '__main__':
    raise SystemExit(main())
