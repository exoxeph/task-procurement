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


## Block 5 completed: comparison and interview materials

- Source-audited 270 facts (27/PDF) from all ten original PDFs before the full
  experiment predictions; the earlier pack09 integration exposure is disclosed.
  Raw clauses, source pages, normalization conventions and allowed equivalent
  representations are recorded in config/manual-facts.json. Codex performed the
  audit; this is not independent human annotation. No fact is flagged disputed.
- Added whole-fact evaluation, per-field breakdowns, failure-inclusive denominators,
  confusion counts, wrong decisions, coverage, reviews, timing and returned usage.
  Same-basename uploads and assisted decisions remain excluded from sample scores.
- Both mode now writes one combined comparison, separate source-evidence reports
  and machine-readable metrics. All three batches are saved under reports/block5/.
- Froze model/prompt/schema/options/config/inputs, ran three serial full batches,
  and kept the first attempted batch as headline. Original artifacts and model
  answers remain unchanged. Every saved prediction was rescored with one final
  evaluator, without inference retries, replacement answers or prompt tuning.
- Headline Python: 6/10 verdicts, 6/10 complete rule sets, 267/270 whole facts,
  three rejects/seven reviews, zero wrong automatic decisions, zero failures.
  Headline Qwen: 5/10 verdicts, 0/10 complete rule sets, 224/270 facts,
  two rejects/eight reviews, zero wrong automatic decisions, zero failures.
  Neither approved anything; zero wrong approvals is not proof of safety.
- Qwen repeat2/repeat3: 5/10 verdicts and 0/10 rule sets in both; 220/270 facts
  in both. Verdicts stayed identical, but actual finding sets changed in packs
  04,05,06,08 versus run1. Temperature zero did not eliminate variability.
- Qwen recorded extraction seconds: 573.71, 555.42, 550.73. Prompt tokens 20,526
  each; output tokens 33,356, 33,414, 33,414. Parent-observed wall seconds:
  574.67, 556.39, 551.72. Local API token bill is absent; hardware/runtime costs
  remain. GPU name observed locally: AMD Radeon RX 7700 XT; not a controlled
  hardware performance benchmark.
- Qwen recovered pack02's 21-day factory-delivery clause, but missed item codes,
  generated malformed numeric strings and confused payment references. The
  source-inspected errors and limits are in docs/approach2-results.md. This setup
  did not outperform Python; no claim that AI is necessary for these ten PDFs.
- README, one-page submission note and five-minute presentation guide now reflect
  the measured comparison, human workflow and limitations. Compact metrics and
  frozen settings/hashes are tracked in docs/approach2-metrics.json and
  docs/approach2-experiment.json; raw reports/artifacts remain Git-ignored.

Independent final review checked all270 labels against the source PDFs, reproduced
headline metrics, and confirmed all three repeat records and documentation.
It found three Important synthetic/adversarial gaps (none observed on the ten
originals): model row-count claims could hide extra detected rows, ambient proxies
or redirects could defeat loopback-only routing, and HTTPException could escape
batch failure handling. All three were reproduced RED then fixed GREEN in one
pass. Shared source row-count validation now uses generic column concepts across
pages/tables; the network opener disables proxies and redirects; transport and
optional-metadata handlers contain HTTPException. Unrecognized/borderless layouts
still cannot be guaranteed detected. Shared column recognition moved from the
baseline into table_layout.py without adding baseline fact fallback to AI.

Ruling: retain historical frozen inference code hashes and append explicit
post-experiment hardening hashes. All three inference processes imported the
original frozen modules before the defensive edits. Prompt/schema/model/input/
config stayed unchanged. All30 stored raw responses were parsed using the final
validator: every stored field remained identical. No model output was replaced.
A separate final hardened-client smoke on pack02 completed with no execution
failures, retained its review result, and is excluded from benchmark repeats.

Ruling: the field score covers status, normalized value, duration anchors, numeric
bounds and declared condition alternatives. Redundant equal bounds normalize to
scalars; non-duration event metadata is not scored separately from reference-field
values. Raw clause boundary/price-note wording is unscored. Strict condition text
can still undercount equivalent paraphrases; disclose this as whole-fact agreement,
not an automatic semantic-truth proof. Incorrect scoring conventions would limit
comparability, which is why conventions and source labels are explicit.

Ruling: no new independent dataset or external human audit is invented. The
reviewer's declined-to-judge items (unseen accuracy and independent human
annotation quality) remain explicit limitations, with future new-document testing
recommended. No deferred minor findings.

Final verification: 173 tests passed; actual final baseline CLI unchanged; actual
final local AI CLI succeeded (review is a valid outcome); proxy/redirect loopback
HTTP integration checks passed. Original PDFs/purchase request/company rules/
manual verdict labels/config policy compare unchanged against 46c7bf5. All30
model digests match the frozen digest; all have zero metadata warnings. No
unrelated video, generated reports, credentials or scratch files are staged.

Block 5 is ready for its verified main commit and user explanation. All planned
implementation blocks are complete; no recording or publication was requested.


Execution decisions retained from the completed scratch ledger:
- Native PowerShell/Python bookkeeping replaced Bash-only skill helpers; progress
  was preserved in tracked documentation. Cost: fewer automatic helper checks,
  compensated by explicit test/commit records.
- Main-branch commits and pauses follow the user's preference. Cost: no branch
  isolation; verified commits provide the review/recovery boundaries.
- Actual HTTP request/schema integration tests replaced brittle prompt-text checks;
  compact schema references were verified against the installed Ollama. Cost:
  behavior checks do not certify every natural-language instruction.
- Conservative input-byte and returned-token guards refuse uncertain large inputs;
  optional metadata failures remain warnings. Cost: some usable inputs can be
  escalated and missing metadata cannot prove a frozen model identity.
- Human correction requires an explicit saved-run path and removes only that
  correction's field-local errors. Cost: an extra flag and intentionally pending
  unrelated/global issues.
- The first full batch is headline, all batches are rescored consistently, and
  strict whole-fact scoring conventions remain explicit. Cost: scores are limited
  to these development documents and declared equivalence conventions.
- Post-review defensive fixes retain original inference hashes and raw outputs.
  Cost: reproducing historical inference code uses the recorded base commit;
  current code includes the separately recorded guards.
