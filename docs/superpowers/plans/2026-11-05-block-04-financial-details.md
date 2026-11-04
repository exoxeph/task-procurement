# Block 4 Financial Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the quoted item and stated financial figures with exact page evidence.

**Architecture:** Locate supported table headers, parse the single item row,
then extract labelled totals and the price-header VAT note. Return the same
ExtractedField records used by Block 3. Keep raw numbers for Blocks 6 and 7.

**Tech Stack:** Python 3.11+, existing PyMuPDF, standard-library dataclasses/re/unittest.

**Spec:** docs/superpowers/specs/2026-11-05-procurement-baseline-design.md

## Global Constraints

- Work on main; one block commit, explanation, and pause before Block 5.
- Keep functions small and readable; no new dependencies or AI.
- Preserve original samples and unrelated user files, including untracked video/.
- No expected-value lookup from filenames, purchase request, or sample IDs.
- No arithmetic correction, numeric normalization, or supplier policy verdict.

## Review Focus

- Pack 09's incorrect stated amount must remain unchanged.
- Pack 10 must preserve VAT-inclusive wording without fabricating missing rows.
- Unsupported/multi-row tables must not silently become a plausible single row.
- Evidence must match exact text on the original page, even with blank lines.
- Missing, malformed, repeated, and conflicting values must retain proper statuses.

### Task 1: Extract and preview financial details

**Files:**
- Create: procurement/financial_details.py, tests/test_financial_details.py
- Modify: README.md, docs/progress.md

**Interfaces:**
- Consumes PdfDocument/PdfPage from Block 2, Evidence/ExtractedField from Block 3.
- Produces extract_financial_details(document: PdfDocument) -> dict[str, ExtractedField].
- Fields: item_code, description, quantity, unit, unit_price, line_amount,
  subtotal, vat_rate, vat_amount, total, unit_price_tax_note.
- Preview: python -m procurement.financial_details PATH [PATH ...].

- [x] Write tests with hand-checked fields from all ten PDFs, including exact
  evidence, VAT inclusion, unchanged bad arithmetic, unsupported tables,
  wrapped descriptions, malformed numbers, conflicts, and CLI attention.
- [x] Run new tests and observe missing-module failure.
- [x] Implement table/totals parsing and preview.
- [x] Run full unittest discovery; expect zero failures.
- [x] Preview packs 09 and 10 and verify all source files unchanged.
- [x] Independently review and fix substantive findings.
- [x] Commit as feat: extract item and financial details with evidence (block 4).
- [x] Explain and pause before Block 5.
