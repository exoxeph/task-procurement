# Supplier document reviewer: Python and local AI extraction

**Read PDF -> Extract cautious facts -> Check policy -> Show evidence.**
Approach 1 uses deterministic Python extraction. Approach 2 uses local Ollama
extraction. Both use the same Python policy checks, evidence report and recorded human
correction workflow. A measured comparison is documented below.

## Run

Python 3.11 or newer, from the project folder:

```powershell
python -m pip install -r requirements.txt
python -m procurement.review
Invoke-Item reports/procurement-review.html
python -m unittest discover -s tests -q
```

The standalone HTML report needs no server or API key to view. Approach 1 needs
no model service; Approach 2 requires local Ollama during extraction. It shows
decisions, findings, original excerpts, raw clauses, parsed
reference events and full source text. Expand the manual-label comparison to see
actual differences; expected answers never feed extraction or policy decisions.

Review particular files or choose an output:

```powershell
python -m procurement.review sample-data/engineer/task1-procurement/supplier-pack-09.pdf --output reports/example.html
```

Normal exit code 1 means a file/reference/report or AI execution error. Approve, Reject and human
review are valid execution outcomes. To additionally fail on sample-label differences:

```powershell
python -m procurement.review --check-labels
```

That strict check currently exits 1 because the cautious baseline escalates four
samples rather than matching every manual decision. The report is still written.

## Run local AI extraction

Start your local Ollama service with qwen3:14b installed (the current Approach 2 default). No external API key or
extra Python SDK is required. Check availability using `ollama list`.

```powershell
python -m procurement.review sample-data/engineer/task1-procurement/supplier-pack-09.pdf --approach approach2 --output reports/ai-example.html
python -m procurement.review --approach both --output reports/comparison.html
```

To use the model from the recorded Qwen2.5 7B experiment below, pass `--model qwen2.5:7b`.
Changing the default model does not change those historical results.

Both mode writes comparison.html, comparison-approach1.html,
comparison-approach2.html and machine-readable comparison.json. Each invocation saves unique
JSON run artifacts under ignored reports/runs/, including original source, validated
facts, raw model answer, document hash, model identity, timing and token usage.
Use --artifacts PATH to choose a directory, --model to select an installed model,
--ollama-url for a loopback base URL, and --timeout for the per-call limit (default
600 seconds, allowing for the larger model). No remote fallback, model download or extraction retry happens. The HTTP client
ignores ambient proxies and refuses redirects, so validated local destinations
remain local. Malformed HTTP responses become saved failed runs and do not stop
the remaining documents.

One extraction request is made per PDF. Optional version/model metadata requests
are separate. Large inputs are refused rather than sliced, and token/completion
checks flag possible context pressure or truncated output. These are conservative
guards, not proof that the model understood every page. Local inference has no
paid-token API bill; hardware and runtime costs still exist.

## Measured comparison

The first full attempted run is the headline; later repeats are reported separately.
All ten PDFs were development-visible. No training occurred.

| Metric | Python baseline | Local Qwen2.5 7B |
| --- | --- | --- |
| Exact verdict matches | 6/10 | 5/10 |
| Exact complete rule-set matches | 6/10 | 0/10 |
| Audited whole-fact matches, including timing qualifiers | 267/270 | 224/270 |
| Automatic decisions | 3/10, all Reject | 2/10, all Reject |
| Human reviews | 7/10 | 8/10 |
| Wrong approvals / wrong rejections | 0 / 0 | 0 / 0 |
| Input / extraction failures | 0 / 0 | 0 / 0 |
| Sum of recorded extraction seconds | 0.04 | 573.71 |

Across three repeats, Qwen verdict/rule-set scores stayed 5/10 and 0/10; whole-fact
matches were 224, 220 and 220 out of 270. The first run stays the headline.
Neither approach approved anything, so zero wrong approvals is limited evidence.
Fact scores are strict agreements with a Codex source audit, not independent human
annotation or unseen accuracy. Raw clause boundaries and price-note wording are
excluded. The high baseline fact score is dominated by simple template fields;
important timing clauses still remain unresolved. Complete rule-set matches include
uncertainty findings, so extra review findings make a set mismatch.

