# Local AI comparison: measured development results

Experiment: qwen25-zero-shot-v1. Headline: the first full attempted run, including failures. All ten PDFs were visible during development; no model training, train/test split or unseen-accuracy claim. Later repeats are reported separately, never selected to improve the headline.

## First full run

| Metric | Python baseline | Local Qwen2.5 7B |
| --- | --- | --- |
| Verdicts | 6/10 | 5/10 |
| Complete rule sets | 6/10 | 0/10 |
| Automatic decisions | 3/10 | 2/10 |
| Human reviews | 7/10 | 8/10 |
| Audited whole facts | 267/270 | 224/270 |
| Wrong approvals / wrong rejections | 0 / 0 | 0 / 0 |
| Input / extraction failures | 0 / 0 | 0 / 0 |
| Sum of recorded extraction seconds | 0.04 | 573.71 |
| Returned prompt / output tokens | 0 / 0 | 20,526 / 33,356 |

Zero wrong approvals is weak evidence here: neither approach approved anything. Exact rule-set agreement includes extraction/qualification findings, so an extra uncertainty finding makes the entire set a mismatch even when a valid business violation was found.

## Per-document headline

| PDF | Original label | Python | Qwen | Qwen triggered findings |
| --- | --- | --- | --- | --- |
| supplier-pack-01.pdf | Approve | Needs a person to check | Needs a person to check | payment, pdf_issue, penalty_unclear |
| supplier-pack-02.pdf | Approve | Needs a person to check | Needs a person to check | extraction_advance_percent, extraction_issue, extraction_item_code, pdf_issue, penalty_unclear, qualified_validity_days, request_item |
| supplier-pack-03.pdf | Reject | Reject | Needs a person to check | extraction_item_code, extraction_quantity, payment, pdf_issue, request_item |
| supplier-pack-04.pdf | Needs a person to check | Needs a person to check | Needs a person to check | extraction_delivery_days, extraction_item_code, extraction_quantity, extraction_validity_days, payment, pdf_issue, request_item |
| supplier-pack-05.pdf | Reject | Reject | Reject | advance, extraction_delivery_reference, extraction_issue, extraction_payment_clause_text, extraction_payment_reference, payment, pdf_issue, penalty_unclear, qualified_delivery_days |
| supplier-pack-06.pdf | Reject | Needs a person to check | Needs a person to check | extraction_quantity, payment, pdf_issue, penalty_unclear |
| supplier-pack-07.pdf | Needs a person to check | Needs a person to check | Needs a person to check | extraction_advance_percent, extraction_delivery_days, extraction_item_code, extraction_quantity, extraction_validity_days, payment, pdf_issue, request_item |
| supplier-pack-08.pdf | Reject | Needs a person to check | Needs a person to check | extraction_issue, extraction_item_code, extraction_quantity, payment, pdf_issue, penalty_unclear, registration_unclear, request_item |
| supplier-pack-09.pdf | Needs a person to check | Needs a person to check | Needs a person to check | extraction_item_code, extraction_payment_clause_text, extraction_quantity, payment, pdf_issue, request_item |
| supplier-pack-10.pdf | Reject | Reject | Reject | delivery, extraction_item_code, payment, pdf_issue, request_item, vat_display |

## What the source audit shows

config/manual-facts.json contains 27 scored facts per PDF, 270 total, transcribed from the original PDFs before inspecting the full experiment predictions. Codex performed the source audit; it is not independent human annotation. Pack 09 had already been examined during integration and the correction demo. Raw source clauses are retained in the audit. Clause boundaries and price-note wording are excluded from numeric scoring. No fact is currently flagged disputed; alternative defensible representations were declared before the full experiment.

Whole-fact matches require the expected extraction status, normalized value, duration starting event, bounds and conditions. Decimal formatting and commas normalize; equal numeric endpoints and a scalar are equivalent. The event value in *_reference is scored as its value; redundant event metadata on non-duration facts is not scored. Only explicitly listed condition paraphrases normalize. Unlisted equivalent phrasing can therefore reduce this strict agreement score. A found value also needs an exact source excerpt. All expected unresolved fields and failed attempts stay in the denominator; disputed facts and assisted runs are counted separately and excluded.

The 267/270 baseline result is dominated by straightforward shared-template facts. It does not mean 98.9% unseen accuracy or eliminate the unresolved timing clauses. On the 30 duration facts alone, baseline matched 27/30 and Qwen matched 15/30. These are whole-fact agreements, including references and qualifiers.

## Source-inspected AI errors and useful behavior

