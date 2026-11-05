"""Compare the development-visible samples with manually reviewed labels."""

import json
from pathlib import Path

from procurement.shared.references import PROJECT_ROOT, SAMPLE_DIRECTORY


def evaluate_samples(results: list, errors=()) -> dict:
    labels = json.loads((PROJECT_ROOT / 'config/manual-labels.json').read_text(encoding='utf-8'))
    rows = []
    assisted_excluded = 0
    for result in results:
        if result.extraction_run is not None and result.extraction_run.metadata.get('assisted'):
            assisted_excluded += 1
            continue
        path = result.document.source_path
        expected = labels['documents'].get(path.name)
        # Labels apply to the original sample paths, never to arbitrary uploads
        # that happen to share a filename. Evaluation never feeds the extractor.
        if expected is None or path.resolve() != (SAMPLE_DIRECTORY / path.name).resolve():
            continue
        codes = sorted({finding.code for finding in result.findings})
        failed = result.extraction_run is not None and result.extraction_run.metadata.get('status') == 'failed'
        rows.append({'file': path.name, 'expected': expected['verdict'], 'actual': result.verdict,
                     'verdict_match': not failed and result.verdict == expected['verdict'],
                     'rule_match': not failed and codes == sorted(expected['rules']),
                     'input_error': False, 'extraction_error': failed,
                     'expected_rules': expected['rules'], 'actual_rules': codes})
    for filename, error in errors:
        path = Path(filename)
        expected = labels['documents'].get(path.name)
        if expected is None or path.resolve() != (SAMPLE_DIRECTORY / path.name).resolve():
            continue
        rows.append({'file': path.name, 'expected': expected['verdict'], 'actual': 'Needs a person to check',
                     'verdict_match': False, 'rule_match': False, 'input_error': True, 'extraction_error': False,
                     'expected_rules': expected['rules'], 'actual_rules': [], 'error': str(error)})
    review = 'Needs a person to check'
    return {'total': len(rows), 'assisted_excluded': assisted_excluded,
            'verdict_matches': sum(row['verdict_match'] for row in rows),
            'rule_matches': sum(row['rule_match'] for row in rows), 'rows': rows,
            'input_failures': sum(row['input_error'] for row in rows),
            'extraction_failures': sum(row['extraction_error'] for row in rows),
            'automatic_decisions':sum(row['actual'] != review and not row['input_error'] and not row['extraction_error'] for row in rows),
            'conservative_escalations':sum(row['actual'] == review and row['expected'] != review
                                           and not row['input_error'] and not row['extraction_error'] for row in rows),
            'unsafe_approvals':sum(row['actual'] == 'Approve' and row['expected'] != 'Approve' for row in rows),
            'incorrect_automatic_decisions':sum(row['actual'] != review and not row['verdict_match'] for row in rows),
            'note': labels['note']}