Qwen correctly interpreted one factory-delivery phrase the baseline could not,
but also missed item codes, produced malformed numeric strings and confused
payment anchors. This particular zero-shot local setup did not beat the baseline;
it does not establish that AI is necessary for these ten PDFs.
See docs/approach2-results.md for source-inspected errors, repeat results and exact
measurement limits. Settings/input hashes are in docs/approach2-experiment.json;
compact run metrics are in docs/approach2-metrics.json. Original manual verdict
labels remain unchanged; failed extraction attempts stay in the denominator.

## Measured baseline results

Manual policy labels are unchanged in config/manual-labels.json. On the ten supplied,
development-visible samples:

| Metric | Actual |
| --- | --- |
| Exact verdict matches | 6/10 |
| Exact triggered-rule set matches | 6/10 |
| Automatic decisions | 3/10, all Reject |
| Human review | 7/10 |
| Additional conservative escalations | 4 |
| Incorrect automatic decisions | 0/3 |
| Unsafe approvals | 0; the baseline makes no approvals on this set |

Packs 03, 05, 10 reject. All others need a person. Packs 01 and 02 contain wording
outside the small term grammar; packs 06 and 08 lack confidently extracted required
facts. They are escalations, not successful matches to their manual labels.
See docs/sample-results.md for reasons and expected-vs-actual decisions.

The old 10/10 result came from a template-shaped parser. It is not the current
result. This version improves specific structural properties, not proven unseen
accuracy. All ten PDFs remained visible during development.

## What changed in Approach 1

- Table cells come from PDF grid boundaries and word coordinates, not a fixed run
  of text lines. Explicit column concepts map fields regardless of column order.
- A small documented vocabulary covers labels such as Qty/Quantity and Unit/UOM.
  It is not a growing list of full supplier sentences.
- Terms locate labelled clauses with or without numbering. Durations, units,
  time operators and reference events are separate components. Whole unexplained
  words, conditions, negation, ranges or conflicting statements prevent a confident
  interpretation. Raw clauses and reference events remain visible.
- Sample-specific available-on-request and complete-template absence heuristics
  are removed. Failure to extract a registration/penalty means review. An explicit
  labelled absence can still establish a policy rejection.
- Policy thresholds, Decimal calculations and decision priority remain ordinary
  Python. Clear violations can reject even when other facts require review.

## Read the code

Start at procurement/review.py, review_document(). It calls the following steps:

`approach1/` contains the Python baseline extractors. `shared/` contains PDF
reading, evidence records, policy checks, evaluation and reporting. The
`approach2/` contains the local Ollama request, extraction prompt and JSON response
validation. Both approaches use the same workflow and rules.

| File | Responsibility |
| --- | --- |
| procurement/approach1/extractor.py | Collect supplier, financial and contract facts |
| procurement/shared/pdf_text.py | Original page text, structural table data and file issues |
| procurement/shared/table_layout.py | Ruled grid boundaries and words inside cells |
| procurement/approach1/financial_details.py | Map column concepts and read labelled totals |
| procurement/approach1/terms.py | Labelled clauses, explicit components and unexplained-word checks |
| procurement/approach1/supplier_details.py | Limited metadata/registration label heuristics |
| procurement/shared/rules.py | Convert numbers, compare requests, check policy and decide |
| procurement/shared/report.py | Standalone HTML with escaped source text |
| procurement/shared/evaluation.py | Compare actual results with unchanged manual labels |
| procurement/shared/extraction.py | Shared value/status/evidence records and preview |
| procurement/shared/references.py | Purchase request and policy configuration |
| procurement/approach2/schema.py | AI JSON shape and strict response parsing |
| procurement/approach2/prompt.txt | General extraction instructions, without sample answers |
| procurement/approach2/extractor.py | One local model call, validation and visible failures |
| procurement/shared/runs.py | Unique run identity, document hash and saved JSON artifacts |

The main command remains `python -m procurement.review`. Individual previews now
use their new module paths, for example:

```powershell
python -m procurement.approach1.financial_details sample-data/engineer/task1-procurement/supplier-pack-09.pdf
python -m procurement.shared.pdf_text sample-data/engineer/task1-procurement/supplier-pack-01.pdf --summary
```

Tests follow the same split under `tests/approach1/`, `tests/approach2/` and
`tests/shared/`. Unit tests use a fake HTTP boundary and need no running model.

Fields retain found, not_found, unrecognized or ambiguous statuses. Only found
supplies a value. found means extracted, not policy-compliant. Source excerpts are
exact page text. Spatially read cells cite the entire original page because native
PDF insertion order can differ from visual cell order; excerpts are not reconstructed
or presented as invented contiguous quotations.

