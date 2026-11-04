# Simple baseline progress

Plan: docs/superpowers/plans/2026-11-05-simple-baseline.md
Spec: docs/superpowers/specs/2026-11-05-simple-baseline-design.md

- User authorized all three stages now and commits on main; previous pauses
  superseded. Existing video/ is unrelated and untouched.
- Pre-flight: existing extractors all return ExtractedField; the rule checker
  consumes those same records, so no intermediate normalization layer is needed.
- Stage 1: existing 68 tests passed before refactoring. Shared resolve_field and
  preview eliminate duplication. Financial parser walks lines in source order,
  consumes each table once, and keeps original excerpts. Existing tests pass.
- Terms tests first failed for missing procurement.terms; implemented numbered
  terms parsing, explicit anchors, week conversion, unknown/conditional wording,
  and conflicting values. Full suite: 72 tests passed.
- Ruling: missing penalty basis requires review even when a percentage is present;
  numeric rates alone cannot establish an order-value-per-week promise.
