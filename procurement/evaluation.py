"""Compare the development-visible samples with manually reviewed labels."""

import json

from procurement.references import PROJECT_ROOT, SAMPLE_DIRECTORY


def evaluate_samples(results: list) -> dict:
    labels = json.loads((PROJECT_ROOT / 'config/manual-labels.json').read_text(encoding='utf-8'))
    rows = []
    for result in results:
        path = result.document.source_path
        expected = labels['documents'].get(path.name)
        # Labels apply to the original sample paths, never to arbitrary uploads
        # that happen to share a filename. Evaluation never feeds the extractor.
        if expected is None or path.resolve() != (SAMPLE_DIRECTORY / path.name).resolve():
            continue
        codes = sorted({finding.code for finding in result.findings})
        rows.append({'file': path.name, 'expected': expected['verdict'], 'actual': result.verdict,
                     'verdict_match': result.verdict == expected['verdict'],
                     'rule_match': codes == sorted(expected['rules']),
                     'expected_rules': expected['rules'], 'actual_rules': codes})
    review = 'Needs a person to check'
    return {'total': len(rows), 'verdict_matches': sum(row['verdict_match'] for row in rows),
            'rule_matches': sum(row['rule_match'] for row in rows), 'rows': rows,
            'automatic_decisions':sum(row['actual'] != review for row in rows),
            'conservative_escalations':sum(row['actual'] == review and row['expected'] != review for row in rows),
            'unsafe_approvals':sum(row['actual'] == 'Approve' and row['expected'] != 'Approve' for row in rows),
            'incorrect_automatic_decisions':sum(row['actual'] != review and not row['verdict_match'] for row in rows),
            'note': labels['note']}
