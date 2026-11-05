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

## Block 3: local Ollama extraction and saved runs complete

- Added approach2/extractor.py: one local /api/chat call per PDF using qwen2.5:7b,
  temperature 0, a 16,384-token context and an 8,192-token output limit. The
  original text of every page and all detected table cells go into the request.
- The general prompt and compact JSON Schema are sent together. The real local
  service accepted the schema's shared $defs references. No new SDK is installed.
- Validation failures, refusals, unavailable models, connection/timeouts, duplicate
  JSON keys, invalid responses, wrong returned models and truncation/context
  pressure yield visible unresolved runs. No retry, remote fallback or download.
- A conservative input-byte guard rejects large documents before sending instead
  of slicing them. Returned prompt/output counts and completion reasons are also
  checked. These checks do not establish that the model understood the whole text.
- Added shared/runs.py: UUID identity, UTC creation time, SHA256 of original PDF,
  validated facts, original source and raw model answer saved without overwrites.
  AI metadata retains model/digest, Ollama version, prompt/schema/request hashes,
  elapsed time, options, token counts and errors. Metadata lookup failures are
  warnings and do not discard an otherwise valid extraction.
- Added --approach approach1|approach2|both, --model, --ollama-url, --timeout and
  --artifacts. Default baseline operation has no model-service dependency. Both
  mode writes separate reports; a combined comparison view is still Block 5.
- Batch processing continues after provider failures. CLI exits 1 for execution
  failure, while ordinary policy review/rejection remains a valid result.
- Evaluation retains original-path input failures in the attempted denominator.
  A completely failed AI extraction is not scored correct merely because human
  review happens to match the manual verdict. Failure counts appear in HTML/CLI.
- Integration exposed a schema-contract issue: item_count != 1 could leave a
  selected item's values found. A failing regression now ensures the six item
  fields become unresolved instead. Independent document-wide checks remain.

Verification performed:

- Observed new APIs/tests fail before implementing requests, run storage and
  failure-inclusive evaluation. Failure handling tests use a fake HTTP boundary;
  no model is needed for the unit suite.
- Reproduced and fixed an optional metadata parsing failure that discarded an
  otherwise valid result, and an HTML omission of extraction failure counts.
- Verified batch continuation after the first AI request fails, separate reports
  in both mode, four saved artifacts for two documents/two approaches, baseline
  operation without network, no file overwrite, and source-hash/run-ID changes.
- All 148 tests passed. The actual ten-PDF baseline CLI remains 6/10 verdict and
  rule-set matches, three Reject and seven human review, with no execution failures.
- Real local service: Ollama 0.40.14, qwen2.5:7b digest
  845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e.
- Real pack 09 run: about 68.54 seconds end-to-end; 2,065 prompt tokens and 3,387
  generated tokens. Printed line amount 322,000 was retained (not repaired to
  320,000). Python reported the line arithmetic problem.
- The same run also produced nonliteral payment excerpts and conflicting delivery
  references; validation retained these as review issues. Its final human-review
  verdict matched the manual label (1/1), but its rule set did not (0/1). This is
  an integration check, not the ten-document AI benchmark or proof of generality.
- Raw model output and validated facts are in ignored reports/block3-smoke/;
  the HTML is reports/approach2-smoke.html. All retained excerpts were checked
  against the original pages. Original samples and config remain unchanged.

Ruling: add conservative byte preflight alongside planned provider token checks;
this reduces silent-truncation risk without claiming to have an exact tokenizer.
Record metadata GET requests separately from the one extraction POST. Retain
metadata warnings without redoing inference. No prompt tuning or extra model run
was used to replace the first integration result.

API references checked during implementation:
https://docs.ollama.com/api/chat
https://docs.ollama.com/capabilities/structured-outputs

Next: Block 4, visible workflow stages and auditable human questions/corrections.
The full repeated ten-PDF AI comparison remains Block 5.


## Block 4 completed: workflow stages and recorded corrections

- Added shared/human_review.py: build_questions turns review findings into
  source-backed questions; apply_corrections validates and records a new assisted
  extraction. response_template supplies a deliberately incomplete starter.
- HTML now shows five workflow stages, affected facts, original page excerpts,
  response-file instructions, reviewer details and the corrected facts. All
  external text is escaped. Execution status is not a claim of semantic truth.
- Added --source-run and --review-response, together for exactly one explicit
  PDF. The saved extraction is loaded without inference. A valid response needs
  matching run ID and live PDF SHA-256, reviewer, ISO timestamp with offset,
  reason and corrections in the common fact shape. No policy/verdict overrides.
- Reused the strict JSON and fact readers in shared/extraction.py for both AI
  and review inputs. Shared code has no dependency on the AI extractor/schema.
- Original artifacts/raw responses remain unchanged; assisted runs have new IDs,
  source links and audit details. Only corrected fields' old validation errors
  are replaced; unrelated and whole-document problems remain. Rules run again.
- Findings now retain their existing affected-field names so questions do not
  guess from prose. No policy comparisons or verdict priorities changed.
- Successful assisted results and failed correction attempts are excluded from
  unassisted sample scores. No timer or automatic approval was added.

Verification: 159 tests passed with `python -m unittest discover -s tests -q`.
The real baseline CLI still produces 6/10 verdict and rule-set matches, three
rejects and seven reviews. Sample PDFs and config files are unchanged.

Demonstration: replayed the actual Block 3 AI artifact for pack 09 (no model call).
It remained pending with seven questions before correction. A response explicitly
labelled **Codex demonstration, not an actual human review** fixed its literal
payment excerpts and delivery reference, while preserving ambiguous 30-90 day
payment terms and the condition 'as agreed by both parties'. Delivery became 28
days after PO. Printed line amount stayed 322000.0; arithmetic still failed.
All three extraction-validation issues were resolved, but payment ambiguity and
line arithmetic still require a person. The assisted result was excluded from
unassisted scores. Its report is reports/block4-assisted.html; demonstration
response and artifacts are under ignored reports/block4-smoke/. The original
artifact SHA-256 before and after was
9c50529239b59af12e0cb27880a099e2f321eb01d333ebe4998bf746837c9cd0.

Ruling: require an explicit --source-run alongside --review-response, instead of
rerunning extraction or guessing an artifact by UUID. This makes the original
review target unambiguous and avoids inference; it costs one additional CLI flag.
Ruling: a correction may replace its own old field-validation issue, while
unrelated/whole-document issues survive. Correcting one fact must not clear an
unsupported input or unrelated ambiguity. Some cases therefore remain pending.

Next: pause for explanation. Block 5 is the full AI comparison and interview
materials; it has not been run as part of this block.
