"""A standalone local HTML review screen, with no server or frontend framework."""

from html import escape


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
<p class="intro">Python baseline for the supplied document format. Unclear information needs a person.
This version uses no AI. Every displayed excerpt comes from the document.</p>''']
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
                     '<tr><th>Document</th><th>Manual label</th><th>Actual decision</th><th>Triggered rules match</th></tr>')
        for row in evaluation['rows']:
            parts.append(f"<tr><td>{escape(row['file'])}</td><td>{escape(row['expected'])}</td>"
                         f"<td>{escape(row['actual'])}</td><td>{'Yes' if row['rule_match'] else 'No'}</td></tr>")
        parts.append('</table></div></details>')
    parts.append('</div><div class="scroll"><table><tr><th>Document</th><th>Supplier</th><th>Decision</th><th>Findings</th></tr>')
    for index, result in enumerate(results):
        supplier = result.fields['supplier_name'].value or 'Unresolved supplier'
        parts.append(f'<tr><td><a href="#document-{index}">{escape(result.document.source_path.name)}</a></td>'
                     f'<td>{escape(supplier)}</td><td>{escape(result.verdict)}</td><td>{len(result.findings)}</td></tr>')
    parts.append('</table></div>')
    for path, error in errors:
        parts.append(f'<article><h2>{escape(str(path))}</h2><span class="badge review">Needs a person to check</span>'
                     f'<p>PDF could not be reviewed: {escape(str(error))}</p></article>')
    for index, result in enumerate(results):
        style = {'Approve': 'approve', 'Reject': 'reject'}.get(result.verdict, 'review')
        parts.append(f'<article id="document-{index}"><h2>{escape(result.document.source_path.name)}</h2>'
                     f'<span class="badge {style}">{escape(result.verdict)}</span>')
        if not result.findings:
            parts.append('<p>All configured checks passed for the facts extracted from this supported format.</p>')
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
