"""Identify and save extractions without overwriting earlier evidence."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from procurement.shared.extraction import ExtractionRun, FACT_NAMES, parse_json, read_fact, validate_fields
from procurement.shared.pdf_text import PdfDocument


def stamp_run(run: ExtractionRun, document: PdfDocument) -> ExtractionRun:
    """Attach identity and an exact PDF hash; in-memory fixtures have no PDF hash."""
    digest = hashlib.sha256(document.source_path.read_bytes()).hexdigest() if document.source_path.is_file() else None
    metadata = dict(run.metadata)
    if 'document_sha256' in metadata and metadata['document_sha256'] != digest:
        raise ValueError('The source file changed during this run.')
    metadata.setdefault('run_id', str(uuid4()))
    metadata.setdefault('created_at', datetime.now(timezone.utc).isoformat())
    metadata['document_sha256'] = digest
    return replace(run, metadata=metadata)


def write_run(run: ExtractionRun, document: PdfDocument, directory: Path) -> Path:
    """Save original source, interpreted facts, issues and the raw AI answer."""
    run_id = UUID(run.metadata['run_id']).hex
    payload = {'document': asdict(document), **asdict(run)}
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{run_id}.json'
    with path.open('x', encoding='utf-8') as output:
        output.write(text)
    return path


def read_run(path: Path, document: PdfDocument) -> ExtractionRun:
    """Load the saved facts; validate them against the current original PDF."""
    payload = parse_json(Path(path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or set(payload) != {'document', 'fields', 'issues', 'metadata', 'raw_response'}:
        raise ValueError('Invalid saved extraction run.')
    metadata, fields, issues = payload['metadata'], payload['fields'], payload['issues']
    if (not isinstance(metadata, dict) or not isinstance(metadata.get('run_id'), str)
            or not isinstance(metadata.get('document_sha256'), str)
            or metadata.get('approach') not in ('approach1', 'approach2', 'approach3', 'approach4')
            or not isinstance(fields, dict) or set(fields) != set(FACT_NAMES)
            or not isinstance(issues, list) or not all(isinstance(issue, str) for issue in issues)
            or (payload['raw_response'] is not None and not isinstance(payload['raw_response'], str))):
        raise ValueError('Invalid saved extraction fields or metadata.')
    UUID(metadata['run_id'])
    checked = validate_fields({name: read_fact(data) for name, data in fields.items()}, document)
    run = ExtractionRun(checked.fields, tuple(dict.fromkeys(tuple(issues) + checked.issues)),
                        metadata, payload['raw_response'])
    return stamp_run(run, document)
