"""Ask a person about unresolved facts and record source-backed corrections."""

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from procurement.shared.extraction import FACT_NAMES, ExtractionRun, read_fact, validate_fields
from procurement.shared.pdf_text import PdfDocument
from procurement.shared.rules import REVIEW, ReviewResult
from procurement.shared.runs import stamp_run


def build_questions(result: ReviewResult) -> list[dict]:
    """Each review finding becomes a question with real excerpts or inspected pages."""
    if result.verdict != REVIEW:
        return []
    questions = []
    for finding in result.findings:
        if finding.severity != REVIEW:
            continue
        fields = list(finding.field_names)
        questions.append({
            'code': finding.code, 'fields': fields,
            'question': f'Check the source document: {finding.reason} '
                        'Which extracted facts, if any, need correcting? '
                        'If the facts are accurate, this finding remains for a person to resolve.',
            'evidence': [asdict(excerpt) for excerpt in finding.evidence],
        })
    return questions


def response_template(run: ExtractionRun) -> dict:
    """A copyable response starter; placeholders are deliberately not a valid review."""
    return {'source_run_id': run.metadata['run_id'],
            'document_sha256': run.metadata['document_sha256'],
            'reviewer': '', 'reviewed_at': '', 'reason': '', 'corrections': {}}


def apply_corrections(run: ExtractionRun, document: PdfDocument, response: dict) -> ExtractionRun:
    """Validate an attributed response, then create a new run without mutating its source."""
    expected = {'source_run_id', 'document_sha256', 'reviewer', 'reviewed_at', 'reason', 'corrections'}
    if not isinstance(response, dict) or set(response) != expected:
        raise ValueError('Review response must contain exactly the documented keys; no policy or verdict overrides.')
    for name in expected - {'corrections'}:
        if not isinstance(response[name], str) or not response[name].strip():
            raise ValueError(f'Review response requires {name}.')
    # Recheck the live PDF, not just the hash claimed by the response.
    stamp_run(run, document)
    for name, source_name in (('source_run_id', 'run_id'), ('document_sha256', 'document_sha256')):
        if response[name] != run.metadata.get(source_name):
            raise ValueError(f'Review response {name} does not match the saved run.')
    try:
        reviewed_at = datetime.fromisoformat(response['reviewed_at'])
    except ValueError as error:
        raise ValueError('reviewed_at must be an ISO 8601 timestamp with a timezone offset.') from error
    if reviewed_at.utcoffset() is None:
        raise ValueError('reviewed_at must include a timezone offset.')
    corrections = response['corrections']
    if not isinstance(corrections, dict) or not corrections or not set(corrections) <= set(FACT_NAMES):
        raise ValueError('corrections must contain one or more known fact names.')
    fields = dict(run.fields)
    for name, data in corrections.items():
        fields[name] = read_fact(data)
    checked = validate_fields(fields, document)
    # A malformed correction is rejected, not silently converted to an unresolved fact.
    for issue in checked.issues:
        if issue.split(':', 1)[0] in corrections:
            raise ValueError(f'Invalid correction: {issue}')
    # Resolved field errors can be replaced; unrelated extraction/document errors remain.
    retained = tuple(issue for issue in run.issues if issue.split(':', 1)[0] not in corrections)
    issues = tuple(dict.fromkeys(retained + checked.issues))
    metadata = {key: value for key, value in run.metadata.items()
                if key not in ('run_id', 'created_at', 'artifact_path', 'elapsed_seconds')}
    metadata.update({'run_id': str(uuid4()), 'created_at': datetime.now(timezone.utc).isoformat(),
                     'source_run_id': run.metadata['run_id'], 'assisted': True,
                     'status': 'needs_review' if issues else 'completed',
                     'human_review': {key: response[key] for key in ('reviewer', 'reviewed_at', 'reason')},
                     'corrections': {name: asdict(checked.fields[name]) for name in corrections},
                     'source_status': run.metadata.get('status')})
    return ExtractionRun(checked.fields, issues, metadata, run.raw_response)
