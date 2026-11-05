"""A standalone local HTML review screen, with no server or frontend framework."""

from html import escape
import json
from dataclasses import asdict

from procurement.shared.human_review import build_questions, response_template


def render_report(results: list, errors: list, evaluation: dict | None = None) -> str:
    """Render document facts and original excerpts, escaping all external text."""
    parts = ['''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Supplier document review</title>
<style>
:root{font-family:system-ui,sans-serif;color:#18312f;background:#edf3f1}
body{max-width:1100px;margin:auto;padding:32px 20px}h1{margin-bottom:8px}
.intro{color:#48635f;max-width:780px}article,.summary{background:white;border:1px solid #d5e2df;
border-radius:12px;padding:22px;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:10px;border-bottom:1px solid #e1e9e7;vertical-align:top}
th{color:#48635f}a{color:#14675d}h2{font-size:21px}h3{font-size:16px}
.badge{display:inline-block;border-radius:6px;padding:5px 10px;font-size:14px;font-weight:650}
.approve{background:#d8f3e5;color:#17613d}.reject{background:#fce0dc;color:#92372e}
.review{background:#fff0c9;color:#775414}.finding{border-top:1px solid #e1e9e7;padding-top:12px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f6;padding:12px;border-radius:6px}
details{margin:12px 0}summary{cursor:pointer;font-weight:600}.muted{color:#617671}
.scroll{overflow-x:auto}td{overflow-wrap:anywhere}footer{font-size:13px;color:#617671}
</style><h1>Supplier document review</h1>
<p class="intro">Read PDF → Extract facts → Check company rules → Review the evidence.</p>
<p class="intro">Unclear information needs a person.
Every displayed excerpt comes from the document; an exact excerpt alone does not prove correct interpretation.</p>''']
    approaches = {result.extraction_run.metadata.get('approach') for result in results if result.extraction_run}
    if 'approach2' in approaches:
        parts.append('<p class="intro">Approach 2: local Ollama extracts facts; Python applies company rules.</p>')
    else:
        parts.append('<p class="intro">Approach 1: Python extraction. This run uses no AI.</p>')
    counts = {verdict: sum(result.verdict == verdict for result in results)
              for verdict in ('Approve', 'Reject', 'Needs a person to check')}
    parts.append('<div class="summary"><b>Batch summary</b><p>' + ' · '.join(
        f'{escape(verdict)}: {count}' for verdict, count in counts.items())
        + f' · File errors: {len(errors)}</p>')
    if evaluation and evaluation['total']:
        parts.append(f"<p>Sample verdict matches: {evaluation['verdict_matches']}/{evaluation['total']}"
                     f" · Triggered-rule set matches: {evaluation['rule_matches']}/{evaluation['total']}</p>"
                     f"<p class='muted'>{escape(evaluation['note'])}</p>")
        parts.append(f"<p>Automatic decision coverage: {evaluation['automatic_decisions']}/{evaluation['total']}"
                     f" · Conservative escalations: {evaluation['conservative_escalations']}"
                     f" · Unsafe approvals on these samples: {evaluation['unsafe_approvals']}</p>"
                     '<details><summary>Compare with unchanged manual labels</summary><div class="scroll"><table>'
                     '<tr><th>Document</th><th>Manual label</th><th>Actual decision</th><th>Triggered rules match</th><th>Execution</th></tr>')
        for row in evaluation['rows']:
            execution = 'Input failed' if row.get('input_error') else 'Extraction failed' if row.get('extraction_error') else 'Completed'
            parts.append(f"<tr><td>{escape(row['file'])}</td><td>{escape(row['expected'])}</td>"
                         f"<td>{escape(row['actual'])}</td><td>{'Yes' if row['rule_match'] else 'No'}</td><td>{execution}</td></tr>")
        parts.append('</table></div></details>')
        parts.append(f"<p>Input failures: {evaluation.get('input_failures', 0)}"
                     f" · Extraction failures: {evaluation.get('extraction_failures', 0)}</p>")
    if evaluation and evaluation.get('assisted_excluded'):
        parts.append(f"<p>Assisted runs excluded from unassisted sample scores: {evaluation['assisted_excluded']}</p>")
    if evaluation and evaluation.get('fields', {}).get('total'):
        audit = evaluation['fields']
        parts.append(f"<p>Audited fact matches, including qualifiers: {audit['matches']}/{audit['total']}"
                     f" · Disputed facts excluded: {audit['disputed']}</p><p>{escape(audit['note'])}</p>")
    parts.append('</div><div class="scroll"><table><tr><th>Document</th><th>Supplier</th><th>Decision</th><th>Findings</th></tr>')
    for index, result in enumerate(results):
        supplier = result.fields['supplier_name'].value or 'Unresolved supplier'
        parts.append(f'<tr><td><a href="#document-{index}">{escape(result.document.source_path.name)}</a></td>'
                     f'<td>{escape(supplier)}</td><td>{escape(result.verdict)}</td><td>{len(result.findings)}</td></tr>')
    parts.append('</table></div>')
    for path, error in errors:
        parts.append(f'<article><h2>{escape(str(path))}</h2><span class="badge review">Needs a person to check</span>'
                     f'<p>Review workflow failed: {escape(str(error))}</p></article>')
    for index, result in enumerate(results):
        style = {'Approve': 'approve', 'Reject': 'reject'}.get(result.verdict, 'review')
        parts.append(f'<article id="document-{index}"><h2>{escape(result.document.source_path.name)}</h2>'
                     f'<span class="badge {style}">{escape(result.verdict)}</span>')
        if result.steps:
            parts.append('<h3>Fixed workflow</h3><p class="muted">These states describe execution, '
                         'not guaranteed factual correctness. A completed rules check can reject a quotation.</p><ol>')
            for step in result.steps:
                parts.append(f"<li>{escape(step['name'])}: <b>{escape(step['status'])}</b></li>")
            parts.append('</ol>')
        if not result.findings:
            parts.append('<p>All configured checks passed for the facts extracted from this supported format.</p>')
        if result.extraction_run:
            parts.append('<details><summary>Extraction run</summary>')
            for name in ('approach', 'model', 'status', 'run_id', 'elapsed_seconds', 'artifact_path',
                         'assisted', 'source_run_id', 'source_status'):
                value = result.extraction_run.metadata.get(name)
                if value is not None:
                    parts.append(f'<p>{escape(name.replace("_", " "))}: {escape(str(value))}</p>')
            if result.extraction_run.metadata.get('assisted'):
                parts.append('<p>Human-assisted result; excluded from unassisted sample scores.</p>')
                audit = result.extraction_run.metadata.get('human_review', {})
                parts.append(f'<pre>{escape(json.dumps(audit, ensure_ascii=False, indent=2))}</pre>')
                changes = result.extraction_run.metadata.get('corrections', {})
                parts.append(f'<pre>{escape(json.dumps(changes, ensure_ascii=False, indent=2))}</pre>')
            parts.append('</details>')
        questions = build_questions(result)
        if questions:
            parts.append('<h3>Human review questions</h3><p>Pending until a person reviews the source. '
                         'Waiting never approves a quotation. Corrections change extracted facts; '
                         'the same company rules run again.</p>')
            for question in questions:
                parts.append(f"<p><b>{escape(question['code'])}</b>: {escape(question['question'])}</p>")
                if question['fields']:
                    parts.append(f"<p>Affected facts: {escape(', '.join(question['fields']))}</p>")
                for excerpt in question['evidence']:
                    parts.append(f"<details><summary>Page {excerpt['page_number']}</summary>"
                                 f"<pre>{escape(excerpt['text'])}</pre></details>")
            if result.extraction_run:
                template = json.dumps(response_template(result.extraction_run), ensure_ascii=False, indent=2)
                example = json.dumps({'line_amount': asdict(result.fields['line_amount'])},
                                     ensure_ascii=False, indent=2)
                parts.append('<details><summary>Prepare a review-response JSON file</summary>'
                             '<p>Copy this starter. Enter reviewer, reviewed_at (ISO 8601 with timezone offset), '
                             'reason, and one or more corrections using the fact shape below. '
                             'Every found fact needs an exact PDF excerpt and page. '
                             'An excerpt validates traceability; the reviewer must check its meaning.</p>'
                             f'<pre>{escape(template)}</pre><p>Fact-shape example copied from this run; '
                             f'check and edit it against the PDF:</p><pre>{escape(example)}</pre>'
                             '<p>Run: python -m procurement.review PDF --source-run SAVED_RUN.json '
                             '--review-response RESPONSE.json --output reports/assisted.html</p></details>')
        for finding in result.findings:
            parts.append(f'<div class="finding"><h3>{escape(finding.code.replace("_", " ").title())}</h3>'
                         f'<p><b>{escape(finding.severity)}</b> — {escape(finding.reason)}</p>'
                         '<details><summary>Supporting document evidence</summary>')
            for excerpt in finding.evidence:
                parts.append(f'<p>Page {excerpt.page_number}</p><pre>{escape(excerpt.text)}</pre>')
            parts.append('</details></div>')
        parts.append('<details><summary>Extracted facts and their evidence</summary><div class="scroll"><table>'
                     '<tr><th>Field</th><th>Value</th><th>Status</th><th>Source</th></tr>')
        for name, field in result.fields.items():
            parts.append(f'<tr><td>{escape(name)}</td><td>{escape(field.value or "—")}')
            details = (("Original wording", field.raw_value), ("Starting event", field.reference_event),
                       ("Minimum", field.minimum_value), ("Maximum", field.maximum_value))
            for label, value in details:
                if value is not None:
                    parts.append(f'<div class="muted">{label}: {escape(value)}</div>')
            for condition in field.conditions:
                parts.append(f'<div class="muted">Condition: {escape(condition)}</div>')
            parts.append(f'</td><td>{escape(field.status)}</td><td>')
            for excerpt in field.evidence:
                parts.append(f'<details><summary>Page {excerpt.page_number}</summary><pre>{escape(excerpt.text)}</pre></details>')
            parts.append('</td></tr>')
        parts.append('</table></div></details><details><summary>Full extracted document text</summary>')
        for page in result.document.pages:
            parts.append(f'<h3>Page {page.page_number}</h3><pre>{escape(page.text)}</pre>')
        parts.append('</details></article>')
    parts.append('<footer>Evidence shows extracted PDF text. Missing-field findings cite the pages inspected; '
                 'absence has no invented quotation. Policy: company-rules.md, with manually transcribed JSON settings.'
                 '</footer></html>')
    return '\n'.join(parts)


