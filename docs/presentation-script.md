# Suggested Loom walkthrough (under five minutes)

## 0:00–0:40 — The problem

“A procurement employee receives supplier quotations and has to compare prices,
quantities and contract terms with company policy. A small mistake can mean
paying too much or accepting an unsafe contract. This tool reviews each document
in fixed steps and shows the evidence behind every decision.”

## 0:40–1:20 — Run it

Run `python -m procurement.review`, then open the printed HTML report path.
Show the batch summary: two approvals, five rejections, three human reviews.

“This is the deterministic Python baseline. The documents share a template, so I
first measured what ordinary code could handle. I have not added an AI model yet.
An AI version would replace the reader while using the same company checks.”

## 1:20–2:40 — Three useful examples

Open pack 03: show the price rejection and original table evidence.
“The quoted price is 229; the maximum is 210. It exceeds the allowed tolerance.”

Open pack 09: show the wrong line amount and unclear payment finding.
“The supplier wrote 322,000. The tool preserves that statement, calculates
50,000 times 6.40 separately, and flags the difference. It does not repair the
document and hide the mistake.”

Open pack 10: show the delivery rejection and separate VAT review finding.
“Even when one condition rejects a document, all other findings remain visible.
Missing VAT rows are never invented.”

## 2:40–3:35 — Explain the code

Open `procurement/review.py` and its `review_document()` function.
“Read PDF, extract supplier details, item figures and terms, then check rules.
These are ordinary functions in a fixed order. There is no autonomous agent.”

Open `procurement/rules.py`. Point to delivery thresholds and verdict priority.
“Numbers use Decimal so boundary comparisons are reliable. A human reviews
unknown wording. The source policy is separate from document extraction.”

## 3:35–4:30 — Testing and honest limits

Show `docs/sample-results.md` and the test command.
“The ten expected verdicts and triggered-rule sets match. All ten documents were
visible during development, so this is not an unseen-document accuracy claim.
I also test boundary values and extraction failures. The current parser handles
the supplied template; OCR and arbitrary contract language are outside its scope.”

“Next I would compare AI extraction with this baseline using the same policy
engine, then evaluate both on new documents. AI's value would be more flexible
reading, while business decisions remain explicit and auditable.”
