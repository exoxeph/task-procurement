# Procurement reviewer: one-page note

## What I built

A deterministic Python comparison baseline: read PDF text and table geometry,
extract cautious facts, check purchase-request/company rules, then show a local
HTML report with decisions and original page evidence. Uncertain cases require
human review. No autonomous agent or framework is needed for this fixed workflow.
This version has no AI model; an AI extractor is still needed for the intended
AI comparison and the brief's AI-system aspect.

## Why I changed the first baseline

The previous parser matched native text positions and complete sample sentences.
Its 10/10 development result did not demonstrate generalization. I replaced item
reading with ruled-grid boundaries, word coordinates and semantic column labels.
Contract extraction separates duration, unit, operator and reference event, with
raw clauses retained. Unexplained wording stays unresolved. Sample-specific
registration and missing-clause inference rules were removed. Policy conditions
remain deterministic because they directly express the supplied business rules.

## Actual results and tests

Manual gold policy labels are unchanged. On all ten development-visible PDFs,
the revised baseline matches 6/10 verdicts and 6/10 triggered-rule sets. It makes
three automatic rejections (03, 05, 10) and seven human-review decisions. Four are
additional conservative escalations: 01, 02, 06, 08. Those are not counted as
correct verdicts. There are zero wrong automatic decisions in this run and zero
approvals; zero unsafe approvals therefore does not establish overall safety.

01's delivery-and-acceptance payment condition and 02's factory-location wording
are outside the small term grammar. 06's missing penalty and 08's missing TIN/BIN
can be judged by a person, but the parser no longer assumes it can prove absence
from a familiar template. Clear price, advance and delivery violations still reject.

Tests cover policy boundaries, exact raw figures, missing/ambiguous values,
conditional or malformed terms, PDF failures and HTML escaping. Structural
transformations cover column reorder, reversed PDF insertion order, wrapped
cells, aliases, extra columns, numeric changes and unsupported rows/currencies.
Synthetic transformations are property tests, not unseen supplier examples.

## Limitations and next steps

Simple ruled BDT tables and a small English clause-component vocabulary are
supported. Borderless/merged/skewed tables, multiple item rows, OCR, unfamiliar
contract prose and legal registration verification are outside scope. Metadata
extraction remains heuristic. Spatial fields cite original page text rather than
invented reconstructed quotations. Weak penalty severity is unspecified in policy,
so it requires review. Delivery is relative to PO, not a fabricated calendar date.

This change reduces specific template dependencies; it does not prove general
accuracy. Next compare AI fact extraction against this baseline using the same
policy engine, labels and coverage metrics, then obtain genuinely new documents
for independent evaluation. Record the Loom video and publish the code/demo
separately. No source samples were changed.
