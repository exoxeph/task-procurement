# Supplier document reviewer

A simple Python baseline: **read PDF -> extract facts -> check rules -> show evidence**.
The workflow uses ordinary functions in a fixed order, with no agent or workflow framework.

## Run the full demo

From this project folder, using Python 3.11 or newer:

```powershell
python -m pip install -r requirements.txt
python -m procurement.review
Invoke-Item reports/procurement-review.html
```

The command reviews all ten supplied PDFs. The report opens locally in your browser;
it needs no server, API key, or internet connection after dependencies are installed.
Expand a document to see findings, exact page evidence, extracted facts, and source text.

To review specific PDFs or choose the output:

```powershell
python -m procurement.review sample-data/engineer/task1-procurement/supplier-pack-09.pdf --output reports/example.html
```

A rejected document is a successful review, so it does not itself cause a terminal
error. Exit code 1 means a file/reference/report failure or a sample-label mismatch.
Valid PDFs still get reviewed when another file cannot be opened.

## Results and testing

```powershell
python -m unittest discover -s tests -q
```

The ten development-visible samples match **10/10 expected verdicts** and
**10/10 sets of triggered rules**: two approvals, five rejections, three human reviews.
Manual labels include reasons in config/manual-labels.json. Evaluation is separate
from extraction and never feeds expected answers into decisions. Labels are applied
only to the original sample paths, not arbitrary files with the same names.

Supplier, financial, and contract-term tests also compare extracted fields with
hand-checked values. Regression tests cover policy boundaries, malformed values,
conditional/contradictory wording, PDF errors, and HTML escaping. These development
results do not establish accuracy on unseen supplier documents.
See docs/sample-results.md for each document's outcome.

## Understand the code

Start with **procurement/review.py -> review_document()**:

```python
document = read_pdf(path)
fields = {}
fields.update(extract_supplier_details(document))
fields.update(extract_financial_details(document))
fields.update(extract_terms(document))
return check_rules(document, fields, items, policy)
```

That is the business workflow. Read its parts only when needed:

| File | Responsibility |
| --- | --- |
| procurement/pdf_text.py | Read text and page numbers; flag file problems |
| procurement/supplier_details.py | Supplier, quote, purchase request, TIN and BIN |
| procurement/financial_details.py | Walk lines: read a table, then stated totals |
| procurement/terms.py | Read the supported numbered contract clauses |
| procurement/rules.py | Convert numbers, check policy, and choose the verdict |
| procurement/report.py | Render one standalone HTML report |
| procurement/evaluation.py | Compare results with manual sample labels |
| procurement/extraction.py | Shared field/evidence records and terminal preview |
| procurement/references.py | Load purchase request and policy settings |

The supplier and financial extractors keep their original public function names.
The financial parser now has one table reader and one page-walking function, rather
than separate line records, header/amount collectors, and table-line tracking.

Every field carries its value, status, and original page excerpts:

- found: one supported value; repeated identical values keep all evidence.
- not_found: no recognized occurrence. This alone does not prove legal absence.
- unrecognized: relevant wording exists but cannot be safely interpreted.
- ambiguous: conflicting supported values; no value is selected.

Financial values stay as printed strings until the checks convert them to Decimal.
Pack 09's wrong 322,000.00 is preserved and flagged. Pack 10 gets no invented VAT.
Amounts are calculated to cents with ROUND_HALF_UP. This baseline supports numbers
below 1 trillion with up to six decimal places; larger values require review.

## Decisions and policy

The source is sample-data/engineer/task1-procurement/company-rules.md.
config/company-rules.json is a manually reviewed transcription; update it with the
Markdown. docs/policy-mapping.md explains each rule and boundary.

All findings remain visible. Final priority: **Reject > Needs a person to check > Approve**.
Unknown required facts require human review. Missing registrations or penalty clauses
are distinguished from an unreadable layout: explicit absence or an inspected complete
supported section can establish absence, while unknown structure requires review.
A weak or unclear penalty clause needs human review because policy does not specify
an automatic rejection for that case.

## Limits and interview scope

This is a **deterministic baseline, with no AI model**. The brief requests an AI system;
this baseline alone does not satisfy that aspect. The planned AI comparison should
replace fact extraction while sharing the same policy engine and evaluation.

Supported: native selectable text, BDT prices, known column headings, one item per
table, and numbered Payment/Delivery/Delay/Validity terms. Complete supported payment,
delivery, validity and penalty wording is checked; unfamiliar qualifications need review.
Delivery is an interval after PO, not a guessed calendar date.
No OCR, arbitrary layouts, legal TIN/BIN verification, or general contract understanding.
A person still needs to resolve flagged cases. The HTML report does not record approvals
or edit documents. No publishing or external service is involved.

Original samples and unrelated video/ files remain unchanged. Generated reports are
ignored by Git. The old ten-block docs are historical; the current three-stage design
is docs/superpowers/specs/2026-11-05-simple-baseline-design.md.

## Presentation materials

- docs/submission-note.md: one-page implementation/results/limitations note.
- docs/presentation-script.md: suggested Loom walkthrough under five minutes.
- docs/sample-results.md: the ten expected and actual outcomes.

The user must record the Loom video and publish the repository/demo separately.
