"""The fixed workflow: read PDF -> extract facts -> check rules -> report."""

import argparse
from pathlib import Path

from procurement.evaluation import evaluate_samples
from procurement.financial_details import extract_financial_details
from procurement.pdf_text import PdfReadError, read_pdf
from procurement.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.report import render_report
from procurement.rules import check_rules
from procurement.supplier_details import extract_supplier_details
from procurement.terms import extract_terms


def review_document(path, items, policy):
    document = read_pdf(path)
    fields = {}
    fields.update(extract_supplier_details(document))
    fields.update(extract_financial_details(document))
    fields.update(extract_terms(document))
    return check_rules(document, fields, items, policy)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path, help='Defaults to the ten supplied PDFs.')
    parser.add_argument('--output', type=Path, default=Path('reports/procurement-review.html'))
    parser.add_argument('--check-labels',action='store_true',help='Exit 1 if development results differ from manual labels.')
    arguments = parser.parse_args()
    if arguments.output.suffix.lower() != '.html':
        parser.error('--output must be an .html report path')
    try:
        items = load_purchase_request()
        policy = load_company_rules()
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot load references: {error}\n')
    paths = arguments.paths or sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))
    if not paths:
        parser.exit(1, 'No supplier PDFs found.\n')
    results, errors = [], []
    for path in paths:
        try:
            result = review_document(path, items, policy)
            results.append(result)
            print(f'{path.name}: {result.verdict}')
        except PdfReadError as error:
            errors.append((str(path), str(error)))
            print(f'{path.name}: Needs a person to check - {error}')
    evaluation = evaluate_samples(results)
    if evaluation['total']:
        print(f"Development samples - Verdicts: {evaluation['verdict_matches']}/{evaluation['total']}; "
              f"Rule sets: {evaluation['rule_matches']}/{evaluation['total']}")
        print(f"Automatic decisions: {evaluation['automatic_decisions']}/{evaluation['total']}; "
              f"Conservative escalations: {evaluation['conservative_escalations']}; "
              f"Unsafe approvals: {evaluation['unsafe_approvals']}")
    try:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(render_report(results, errors, evaluation), encoding='utf-8')
    except OSError as error:
        parser.exit(1, f'Cannot write report: {error}\n')
    print(f'Report: {arguments.output.resolve()}')
    # Reject and review are valid business decisions, not execution failures.
    mismatch = evaluation['verdict_matches'] != evaluation['total'] or evaluation['rule_matches'] != evaluation['total']
    return int(bool(errors) or (arguments.check_labels and mismatch))


if __name__ == '__main__':
    raise SystemExit(main())
