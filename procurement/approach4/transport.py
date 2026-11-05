"""One place for the model call of both approach 4 agents: local Ollama or OpenRouter.

Returns the answer text and call details, and raises on anything abnormal (truncation,
refusal, error object, wrong model) so callers fail closed. Document text only ever goes to
the loopback Ollama server or to OpenRouter, never anywhere else, and the OpenRouter key is
sent in a header only.
"""

import hashlib
import json
from urllib.request import Request

from procurement.approach2.extractor import OPTIONS as OLLAMA_OPTIONS, _local_endpoint, urlopen as ollama_urlopen
from procurement.approach2.openrouter import URL, provider_preferences, sampling_options, urlopen
from procurement.shared.extraction import parse_json

PROVIDERS = ('ollama', 'openrouter')
MAX_RESPONSE_BYTES = 32 * 1024 * 1024


def chat_json(provider, model, messages, schema, *, schema_name, key='', endpoint='http://localhost:11434',
              timeout=180.0, max_tokens=8192):
    """Return (answer_text, details). details has served_by, usage and request_sha256."""
    if provider == 'ollama':
        num_ctx = OLLAMA_OPTIONS['num_ctx']
        body = {'model': model, 'stream': False, 'format': schema, 'messages': messages,
                'options': {'temperature': 0, 'num_ctx': num_ctx, 'num_predict': max_tokens}}
        request = Request(_local_endpoint(endpoint) + '/api/chat', data=json.dumps(body).encode('utf-8'),
                          headers={'Content-Type': 'application/json'}, method='POST')
        opener = ollama_urlopen
    elif provider == 'openrouter':
        if not key:
            raise ValueError('OPENROUTER_API_KEY is not set. Put it in .env or the environment.')
        body = {'model': model, 'messages': messages, **sampling_options(model), 'max_tokens': max_tokens,
                'response_format': {'type': 'json_schema',
                                    'json_schema': {'name': schema_name, 'strict': True, 'schema': schema}},
                'provider': provider_preferences()}
        request = Request(URL, data=json.dumps(body).encode('utf-8'), method='POST',
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        opener = urlopen
    else:
        raise ValueError(f'Unknown provider: {provider}')
    details = {'request_sha256': hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
    with opener(request, timeout=timeout) as reply:
        data = reply.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError('Model response exceeds the supported size.')
    response = parse_json(data.decode('utf-8'))
    if not isinstance(response, dict):
        raise ValueError('Model service returned a non-object response.')
    if provider == 'ollama':
        details['served_by'] = 'ollama'
        details['usage'] = {name: response.get(name) for name in ('prompt_eval_count', 'eval_count')}
        text = (response.get('message') or {}).get('content')
        if response.get('model') != model:
            raise ValueError('Ollama returned a different model; no automatic fallback is allowed.')
        if response.get('done') is not True or response.get('done_reason') != 'stop':
            raise ValueError('Ollama did not complete normally; response may be truncated.')
        counts = [response.get(name) for name in ('prompt_eval_count', 'eval_count')]
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError('Ollama did not return valid token counts.')
        if (counts[1] >= max_tokens or sum(counts) >= OLLAMA_OPTIONS['num_ctx']):
            raise ValueError('Ollama token counts indicate context/output pressure; review required.')
    else:
        details['served_by'] = response.get('provider')
        details['usage'] = response.get('usage')
        if isinstance(response.get('error'), dict):
            raise ValueError(f"OpenRouter error: {response['error'].get('message', 'unknown')}")
        choices = response.get('choices')
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError('OpenRouter returned no single answer.')
        if choices[0].get('finish_reason') != 'stop':
            raise ValueError(f"OpenRouter did not finish normally: {choices[0].get('finish_reason')}; "
                             'response may be truncated.')
        text = (choices[0].get('message') or {}).get('content')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('The model did not return a text answer.')
    return text, details
