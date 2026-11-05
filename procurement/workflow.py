"""The fixed workflow, as four small LangGraph graphs: one per approach.

Every graph is a straight line from START to END. There are no branches, no loops and no
tools, and no model ever chooses the next step: the code does. The AI only fills in the
answer inside the extract step (and, in approach 4, the judge step). Any failure is
carried forward as data and ends as "Needs a person to check".

    approach 1   read -> extract (Python)    -> validate           -> rules -> persist -> report
    approach 2   read -> extract (AI)        -> validate           -> rules -> persist -> report
    approach 3   read -> extract (AI, typed) -> validate           -> rules -> persist -> report
    approach 4   read -> extract (AI reader) -> annotate warnings  -> judge -> persist -> report

The node bodies are the same code that used to live in review_document; only the shape
changed. A graph can be printed as a diagram:  python -m procurement.workflow --mermaid approach4
"""

import argparse
from dataclasses import replace
from functools import lru_cache
import os
from pathlib import Path
from time import perf_counter
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from procurement.shared.extraction import FACT_NAMES, Evidence, parse_json, validate_fields
from procurement.shared.human_review import apply_corrections
from procurement.shared.pdf_text import read_pdf
from procurement.shared.rules import REVIEW, Finding, ReviewResult, check_rules
from procurement.shared.runs import read_run, stamp_run, write_run

APPROACHES = ('approach1', 'approach2', 'approach3', 'approach4')


class State(TypedDict, total=False):
    # Inputs, set once before the graph starts.
    path: object
    items: dict
    policy: dict
    approach: str
    model: object
    endpoint: str
    timeout: float
    artifact_dir: object
    source_run: object
    review_response: object
    provider: str
    started: float
    # Produced by the nodes, in order.
    document: object
    run: object
    checked_document: object
    result: object
    final: object


def document_level_issues(issues):
    """Keep run issues about the document or whole run; drop one-fact ("quantity: ...") issues."""
    return tuple(issue for issue in issues if issue.split(': ', 1)[0] not in FACT_NAMES)


# ----------------------------------------------------------------------------- shared nodes

def read_pdf_node(state: State) -> dict:
    document = read_pdf(state['path'])
    if (state.get('source_run') is None) != (state.get('review_response') is None):
        raise ValueError('A correction requires both source_run and review_response.')
    return {'document': document}


def _prepare(state: State, run) -> dict:
    """Stamp the run and build the document that carries only document-level issues."""
    document = state['document']
    run = stamp_run(run, document)
    # pdf_issue is for problems with the document or the whole run (unreadable page, several
    # items, a failed model call). A problem with one fact ("quantity: ...") is already shown by
    # that fact's own finding, so it is not repeated as a pdf_issue.
    document_level = document_level_issues(run.issues)
    checked = replace(document, issues=tuple(dict.fromkeys(document.issues + document_level)))
    return {'run': run, 'checked_document': checked}


def validate_node(state: State) -> dict:
    """Approaches 1 to 3: strict validation. A fact that fails a check is erased."""
    run = state['run']
    validation = validate_fields(run.fields, state['document'])
    run = replace(run, fields=validation.fields, issues=tuple(dict.fromkeys(run.issues + validation.issues)))
    return _prepare(state, run)


def annotate_warnings_node(state: State) -> dict:
    """Approach 4: keep the extractor's facts. Code warnings travel with them, nothing is erased."""
    return _prepare(state, state['run'])


def decide_rules_node(state: State) -> dict:
    """Approaches 1 to 3: the Python rules engine applies the company rules."""
    run = state['run']
    return {'result': check_rules(state['checked_document'], run.fields, state['items'], state['policy'])}


def persist_node(state: State) -> dict:
    run = state['run']
    if state.get('artifact_dir') is None:
        return {}
    artifact_path = write_run(run, state['document'], state['artifact_dir'])
    return {'run': replace(run, metadata={**run.metadata, 'artifact_path': str(artifact_path.resolve())})}


STEP_NAMES = {
    'approach4': ('Read PDF', 'Agent 1: extract facts step by step',
                  'Code: annotate quote and format warnings (nothing erased)',
                  'Agent 2: check facts against the source and apply the rules',
                  'Report decision and human handoff'),
}


def report_node(state: State) -> dict:
    document, run, result = state['document'], state['run'], state['result']
    extraction_status = (run.metadata.get('source_status') if run.metadata.get('assisted')
                         else run.metadata.get('status'))
    review = 'Needs a person to check'
    if state['approach'] == 'approach4':
        names = STEP_NAMES['approach4']
        steps = (
            {'name': names[0], 'status': 'needs_review' if document.issues else 'completed'},
            {'name': names[1], 'status': extraction_status or 'completed'},
            {'name': names[2], 'status': 'needs_review' if run.metadata.get('warnings') else 'completed'},
            {'name': names[3], 'status': 'needs_review' if result.verdict == review else 'completed'},
            {'name': names[4], 'status': 'needs_review' if result.verdict == review else 'completed'},
        )
    else:
        steps = (
            {'name': 'Read PDF', 'status': 'needs_review' if document.issues else 'completed'},
            {'name': 'Extract facts', 'status': extraction_status or 'completed'},
            {'name': 'Validate facts', 'status': 'needs_review' if run.issues or any(
                fact.status in ('ambiguous', 'unrecognized') for fact in run.fields.values()) else 'completed'},
            {'name': 'Check purchase request and company rules',
             'status': 'needs_review' if any(f.severity == review for f in result.findings) else 'completed'},
            {'name': 'Report decision and human handoff',
             'status': 'needs_review' if result.verdict == review else 'completed'},
        )
    return {'final': replace(result, extraction_run=run, steps=steps)}