The baseline now returns an ExtractionRun containing fields, validation issues
and approach metadata. Facts can also retain original wording, reference events,
conditions and numeric bounds. Shared validation checks exact source excerpts,
numeric formats and conflicting references. It cannot prove that an interpretation
is semantically correct. Policy checks keep unsupported conditions and ranges for
human review and do not apply delivery-based thresholds to invoice-based deadlines.
Missing or unsupported currency prevents monetary comparison against BDT limits.

## Human review and corrections

The HTML shows five steps: read PDF, extract facts, validate facts, check the
purchase request/company rules, and report the decision or handoff. States describe
execution and unresolved issues, not guaranteed semantic correctness.

A pending result includes specific questions, affected fields and PDF excerpts.
Open **Prepare a review-response JSON file** in that document's report card. Copy
the starter and fact-shape example into a JSON file. Supply the reviewer name,
review time with timezone offset, reason and source-backed corrected facts. Keep
real conditions, ranges and uncertainty; changing extraction cannot authorize a
policy exception. The local file records the reviewer identity supplied; it does
not authenticate that identity.

Apply the response to its saved extraction, without another model call:

```powershell
python -m procurement.review sample-data/engineer/task1-procurement/supplier-pack-09.pdf --source-run reports/runs/SAVED_RUN.json --review-response RESPONSE.json --output reports/assisted.html
```

Use the actual saved-run path shown in the original report. Exactly one explicit
PDF is required. The response must match both the original run ID and the PDF's
SHA-256 hash. Invalid evidence, unknown fields, missing audit details, verdict
overrides and policy overrides are rejected.

The original extraction stays unchanged. A new assisted run stores the correction,
reviewer details and source-run link, then the same Python rules run again. A valid
correction can still require review or produce rejection. Assisted decisions and
failed correction attempts do not enter unassisted development accuracy scores.
Nothing automatically approves while waiting for a response.

## Limits and policy choices

The table reader supports simple ruled rectangular grids with shared vertical spans
and horizontal row separators. Borderless, merged, rotated or incomplete grids need
review. Column order, PDF insertion order, descriptions wrapping within a cell and
harmless extra columns are supported. Multiple item rows require review because
this version still has a single-item decision schema. Detected item tables are
counted independently across pages, so an incorrect AI item_count cannot hide
extra recognized rows. Unrecognized/borderless layouts still rely on reported
uncertainty and are not guaranteed to be detected. Currency must explicitly be
BDT. Unclear price qualifiers require review.

The small English term-component grammar is intentionally cautious. It has no
semantic model and cannot establish the meaning of arbitrary prose. Unrecognized
English or other-language qualifications remain unresolved. Metadata label parsing
is still heuristic. There is no OCR or legal TIN/BIN verification. Delivery is an
interval after PO, not a guessed calendar date.

Company-rules.md is authoritative; config/company-rules.json is its manual companion.
Update both together. A weak penalty gets human review because severity is unspecified.
An explicitly absent penalty rejects; a missing extraction alone cannot prove absence.
Numbers below 1 trillion and up to six decimal places are supported; calculated
amounts use Decimal with ROUND_HALF_UP to cents. Raw incorrect figures remain intact.
Reject takes priority over review, and all findings remain visible.

Tests cover policy boundaries, malformed/conflicting values, file errors, HTML
escaping and structural transformations. Synthetic fixtures are property checks,
not extra supplier evaluation documents or a held-out benchmark. The real ten-document
AI comparison and repeatability measurements are documented in docs/approach2-results.md.

## Materials

- docs/submission-note.md: one-page implementation/results/limitations note.
- docs/presentation-script.md: suggested Loom walkthrough.
- docs/sample-results.md: baseline outcomes and reasons.
- docs/approach2-results.md: first full AI comparison, repeats and source-inspected errors.
- config/manual-facts.json: source-audited fact labels; never used during extraction.
- docs/superpowers/specs/2026-11-05-structural-baseline-design.md: baseline design.
- docs/superpowers/specs/2026-11-05-approach2-design.md: shared workflow and AI design.
- docs/approach2-progress.md: implementation progress and actual integration results.

Original sample files and unrelated video/ remain untouched. Generated reports
are ignored by Git. Older block/simple-baseline documents describe prior versions.
Record Loom and publish the repository/demo separately.
