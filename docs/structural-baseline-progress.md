# Structural baseline progress

Plan: docs/superpowers/plans/2026-11-05-structural-baseline.md
Base commit: f312151. User authorized implementation/retest/commit on main.

- Existing untracked video/ remains outside scope. No new runtime dependencies.
- Pre-flight: PdfPage gains optional PdfTable cells/outside-table text with defaults
  so existing metadata/field interfaces stay stable. Rules still consume fields.
- Test-first: four structural/component tests failed against the old parser:
  reordered columns, aliases/wrapping, concept-order durations, and refusing native
  text order as a table. Coordinate extraction and column mapping now pass them.
- Ruling: simple ruled grids only; merged/borderless/rotated or multi-item cases
  require review. This tests particular structural properties, not arbitrary layouts.
- Ruling: cell evidence cites unchanged entire page text, not reconstructed cell
  strings presented as contiguous source quotes. Cost: broader evidence excerpts.
- Removed full-sentence term patterns. Clauses retain their source text, duration
  operator/unit and explicit event references. Unknown residual tokens cannot pass.
- Removed available-on-request and known-section-set absence rules. Explicit
  labelled absence still rejects; failure to extract a fact requires review.
- Policy regression tests now use a controlled, unqualified payment fixture to
  isolate numeric boundaries. Original ten gold verdict/reason labels are unchanged.
  Old text-only table unit fixtures explicitly supply cell records; independent
  real synthetic PDF tests exercise coordinate extraction, with no production
  text-order fallback. Existing all-ten raw financial checks still pass unchanged.
- First revised full suite: 104 tests passed. Actual batch:6/10 verdict/rule matches,
  three automatic rejections, seven reviews, four extra escalations, zero approvals.
- Added explicit metrics for coverage, conservative escalations, unsafe approvals
  and incorrect automatic decisions. Normal CLI reports differences without failing;
  --check-labels provides strict comparison and currently exits1. Tests failed before
  these metrics/flag were implemented and now pass.
- Additional regressions reproduced ignored Unicode words and price qualifiers;
  whole Unicode tokens and unexplained header qualifiers now force review. Initial
  fixtures covered already-conservative paths (combining marks/header overflow),
  so refine to plain Unicode letters and correctly sized cells to verify RED/GREEN.
- No evaluation labels were changed or expected answers fed into extraction.
- Independent review: three Important findings (unconsumed/conflicting percentages,
  cross-obligation duration subjects, and an unreadable second table concealed by
  a valid table). Four rule regressions plus a real-PDF extra-table property test
  reproduced these and a related foreign-currency summary issue before fixing.
- Fixed: consume only recognized advance percentages; validate any balance portion
  against the agreed advance and 100%; use obligation-specific residual vocabulary;
  flag apparent item headers outside consumed grids without parsing their text rows;
  refuse unexplained/foreign summary currency qualifiers. Full suite:110 passed.
- Final review minor (deferred): full-page financial evidence is broad. Keep it
  exact rather than fabricate a contiguous excerpt for spatially reordered cells;
  narrower trustworthy context can be added later. This limit is in README.
- Final actual batch:6/10 exact verdict and rule-set matches;3/10 automatic decisions,
  all correct rejections;7/10 reviews;4 conservative escalations;0 approvals.
  Zero unsafe approvals here does not establish safety. Gold labels are unchanged.
- Verification: all ten original PDF byte sequences match f312151. Git reports no
  sample-data or manual-label changes. Every extracted/finding evidence excerpt
  was checked against its referenced original page. video/ remains outside scope.
- Ruling: normal CLI success means a report was produced, not that gold labels
  matched. --check-labels is explicit strict evaluation; current differences exit1.
