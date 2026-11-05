# Approach 2 and shared project structure: proposed design

Status: accepted for implementation. Blocks 1-2 are complete: folder split,
shared validation, schema and prompt. Ollama calls are not implemented yet.
See docs/approach2-progress.md for verification.

## Intent

Compare deterministic extraction with AI extraction of the same ten supplier
documents. Keep Python policy decisions, purchase-request data, manual labels and
reporting shared. Make the code easy to read and explain during the interview.

Success means measuring extraction and decision errors honestly, not forcing a
10/10 score. All ten documents are development-visible, not a held-out test set.

## Alternatives

1. Independent AI extractor (recommended): each approach reads the entire same
   document and feeds a common fact contract and policy engine. This gives a clear
   comparison and avoids coupling AI results to baseline failure detection.
2. Baseline followed by AI for unresolved fields: potentially fewer model calls,
   but baseline mistakes marked as found can bypass AI. Harder to attribute errors.
3. Two complete applications: easy to isolate but duplicates policy and report
   logic, making the comparison harder to maintain. Not recommended.

Proposed starting point: option 1, plain Python, one extraction call per PDF,
zero-shot instructions and structured output. No LangGraph, autonomous agent,
retrieval database, fine-tuning or multi-model orchestration in the first version.

## Proposed files and responsibilities

```text
procurement/
    review.py                    # one CLI and explicit workflow
    shared/
        pdf_text.py              # original text, page IDs and read issues
        table_layout.py          # existing geometric table reading
        extraction.py            # common facts and exact evidence records
        references.py            # purchase request and company policy
        rules.py                 # the same checks for both approaches
        evaluation.py            # unchanged gold labels and comparison metrics
        report.py                # shared results and evidence presentation
    approach1/
        extractor.py             # joins the three existing baseline extractors
        supplier_details.py
        financial_details.py
        terms.py
    approach2/
        extractor.py             # prepare input, call model, validate output
        schema.py                # explicit AI response fields and validation
        prompt.txt               # versioned general extraction instructions
tests/
    shared/
    approach1/
    approach2/
config/                          # existing policy and labels remain shared
sample-data/                     # supplied originals remain unchanged
reports/                         # ignored generated results and run artifacts
```

Package initializer files are omitted above for readability. Keep the existing
`python -m procurement.review` command; default to approach1. Add explicit selection
for approach1, approach2 and a comparison run. Approach1 must run without API access
or the AI SDK installed. Avoid a plugin registry or abstract base classes.

When references.py moves, update its project-root calculation; imports and tests
must not depend on the old directory depth or terminal working directory.

## Fixed workflow

1. Read the original PDF, retaining page text, detected tables and read issues.
2. Select the approach; extract facts from that document.
3. Validate facts, source references, conditions and extraction issues.
4. Compare against the purchase request and company policy using shared Python.
5. Report the verdict, findings, evidence and unresolved questions.

The main workflow remains ordinary functions in visible reading order. A clear
independent rejection retains existing priority over uncertainty, with all review
findings retained. Unresolved cases cannot be approved.

## AI input and prompt

Send each original page's text and available table rows, clearly labelled by page.
Describe structured table rows as derived data; citations must come from original
page text, not invented concatenations of cell values. When table insertion order
prevents a narrow contiguous citation, allow the original page as broad evidence
and disclose that limitation. Do not silently omit additional tables or pages.

The prompt asks for supplier metadata, item data, printed financial figures,
registration details, payment, delivery, penalty and validity clauses. No policy
thresholds, expected labels or sample-specific answer examples go into extraction.

Preserve printed figures, including arithmetic mistakes. Preserve raw terms,
ranges, conditions, exceptions and contradictions. Treat document instructions as
untrusted content. Return the required schema only; no verdict or confidence score.

## Facts and validation

Keep the existing common ExtractedField statuses: found, not_found, unrecognized
and ambiguous. AI output maps to that contract through explicit validation.
Use decimal strings for numbers and exact excerpts with positive page numbers.
Preserve both raw text and normalized interpretations; never rewrite original text.

