# Implementation progress

## Working agreement

Implement the baseline's ten blocks on main. After each block, verify, commit,
explain, and pause. User authorization takes precedence over skill defaults
that normally use a worktree, request another plan confirmation, or continue
through all tasks. The ten-block plan in chat is the approved scope.

## Block 1

- Status: complete; explanation and requested pause delivered.
- Plan: `docs/superpowers/plans/2026-11-05-block-01-reference-data.md`.
- Pre-flight: no existing application or shared code interfaces.
- Ruling: initialize Git on main because this directory was not a repository.
- Ruling: implement inline; no agent delegation is needed for this small block.
- Ruling: policy settings are a manual transcription; changing the original
  Markdown requires reviewing and updating the configuration and mapping.
- Ruling: reserve interpretation of an insufficient penalty for human review;
  the source does not assign its severity explicitly.
- Verification: `python -m unittest discover -s tests -v` passed all 18 tests.
- Verification: `python -m procurement.references` loaded five requested items
  and the policy thresholds without issuing supplier verdicts.
- Test-first record: initial discovery failed because the procurement module
  did not exist. After implementation, one test's case-sensitive message match
  failed on `Quantity`; fixed the assertion to match case-insensitively.
- Independent review: no critical or important issues reported; reviewer also
  ran the full suite successfully.
- Deferred minor: optional tests for fractional policy days, reversed delivery
  limits, and an incorrect uncertainty decision; those validations already exist.
- Git handling: mark PDFs binary to preserve their bytes and avoid text
  normalization of the supplied ASCII-encoded PDF files.

## Block 2

- Status: complete; explanation and requested pause delivered.
- Plan: `docs/superpowers/plans/2026-11-05-block-02-pdf-text.md`.
- Pre-flight: independent of Block 1; later extraction blocks will consume
  the source path, page numbers, text, and extraction issues.
- Ruling: continue inline on main and pause at this block's boundary, as requested.
- Baseline: all 18 existing tests passed before changes.
- Ruling: use native PDF content order and preserve extracted text unchanged;
  this is not a guarantee of visual reading order for arbitrary layouts.
- Test-first record: new PDF tests failed because `procurement.pdf_text` did
  not exist, then passed after implementing the reader.
- Verification: full suite passed 32 tests (18 existing, 14 new).
- Ruling: repaired PDFs return available text with an explicit extraction issue;
  unreadable or locked PDFs raise PdfReadError. Neither produces a supplier verdict.
- Verification: preview printed sample 01 with its page reference. All ten
  supplied PDFs read as one page each with no known extraction issues.
- Verification: all 16 sample files are unchanged; all ten PDF byte sequences
  match the originals in the previous commit.
- Independent review: no critical or important issues; reviewer reran all 32 tests.
- Deferred minor: optional direct equality test against native extraction output
  and a mixed valid/missing-path CLI continuation test. Current tests cover
  extracted evidence, page ordering, clean CLI success, and individual failures.

## Block 3

- Status: complete; paused before Block 4.
- Plan: docs/superpowers/plans/2026-11-05-block-03-supplier-details.md.
- Pre-flight: consumes the unchanged PdfDocument/PdfPage interface from Block 2;
  no modifications to the PDF reader or reference loaders are needed.
- Ruling: continue on main with a single commit and pause as explicitly requested.
- Ruling: declare baseline template assumptions and unsupported identifier/date
  formats rather than claim arbitrary-layout support or legal ID validation.
- Ruling: not_found is an extraction state, not a confirmed policy violation;
  missing-registration policy interpretation belongs to Blocks 6-8.
- Test-first record: new tests failed because procurement.supplier_details did
  not exist. The first implementation then passed all 48 tests (16 new).
- Verification: hand-checked six fields for all ten supplied documents; pack 08
  retains missing TIN/BIN without invented evidence. Exact page excerpts,
  filename independence, conflicts, unsupported values, and CLI issues are tested.
- Regression: a new test showed ordinary words `tin 123` and `bin 456` could
  become registration fields. Root cause was overly broad label patterns.
  Restrict TIN/BIN labels to a following colon or line end; document that
  supported syntax and verify the regression changes from failing to passing.
- Independent review: no critical or important findings in the original 48-test
  implementation. The final label-context fix is additionally verified by the
  new regression test and full suite.
- Deferred minor: extend exact-evidence assertions to all ten packs and add a
  two-page conflicting-value fixture. Current tests check all six values across
  the ten packs, exact evidence on pack 01, conflicts, and explicit page numbers.
- Final verification: all 49 tests passed. A separate verification pass checked
  every evidence substring against its referenced page across all ten PDFs and
  confirmed their original bytes are unchanged. All present fields matched;
  pack 08 correctly has four found fields and two not_found registration fields.
- Preview: pack 01 exits 0 with values and evidence; pack 08 exits 1 with
  not_found TIN/BIN. This signals extraction attention, not a policy verdict.
