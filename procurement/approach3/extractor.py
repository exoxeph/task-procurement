"""One local Ollama extraction call, followed by strict response validation."""

from dataclasses import replace
from http.client import HTTPException
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from procurement.approach2.schema import OUTPUT_SCHEMA, SCHEMA_VERSION, parse_json, parse_response
from procurement.shared.extraction import ExtractedField, ExtractionRun, FACT_NAMES
from procurement.shared.pdf_text import PdfDocument
from procurement.shared.runs import stamp_run


OPTIONS = {'temperature': 0, 'num_ctx': 16384, 'num_predict': 8192}
PROMPT_PATH = Path(__file__).with_name('prompt.txt')


class NoRedirects(HTTPRedirectHandler):
    """A validated local URL must never redirect document data elsewhere."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        raise ValueError('Ollama redirects are not allowed.')


# Do not inherit HTTP_PROXY/HTTPS_PROXY from the surrounding environment.
urlopen = build_opener(ProxyHandler({}), NoRedirects()).open


def _local_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if (parsed.scheme not in ('http', 'https') or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('Use a local Ollama base URL without credentials or a path.')
    return endpoint.rstrip('/')


def build_request(document: PdfDocument, model: str) -> dict:
    """Keep original page text separate from derived table reading aids."""
    prompt = PROMPT_PATH.read_text(encoding='utf-8')
    pages = []
    for page in document.pages:
        tables = [{'headers': list(table.headers), 'rows': [list(row) for row in table.rows]}
                  for table in page.tables]
        pages.append({'page_number': page.page_number, 'original_text': page.text, 'tables': tables})
    document_input = {'pages': pages, 'read_issues': list(document.issues)}
    return {'model': model, 'stream': False, 'format': OUTPUT_SCHEMA, 'options': dict(OPTIONS),
            'messages': [
                {'role': 'system', 'content': prompt + '\nRequired JSON schema:\n' + json.dumps(OUTPUT_SCHEMA)},
                {'role': 'user', 'content': json.dumps(document_input, ensure_ascii=False)},
            ]}


def _read_http(request: Request, timeout: float) -> str:
    with urlopen(request, timeout=timeout) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('Ollama response exceeds the supported size.')
    return data.decode('utf-8')


def _server_metadata(endpoint: str, model: str, timeout: float) -> dict:
    """Metadata requests are optional; they never retry the extraction call."""
    metadata = {'ollama_version': None, 'model_digest': None, 'metadata_warnings': []}
    for route in ('version', 'tags'):
        try:
            response = json.loads(_read_http(Request(endpoint + '/api/' + route), min(timeout, 3)))
            if route == 'version':
                metadata['ollama_version'] = response['version']
            else:
                metadata['model_digest'] = next((entry.get('digest') for entry in response['models']
                                                  if entry.get('name') == model), None)
        except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError) as error:
            metadata['metadata_warnings'].append(f'{route}: {error}')
    return metadata


def extract_document(document: PdfDocument, *, model='qwen2.5:7b',
                     endpoint='http://localhost:11434', timeout=180.0) -> ExtractionRun:
    """Return validated facts or a visible failed run; never guess or switch models."""
    started = perf_counter()
    metadata = {'approach': 'approach2', 'model': model, 'schema_version': SCHEMA_VERSION,
                'options': dict(OPTIONS), 'status': 'failed'}
    raw, provider_text = None, None
    try:
        endpoint = _local_endpoint(endpoint)
        metadata['endpoint'] = endpoint
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Timeout must be a positive finite number.')
        request_body = build_request(document, model)
        metadata['prompt_sha256'] = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()
        metadata['schema_sha256'] = hashlib.sha256(json.dumps(OUTPUT_SCHEMA, sort_keys=True).encode()).hexdigest()
        metadata['request_sha256'] = hashlib.sha256(json.dumps(request_body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        # Conservative byte-based guard for these local text models. Token counts
        # returned by the service are checked too; neither is semantic verification.
        input_bytes = len(json.dumps(request_body['messages'], ensure_ascii=False).encode('utf-8'))
        metadata['input_bytes'] = input_bytes
        if input_bytes + 512 > OPTIONS['num_ctx']:
            raise ValueError('Full document exceeds the supported input budget; nothing was truncated or sent.')
        request = Request(endpoint + '/api/chat', data=json.dumps(request_body).encode('utf-8'),
                          headers={'Content-Type': 'application/json'}, method='POST')
        provider_text = _read_http(request, timeout)
        response = parse_json(provider_text)
        if not isinstance(response, dict):
            raise ValueError('Ollama returned a non-object response.')
        raw = response.get('message', {}).get('content')
        metadata['usage'] = {name: response.get(name) for name in
                             ('prompt_eval_count', 'eval_count', 'total_duration', 'load_duration',
                              'prompt_eval_duration', 'eval_duration')}
        if response.get('model') != model:
            raise ValueError('Ollama returned a different model; no automatic fallback is allowed.')
        if response.get('done') is not True or response.get('done_reason') != 'stop':
            raise ValueError('Ollama did not complete normally; response may be truncated.')
        for name in ('prompt_eval_count', 'eval_count'):
            if type(response.get(name)) is not int or response[name] < 0:
                raise ValueError('Ollama did not return valid token counts.')
        if (response['prompt_eval_count'] >= OPTIONS['num_ctx'] - OPTIONS['num_predict']
                or response['eval_count'] >= OPTIONS['num_predict']
                or response['prompt_eval_count'] + response['eval_count'] >= OPTIONS['num_ctx']):
            raise ValueError('Ollama token counts indicate context/output pressure; review required.')
        if not isinstance(raw, str):
            raise ValueError('Ollama did not return a text answer.')
        run = parse_response(raw, document)
        metadata.update(_server_metadata(endpoint, model, timeout))
        issues = tuple(dict.fromkeys(document.issues + run.issues))
        metadata['status'] = 'needs_review' if issues else 'completed'
        run = replace(run, issues=issues)
    except (OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError, URLError) as error:
        # Keep the original answer for inspection, including malformed JSON.
        if isinstance(error, HTTPError):
            provider_text = error.read(65536).decode('utf-8', errors='replace')
        metadata['error'] = str(error)
        if provider_text is not None:
            metadata['provider_response'] = provider_text
        run = ExtractionRun({name: ExtractedField(None, 'unrecognized', ()) for name in FACT_NAMES},
                            tuple(document.issues) + (f'Ollama extraction failed: {error}',), {}, raw)
    metadata['elapsed_seconds'] = perf_counter() - started
    return stamp_run(replace(run, metadata=metadata), document)
