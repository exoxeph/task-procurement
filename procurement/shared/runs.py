"""Identify and save extractions without overwriting earlier evidence."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from procurement.shared.extraction import ExtractionRun
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
