"""Compare the development-visible samples with manually reviewed labels."""

import json
import hashlib
from pathlib import Path

from procurement.shared.extraction import NUMERIC_FIELDS, read_number
from procurement.shared.references import PROJECT_ROOT, SAMPLE_DIRECTORY


def evaluate_samples(results: list, errors=()) -> dict:
    labels = json.loads((PROJECT_ROOT / 'config/manual-labels.json').read_text(encoding='utf-8'))
    rows = []
    assisted_excluded = 0
    elapsed_seconds = 0.0
    prompt_tokens = output_tokens = 0
    run_ids = []
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
        if result.extraction_run:
            metadata = result.extraction_run.metadata
            elapsed_seconds += metadata.get('elapsed_seconds', 0)
            usage = metadata.get('usage', {})
            prompt_tokens += usage.get('prompt_eval_count') or 0
            output_tokens += usage.get('eval_count') or 0
            run_ids.append(metadata.get('run_id'))
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
    confusion = {expected: {actual: 0 for actual in ('Approve', 'Reject', review, 'Failed')}
                 for expected in ('Approve', 'Reject', review)}
    for row in rows:
        actual = 'Failed' if row['input_error'] or row['extraction_error'] else row['actual']
        confusion[row['expected']][actual] += 1
    return {'total': len(rows), 'assisted_excluded': assisted_excluded,
            'verdict_matches': sum(row['verdict_match'] for row in rows),
            'rule_matches': sum(row['rule_match'] for row in rows), 'rows': rows,
            'input_failures': sum(row['input_error'] for row in rows),
            'extraction_failures': sum(row['extraction_error'] for row in rows),
            'automatic_decisions':sum(row['actual'] != review and not row['input_error'] and not row['extraction_error'] for row in rows),
            'conservative_escalations':sum(row['actual'] == review and row['expected'] != review
                                           and not row['input_error'] and not row['extraction_error'] for row in rows),
            'unsafe_approvals':sum(row['actual'] == 'Approve' and row['expected'] != 'Approve' for row in rows),
            'wrong_rejections':sum(row['actual'] == 'Reject' and row['expected'] != 'Reject' for row in rows),
            'review_count':sum(row['actual'] == review and not row['input_error'] and not row['extraction_error'] for row in rows),
            'elapsed_seconds': elapsed_seconds, 'prompt_tokens': prompt_tokens, 'output_tokens': output_tokens,
            'run_ids': run_ids, 'confusion': confusion,
            'incorrect_automatic_decisions':sum(row['actual'] != review and not row['verdict_match'] for row in rows),
            'note': labels['note']}


def _normalized(value, name):
    if value is None:
        return None
    if name in NUMERIC_FIELDS:
        return read_number(value, name)
    return ' '.join(value.split()).casefold().rstrip('.')


def _fact_matches(fact, expected, name):
    """Compare meaning-bearing attributes; a correct number alone is insufficient."""
    if fact.status not in expected['statuses']:
        return False
    if _normalized(fact.value, name) != _normalized(expected['value'], name):
        return False
    if name.endswith('_days') and fact.reference_event != expected.get('reference_event'):
        return False
    conditions = sorted(_normalized(value, '') for value in fact.conditions)
    allowed = [sorted(_normalized(value, '') for value in group) for group in expected['conditions']]
    if conditions not in allowed:
        return False
    for attribute in ('minimum_value', 'maximum_value'):
        actual = getattr(fact, attribute)
        wanted = expected.get(attribute)
        if actual is None and name in NUMERIC_FIELDS and fact.status == 'found':
            actual = fact.value
        if wanted is None and name in NUMERIC_FIELDS:
            wanted = expected['value']
        if _normalized(actual, name) != _normalized(wanted, name):
            return False
    return True


def evaluate_fields(results: list, labels: dict, errors=()) -> dict:
    """Score all audited facts per attempted original sample, including failures."""
    rows, disputed, assisted_excluded = [], 0, 0
    attempts = [(result.document.source_path, result) for result in results]
    attempts.extend((Path(path), None) for path, _ in errors)
    for path, result in attempts:
        if result and result.extraction_run and result.extraction_run.metadata.get('assisted'):
            assisted_excluded += 1
            continue
        expected_document = labels['documents'].get(path.name)
        if expected_document is None or path.resolve() != (SAMPLE_DIRECTORY / path.name).resolve():
            continue
        # A changed source must not borrow fact labels from the original PDF.
        hash_matches = (path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()
                        == expected_document['document_sha256'])
        failed = result is None or (result.extraction_run and result.extraction_run.metadata.get('status') == 'failed')
        pages = {page.page_number: page.text for page in result.document.pages} if result else {}
        for name, expected in expected_document['facts'].items():
            if expected.get('disputed'):
                disputed += 1
                continue
            fact = result.fields.get(name) if result else None
            traced = bool(fact and fact.evidence and all(
                excerpt.page_number in pages and excerpt.text.strip() and excerpt.text in pages[excerpt.page_number]
                for excerpt in fact.evidence))
            try:
                match = bool(hash_matches and not failed and fact and _fact_matches(fact, expected, name)
                             and (fact.status != 'found' or traced))
            except (ValueError, TypeError):
                match = False
            rows.append({'file': path.name, 'field': name, 'match': match,
                         'expected': expected, 'actual': None if fact is None else {
                             'value': fact.value, 'status': fact.status, 'reference_event': fact.reference_event,
                             'conditions': list(fact.conditions), 'minimum_value': fact.minimum_value,
                             'maximum_value': fact.maximum_value},
                         'source_traced': traced, 'failed': bool(failed), 'document_hash_matches': hash_matches})
    by_field = {}
    for row in rows:
        counts = by_field.setdefault(row['field'], {'matches': 0, 'total': 0})
        counts['total'] += 1
        counts['matches'] += int(row['match'])
    return {'total': len(rows), 'matches': sum(row['match'] for row in rows), 'by_field': by_field,
            'disputed': disputed, 'assisted_excluded': assisted_excluded, 'rows': rows,
            'note': labels.get('audit', 'Source-audited development labels; not independent testing.')}