def render_comparison(groups: dict, report_paths: dict) -> str:
    """One side-by-side view; preserve per-approach evidence reports separately."""
    names = list(groups)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<title>Procurement extraction comparison</title><style>'
             'body{font:16px system-ui;max-width:1200px;margin:auto;padding:24px;color:#18312f}'
             'table{border-collapse:collapse;width:100%;margin:20px 0}td,th{border:1px solid #ccd9d5;'
             'padding:10px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere}'
             'details{margin:16px 0}.scroll{overflow:auto}</style><h1>Procurement extraction comparison</h1>'
             '<p>Same documents and Python rules; different fact extractors. All ten samples were '
             'development-visible. No training or held-out testing occurred. Human-assisted results '
             'are excluded. Valid JSON and exact citations do not prove correct interpretation.</p>']
    for name in names:
        parts.append(f'<p><a href="{escape(report_paths[name], quote=True)}">'
                     f'{escape(name)}: full findings, workflow stages and source evidence</a></p>')
    metrics = [('Verdict matches', 'verdict_matches'), ('Rule-set matches', 'rule_matches'),
               ('Automatic decisions', 'automatic_decisions'), ('Human review', 'review_count'),
               ('Conservative escalations', 'conservative_escalations'), ('Wrong approvals', 'unsafe_approvals'),
               ('Wrong rejections', 'wrong_rejections'), ('Input failures', 'input_failures'),
               ('Extraction failures', 'extraction_failures'), ('Extraction seconds', 'elapsed_seconds'),
               ('Returned prompt tokens', 'prompt_tokens'), ('Returned output tokens', 'output_tokens')]
    parts.append('<div class="scroll"><table><tr><th>Metric</th>' + ''.join(
        f'<th>{escape(name)}</th>' for name in names) + '</tr>')
    for title, key in metrics:
        parts.append(f'<tr><th>{title}</th>')
        for name in names:
            group = groups[name]
            value = group.get(key, 0)
            if key in ('verdict_matches', 'rule_matches', 'automatic_decisions', 'review_count'):
                value = f"{value}/{group['total']}"
            if key == 'elapsed_seconds':
                value = f'{value:.2f}'
            parts.append(f'<td>{escape(str(value))}</td>')
        parts.append('</tr>')
    parts.append('<tr><th>Audited facts incl. qualifiers</th>')
    for name in names:
        audit = groups[name].get('fields', {})
        parts.append(f"<td>{audit.get('matches', 0)}/{audit.get('total', 0)}; "
                     f"disputed excluded: {audit.get('disputed', 0)}</td>")
    parts.append('</tr></table></div><p>Local inference has no paid-token API bill; '
                 'runtime and hardware still have costs. Times are recorded per extraction, '
                 'not a controlled hardware benchmark. Unresolved expected facts remain in the denominator.</p>')
    if names:
        note = groups[names[0]].get('fields', {}).get('note', '')
        parts.append(f'<p>{escape(note)}</p><p>Fact scoring includes status, normalized value, '
                     'duration starting events, bounds and conditions. Raw clause boundaries and '
                     'price-note wording are excluded from these 27 audited facts per PDF.</p>')
    files = sorted({row['file'] for group in groups.values() for row in group['rows']})
    parts.append('<h2>Per-document decisions and rules</h2><div class="scroll"><table><tr><th>PDF</th>'
                 + ''.join(f'<th>{escape(name)}</th>' for name in names) + '</tr>')
    for filename in files:
        parts.append(f'<tr><th>{escape(filename)}</th>')
        for name in names:
            row = next((row for row in groups[name]['rows'] if row['file'] == filename), None)
            value = ('Not attempted' if row is None else
                     f"{row['actual']} (label: {row['expected']}); rules: {', '.join(row['actual_rules']) or 'none'}")
            parts.append(f'<td>{escape(value)}</td>')
        parts.append('</tr>')
    parts.append('</table></div>')
    for name in names:
        group = groups[name]
        parts.append(f'<h2>Confusion: {escape(name)}</h2><table><tr><th>Expected / actual</th>'
                     '<th>Approve</th><th>Reject</th><th>Needs a person to check</th><th>Failed</th></tr>')
        for expected, outcomes in group['confusion'].items():
            parts.append(f'<tr><th>{escape(expected)}</th>' + ''.join(
                f'<td>{count}</td>' for count in outcomes.values()) + '</tr>')
        parts.append('</table><details><summary>Matches by audited field</summary><table>'
                     '<tr><th>Field</th><th>Matches / attempted</th></tr>')
        for field, counts in group.get('fields', {}).get('by_field', {}).items():
            parts.append(f"<tr><td>{escape(field)}</td><td>{counts['matches']}/{counts['total']}</td></tr>")
        parts.append('</table></details><details><summary>Audited fact mismatches</summary>')
        for row in group.get('fields', {}).get('rows', []):
            if not row['match']:
                parts.append(f"<h3>{escape(row['file'])}: {escape(row['field'])}</h3>"
                             f"<pre>{escape(json.dumps({'expected': row['expected'], 'actual': row['actual']}, indent=2))}</pre>")
        parts.append('</details>')
    return '\n'.join(parts) + '</html>'