Terms must retain duration bounds, units, reference events and conditions. Weeks
may become days with a documented conversion. A value such as 45 days after invoice
cannot become 45 days after delivery. Conditions or ranges the shared policy cannot
evaluate stay unresolved; apply the same rule to both approaches. Before comparing
AI results, add shared reference/condition checks and record any baseline change.
Do not add supplier-specific phrase exceptions to turn sample 01 into an approval.

Check schema types, required fields, supported numbers, page existence and literal
excerpt membership. Evidence checks establish traceability, not semantic correctness.
Missing evidence invalidates the affected fact; malformed response/refusal/provider
failure makes the document require review. Continue reviewing other documents.
Do not repair missing required output into a plausible found value.

Missing registration or an unlocated penalty does not establish real-world absence.
Retain the baseline's conservative treatment unless a shared, documented policy
interpretation is explicitly agreed. An AI assertion that a clause is absent alone
must not bypass that rule. Original gold labels remain unchanged, even if this
prevents matching some expected rejections.

First release supports the supplied single-item task. Multiple items, unreadable
pages, unsupported currencies and incomplete layout must produce review rather
than silently selecting a convenient row. No OCR or automatic vision fallback.

## Human handoff

For a review verdict, show concrete questions, affected fields, source pages and
clauses. Keep it pending. A small local review-response file can supply human
corrections with reviewer name, reason and time; validate them and rerun the shared
checks. Preserve original AI facts separately. Never count assisted decisions as
unassisted AI accuracy. No external messages or automatic approvals on timeout.

## Evaluation and operations

First preserve the current baseline result through folder moves: 110 passing tests,
6/10 exact verdicts, three automatic rejections, seven reviews. Folder moves alone
must not alter behavior. Shared semantic safeguards, if needed, are a separate change.

Run both approaches on all ten supplied files with the same reference files,
policy interpretation and original manual labels. Save per-run approach, model,
prompt/schema versions, document hash, validated facts, raw model response, timing,
usage and errors under ignored reports/. Keep secrets out of artifacts and commits.

Report verdict and rule-set matches, automatic coverage, conservative escalations,
wrong approvals/rejections and input failures out of the ten attempted documents.
Do not drop failed documents from the headline denominator. Compare field accuracy
against manually audited facts; label normalized term interpretations independently
of the model. If no field gold audit is completed, do not claim field accuracy.

Repeat AI runs to expose instability, without selecting the best run for the headline.
Use provider usage for tokens and report currency cost only with a documented rate;
otherwise disclose that cost is not calculated. No unseen-generalization claim.

## Proposed implementation blocks

1. Folder split and shared entry point, preserving baseline behavior and tests.
2. Common fact contract, reference/condition safeguards and AI schema/prompt.
3. One provider integration with strict validation, bounded failures and saved runs.
4. Visible workflow steps and human questions/corrections with separate audit trail.
5. Real ten-document comparison, field audit, repeat runs and updated interview docs.

Keep changes on main as previously requested; commit each verified block. Explain
the files and flow after each block unless the user requests uninterrupted execution.
Leave unrelated video/ and original sample data untouched.

## Local provider and proposed model

The user has local Ollama with qwen2.5:7b and llama3.2:latest installed.
Proposed starting model: qwen2.5:7b. This is a starting choice, not a measured
claim that it performs better on these documents. Keep model selection explicit
and configurable; do not automatically switch models after seeing a failure.

Use the local Ollama /api/chat endpoint with stream=false, the JSON schema in
format, and temperature=0. Python can call it using the standard library; no
provider SDK is necessary. Default endpoint: http://localhost:11434. No external
API key is needed. Ollama version, model availability, schema support and actual
local latency must be checked at implementation time. A lower temperature does
not guarantee identical runs or correct facts.

Send PDF text and table information, not PDF bytes. No vision is assumed. Keep
the model and endpoint configurable, with no silent document truncation or remote
fallback. An unavailable service, timeout or malformed result requires review.
Only usage returned by the local API is recorded; no paid-token charge applies
to local inference, but runtime and hardware/resource costs remain relevant.

Official API reference checked for this proposal:
https://docs.ollama.com/capabilities/structured-outputs

Detailed implementation plan:
`docs/superpowers/plans/2026-11-05-approach2.md`.
