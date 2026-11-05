"""Run one sample PDF through one approach and print newline-delimited JSON events (used by the web API).

One process per request: a visitor's OpenRouter key lives only in this process's environment and is never printed.
"""
import json
import sys

from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.workflow import APPROACHES, describe, run_workflow


def emit(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def classify(text):
    t = text.lower()
    if '401' in t or ('invalid' in t and 'key' in t) or 'not set' in t:
        return 'invalid_key'
    if '402' in t or 'payment required' in t:
        return 'insufficient_credit'
    if '429' in t:
        return 'rate_limited'
    if 'timed out' in t or 'timeout' in t:
        return 'timeout'
    return 'provider_error'


def serialize(result, seconds):
    run = result.extraction_run
    meta = run.metadata if run else {}
    judge = meta.get('judge', {})
    cost = sum(((u or {}).get('cost') or 0) for u in (meta.get('usage'), judge.get('usage')))
    page = lambda evidence: [{'page': e.page_number, 'text': e.text[:400]} for e in evidence[:3]]
    return {
        'event': 'result', 'verdict': result.verdict, 'seconds': round(seconds, 2), 'costUsd': round(cost, 6),
        'models': {'extractor': meta.get('model'), 'judge': judge.get('model')},
        'findings': [{'code': f.code, 'severity': f.severity, 'reason': f.reason, 'facts': list(f.field_names),
                      'evidence': page(f.evidence)} for f in result.findings],
        'facts': [{'name': n, 'status': f.status, 'value': f.value, 'rawValue': f.raw_value,
                   'referenceEvent': f.reference_event, 'conditions': list(f.conditions),
                   'evidence': [{'page': e.page_number, 'text': e.text} for e in f.evidence],
                   'warnings': (meta.get('warnings') or {}).get(n, []), 'note': (meta.get('notes') or {}).get(n)}
                  for n, f in result.fields.items()],
    }


def main(sample, approach):
    if approach not in APPROACHES or not sample.startswith('supplier-pack-'):
        emit({'event': 'error', 'code': 'bad_request', 'message': 'Unknown sample or approach.'})
        return 1
    path = SAMPLE_DIRECTORY / f'{sample}.pdf'
    nodes = [s['node'] for s in describe(approach)]
    labels = {s['node']: s['label'] for s in describe(approach)}
    emit({'event': 'step', 'name': labels[nodes[0]], 'status': 'running'})

    def on_step(e):
        emit({'event': 'step', 'name': e['label'], 'status': 'completed', 'actor': e['actor'], 'seconds': round(e['seconds'], 2)})
        i = nodes.index(e['node'])
        if i + 1 < len(nodes):
            emit({'event': 'step', 'name': labels[nodes[i + 1]], 'status': 'running'})

    import time
    started = time.perf_counter()
    try:
        provider = 'ollama' if approach == 'approach1' else 'openrouter'
        result = run_workflow(path, load_purchase_request(), load_company_rules(), approach=approach,
                              provider=provider, timeout=240.0, on_step=on_step)
    except Exception as error:  # a failure is always reported, never raised past here
        emit({'event': 'error', 'code': classify(str(error)), 'message': str(error)[:300].replace('\n', ' ')})
        return 1
    run_meta = result.extraction_run.metadata if result.extraction_run else {}
    if run_meta.get('status') == 'failed':
        judge = run_meta.get('judge', {})
        text = judge.get('error') or run_meta.get('error') or 'The model call failed.'
        emit({'event': 'error', 'code': classify(text), 'message': text[:300]})
        return 1
    emit(serialize(result, time.perf_counter() - started))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