# ----------------------------------------------------------------------------- extract nodes

def apply_human_correction_node(state: State) -> dict:
    """A reviewer's recorded correction of a saved run replaces the model call. No inference."""
    original = read_run(state['source_run'], state['document'])
    response = parse_json(Path(state['review_response']).read_text(encoding='utf-8'))
    return {'run': apply_corrections(original, state['document'], response)}


def extract_python_node(state: State) -> dict:
    from procurement.approach1.extractor import extract_document as extract_baseline
    run = extract_baseline(state['document'])
    return {'run': replace(run, metadata={**run.metadata, 'status': 'needs_review' if run.issues else 'completed',
                                          'elapsed_seconds': perf_counter() - state['started']})}


def extract_ai_node(state: State) -> dict:
    document, model, timeout = state['document'], state.get('model'), state['timeout']
    provider = state['provider']
    if provider == 'gemini':
        from procurement.approach2.gemini import extract_document as extract_gemini
        return {'run': extract_gemini(document, model=model, timeout=timeout)}
    if provider == 'openrouter':
        from procurement.approach2.openrouter import extract_document as extract_openrouter
        return {'run': extract_openrouter(document, model=model, timeout=timeout)}
    from procurement.approach2.extractor import extract_document as extract_ollama
    return {'run': extract_ollama(document, model=model or 'qwen3:14b', endpoint=state['endpoint'], timeout=timeout)}


def extract_ai_typed_node(state: State) -> dict:
    document, model, timeout = state['document'], state.get('model'), state['timeout']
    if state['provider'] == 'openrouter':
        from procurement.approach3.openrouter import extract_document as extract_openrouter3
        return {'run': extract_openrouter3(document, model=model, timeout=timeout)}
    from procurement.approach3.extractor import extract_document as extract_ollama3
    return {'run': extract_ollama3(document, model=model or 'qwen2.5:7b', endpoint=state['endpoint'], timeout=timeout)}


def agent1_extract_node(state: State) -> dict:
    from procurement.approach4.extractor import extract_document as extract_ai4
    return {'run': extract_ai4(state['document'], model=state.get('model'), timeout=state['timeout'],
                               provider=state['provider'], endpoint=state['endpoint'])}


# ----------------------------------------------------------------------------- approach 4 judge

def failed_extraction_result(state: State):
    """Approach 4 when agent 1 failed: there are no facts for the judge to read.

    No Python rules here. One clear finding says the reader failed and why; the verdict is
    "Needs a person to check", never an approval.
    """
    run = state['run']
    document = state['checked_document']
    reason = '; '.join(str(issue) for issue in run.issues) or run.metadata.get('error') or 'no reason recorded'
    inspected = tuple(Evidence(page.page_number, page.text) for page in document.pages)
    failure = Finding('extraction_failed', REVIEW, f'Reader agent failed: {reason}', inspected)
    return ReviewResult(document, run.fields, (failure,), REVIEW)


def agent2_judge_node(state: State) -> dict:
    """Approach 4: one judge checks the facts against the source and applies the company rules."""
    run = state['run']
    if run.metadata.get('status') == 'failed':
        return {'result': failed_extraction_result(state)}
    from procurement.approach4.judge import judge
    provider = state['provider']
    # Same service as the extractor. On OpenRouter the judge model may differ (OPENROUTER_JUDGE_MODEL).
    judge_model = run.metadata.get('model')
    if provider == 'openrouter':
        judge_model = os.environ.get('OPENROUTER_JUDGE_MODEL') or os.environ.get('OPENROUTER_DECIDER_MODEL') or judge_model
    decision, decision_meta = judge(
        state['checked_document'], run, state['items'], state['policy'], model=judge_model,
        key=os.environ.get('OPENROUTER_API_KEY', '') if provider == 'openrouter' else '',
        timeout=state['timeout'], provider=provider, endpoint=state['endpoint'])
    metadata = {**run.metadata, 'judge': decision_meta,
                'elapsed_seconds': (run.metadata.get('elapsed_seconds') or 0) + decision_meta['elapsed_seconds']}
    if decision_meta['status'] == 'failed':
        metadata['status'] = 'failed'
    return {'result': decision, 'run': replace(run, metadata=metadata)}


# ----------------------------------------------------------------------------- the four graphs

