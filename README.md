# Supplier document reviewer

A readable Python implementation of the Task 1 procurement workflow.
The project is being built one block at a time. **Blocks 1-4 are implemented.**
It loads reference inputs, reads PDFs, and extracts supplier, quotation, item,
and financial details with page evidence. It does not extract contract terms,
check financial arithmetic, or issue procurement decisions yet.

## Requirements

Python 3.11 or newer. Block 1 uses the standard library; Block 2 uses PyMuPDF.

Install the pinned PDF dependency:

```powershell
python -m pip install -r requirements.txt
```

From PowerShell in this project directory:

```powershell
python -m procurement.references
```

This prints the five requested items, exact maximum prices, policy thresholds,
and decision priority. It does not issue supplier verdicts.

Run all tests:

```powershell
python -m unittest discover -s tests -v
```

## Block 1: reading guide

Start with `procurement/references.py`:

1. The path constants locate reference files relative to the project, rather
   than relying on where a terminal was opened.
2. `PurchaseRequestItem` is a small named record for one requested item.
   `@dataclass` generates its constructor; `frozen=True` prevents accidentally
   changing a loaded record.
3. `load_purchase_request()` reads CSV rows and returns a dictionary keyed by
   item code. For example, `items["A"].quantity_requested` gives `12000`.
4. `load_company_rules()` reads the explicit JSON policy settings and checks
   that required settings are present and valid. It does not read or understand
   arbitrary Markdown policies.
5. `main()` prints a preview. The `if __name__ == "__main__"` line runs that
   preview when launched as a command, but not when another module imports it.

`Decimal` represents base-10 values exactly. CSV money is converted directly
from text, and JSON fractions are parsed as Decimal. This avoids binary float
rounding in later financial calculations. Percentages use percentage points:
`3.0` means 3%, not 0.03.

An invalid reference file raises an exception with the affected field or row.
The preview turns that into an error message and exits. Bad reference data
cannot silently become an empty request or an approval.

## Block 2: PDF text and page references

Preview a supplier PDF:

```powershell
python -m procurement.pdf_text sample-data/engineer/task1-procurement/supplier-pack-01.pdf
```

Add `--summary` to print only the filename, page count, and extraction issue
count. Multiple paths can be passed in the same command.

Start reading `procurement/pdf_text.py` at `read_pdf()`. Its flow is:

```text
Receive a PDF path
    -> Check the file exists
    -> Open it with PyMuPDF
    -> Check it is a readable, unlocked PDF
    -> Flag any repair performed by the library
    -> Read each page and keep its original page number
    -> Flag pages with no selectable text
    -> Return the source path, pages, and issues
```

The two dataclasses are small named records, like `PurchaseRequestItem`:

- `PdfPage` stores `page_number` and `text`.
- `PdfDocument` stores `source_path`, `pages`, and `issues`.

Example:

```python
from pathlib import Path
from procurement.pdf_text import read_pdf

document = read_pdf(Path("sample-data/engineer/task1-procurement/supplier-pack-01.pdf"))
first_page = document.pages[0]  # Python indexes start at 0.

print(first_page.page_number)  # Document page numbers start at 1.
print(first_page.text)         # The text extracted from page 1.
print(document.issues)        # An empty tuple () means no known issues.
```

Inside the loop, `enumerate(pdf, start=1)` supplies each page and its page
number. `page.get_text("text", sort=False)` gets text in native PDF content
order. `pages.append(...)` stores it. `text.strip()` is used only to check
whether the text is empty; the stored text is not stripped or rewritten.

`tuple(pages)` turns the temporary list into a fixed sequence before returning
it. A blank page stays in the sequence, so page 3 never becomes page 2.

`PdfReadError` is our named exception for a document that cannot be read safely.
The reader raises it for missing, empty, malformed, non-PDF, locked, or otherwise
unreadable files. A repaired PDF or textless page instead returns available
pages with explicit issues. Later workflow blocks must route extraction issues
to human attention, rather than assume missing text means a missing clause.

`main()` is just the command-line preview. It calls `read_pdf()`, prints the
result, and returns `0` for clean extraction or `1` if attention is needed.
`SystemExit(main())` passes that result to the terminal as an exit code.
The preview continues to the other supplied paths if one file fails.

### Extraction limits

