# Supplier document reviewer: structural Python baseline

**Read PDF -> Extract cautious facts -> Check policy -> Show evidence.**
This is a deterministic comparison baseline, with no AI or workflow framework.
It is not a general contract reader and does not yet meet the brief's AI requirement.

## Run

Python 3.11 or newer, from the project folder:

```powershell
python -m pip install -r requirements.txt
python -m procurement.review
Invoke-Item reports/procurement-review.html
python -m unittest discover -s tests -q
```

The standalone HTML report needs no server, API key, or internet connection after
installation. It shows decisions, findings, original excerpts, raw clauses, parsed
reference events and full source text. Expand the manual-label comparison to see
actual differences; expected answers never feed extraction or policy decisions.

Review particular files or choose an output:

```powershell
python -m procurement.review sample-data/engineer/task1-procurement/supplier-pack-09.pdf --output reports/example.html
```

Normal exit code 1 means a file/reference/report error. Approve, Reject and human
review are valid execution outcomes. To additionally fail on sample-label differences:

```powershell
python -m procurement.review --check-labels
```

That strict check currently exits 1 because the cautious baseline escalates four
samples rather than matching every manual decision. The report is still written.

## Measured results

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

| File | Responsibility |
| --- | --- |
| procurement/pdf_text.py | Original page text, structural table data and file issues |
| procurement/table_layout.py | Ruled grid boundaries and words inside cells |
| procurement/financial_details.py | Map column concepts and read labelled totals |
| procurement/terms.py | Labelled clauses, explicit components and unexplained-word checks |
| procurement/supplier_details.py | Limited metadata/registration label heuristics |
| procurement/rules.py | Convert numbers, compare requests, check policy and decide |
| procurement/report.py | Standalone HTML with escaped source text |
| procurement/evaluation.py | Compare actual results with unchanged manual labels |
| procurement/extraction.py | Shared value/status/evidence records and preview |
| procurement/references.py | Purchase request and policy configuration |

Fields retain found, not_found, unrecognized or ambiguous statuses. Only found
supplies a value. found means extracted, not policy-compliant. Source excerpts are
exact page text. Spatially read cells cite the entire original page because native
PDF insertion order can differ from visual cell order; excerpts are not reconstructed
or presented as invented contiguous quotations.

## Limits and policy choices

The table reader supports simple ruled rectangular grids with shared vertical spans
and horizontal row separators. Borderless, merged, rotated or incomplete grids need
review. Column order, PDF insertion order, descriptions wrapping within a cell and
harmless extra columns are supported. Multiple item rows require review because
this version still has a single-item decision schema. Currency must explicitly be
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
not extra supplier evaluation documents or a held-out benchmark. The next useful
comparison is AI extraction feeding the same rules and the same evaluation.

## Materials

- docs/submission-note.md: one-page implementation/results/limitations note.
- docs/presentation-script.md: suggested Loom walkthrough.
- docs/sample-results.md: current outcomes and reasons.
- docs/superpowers/specs/2026-11-05-structural-baseline-design.md: current design.

Original sample files and unrelated video/ remain untouched. Generated reports
are ignored by Git. Older block/simple-baseline documents describe prior versions.
Record Loom and publish the repository/demo separately.
