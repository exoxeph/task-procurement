# Structural, cautious Python baseline

User authorized fixing Approach 1, retesting and committing on main after choosing
structural table extraction and cautious component-based terms. This supersedes
the template-based extraction in the simple-baseline design. No AI calls or new
runtime dependency. Preserve supplied data and unrelated video/.

## Choices

Chosen: detect ruled table cells from PDF drawing coordinates, map semantic column
labels independently of order, and read words inside cells. Alternative: add more
text-order or sentence variants; rejected because it compounds sample dependence.
AI extraction remains a later comparison, not part of this change.

## Extraction

PdfPage gains optional table records with original cell text. Keep original page
text untouched for evidence. Group vertical grid boundaries by their span, use
horizontal rules as row boundaries, assign words by cell position. Support reordered
columns, wrapped descriptions, and harmless extra columns. Ambiguous columns,
unsupported currencies, missing layout, multiple item rows, and unreadable grids
require review rather than guessing. No fixed native text-line offsets. Totals
remain explicitly labelled numeric values; never calculate missing source figures.

Terms locate labelled sections independently of numbering using a small documented
concept vocabulary. Extract duration/unit/reference-event components, not complete
sample sentences. Bare numeric matches do not establish meaning. Preserve raw
clauses and parsed components; require an explicit time operator and reference
event. A limited composition grammar permits concept order changes and inflections;
any unexplained words, ranges, negation, conditions or conflicting values make the
affected field unresolved. No expanding sentence allowlist to regain 10/10.

Rules remain policy-driven. Remove specific available-on-request registration and
set-of-template-section absence heuristics. Missing extraction means review unless
an explicit labelled absence is established. Clear policy violations still reject
despite other review findings. Existing metadata label parsing remains a declared
limited heuristic, not general entity recognition.

## Evaluation

Keep manual policy labels unchanged. Report actual matches, automated decision
coverage, conservative escalations and unsafe approvals. Human review on a rejected
gold sample is not labelled correct; distinguish escalation from a wrong approval.
Do not change labels or weaken tests to restore the original accuracy claim.
Add structural transformations (column reorder, renamed file, content insertion order,
numeric mutation, wrapping, extra rows) and terms transformations (concept order,
weeks/days, unknown anchors/conditions, conflict/negation). These are parser property
checks on synthetic fixtures, not unseen benchmark documents or legal validation.

## Readability and delivery

Small named functions and explicit domain vocabulary. Preserve public extractor
interfaces and field statuses. Update README, report, sample-results, note and Loom
script with actual limitations and observed results. Run full tests and real batch,
independent review, fix substantive findings, verify samples unchanged, commit.
