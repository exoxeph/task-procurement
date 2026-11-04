# Procurement reviewer: one-page note

## What I built

A local Python baseline that reviews supplier quotations in four fixed steps:
read PDF text, extract facts, check purchase-request/company rules, and show the
decision with exact page excerpts. A single command reviews all supplied PDFs
and writes an HTML report that opens directly in a browser. No server is needed.

The report shows Approve, Reject, or Needs a person to check, all triggered rules,
the extracted fields and their statuses, and the original extracted page text.
Rejection takes priority, while other findings remain visible. Unknown extraction
does not silently pass a check. No missing figures or evidence are fabricated.

## Why this approach

The supplied documents share a readable template. A deterministic parser gives
an explainable baseline for measuring the additional value of AI extraction.
Python functions make the workflow explicit. No agent runs freely and no workflow
framework is necessary for this short sequence. Rules and verdict selection stay
together so changes can be demonstrated live.

This version does **not use AI**. The brief requests an AI system, so this baseline
alone does not fully satisfy that aspect of the submission. The intended next
comparison replaces extraction with an AI reader while keeping policy and
evaluation unchanged. A model would extract facts, never decide company policy.

## Testing and results

All ten supplied PDFs were manually reviewed and were available during development.
The baseline matches 10/10 expected verdicts: two Approve, five Reject, three
Needs a person to check. It also matches all ten manually labelled sets of
triggered rule codes, including secondary review findings on rejected documents.
Separate tests compare supplier, financial and term fields with hand-checked values.

Regression tests cover exact policy boundaries, malformed figures, conflicting
values, missing clauses, arithmetic, PDF reading failures, and escaped HTML.
Small synthetic text/PDF fixtures test behavior; they are not additional supplier
benchmark data. Sample accuracy is a development result, not unseen accuracy.

## Limitations and next steps

The parser supports native-text BDT quotations with the known table headings,
one item per table, and numbered terms. It does not perform OCR or understand
arbitrary layouts, legal registration validity, or every contractual phrasing.
Unclear formats require human review. Delivery is interpreted as elapsed days
after the purchase order, not an invented calendar date.

The policy does not assign severity to an existing penalty below its minimum;
this implementation uses human review. Missing penalty rejects only when absence
is explicit or the complete supported terms can be inspected. Missing TIN/BIN in
an unknown layout requires review; the supplied explicit available-on-request
statement establishes their absence for pack 08.

Next: compare an AI extractor on the same ten visible samples, collect genuinely
new documents for an independent evaluation, and add OCR/multi-item support only
with evidence that the business needs them. Record the Loom presentation and
publish the repository/demo separately; neither action is performed by this code.
