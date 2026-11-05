"""Approach 2 through the Gemini API: same prompt, schema and validation as the local model.

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

from procurement.approach2.extractor import NoRedirects, PROMPT_PATH, build_request
from procurement.approach2.schema import OUTPUT_SCHEMA, SCHEMA_VERSION, parse_json, parse_response
from procurement.shared.extraction import ExtractedField, ExtractionRun, FACT_NAMES
from procurement.shared.pdf_text import PdfDocument
from procurement.shared.runs import stamp_run


DEFAULT_MODEL = 'gemini-3.8-flash'
HOST = 'https://generativelanguage.googleapis.com'
OPTIONS = {'temperature': 0, 'maxOutputTokens': 16384}

# Never inherit proxies, and never follow a redirect with document data.
urlopen = build_opener(ProxyHandler({}), NoRedirects()).open


def build_gemini_request(document: PdfDocument, model: str) -> dict:
    """Reuse approach 2's exact prompt and page input; only the envelope differs."""
    messages = build_request(document, model)['messages']
    return {'systemInstruction': {'parts': [{'text': messages[0]['content']}]},
            'contents': [{'role': 'user', 'parts': [{'text': messages[1]['content']}]}],
            'generationConfig': {**OPTIONS, 'responseMimeType': 'application/json',
                                 'responseJsonSchema': OUTPUT_SCHEMA}}


def _answer_text(response: dict) -> str:
    candidates = response.get('candidates')
    if not isinstance(candidates, list) or len(candidates) != 1:
        reason = (response.get('promptFeedback') or {}).get('blockReason')
        raise ValueError(f'Gemini returned no answer{f" (blocked: {reason})" if reason else ""}.')
    candidate = candidates[0]
    if candidate.get('finishReason') != 'STOP':
        raise ValueError(f"Gemini did not finish normally: {candidate.get('finishReason')}; response may be truncated.")
    parts = (candidate.get('content') or {}).get('parts') or []
    # Skip any reasoning summaries; only the answer part is the JSON.
    text = ''.join(part.get('text', '') for part in parts if not part.get('thought'))
    if not text.strip():
        raise ValueError('Gemini did not return a text answer.')
    return text


def extract_document(document: PdfDocument, *, model=None, timeout=180.0) -> ExtractionRun:
    """Return validated facts or a visible failed run; never guess or switch models."""
    started = perf_counter()
    model = model or os.environ.get('GEMINI_MODEL') or DEFAULT_MODEL
    metadata = {'approach': 'approach2', 'provider': 'gemini', 'model': model,
                'schema_version': SCHEMA_VERSION, 'options': dict(OPTIONS), 'status': 'failed'}
    key = os.environ.get('GEMINI_API_KEY', '')
    raw, provider_text = None, None
    try:
        if not key:
            raise ValueError('GEMINI_API_KEY is not set. Put it in .env or the environment.')
        if not re.fullmatch(r'[A-Za-z0-9._-]+', model):
            raise ValueError('Model name may only contain letters, digits, dot, dash and underscore.')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Timeout must be a positive finite number.')
        body = build_gemini_request(document, model)
        metadata['prompt_sha256'] = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()
        metadata['schema_sha256'] = hashlib.sha256(json.dumps(OUTPUT_SCHEMA, sort_keys=True).encode()).hexdigest()
        metadata['request_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        request = Request(f'{HOST}/v1beta/models/{model}:generateContent', data=json.dumps(body).encode('utf-8'),
                          headers={'Content-Type': 'application/json', 'x-goog-api-key': key}, method='POST')
        with urlopen(request, timeout=timeout) as reply:
            data = reply.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('Gemini response exceeds the supported size.')
        provider_text = data.decode('utf-8')
        response = parse_json(provider_text)
        if not isinstance(response, dict):
            raise ValueError('Gemini returned a non-object response.')
        usage = response.get('usageMetadata') or {}
        metadata['usage'] = {name: usage.get(name) for name in
                             ('promptTokenCount', 'candidatesTokenCount', 'thoughtsTokenCount', 'totalTokenCount')}
        if response.get('modelVersion') and not str(response['modelVersion']).startswith(model):
            metadata['served_model_version'] = response['modelVersion']
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
                            tuple(document.issues) + (f'Gemini extraction failed: {message}',), {}, raw)
    metadata['elapsed_seconds'] = perf_counter() - started
    return stamp_run(replace(run, metadata=metadata), document)
