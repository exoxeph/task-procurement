"""The fixed workflow: read PDF -> extract facts -> check rules -> report."""

import argparse
from dataclasses import replace
import math
from pathlib import Path
from time import perf_counter

from procurement.shared.evaluation import evaluate_samples
from procurement.approach1.extractor import extract_document as extract_baseline
from procurement.shared.pdf_text import PdfReadError, read_pdf
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.report import render_report
from procurement.shared.rules import check_rules
from procurement.shared.runs import stamp_run, write_run


def review_document(path, items, policy, *, approach='approach1', model='qwen2.5:7b',
                    endpoint='http://localhost:11434', timeout=180.0, artifact_dir=None):
    started = perf_counter()
    document = read_pdf(path)
    if approach == 'approach1':
        run = extract_baseline(document)
        run = replace(run, metadata={**run.metadata, 'status': 'needs_review' if run.issues else 'completed',
                                     'elapsed_seconds': perf_counter() - started})
    elif approach == 'approach2':
        from procurement.approach2.extractor import extract_document as extract_ai
        run = extract_ai(document, model=model, endpoint=endpoint, timeout=timeout)
    else:
        raise ValueError(f'Unknown extraction approach: {approach}')
    run = stamp_run(run, document)
    if artifact_dir is not None:
        artifact_path = write_run(run, document, artifact_dir)
        run = replace(run, metadata={**run.metadata, 'artifact_path': str(artifact_path.resolve())})
    document = replace(document, issues=tuple(dict.fromkeys(document.issues + run.issues)))
    result = check_rules(document, run.fields, items, policy)
    return replace(result, extraction_run=run)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path, help='Defaults to the ten supplied PDFs.')
    parser.add_argument('--output', type=Path, default=Path('reports/procurement-review.html'))
    parser.add_argument('--check-labels',action='store_true',help='Exit 1 if development results differ from manual labels.')
    parser.add_argument('--approach', choices=('approach1', 'approach2', 'both'), default='approach1')
    parser.add_argument('--model', default='qwen2.5:7b', help='Installed local Ollama model.')
    parser.add_argument('--ollama-url', default='http://localhost:11434')
    parser.add_argument('--timeout', type=float, default=180.0, help='Seconds per extraction call.')
    parser.add_argument('--artifacts', type=Path, default=Path('reports/runs'))
    arguments = parser.parse_args()
    if arguments.output.suffix.lower() != '.html':
        parser.error('--output must be an .html report path')
    if not math.isfinite(arguments.timeout) or arguments.timeout <= 0:
        parser.error('--timeout must be a positive finite number')
    try:
        items = load_purchase_request()
        policy = load_company_rules()
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot load references: {error}\n')
    paths = arguments.paths or sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))
    if not paths:
        parser.exit(1, 'No supplier PDFs found.\n')
    approaches = ('approach1', 'approach2') if arguments.approach == 'both' else (arguments.approach,)
    failed = False
    for approach in approaches:
        results, errors = [], []
        for path in paths:
            print(f'{approach}: reading {path.name}...', flush=True)
            try:
                result = review_document(path, items, policy, approach=approach, model=arguments.model,
                                         endpoint=arguments.ollama_url, timeout=arguments.timeout,
                                         artifact_dir=arguments.artifacts)
                results.append(result)
                print(f'{path.name}: {result.verdict}', flush=True)
            except (PdfReadError, OSError, ValueError) as error:
                errors.append((str(path), str(error)))
                print(f'{path.name}: Needs a person to check - {error}', flush=True)
        evaluation = evaluate_samples(results, errors)
        print_evaluation(evaluation)
        output = arguments.output
        if arguments.approach == 'both':
            output = output.with_name(f'{output.stem}-{approach}{output.suffix}')
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_report(results, errors, evaluation), encoding='utf-8')
        except OSError as error:
            parser.exit(1, f'Cannot write report: {error}\n')
        print(f'Report: {output.resolve()}')
        execution_error = bool(errors) or any(r.extraction_run.metadata.get('status') == 'failed' for r in results)
        mismatch = evaluation['verdict_matches'] != evaluation['total'] or evaluation['rule_matches'] != evaluation['total']
        failed |= execution_error or (arguments.check_labels and mismatch)
    return int(failed)


def print_evaluation(evaluation):
    """Keep console metrics consistent for each approach."""
    if evaluation['total']:
        print(f"Development samples - Verdicts: {evaluation['verdict_matches']}/{evaluation['total']}; "
              f"Rule sets: {evaluation['rule_matches']}/{evaluation['total']}")
        print(f"Automatic decisions: {evaluation['automatic_decisions']}/{evaluation['total']}; "
              f"Conservative escalations: {evaluation['conservative_escalations']}; "
              f"Unsafe approvals: {evaluation['unsafe_approvals']}")
        print(f"Input failures: {evaluation['input_failures']}; Extraction failures: {evaluation['extraction_failures']}")


if __name__ == '__main__':
    raise SystemExit(main())
