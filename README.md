# Supplier document reviewer

A readable Python implementation of the Task 1 procurement workflow.
The project is being built one block at a time. **Blocks 1 and 2 are implemented.**
It loads the reference inputs and reads PDF text with page references.
It does not extract supplier facts or issue procurement decisions yet.

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
