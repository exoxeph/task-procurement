# Approach 2 implementation progress

Plan: docs/superpowers/plans/2026-11-05-approach2.md

## Block 1: folder split complete

- Baseline commit before implementation: 46c7bf5.
- Moved baseline-specific extraction into procurement/approach1/.
- Moved PDF reading, facts, references, rules, evaluation and reporting into
  procurement/shared/.
- Added approach1/extractor.py to collect the three existing extractors' facts.
- Kept procurement/review.py as the main entry point. Its review_document()
  function now visibly reads a document, extracts facts and checks the rules.
- Created an empty approach2 package for the future Ollama extractor; no AI
  behavior is implemented in this block.
- Moved tests to matching subfolders and updated import paths, module preview
  commands and file-relative reference paths. Updated the README code map.

Verification performed:

- Before: 110 tests passed; baseline CLI matched 6/10 verdicts and rule sets.
- New workflow test initially failed because the new extractor package did not
  exist, then passed after the move. The reference-loading test initially used
  a formatting-specific expected string (20 instead of the existing 20.0);
  corrected it to compare Decimal values, without changing production policy.
- After: python -m unittest discover -s tests -q passed all 112 tests.
- The real CLI processed all ten PDFs: 6/10 verdict and rule matches, three
  automatic rejections, seven human reviews and four additional escalations.
- Every document's complete fields, evidence, findings and verdict matched the
  pre-move snapshot under ignored reports/before-move-facts.json.
- Defaults loaded correctly from a temporary working directory.
- Original sample files and config/ have no changes against 46c7bf5.
- Git whitespace checks passed. Unrelated video/ remains untouched.

Ruling: follow the user's explicit main-branch and pause-after-block preferences.
Use native PowerShell/Python bookkeeping in place of Bash skill helpers because
the plan uses Block headings and the current shell is PowerShell. Final independent
review is due after the complete implementation, as specified by the native
execution workflow.

## Block 2: fact contract, guards, schema and prompt complete

- Extended ExtractedField with optional original wording, reference event,
  conditions and numeric bounds. Added ExtractionRun for facts, issues and run
  metadata. Existing three-argument field construction remains valid.
- Defined all 32 fact names centrally and added shared source/numeric validation.
  Unsupported facts become unresolved. Exact evidence confirms traceability,
  not semantic correctness; a dedicated test demonstrates that limit.
- Adapted the baseline aggregator to return ExtractionRun and retain its known
  reference events and explicitly supported BDT currency. The workflow carries
  extraction issues into review and retains the run on the final result.
- Added shared guards for reference events, ranges, conditions, currency and
  contradictory reference fields. A 60-day interval after invoice does not become
  a late-delivery rejection. Independent definite violations still reject.
- Uncertain raw clauses cannot be hidden behind a simple parsed duration. Penalty
  absence requires explicit evidence and cannot reject when qualified by unresolved
  conditions. Human review remains conservative for missing registration/penalty.
- Added approach2/schema.py: standard JSON Schema plus readable local validation,
  including duplicate-key/nonfinite JSON rejection and per-field error reporting.
- Added approach2/prompt.txt: zero-shot extraction instructions, preserving actual
  figures, conditions, conflicts, page evidence and unresolved information. It has
  no sample answers or company thresholds.
- Report fields now display raw wording, reference events, bounds and conditions
  with HTML escaping. Updated the README to describe current implementation status.

Verification performed:

- New schema/contract tests failed on missing APIs before implementation.
- New policy tests reproduced false approvals for reference/condition/range
  changes and false rejections for unsupported currency, then passed with guards.
- Added regression cases for qualified penalty absence, conflicting references,
  ambiguous raw clauses and escaped term metadata. Observed failures before fixes.
- All 132 tests passed. Tests run without a model or network connection.
- The real ten-PDF CLI still matches 6/10 verdicts and rule sets: three Reject,
  seven human review. All previous fact values, statuses, evidence, findings and
  decisions matched the pre-move snapshot; added metadata validates with no issues.
- Original sample/config files remain unchanged. Whitespace checks passed.

Ruling: test the prompt's integration into actual model requests in Block 3 rather
than asserting literal wording in a test_prompt.py file. Reading the prompt and
testing real request construction gives useful coverage without prose snapshot tests.
Use a shared JSON Schema $defs fact definition to avoid repeating the same shape
32 times in model input; verify provider acceptance during Block 3 integration.
No schema or evidence check guarantees that the model understood the text correctly.

Next: Block 3, local Ollama calls, bounded failure handling and saved runs. No AI
extraction results have been measured yet.
