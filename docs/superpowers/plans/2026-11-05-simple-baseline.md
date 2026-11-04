# Simple Baseline Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task.

**Goal:** Finish an understandable, evidence-backed Python procurement baseline.
**Architecture:** read PDF -> extract facts -> check rules/decide -> HTML report.
**Tech Stack:** Python 3.11, existing PyMuPDF, standard library.
**Spec:** docs/superpowers/specs/2026-11-05-simple-baseline-design.md

## Constraints and review focus

Main, one commit per stage; user authorized all stages without pauses. Preserve
samples and video/. Keep public extraction APIs and raw evidence. Do not claim AI
or unseen accuracy. Review unclear/missing clauses, exact numeric boundaries,
wrong request identity, conflicting values, HTML escaping, and malformed inputs.

### Stage 1: Simple extraction

- [x] Run 68 existing tests as the refactor safety net.
- [x] Move duplicated field resolution and CLI preview to extraction.py; rewrite
  financial extraction as a sequential line walk with one table reader.
- [x] Add tests for extract_terms(document): all ten terms, exact evidence,
  unsupported/missing/conflicting clauses. Observe failure before implementation.
- [x] Implement terms.py, retaining uncertain statuses; run full suite.
- [x] Commit refactor: simplify extraction and finish contract terms.

### Stage 2: Rules and decisions

- [x] Write failing tests for check_rules(document, fields, items, policy),
  exact price/quantity/payment/delivery/advance/validity/penalty boundaries,
  arithmetic, missing registrations, ambiguity, and verdict precedence.
- [x] Implement rules.py with Finding and ReviewResult records; Decimal conversion
  and rule checks stay together. Retain all findings with source evidence.
- [x] Add review_document(path, items, policy) in review.py as the four-step entry.
- [x] Run all tests and commit feat: check procurement rules and explain verdicts.

### Stage 3: Report and evaluation

- [ ] Write failing tests for a report containing reasons/excerpts and escaped
  HTML, mixed invalid/valid PDFs, and manual expected verdicts/triggered rules.
- [ ] Implement python -m procurement.review [paths] --output report.html, default
  all ten supplied PDFs, one local HTML report with readable document details.
- [ ] Add manual labels and evaluation; report sample accuracy as development
  results. Add a one-page note and presentation script; rewrite README as a
  concise run guide and code map matching the final implementation.
- [ ] Run the full suite and actual batch command; independent final code review,
  fix substantive findings with regression tests, verify samples unchanged.
- [ ] Commit feat: add review report and sample evaluation; report outcomes.
