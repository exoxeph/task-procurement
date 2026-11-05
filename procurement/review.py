"""Fixed workflow: read PDF -> extract -> validate -> check rules -> report/handoff."""

import argparse
import math
import json
from pathlib import Path

from procurement.shared.evaluation import evaluate_fields, evaluate_samples
from procurement.shared.env import load_env
from procurement.shared.extraction import parse_json
from procurement.shared.pdf_text import PdfReadError
from procurement.shared.references import PROJECT_ROOT, SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.report import render_comparison, render_report
from procurement.workflow import document_level_issues, run_workflow  # noqa: F401  (re-exported)


def review_document(path, items, policy, *, approach='approach1', model=None,
                    endpoint='http://localhost:11434', timeout=600.0, artifact_dir=None,
                    source_run=None, review_response=None, provider='ollama', on_step=None):
    """Run one PDF through the approach's fixed LangGraph workflow (see procurement/workflow.py)."""
    return run_workflow(path, items, policy, approach=approach, model=model, endpoint=endpoint,
                        timeout=timeout, artifact_dir=artifact_dir, source_run=source_run,
                        review_response=review_response, provider=provider, on_step=on_step)


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
