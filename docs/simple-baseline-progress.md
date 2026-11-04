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
- Stage 1 committed: 0969d15.
- Stage 2: rule tests failed for missing procurement.rules, then all 12 policy
  tests passed. They exercise all ten verdicts, numeric boundaries, bad identity,
  uncertain extraction, arithmetic and reject precedence. Full suite: 84 passed.
- Ruling: absent penalty rejects only for explicit absence or a recognized complete
  terms section with no penalty wording. Unknown wording requires human review.
- Ruling: Decimal arithmetic rounds calculated monetary amounts to cents using
  ROUND_HALF_UP; raw stated figures are retained. All applicable findings remain.
- Stage 2 committed: ed868f4.
- Stage 3: report tests failed for missing evaluation/report modules. Implemented
  standalone escaped HTML, batch CLI, manually labelled verdict/rule comparison,
  README, sample-results table, one-page note and Loom script.
- Independent whole-change review found five Important issues: qualified clauses
  accepted by substring, contradictory advance zero hiding a positive amount,
  malformed percentages matched as positive suffixes, conflicting price tax notes
  ignored, and oversized Decimal values causing arithmetic failure. No minor
  findings were reported.
- Final fixes: five new regression tests failed first (including percentage
  subcases), then passed. Match complete supported payment/delivery/validity/penalty
  wording, collect every advance candidate, validate full percentage tokens,
  review uncertain tax notes, and bound numeric size/precision before arithmetic.
- Ruling: numbers below 1 trillion and up to six decimal places are supported;
  larger values require review. Cost: unusually large valid quotations need a
  person rather than automatic approval. This keeps Decimal calculations safe.
- Ruling: dedicated penalty/VAT/registration checks report their own uncertainty;
  avoid duplicating the same problem under generic extraction codes. Price-note
  uncertainty gets its own check. Cost: findings are grouped by business rule.
- Final suite: 94 tests passed. Actual default batch: 10/10 verdict matches and
  10/10 triggered-rule set matches; two Approve, five Reject, three human review.
- Verification: Git reports no sample-data changes and all ten PDFs match their
  original committed bytes. A raw text-file byte comparison encountered normal
  Windows CRLF checkout conversion; use Git's normalized diff for those files.
  All field and finding evidence matches its source page on all ten PDFs.
  Generated reports are ignored. video/ remains untouched and outside commits.
