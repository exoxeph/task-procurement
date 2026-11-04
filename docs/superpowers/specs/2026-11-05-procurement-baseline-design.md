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

## Block 3 design

- `procurement/extraction.py` defines Evidence(page_number, text) and
  ExtractedField(value, status, evidence) records for later extraction blocks.
- `procurement/supplier_details.py` exposes
  `extract_supplier_details(document: PdfDocument) -> dict[str, ExtractedField]`.
- Extract supplier_name, quotation_number, quotation_date,
  purchase_request_reference, tin, and bin from page text, never filenames.
- Supplier name uses an explicit `Supplier name:` / `Supplier:` line, the
  nonempty line immediately preceding a QUOTATION heading, or a `For ...`
  signoff. These are declared baseline template assumptions, not universal
  supplier recognition. Conflicting candidates require attention.
- Other fields use label-based parsing, supporting values on the same line
  or following whitespace. Recognize Quotation no./number/#, Date/Quotation
  date, Reference/Purchase request reference, TIN, and BIN case-insensitively.
- Quote and PR identifiers must be alphanumeric tokens containing a digit;
  registration identifiers accept digits and hyphens. TIN/BIN labels require
  a following colon or line end to avoid matching ordinary nouns.
  Dates accept only valid
  ISO YYYY-MM-DD calendar dates. Unsupported formats are flagged, not guessed.
  These are parser format assumptions, not legal registration validation.
- Status is found, not_found (no recognized label/candidate), unrecognized
  (a label has unsupported/missing content), or ambiguous (conflicting values).
  Only found supplies a value. Repeated identical values retain all evidence.
- Evidence contains exact extracted page substrings. Never invent a quotation
  for a missing field. Never treat not_found as proof of legal/policy absence.
- Preserve Block 2 issues alongside field results: callers keep PdfDocument,
  and the CLI prints its issues and uses a nonzero exit code when attention
  is needed. No supplier policy decisions, item parsing, or AI in this block.
- All ten originals are checked. Small modified in-memory text fixtures test
  parser behavior, not unseen supplier accuracy or benchmark generalization.

## Block 4 design

- `procurement/financial_details.py` exposes
  `extract_financial_details(document: PdfDocument) -> dict[str, ExtractedField]`.
  Reuse the Evidence and ExtractedField records without changing Block 3.
- Extract item_code, description, quantity, unit, unit_price, line_amount,
  subtotal, vat_rate, vat_amount, total, and unit_price_tax_note.
- Locate the ordered Item / Description / Qty / Unit / Unit price (BDT) /
  Amount (BDT) table headers in native PDF text. The last two headers may
  share one line, as in pack 10. Case and blank-line differences are accepted.
- Support one item per table in native cell-per-line order. The description
  may wrap, but may not contain a standalone numeric line. Extra rows,
  incomplete tables, or unsupported structures remain unrecognized rather
  than silently selecting a row. Repeated agreeing tables retain evidence;
  conflicting occurrences remain unresolved.
- Raw numbers accept plain or correctly comma-grouped non-negative decimal
  notation; quantity is a whole-number token. Do not normalize values or fix
  arithmetic in this block. Block 6 converts types; Block 7 checks arithmetic.
- Item fields cite the exact table header/body excerpt, so the assigned
  column has context. Totals cite their exact label/value excerpts.
- Subtotal, VAT rate, and VAT amount use explicit labels. Missing rows have
  not_found status without invented evidence or calculated replacements.
- Distinguish summary labels from ordinary description words, and exclude
  table lines from totals parsing. Descriptions starting with Total, Subtotal,
  VAT, or Supplier must not alone terminate the item row or create totals.
- unit_price_tax_note captures explicit `VAT included` / `VAT excluded`
  wording in the price header. A plain price header has no explicit tax note;
  do not assume an exclusion statement. Preserve the total's parenthesized
  wording in its evidence, including `all taxes included` in pack 10.
- Preview uses the existing CLI conventions. Required item fields and total
  must be found; missing optional subtotal/VAT/tax-note rows alone are not an
  extraction failure. Any ambiguous/unrecognized field or PDF issue still
  requires attention. Company policy may later flag a missing VAT breakdown.
- No company-rule decisions, currency conversion, AI, or new dependencies.
- User's untracked video/ directory is outside this block and its commit.
