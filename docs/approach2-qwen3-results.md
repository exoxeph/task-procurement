# Approach 2: Qwen3 14B model-only rerun

On 2026-11-05, Approach 2 was switched to local `qwen3:14b` and rerun on
supplier packs 01–05. This follows the user's five-PDF extraction investigation.
It is a separate experiment from the earlier ten-document Qwen2.5 results.

## What changed

- Default Approach 2 model: `qwen2.5:7b` → `qwen3:14b`.
- Default extraction/workflow timeout: 180 → 600 seconds. The first 14B call
  took 327.52 seconds, exceeding the previous timeout.
- No prompt, schema, document input, generation options or policy changes.
- The five saved request objects were checked against the previous five-PDF
  run: their only difference is the model name. Both use temperature 0,
  context 16384 and output limit 8192. No explicit `think` setting was supplied.
- One call per PDF, without retries, fallback or human corrections.

Ollama version was 0.40.14. The 14B model digest is recorded in the metrics.
During the run, Ollama reported a 12 GB runner with 6% CPU / 94% GPU placement.
Times include model loading and metadata collection and are observations on this
machine, rather than a controlled hardware benchmark.

## Results on the same five PDFs

| Metric | Qwen2.5 7B | Qwen3 14B |
| --- | --- | --- |
| Audited fact matches | 112/135 | 112/135 |
| Extraction time | 290.06 seconds | 1483.51 seconds |
| Input/provider execution failures | 0 | 0 |
| Verdict matches after unchanged rules | 2/5 | 2/5 |
| Complete finding-set matches | 0/5 | 0/5 |

Fact matching includes status, normalized value, duration starting event, bounds,
conditions and exact source evidence. It measures the full field contract;
it is not a score of whether a number looks sensible in the raw answer.
There are 27 audited fields per PDF; raw clause boundaries and price-note wording
are excluded. All 32 requested fields remain visible in the extraction report.

Qwen3 improved several raw outputs:

- It returned the correct item codes and quantities for all five PDFs, checked
  against the existing labels. PDF 1's table citations still fail validation.
- PDF 3: `800` replaces `s800`, item code C is found, and both payment fields
  consistently indicate 40 days after delivery.
- PDF 4: `50,000`, `30`, `28` and `40` replace the earlier quantities/durations
  with erroneous S prefixes. Item code D is found.
- Delivery-day fields match 5/5, compared with 3/5 previously; penalty-clause
  fields match 5/5, compared with 2/5 previously.

Other errors offset those improvements:

- Percentage values such as `15%`, `10%` and `40%` violate the requested decimal
  string convention, so the numeric validator marks them unresolved. VAT rate
  and advance percentage each match 0/5 under the existing contract.
- PDF 1 reconstructs table citations such as `Qty\n12,000`; these are not
  contiguous quotations from the original PDF text. Its payment reference also
  confuses the advance-payment event with the balance-payment event.
- PDF 5 still has nonliteral payment evidence. Its `40%` advance value cannot
  pass the numeric contract, preventing the original advance violation from
  supporting an automatic rejection.

Applying the existing rules to the saved answers, without calling AI again,
changes which documents match: PDF 3 now rejects correctly, but PDF 5 becomes
human review. Both models match PDFs 04 plus one of 03/05. The finding-set metric
also counts additional uncertainty findings; 0/5 does not mean all checks fail.

This run shows specific extraction improvements, with no improvement in the
aggregate field or verdict scores and roughly five times the extraction time.
It does not establish unseen-document accuracy. All five documents were already
development-visible, the source-audited labels were unchanged, and this was one
run per model with no training or independently human-validated test set.

## Inspect the outputs

The generated artifacts are local and ignored by Git:

- `reports/extraction-only-20261105T074751Z/extraction.html`: all raw AI fields
  beside Python validation, with separate input/request/raw JSON files.
- `reports/extraction-only-20261105T074751Z/model-comparison.html`: extraction
  metrics for these two five-PDF runs.
- `reports/extraction-only-20261105T074751Z/policy-comparison.html`: unchanged
  rules applied offline, with links to each model's full findings.
- `reports/extraction-only-20261105T070244Z/`: the original five-PDF 7B run.

Tracked [metrics](approach2-qwen3-metrics.json) record per-field and per-document
counts, issues, run IDs, model digests and request hashes. Historical ten-PDF
results in `approach2-results.md` remain unchanged.
