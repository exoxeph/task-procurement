"""Agent 1: step-by-step fact extraction, on local Ollama or OpenRouter (key from .env, header only)."""

from dataclasses import replace
from http.client import HTTPException
import hashlib
import json
import math
import os
from pathlib import Path
import re
from time import perf_counter
from urllib.error import HTTPError, URLError

from procurement.approach4.schema import OUTPUT_SCHEMA, SCHEMA_VERSION, parse_response
from procurement.approach4.transport import PROVIDERS, chat_json
from procurement.shared.extraction import ExtractedField, ExtractionRun, FACT_NAMES
from procurement.shared.pdf_text import PdfDocument
from procurement.shared.runs import stamp_run

DEFAULT_MODELS = {'ollama': 'qwen3:14b', 'openrouter': 'qwen/qwen3-14b'}
PROMPT_PATH = Path(__file__).with_name('prompt.txt')
MAX_TOKENS = {'ollama': 8192, 'openrouter': 16384}


def build_messages(document: PdfDocument) -> list:
    pages = [{'page_number': page.page_number, 'original_text': page.text,
              'tables': [{'headers': list(table.headers), 'rows': [list(row) for row in table.rows]}
                         for table in page.tables]} for page in document.pages]
    document_input = {'pages': pages, 'read_issues': list(document.issues)}
    system = (PROMPT_PATH.read_text(encoding='utf-8') + '\nRequired JSON schema:\n'
              + json.dumps(OUTPUT_SCHEMA, separators=(',', ':')))
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(document_input, ensure_ascii=False)}]


def extract_document(document: PdfDocument, *, model=None, timeout=180.0, provider='openrouter',
                     endpoint='http://localhost:11434') -> ExtractionRun:
    """Return the facts with warnings attached, or a visible failed run; never guess."""
    started = perf_counter()
    if model is None:
        model = (os.environ.get('OPENROUTER_MODEL') if provider == 'openrouter' else None) or DEFAULT_MODELS.get(provider)
    metadata = {'approach': 'approach4', 'provider': provider, 'model': model,
                'schema_version': SCHEMA_VERSION, 'status': 'failed'}
    key = os.environ.get('OPENROUTER_API_KEY', '') if provider == 'openrouter' else ''
    raw = provider_text = None
    try:
        if provider not in PROVIDERS:
            raise ValueError(f'Unknown provider: {provider}')
        if not re.fullmatch(r'[A-Za-z0-9._:/-]+', model or ''):
            raise ValueError('Model name may only contain letters, digits and . _ : / -')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Timeout must be a positive finite number.')
        metadata['prompt_sha256'] = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()
        raw, details = chat_json(provider, model, build_messages(document), OUTPUT_SCHEMA,
                                 schema_name='procurement_facts', key=key, endpoint=endpoint,
                                 timeout=timeout, max_tokens=MAX_TOKENS[provider])
        metadata.update(details)
        run = parse_response(raw, document)
        issues = tuple(dict.fromkeys(document.issues + run.issues))
        metadata.update(run.metadata)
        metadata['status'] = 'needs_review' if issues or run.metadata['warnings'] else 'completed'
        run = replace(run, issues=issues)
    except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError, URLError) as error:
        if isinstance(error, HTTPError):
            provider_text = error.read(65536).decode('utf-8', errors='replace')
        redact = key or '\0'
        message = str(error).replace(redact, '[redacted]')
        metadata['error'] = message
        if provider_text is not None:
            metadata['provider_response'] = provider_text.replace(redact, '[redacted]')
        run = ExtractionRun({name: ExtractedField(None, 'unrecognized', ()) for name in FACT_NAMES},
                            tuple(document.issues) + (f'Extraction failed: {message}',), {}, raw)
    metadata['elapsed_seconds'] = perf_counter() - started
    return stamp_run(replace(run, metadata=metadata), document)
