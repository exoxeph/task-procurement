# Procurement reviewer: submission note

I built a local procurement review workflow with two interchangeable extractors:
a cautious Python parser and a zero-shot Qwen2.5:7b model through Ollama. Both read
the same PDF text/table aids, return the same fact contract, and use the same
Python purchase-request and company-policy checks. The model extracts facts; it
does not choose the business rules. The five steps are ordinary readable Python
functions, so a graph framework is unnecessary for this fixed workflow.

## Measured first full run

On the ten development-visible PDFs, Python matched 6/10 verdicts and 6/10 complete
rule sets. Qwen matched 5/10 and 0/10. Source-audited whole-fact agreement was
267/270 versus 224/270, including status, normalized values and timing qualifiers.
Python made three rejections and seven reviews; Qwen made two rejections and eight
reviews. Neither approved anything, and neither made a wrong automatic decision
against the existing labels. Zero wrong approvals here does not establish safety.

Recorded extraction time summed to 0.04 seconds for Python and 573.71 seconds for
Qwen. The model returned 20,526 prompt and 33,356 output tokens. Local inference
has no paid-token API bill; hardware/runtime costs remain. The first attempted
batch is the headline; repeated results, settings and hashes are recorded in
approach2-results.md, approach2-metrics.json and approach2-experiment.json.

## What the comparison teaches

Qwen interpreted pack 02's factory-delivery wording as 21 days after PO, which the
small Python grammar left unresolved. It also missed item codes, produced numeric
strings such as "s800", confused payment references and sometimes cited text that
was not an exact PDF excerpt. Missing item codes prevented some request-price
checks. A structured JSON response alone was not correct extraction. Extra
uncertainty findings made complete rule sets mismatch even when some business
checks were correct. This local setup did not beat the baseline; I would not make
it the default from these measurements.

The earlier template-specific parser's 10/10 result is historical. The current
baseline uses table geometry/column concepts and cautious term components, with
property tests for structural changes. Its high fact score is dominated by simple
shared-template fields; duration agreement is 27/30 versus Qwen's 15/30, and
important ambiguities still need review.

## Evidence, handoff and limits

The standalone HTML shows workflow states, findings, original excerpts and human
questions. A single-document response can correct facts with reviewer, time,
reason and exact evidence. The run ID and live PDF hash must match; the original
answer stays saved and a separate assisted run passes through the same rules.
Assisted results never enter AI-only scores. Reviewer identity is recorded,
not authenticated. Waiting never automatically approves a document.

All ten PDFs were visible during development; no training or held-out evaluation
occurred. Codex audited the fact labels from source; they are not independent
human annotations. Original policy/verdict labels and supplied files were not
changed to fit results. Missing extraction cannot prove real-world absence, so
registration/penalty omissions can remain conservative reviews despite historical
reject labels. Exact citations cannot prove semantic interpretation. OCR,
multiple-item decisions, legal registration checks and unfamiliar layouts remain
outside scope. The next meaningful evaluation needs genuinely new quotations.
