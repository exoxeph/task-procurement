"""Approach 3 through OpenRouter: same prompt, schema and validation as the local model.

Only the document text leaves this machine. The API key is read from the
environment (.env), sent in a header, and never stored in metadata or hashes.
"""

from dataclasses import replace
from http.client import HTTPException
import hashlib
import json
import math
import os
import re
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from procurement.approach3.extractor import NoRedirects, PROMPT_PATH, build_request
from procurement.approach3.schema import OUTPUT_SCHEMA, SCHEMA_VERSION, parse_json, parse_response
from procurement.shared.extraction import ExtractedField, ExtractionRun, FACT_NAMES
from procurement.shared.pdf_text import PdfDocument
from procurement.shared.runs import stamp_run


DEFAULT_MODEL = 'qwen/qwen3-14b'
URL = 'https://openrouter.ai/api/v1/chat/completions'
OPTIONS = {'temperature': 0, 'max_tokens': 16384}

# Never inherit proxies, and never follow a redirect with document data.
urlopen = build_opener(ProxyHandler({}), NoRedirects()).open


def provider_preferences() -> dict:
    ignored = [name.strip() for name in os.environ.get('OPENROUTER_IGNORE_PROVIDERS', '').split(',') if name.strip()]
    return {'require_parameters': True, **({'ignore': ignored} if ignored else {})}


def build_openrouter_request(document: PdfDocument, model: str) -> dict:
    """Reuse approach 3's exact prompt and page input; only the envelope differs."""
    messages = build_request(document, model)['messages']
    return {'model': model, 'messages': messages, **OPTIONS,
            'response_format': {'type': 'json_schema',
                                'json_schema': {'name': 'procurement_facts', 'strict': True, 'schema': OUTPUT_SCHEMA}},
            # Route only to backends that actually honor the schema, minus any named in
            # OPENROUTER_IGNORE_PROVIDERS (comma separated), for example one that keeps failing.
            'provider': provider_preferences()}


def _answer_text(response: dict) -> str:
    if isinstance(response.get('error'), dict):
        raise ValueError(f"OpenRouter error: {response['error'].get('message', 'unknown')}")
    choices = response.get('choices')
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError('OpenRouter returned no single answer.')
    choice = choices[0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError(f"OpenRouter did not finish normally: {choice.get('finish_reason')}; response may be truncated.")
    text = (choice.get('message') or {}).get('content')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('OpenRouter did not return a text answer.')
    return text


def extract_document(document: PdfDocument, *, model=None, timeout=180.0) -> ExtractionRun:
    """Return validated facts or a visible failed run; never guess or switch models."""
    started = perf_counter()
    model = model or os.environ.get('OPENROUTER_MODEL') or DEFAULT_MODEL
    metadata = {'approach': 'approach3', 'provider': 'openrouter', 'model': model,
                'schema_version': SCHEMA_VERSION, 'options': dict(OPTIONS), 'status': 'failed'}
    key = os.environ.get('OPENROUTER_API_KEY', '')
    raw, provider_text = None, None
    try:
        if not key:
            raise ValueError('OPENROUTER_API_KEY is not set. Put it in .env or the environment.')
        if not re.fullmatch(r'[A-Za-z0-9._:/-]+', model):
            raise ValueError('Model slug may only contain letters, digits and . _ : / -')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Timeout must be a positive finite number.')
        body = build_openrouter_request(document, model)
        metadata['prompt_sha256'] = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()
        metadata['schema_sha256'] = hashlib.sha256(json.dumps(OUTPUT_SCHEMA, sort_keys=True).encode()).hexdigest()
        metadata['request_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        request = Request(URL, data=json.dumps(body).encode('utf-8'), method='POST',
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urlopen(request, timeout=timeout) as reply:
            data = reply.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('OpenRouter response exceeds the supported size.')
        provider_text = data.decode('utf-8')
        response = parse_json(provider_text)
        if not isinstance(response, dict):
            raise ValueError('OpenRouter returned a non-object response.')
        usage = response.get('usage') or {}
        metadata['usage'] = {name: usage.get(name) for name in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
        if response.get('model') and response['model'] != model:
            metadata['served_model'] = response['model']
        if response.get('provider'):
            metadata['served_by'] = response['provider']
        raw = _answer_text(response)
        run = parse_response(raw, document)
        issues = tuple(dict.fromkeys(document.issues + run.issues))
        metadata['status'] = 'needs_review' if issues else 'completed'
        run = replace(run, issues=issues)
    except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError, URLError) as error:
        if isinstance(error, HTTPError):
            provider_text = error.read(65536).decode('utf-8', errors='replace')
        message = str(error).replace(key, '[redacted]') if key else str(error)
        metadata['error'] = message
        if provider_text is not None:
            metadata['provider_response'] = provider_text.replace(key, '[redacted]') if key else provider_text
        run = ExtractionRun({name: ExtractedField(None, 'unrecognized', ()) for name in FACT_NAMES},
                            tuple(document.issues) + (f'OpenRouter extraction failed: {message}',), {}, raw)
    metadata['elapsed_seconds'] = perf_counter() - started
    return stamp_run(replace(run, metadata=metadata), document)
