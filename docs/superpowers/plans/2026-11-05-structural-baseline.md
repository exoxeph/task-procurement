# Structural baseline implementation plan

> Use superpowers:executing-plans with test-driven changes and final independent review.

**Goal:** Replace sample-shaped extraction assumptions and retest honestly.
**Spec:** docs/superpowers/specs/2026-11-05-structural-baseline-design.md
**Architecture:** native text + ruled table cells -> cautious facts -> policy -> report.
**Constraints:** main, no AI/dependencies, preserve samples/video, unchanged gold labels.

1. [x] Write and run failing structural/property tests. Add PdfTable and geometry
   extraction in table_layout.py/pdf_text.py; financial parser maps columns, not lines.
2. [x] Write and run failing component-based term tests. Replace full sentence
   patterns with section concepts, explicit components, and residual-word checks.
   Expose raw clauses/components; unknown wording remains unresolved.
3. [x] Remove sample-specific absence rules. Update behavioral tests for changed
   extraction scope; retain policy boundary/arithmetic tests and original labels.
4. [x] Evaluate original labels without tuning, add escalation/coverage metrics,
   update report/docs and save honest sample results.
5. [x] Run full suite and batch, independent review, verify fixes and untouched
   source data; commit on main and explain measured outcome and limits.

Review focus: false approval from incomplete geometry or conditional clauses;
duplicate headings, unsupported currency, mixed/extra rows, absent evidence,
unchanged gold labels, identity and arithmetic rules, honest CLI evaluation status.
