# Block 2 PDF Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read supplier PDF text with source paths and stable page references.

**Architecture:** A small PyMuPDF reader returns page records and extraction
issues. A command-line preview uses the same reader; it never makes supplier
decisions. Later parsers will consume each page's unchanged text and number.

**Tech Stack:** Python 3.11+, PyMuPDF 2.0, standard-library unittest.

**Spec:** docs/superpowers/specs/2026-11-05-procurement-baseline-design.md

## Global Constraints

- Work on `main`; one commit for this block; explain and pause afterward.
- Keep the Python readable and dependencies minimal.
- Original sample documents remain unchanged.
- Implement Block 2 only, without OCR, AI, supplier parsing, or verdicts.
- Retain a source path and one-based page numbers for later evidence.

## Review Focus

- Blank pages must remain in place and create extraction issues.
- Later pages must keep their original numbers in multi-page documents.
- Missing, empty, malformed, and non-PDF files must fail clearly.
- Password-protected and repaired PDFs must not look like clean extraction.
- The preview must report failures through its exit code, not just print them.

### Task 1: Extract and preview PDF pages

**Files:**
- Create: `procurement/pdf_text.py`, `requirements.txt`, `tests/test_pdf_text.py`
- Modify: `README.md`, `docs/progress.md`

**Interfaces:**
- Consumes: supplied PDF paths; independent of Block 1 loaders.
- Produces: `PdfPage(page_number: int, text: str)`.
- Produces: `PdfDocument(source_path: Path, pages: tuple[PdfPage, ...], issues: tuple[str, ...])`.
- Produces: `read_pdf(path: Path) -> PdfDocument`, raising `PdfReadError` on unreadable documents.
- Produces: `python -m procurement.pdf_text PATH [PATH ...] [--summary]`.

- [x] Write tests for the ten samples, multi-page ordering, blank and mixed
  pages, missing/empty/malformed/non-PDF/encrypted/repaired documents, and CLI.
- [x] Run `python -m unittest discover -s tests -p test_pdf_text.py -v`;
  expect failure because the reader does not exist.
- [x] Implement the records, reader, dependency pin, and preview.
- [x] Run `python -m unittest discover -s tests -v`; expect zero failures.
- [x] Run the preview on a supplied PDF and summary extraction on all ten.
- [x] Review code and read the independent review; fix substantive findings.
- [x] Commit as `feat: extract PDF text with page references (block 2)`.
- [x] Explain the flow and pause before Block 3.
