# Supplier document reviewer

A readable Python implementation of the Task 1 procurement workflow.
The project is being built one block at a time. **Only Block 1 is implemented.**
It loads the purchase request and company policy; it does not check PDFs yet.

## Requirements

Python 3.11 or newer. Block 1 uses only the Python standard library, so there
are no packages to install yet.

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

## Policy and scope

The supplied `company-rules.md` remains authoritative. Its manually transcribed
companion is `config/company-rules.json`. Read `docs/policy-mapping.md` for the
complete mapping, exact boundaries, and the ambiguity about a weak penalty.
Changing the Markdown requires reviewing the companion settings too.

The source samples are unchanged. Temporary malformed CSV/JSON inputs in unit
tests check loader error handling; they are not extra supplier benchmark data.
Later evaluation will use all ten provided PDFs and disclose that they were
available during development.

The accepted ten-block design and current progress are recorded in
`docs/superpowers/specs/2026-11-05-procurement-baseline-design.md` and
`docs/progress.md`.