- Pack 02: Qwen correctly read the factory-delivery wording as 21 days after PO, where the baseline left delivery unresolved. However, it missed the item code and attached numeric bounds to the categorical penalty-clause fact, so the document still required review. This is a useful language interpretation example, not proof of generalization.
- Pack 03: Qwen retained price 229 but missed item code C and generated quantity value "s800". Validation refused that number. Without an item match, Python could not apply the purchase-request price comparison, so the expected price rejection was not made.
- Pack 09: it kept the printed 322,000 amount instead of repairing it, and converted four weeks to 28 days after PO. It also generated quantity "S50000", chose one payment endpoint and invented a purchase-order anchor for a clause that lacks a delivery anchor. The invalid quantity prevented the line-arithmetic check. The range still caused review; this was not full correctness.
- Across the run, nine payment-duration facts and eight payment-reference facts disagreed with the audit. Exact source evidence does not catch every wrong interpretation: a genuine quotation can support an incorrect normalization.
- Packs 06 and 08 remain review when penalty or registration details cannot be established. Shared code distinguishes an absent extraction from proof of real-world absence. This conservative choice differs from historical manual verdict labels; those labels were not changed.

## Repeats

| Repeat | Verdicts | Full rule sets | Whole facts | Reviews | Execution failures | Extraction seconds | Prompt / output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| run1 | 5/10 | 0/10 | 224/270 | 8/10 | 0 | 573.71 | 20,526 / 33,356 |
| run2 | 5/10 | 0/10 | 220/270 | 8/10 | 0 | 555.42 | 20,526 / 33,414 |
| run3 | 5/10 | 0/10 | 220/270 | 8/10 | 0 | 550.73 | 20,526 / 33,414 |

All three Python repeats remained 6/10 verdicts, 6/10 full rule sets and 267/270 facts. Qwen verdicts were identical across repeats. Complete rule-set match scores also stayed at 0/10, but the actual finding sets changed for packs 04, 05, 06 and 08 between run 1 and later repeats. Whole-fact agreement varied from 220 to 224 out of 270 (81.5%-83.0%). Temperature zero did not eliminate extraction variability. Later runs 2 and 3 had the same scored fact outcomes. Every AI repeat made two Reject decisions (05, 10), eight reviews and zero approvals; all 30 attempts remain represented. Each repeat had zero input/extraction execution failures, despite its interpretation/validation issues.

The planned three batches took 574.67, 556.39 and 551.72 seconds wall-clock from their parent runner (including startup/reporting), versus the extraction-time sums above. These are local timings with model loading/caching effects, not a controlled hardware performance comparison.

## Frozen settings and reproducibility

Frozen before the full experiment: model qwen2.5:7b, Ollama 0.40.14, temperature 0, context 16384, output limit 8192, timeout 180 seconds, unchanged zero-shot prompt and schema. The selected model digest, exact input/config/file hashes and canonical schema hash are recorded in docs/approach2-experiment.json. Source/config files remain unchanged from the plan commit. The machine reports AMD Radeon RX 7700 XT and Ollama reported 100% GPU; this is a local measurement, not a controlled hardware benchmark. Local inference has no paid-token API bill; hardware, electricity and runtime are not free.

Three sequential invocations use distinct run directories:

```powershell
python -m procurement.review --approach both --output reports/block5/run1/comparison.html --artifacts reports/block5/run1/runs
python -m procurement.review --approach both --output reports/block5/run2/comparison.html --artifacts reports/block5/run2/runs
python -m procurement.review --approach both --output reports/block5/run3/comparison.html --artifacts reports/block5/run3/runs
```

The first batch started after the source labels/settings were frozen, while evaluation/report code was being completed. All saved artifacts are rescored offline with the same final evaluator, without another model call or changing the predictions. Original per-approach evidence reports remain available. Compact metrics and per-file rule sets are in docs/approach2-metrics.json; full raw responses, facts and HTML are under ignored reports/block5/. The earlier single-PDF integration smoke run is not one of these three repeats.

## Independent review and post-experiment safeguards

The independent reviewer checked the source labels and reproduced the first-run
metrics. It found three Important gaps using synthetic/adversarial inputs, none
observed in the ten originals: a model could hide a second detected item row,
ambient proxies/redirects could bypass the local-only destination promise, and
malformed HTTP responses could escape batch failure handling. Regression tests
first reproduced those failures, then passed after a shared source-row guard,
proxy-free nonredirecting opener and HTTPException containment were added.

All three inference processes had imported the frozen modules before those code
changes. Prompt/schema/model/settings/source inputs were unchanged. The manifest
retains the original hashes and records post-experiment hardening hashes; all
artifacts are rescored with the same final guard, without inference retries.
The new source guard recognizes item-column concepts, not arbitrary layouts;
it cannot prove the absence of an unrecognized or borderless item table.
Unseen accuracy and independent human-annotation quality remain unestablished.

## Decision

This particular local zero-shot setup did not beat the baseline. AI can interpret wording beyond a small grammar, but these measurements do not justify making it the default or claiming AI is necessary for these ten PDFs. The strong part of the demonstration is the shared policy engine, visible failure handling, source evidence, human correction audit and reproducible comparison. Future improvements should be a new named experiment, then be evaluated on genuinely new quotations. Do not silently tune against these results or present the best repeat as typical.

Final verification: 173 tests passed. The final baseline CLI retained its results; a separate hardened-client pack02 AI smoke completed without execution failure and stayed review. That smoke is excluded from the three-repeat comparison. All30 frozen raw responses were revalidated with final guards, preserving every stored field.
