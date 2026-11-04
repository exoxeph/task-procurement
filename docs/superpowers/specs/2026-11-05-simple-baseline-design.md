> Historical design. Extraction and evaluation are superseded by
> 2026-11-05-structural-baseline-design.md after the overfitting correction.

# Simple Python baseline

The user chose a simpler Python baseline and authorized completing all three
stages now, with a commit per stage on main. This supersedes the ten-block
sequence and its pauses. Existing sample files and unrelated video/ stay intact.

## Approaches

Chosen: simplify deterministic extraction and share one rules engine with a
future AI extractor. Alternative: replace extraction with AI now. The user chose
the baseline first. The baseline is not itself the AI system requested by the
brief; README and the submission note must state that limitation honestly.

## Four fixed steps

Read PDF -> extract facts -> check rules and decide -> show evidence.

1. Extraction: retain public supplier/financial APIs and their tests. Share field
   resolution and CLI preview. Financial extraction walks lines once, consumes
   tables, then reads totals; no line-offset record or table-line bookkeeping.
   Add a short terms parser for the supplied numbered Payment/Delivery/Delay/
   Validity sections. Unsupported or contradictory wording remains unresolved.
2. Rules: one check_rules(document, fields, requested_items, policy) function
   converts numbers locally, checks request identity/item/units and every company
   threshold, validates arithmetic with Decimal, collects findings, and applies
   Reject > Needs a person to check > Approve. Uncertain facts require review.
   Absence claims cite the actual inspected registration/terms text, not invented
   excerpts. Missing TIN/BIN is a rejection only for an explicit missing-details
   statement in this supported template; otherwise unresolved extraction is review.
3. Demo/evaluation: a CLI writes a standalone local HTML report with fields,
   reasons, evidence, source text, and batch results. HTML escapes document text.
   No web framework, hosted service, or workflow framework. Manual labels for all
   ten development-visible documents include reasons; compare verdicts and the
   expected triggered rules, not merely an aggregate accuracy number.

## Limits and readability

Native text, BDT, one item per table, known labels and numbered terms. No OCR or
claim of arbitrary supplier layouts. Preserve wrong raw figures; do not fabricate
missing VAT. Keep existing regression coverage while reducing helper layers.
Missing/weak penalty wording is conservative: explicitly absent clause rejects;
insufficient/unclear rate or basis requires review. Rules use the policy settings.
No external AI calls, publishing, pushes, or changes to video/. A presentation
script and one-page note support the user's own Loom recording.
