# Block 1 Reference Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load reliable purchase requirements and structured company rules.

**Architecture:** A CSV loader returns item records keyed by item code. A JSON
loader returns policy settings with exact decimal percentages. Both validate
their inputs; neither checks supplier PDFs or makes decisions yet.

**Tech Stack:** Python 3.11 standard library: csv, json, decimal, pathlib,
dataclasses, unittest.

**Spec:** docs/superpowers/specs/2026-11-05-procurement-baseline-design.md

## Global Constraints

- Work on `main`; one commit for this block; explain and pause afterward.
- Keep the Python readable and dependencies minimal.
- Original sample documents remain unchanged.
- No filename-specific supplier decisions and no Markdown-understanding parser.
- Use all ten supplied PDFs for later sample evaluation, not a held-out claim.

## Review Focus

- A UTF-8 byte-order mark must not break CSV header matching.
- Duplicate items must not silently overwrite earlier purchase requirements.
- Missing, negative, or non-finite amounts must not become valid reference data.
- Missing or malformed policy settings must stop loading.
- Running from another directory must still find the default files.

### Task 1: Load and preview reference data

**Files:**
- Create: `procurement/__init__.py`, `procurement/references.py`
- Create: `config/company-rules.json`, `docs/policy-mapping.md`, `README.md`
- Test: `tests/test_references.py`

**Interfaces:**
- Consumes: supplied purchase-request.csv and company-rules.md (manual mapping).
- Produces: `load_purchase_request(path: Path = ...) -> dict[str, PurchaseRequestItem]`
- Produces: `load_company_rules(path: Path = ...) -> dict`
- Produces: `python -m procurement.references` preview, without supplier verdicts.

- [x] Write tests for supplied-file loading and each Review Focus failure mode.
- [x] Run `python -m unittest discover -s tests -v`; verify missing loader failure.
- [x] Implement the loaders, explicit policy settings, and readable preview.
- [x] Run the full suite; expect zero failures.
- [x] Run `python -m procurement.references`; expect five requested items and policy thresholds.
- [x] Review the mapping against every source rule and inspect the Git diff.
- [x] Commit on main as `feat: load purchase requirements and company policy (block 1)`.
- [x] Explain the code and pause before Block 2.
