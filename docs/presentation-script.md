# Five-minute presentation guide

## 0:00-0:40: Problem and architecture

"The task is to check supplier quotations against a purchase request and company
rules. I implemented two ways to extract facts: Python parsing and a local LLM.
They feed the same Python policy engine, so the comparison isolates extraction."

Show review_document(): read PDF, extract, validate, check policy, report/handoff.
Explain that this is a fixed workflow; LangGraph would add machinery without a
branching-agent requirement. The model never decides company policy.

## 0:40-1:35: Show the actual comparison

Open reports/block5/run1/comparison.html. Use the already completed run during
the recording; the local model batch took about 9.6 minutes of extraction time.

"Python matched 6/10 verdicts. This zero-shot Qwen setup matched 5/10 and no complete
rule sets. It did not beat the baseline. I kept the first full run as the headline
and repeated the same experiment; I did not pick the best repeat."

Show fact agreement, reviews, failures, wrong decisions and the confusion table.
"Neither made approvals. Zero wrong approvals therefore is not proof of safety.
The 267/270 baseline fact agreement is mostly simple template facts, not unseen
accuracy. Whole-duration agreement is 27/30 versus 15/30 for Qwen."

## 1:35-2:40: Show evidence of both value and failure

Pack 02: show the original factory-delivery clause. Qwen extracted 21 days after
PO, where the small baseline grammar left delivery unresolved. Then show its
missing item code/invalid categorical bounds; language interpretation helped one
field but did not make the whole result reliable.

Pack 03: Qwen retained price 229, but missed item C and returned quantity "s800".
Validation refused that number, and the missing item prevented the price check.
Pack 09: the printed amount is 322,000, while 50,000 times 6.40 is 320,000. Python
catches this; Qwen preserved the printed amount but its invalid quantity stopped
that arithmetic check. Show exact source evidence, not just an output badge.

## 2:40-3:35: Human handoff

Open reports/block4-assisted.html. Explain clearly that this is an implementation
demonstration response, not an actual person's review.

"A pending result produces specific questions with source pages. A reviewer can
correct facts using a local JSON response. We check reviewer details, time, reason,
run identity, the PDF hash and exact evidence. The original output stays saved.
A new assisted run goes through the same rules and is excluded from AI-only
scores. Correcting extraction is not a button to approve a noncompliant quote."

Show that pack 09 remains review because its payment range and arithmetic remain
problematic. Mention that recorded reviewer names are not authenticated.

## 3:35-4:35: Honest evaluation and interview conclusion

"All ten files were development-visible, and I did not train a model. The fact
audit came from source PDFs and was performed by Codex; it is not independent
human annotation. I froze the prompt/model/settings, saved raw runs, retained
failures in the denominator and ran three repeats. Exact JSON and exact evidence
are necessary checks, but they cannot establish semantic truth."

Show the repeat table in docs/approach2-results.md and the frozen manifest.
"This model/prompt is a useful experiment, not a demonstrated production upgrade.
I would keep the stronger baseline as the default and evaluate any new model or
prompt as a separate experiment on genuinely new quotations."

## 4:35-5:00: Close with what is reviewable

Show tests passing and the folder separation: approach1/, approach2/, shared/.
Mention that OCR, complex layouts, multiple-item decisions and legal registration
verification remain outside scope. Code, measured results and correction audit are
ready for review. Record and publish the actual Loom separately.
