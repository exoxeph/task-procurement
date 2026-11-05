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

Next: Block 2, the shared fact contract, cautious term guards, JSON schema and
general extraction prompt. Do not claim Ollama extraction is available yet.
