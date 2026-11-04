# Procurement baseline design

## Agreed scope

Implement the ten-block, plain-Python approach discussed in chat. The user
authorized implementation on `main`, one commit per block, with an explanation
and a pause after each block. Use descriptive names, small functions, and few
dependencies. Do not start another block until the user asks to continue.

## Approaches

1. Baseline: PDF text extraction, reusable parsing patterns, deterministic policy.
2. Later comparison: AI extraction with the same validation and policy engine.

The user selected both for eventual comparison and requested the baseline first.
All ten supplied PDFs are development-visible sample evaluation data. Do not
claim an unseen benchmark or generalization from their results.

## Blocks

1. Load purchase requirements and manually transcribed company policy.
2. Extract PDF text with page references.
3. Parse supplier and quotation details with evidence.
4. Parse item and financial details with evidence.
5. Parse payment, delivery, penalty, and validity terms with evidence.
6. Normalize facts and identify missing or ambiguous extraction.
7. Check every applicable company rule and arithmetic calculation.
8. Apply Reject > Needs a person to check > Approve; preserve all findings.
9. Compare extracted fields, findings, and verdicts against manual labels.
10. Add a simple document-review interface and batch summary.

## Block 1 design

- Python 3.11+, standard library only at this stage.
- `procurement/references.py`: CSV and JSON loading, readable item records,
  validation of reference inputs. Default paths resolve from the module's
  location, rather than the terminal's current working directory.
- `config/company-rules.json`: explicit transcription, not an automatic Markdown
  interpreter. Percentages use percentage points: `3.0` means 3%, not 0.03.
- `docs/policy-mapping.md`: maps settings and future checks to the original
  company-rules.md. The original Markdown remains authoritative.
- Monetary values and fractional percentages use Decimal, not binary floats.
- Missing or malformed reference data stops loading with a readable error; it
  cannot safely produce an approval.
- No PDF reading, supplier checks, AI calls, or verdicts in Block 1.

## Policy ambiguity

The source requires a weekly penalty of at least 0.5% but does not explicitly
assign a verdict for an existing clause below that minimum. Preserve this
ambiguity. In Block 7, use human review under the uncertainty rule rather than
inventing an automatic rejection. A missing clause is explicitly a rejection.

## Block 2 design

- Use PyMuPDF to read native PDF text. Pin the locally verified version in
  `requirements.txt`; do not introduce OCR or AI.
- `procurement/pdf_text.py` exposes `read_pdf(path) -> PdfDocument`.
- A `PdfDocument` stores the resolved source path, a tuple of `PdfPage` records,
  and extraction issues. Each page has a one-based page number and its text.
- Preserve native extraction output without stripping, rewriting, or merging
  pages. Use PDF content order, which may differ from visual reading order in
  complex layouts; the provided templates will be checked individually.
- A page with no selectable text stays in the page list and creates an issue.
  Do not silently skip it or assume OCR has occurred.
- Flag repaired PDFs as extraction issues. Missing, empty, invalid, non-PDF,
  password-protected, or unreadable files raise a readable `PdfReadError`.
- A command-line preview takes one or more PDF paths, prints page text, and
  supports a summary option. Failed or flagged extraction has a nonzero exit
  code. Neither the reader nor preview makes a procurement decision.
- Test all ten supplied documents. Temporary blank, combined, damaged, and
  encrypted fixtures exercise file handling, not supplier benchmark accuracy.
- Nonempty text alone does not establish complete or correct extraction. OCR,
  difficult layouts, and evidence span matching remain outside this block.

## Verification and delivery

Use test-first development for input handling. Check the actual supplied CSV
and configuration, plus small malformed-input unit fixtures (not additional
supplier evaluation documents). Run the full test suite and the reference-data
preview before committing. Record progress, explain the files and Python
concepts, then pause. No remote push is requested.