# (extract node, validate-or-annotate node, decide node), per approach.
GRAPH_NODES = {
    'approach1': (('extract_python', extract_python_node), ('validate', validate_node),
                  ('decide_rules', decide_rules_node)),
    'approach2': (('extract_ai', extract_ai_node), ('validate', validate_node),
                  ('decide_rules', decide_rules_node)),
    'approach3': (('extract_ai_typed', extract_ai_typed_node), ('validate', validate_node),
                  ('decide_rules', decide_rules_node)),
    'approach4': (('agent1_extract', agent1_extract_node), ('annotate_warnings', annotate_warnings_node),
                  ('agent2_judge', agent2_judge_node)),
}

# Who does each step. "ai" steps make exactly one model call; everything else is plain code.
NODE_INFO = {
    'read_pdf': ('code', 'Read pages and tables'),
    'extract_python': ('code', 'Extract facts with Python readers'),
    'extract_ai': ('ai', 'Extract facts with one AI call'),
    'extract_ai_typed': ('ai', 'Extract facts with one AI call and a strict output schema'),
    'agent1_extract': ('ai', 'Agent 1: extract facts step by step'),
    'apply_human_correction': ('code', "Apply a reviewer's recorded correction"),
    'validate': ('code', 'Validate quotes, formats and events'),
    'annotate_warnings': ('code', 'Annotate warnings, erase nothing'),
    'decide_rules': ('code', 'Apply the company rules'),
    'agent2_judge': ('ai', 'Agent 2: check the facts and apply the rules'),
    'persist': ('code', 'Save the run'),
    'report': ('code', 'Report decision and human handoff'),
}


@lru_cache(maxsize=None)
def build_graph(approach: str, corrected: bool = False):
    """Compile the fixed, straight-line graph for one approach.

    corrected=True swaps the model call for a reviewer's recorded correction of a saved run.
    """
    if approach not in GRAPH_NODES:
        if not corrected:
            raise ValueError(f'Unknown extraction approach: {approach}')
        approach = 'approach1'
    (extract_name, extract_fn), (check_name, check_fn), (decide_name, decide_fn) = GRAPH_NODES[approach]
    if corrected:
        extract_name, extract_fn = 'apply_human_correction', apply_human_correction_node
    nodes = [('read_pdf', read_pdf_node), (extract_name, extract_fn), (check_name, check_fn),
             (decide_name, decide_fn), ('persist', persist_node), ('report', report_node)]
    graph = StateGraph(State)
    for name, function in nodes:
        graph.add_node(name, function)
    graph.add_edge(START, nodes[0][0])
    for (before, _), (after, _) in zip(nodes, nodes[1:]):
        graph.add_edge(before, after)
    graph.add_edge(nodes[-1][0], END)
    return graph.compile()


def describe(approach: str, corrected: bool = False) -> list:
    """The steps of one approach in order: name, who does it (code or ai) and what it does."""
    names = [name for name in build_graph(approach, corrected).get_graph().nodes if not name.startswith('__')]
    return [{'node': name, 'actor': NODE_INFO[name][0], 'label': NODE_INFO[name][1]} for name in names]


def mermaid(approach: str, corrected: bool = False) -> str:
    """The graph as Mermaid text, generated from the real nodes and edges."""
    return build_graph(approach, corrected).get_graph().draw_mermaid()


def run_workflow(path, items, policy, *, approach='approach1', model=None, endpoint='http://localhost:11434',
                 timeout=600.0, artifact_dir=None, source_run=None, review_response=None, provider='ollama',
                 on_step: Callable | None = None):
    """Run one PDF through the approach's graph and return the ReviewResult.

    on_step, if given, is called after each node with {'node', 'actor', 'label', 'seconds'}, which
    is what a progress bar needs. Failures raise exactly as before (PdfReadError, OSError, ValueError).
    """
    graph = build_graph(approach, source_run is not None)
    state: State = {'path': path, 'items': items, 'policy': policy, 'approach': approach, 'model': model,
                    'endpoint': endpoint, 'timeout': timeout, 'artifact_dir': artifact_dir,
                    'source_run': source_run, 'review_response': review_response, 'provider': provider,
                    'started': perf_counter()}
    last = perf_counter()
    for update in graph.stream(state, stream_mode='updates'):
        for node, changes in update.items():
            state.update(changes or {})  # a node with nothing to change is reported as None
            now = perf_counter()
            if on_step is not None:
                actor, label = NODE_INFO[node]
                on_step({'node': node, 'actor': actor, 'label': label, 'seconds': now - last})
            last = now
    return state['final']


def main() -> int:
    parser = argparse.ArgumentParser(description='Print the fixed workflow graphs.')
    parser.add_argument('--mermaid', choices=APPROACHES + ('all',), help='Print Mermaid text for one approach or all.')
    parser.add_argument('--write', type=Path, help='Write one .mmd file per approach into this folder.')
    arguments = parser.parse_args()
    if arguments.write:
        arguments.write.mkdir(parents=True, exist_ok=True)
        for approach in APPROACHES:
            (arguments.write / f'{approach}.mmd').write_text(mermaid(approach), encoding='utf-8')
        print(f'Wrote {len(APPROACHES)} diagrams to {arguments.write}')
    if arguments.mermaid:
        for approach in (APPROACHES if arguments.mermaid == 'all' else (arguments.mermaid,)):
            print(f'%% {approach}\n{mermaid(approach)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