This block does not perform OCR. Scanned or textless pages require human
review or an OCR step. Nonempty text is not proof that every part of a page was
read correctly. Native content order can differ from visual reading order on
complex layouts. Page references identify the source page, not bounding boxes
or exact evidence spans; later parsers must select supporting quotations.

## Block 3: supplier and quotation details

```powershell
python -m procurement.supplier_details sample-data/engineer/task1-procurement/supplier-pack-01.pdf
```

This extracts supplier name, quotation number, quotation date, purchase-request
reference, TIN, and BIN. Each found value includes the source page and exact
supporting text. Pack 08 prints `not_found` for TIN and BIN and exits with code 1
to request attention. That is an extraction result, not a rejection verdict.

The two new files have separate jobs:

- `procurement/extraction.py` defines the small `Evidence` and `ExtractedField`
  records. Other extraction blocks can reuse them.
- `procurement/supplier_details.py` contains the parsing functions and preview.

The flow is:

```text
read_pdf(path)                         Block 2
    -> A document containing pages
    -> extract_supplier_details(document)
        -> Find supplier-name candidates
        -> Find each labelled quotation/registration field
        -> Check whether the value has a supported format
        -> Compare repeated occurrences
        -> Return six named field results with evidence
    -> Preview prints fields AND existing document extraction issues
```

Try the function directly:

```python
from pathlib import Path
from procurement.pdf_text import read_pdf
from procurement.supplier_details import extract_supplier_details

document = read_pdf(Path("sample-data/engineer/task1-procurement/supplier-pack-01.pdf"))
fields = extract_supplier_details(document)

quotation = fields["quotation_number"]
print(quotation.value)                    # QT-2026-901
print(quotation.status)                   # found
print(quotation.evidence[0].page_number)   # 1
print(quotation.evidence[0].text)          # Exact label/value text from the page
```

The four statuses mean:

| Status | Meaning | Value returned |
| --- | --- | --- |
| found | Recognized occurrences agree | The extracted text |
| not_found | No supported label/name candidate was located | None |
| unrecognized | A label exists, but its content is missing or unsupported | None |
| ambiguous | Recognized occurrences contain conflicting values | None |

Identical repeated values retain all evidence. If even one labelled occurrence
is unrecognized, the result stays unresolved. A missing field has no invented
evidence. Keep `document.issues` alongside the field dictionary: the dictionary
does not replace the original document's extraction warnings.

### Reading the helper functions

Start at `extract_supplier_details()`, the public entry point. Its loop calls
`_extract_labelled_field()` for each field in `FIELD_LABELS`. The leading
underscore is a naming convention for an internal helper, not special syntax.

`_extract_labelled_field()` uses regular expressions (text search patterns) to
find labels and the token following them. It preserves the original label/value
substring as evidence. `_value_is_supported()` checks parser formats, and
`_resolve_field()` decides whether candidates agree or need attention.

The supplier has no explicit name label in the samples. `_extract_supplier_name()`
therefore checks the line above QUOTATION and the `For ...` signoff, as well as
explicit Supplier/Supplier name labels. These candidates must agree.

### Baseline parser assumptions

This parser supports the provided template and declared wording variations;
it is not an arbitrary document-understanding system. Names may be in the
declared heading/signoff positions. Quote/PR identifiers are single tokens
containing a digit; registration identifiers use digits and hyphens, and their
TIN/BIN labels must be followed by a colon or line break. Dates
must be valid YYYY-MM-DD dates. Unsupported formats are flagged rather than
interpreted. Registration formatting is not legal or registry validation.

`not_found` does not prove a supplier omitted a legally required identifier:
the parser might not support the wording or layout. Later validation and policy
blocks must distinguish extraction limitations from verified document absence.

Tests use all ten supplied PDFs and small in-memory text changes to check parser
behavior. Those checks are not an unseen supplier-document benchmark.

## Block 4: item and financial details

```powershell
python -m procurement.financial_details sample-data/engineer/task1-procurement/supplier-pack-09.pdf
python -m procurement.financial_details sample-data/engineer/task1-procurement/supplier-pack-10.pdf
```

The first preview preserves the stated (incorrect) line amount of `322,000.00`.
The second shows `VAT included` and not_found for subtotal, VAT rate, and VAT
amount. No figures are calculated or repaired during extraction.

Read `procurement/financial_details.py` starting at
`extract_financial_details()`. The flow is:

