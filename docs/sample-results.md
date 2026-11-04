# Structural baseline: current sample results

All ten PDFs were visible during development. These are not unseen results.
Manual gold verdicts and triggered-rule labels are unchanged from commit f312151.
Human review on an expected Approve/Reject is an escalation, not a correct match.

| Document | Manual verdict | Actual verdict | Rules match | Actual findings |
| --- | --- | --- | --- | --- |
| supplier-pack-01.pdf | Approve | Needs a person to check | No | payment |
| supplier-pack-02.pdf | Approve | Needs a person to check | No | extraction_delivery_days |
| supplier-pack-03.pdf | Reject | Reject | Yes | price |
| supplier-pack-04.pdf | Needs a person to check | Needs a person to check | Yes | price |
| supplier-pack-05.pdf | Reject | Reject | Yes | advance |
| supplier-pack-06.pdf | Reject | Needs a person to check | No | penalty_unclear |
| supplier-pack-07.pdf | Needs a person to check | Needs a person to check | Yes | quantity |
| supplier-pack-08.pdf | Reject | Needs a person to check | No | penalty_basis, registration_unclear |
| supplier-pack-09.pdf | Needs a person to check | Needs a person to check | Yes | line_arithmetic, payment |
| supplier-pack-10.pdf | Reject | Reject | Yes | delivery, vat_display |

Exact verdict matches: 6/10. Exact triggered-rule set matches: 6/10.
Automatic decisions: 3/10 (three Reject). Human review: 7/10.
Additional conservative escalations: 4. Incorrect automatic decisions: 0.
Unsafe approvals: 0; there are no approvals, so this alone is not a safety claim.

## Why the four additional escalations?

- 01: payment is tied to delivery and acceptance. The small component grammar
  cannot establish that timing confidently, so it preserves the clause for review.
- 02: the delivery clause includes a factory-location qualification outside the
  deliberately small vocabulary. It is not silently discarded.
- 06: no penalty clause is extracted. The old known-section-set inference is gone;
  absence is now unresolved without an explicit statement.
- 08: no TIN/BIN is extracted. The old available-on-request special case is gone.
  Unproven registration absence needs review, alongside the unclear penalty basis.

The previous 10/10 template-shaped result is historical. Structural improvements
are demonstrated only by tested transformations: reordered columns, reversed PDF
insertion order, wrapped cells, aliases, extra columns and numeric changes.
Unsupported grids/extra rows, unknown currency/qualifiers, residual words, conflicting
percentages and obligation mismatches require review. This does not establish
generalization to new suppliers. Metadata parsing remains heuristic.

Reproduce: `python -m procurement.review`. Add `--check-labels` to return exit1
for these disclosed label differences; the HTML report is written either way.
Run regression/property tests: `python -m unittest discover -s tests -q`.
