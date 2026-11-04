# Block 3 Supplier Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract six supplier/quotation fields with exact evidence and explicit uncertainty.

**Architecture:** Small evidence records are shared with future extraction
blocks. A label-based parser consumes Block 2's page text and returns named
field results. A CLI previews values, statuses, and evidence without verdicts.

**Tech Stack:** Python 3.11+, existing PyMuPDF dependency, standard-library re,
datetime, dataclasses, unittest.

**Spec:** docs/superpowers/specs/2026-11-05-procurement-baseline-design.md

## Global Constraints

- Work on main; commit this block, explain it, then pause before Block 4.
- Keep code readable; use no AI or new dependencies.
- Original sample files remain unchanged; do not read values from filenames.
- No price, quantity, contract-term extraction, or procurement decisions yet.

## Review Focus

- Every evidence string must occur exactly on its referenced source page.
- Repeated equal values are acceptable; conflicting candidates are ambiguous.
- Missing or unsupported label values must not become invented facts.
- Renamed files and page rearrangement must not alter field values or evidence pages.
- Extraction issues from Block 2 must still cause the CLI to request attention.

### Task 1: Parse and preview supplier details

**Files:**
- Create: procurement/extraction.py, procurement/supplier_details.py
- Test: tests/test_supplier_details.py
- Modify: README.md, docs/progress.md

**Interfaces:**
- Consumes PdfDocument and PdfPage from procurement.pdf_text.
- Produces Evidence(page_number: int, text: str).
- Produces ExtractedField(value: str | None, status: str, evidence: tuple[Evidence, ...]).
- Produces extract_supplier_details(document: PdfDocument) -> dict[str, ExtractedField].
- Produces python -m procurement.supplier_details PATH [PATH ...].

- [x] Write tests with hand-checked expected fields for all ten supplied PDFs,
  exact evidence/page checks, label variations, repeated/conflicting values,
  unsupported/missing values, alternate source paths, and CLI attention handling.
- [x] Run new tests; expect failure because the parser does not exist.
- [x] Implement records, parser, and CLI.
- [x] Run full unittest discovery; expect zero failures.
- [x] Preview packs 01 and 08; the second must flag missing registration fields.
- [x] Review independently and address substantive findings.
- [x] Verify original samples unchanged; commit Block 3 on main.
- [x] Explain code flow and pause before Block 4.