```text
PdfDocument from Block 2
    -> Read nonempty lines while remembering their original text positions
    -> Locate the supported item-table headers
    -> Read the item code, description, quantity, unit, price, and amount
    -> Preserve an explicit VAT included/excluded note in the price header
    -> Read separately labelled subtotal, VAT rate, VAT amount, and total
    -> Resolve repeated/conflicting values
    -> Return eleven ExtractedField records with page evidence
```

Example:

```python
from pathlib import Path
from procurement.pdf_text import read_pdf
from procurement.financial_details import extract_financial_details

document = read_pdf(Path("sample-data/engineer/task1-procurement/supplier-pack-09.pdf"))
fields = extract_financial_details(document)

print(fields["quantity"].value)       # "50,000", still text
print(fields["unit_price"].value)     # "6.40"
print(fields["line_amount"].value)    # "322,000.00", as written in the PDF
print(fields["line_amount"].status)   # found means extracted, not correct arithmetic
```

The six item fields are `item_code`, `description`, `quantity`, `unit`,
`unit_price`, and `line_amount`. The other fields are `subtotal`, `vat_rate`,
`vat_amount`, `total`, and `unit_price_tax_note`. They use the same four statuses
and evidence records as Block 3. Keep `document.issues` alongside them.

### Reading the helpers

- `_page_lines()` stores each nonempty line with its start/end positions in
  the original page text. This lets matching ignore blank lines while evidence
  still includes the original whitespace.
- `_header_end()` checks the expected column headers. It supports separate
  price/amount headers and pack 10's combined header line.
- `_item_values()` reads a supported single-item body. The final four cells
  must be quantity, unit, unit price, and line amount. Description text can wrap.
- `_summary_value()` and `_is_vat_label()` distinguish financial labels from
  descriptions such as `Total protection cotton fabric` or `VAT resistant fabric`.
- `_collect_item_tables()` puts recognized row values into candidate lists.
  Item evidence includes the full table header/body, giving the columns context.
  It also remembers which lines belong to tables.
- `_collect_amount()` reads a whole amount after a label, either on the same
  line or the next nonempty line. It does not accept a partial numeric match.
- `_collect_totals()` finds explicit subtotal, VAT, and total labels outside
  those table lines, so descriptions do not become financial summary entries.
- `_resolve_field()` uses the same uncertainty rules as Block 3. It is kept
  local so this block does not change the supplier parser already explained.
- `main()` reads paths, calls the reader and extractor, and prints the results.

### Supported format and limits

This baseline expects the native cell-per-line order of the supplied tables:
Item, Description, Qty, Unit, Unit price (BDT), Amount (BDT), then a single item.
The last two headers may share a line. Blank lines and case variations are
accepted. A description may wrap but cannot contain a standalone numeric line:
that would be indistinguishable from an extra item row in this simple parser.
Unsupported/incomplete or multi-row bodies are flagged instead of guessing.

Numbers stay as strings, with their commas and decimal places. Supported forms
are non-negative plain numbers or correctly comma-grouped numbers; quantity
must be a whole-number token. Block 6 will normalize types and Block 7 will
check arithmetic. These formats do not establish generalization to arbitrary
tables, currencies, OCR, or invoice layouts.

An explicit `VAT included` or `VAT excluded` price-header note is preserved.
A plain header has no such statement, so its tax note is not_found; no exclusion
claim is invented. Parenthesized total wording, such as `all taxes included`,
remains in the total's evidence. Missing subtotal or VAT rows are never derived.

The preview needs attention for missing required item fields/total, unsupported
or conflicting fields, or PDF extraction issues. Missing optional subtotal,
VAT, or tax-note fields alone do not indicate a parser failure. Thus pack 10
can exit 0 for extraction while later policy checks still flag its VAT display.
No preview exit code is a supplier approval.

## Policy and scope

The supplied `company-rules.md` remains authoritative. Its manually transcribed
companion is `config/company-rules.json`. Read `docs/policy-mapping.md` for the
complete mapping, exact boundaries, and the ambiguity about a weak penalty.
Changing the Markdown requires reviewing the companion settings too.

The source samples are unchanged. Temporary malformed CSV/JSON inputs and
blank, combined, encrypted, or damaged PDF fixtures check file handling; they
are not extra supplier benchmark data.
Later evaluation will use all ten provided PDFs and disclose that they were
available during development.

The accepted ten-block design and current progress are recorded in
`docs/superpowers/specs/2026-11-05-procurement-baseline-design.md` and
`docs/progress.md`.
