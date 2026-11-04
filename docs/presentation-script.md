# Suggested Loom walkthrough (under five minutes)

## 0:00-0:40: Problem and fixed workflow

Procurement staff compare supplier quotations with a purchase request and company
policy. Show review_document(): read PDF, extract facts, check rules, show evidence.
This is the Python baseline, with no AI model yet.

## 0:40-1:30: Run the real batch

Run python -m procurement.review and open reports/procurement-review.html.
Show three rejections and seven human reviews. Expand the unchanged manual-label
comparison: six exact verdict matches. Explain four conservative escalations.
Do not present human-review escalation as a correct match or hide the denominator.

## 1:30-2:30: Show useful findings

Pack03: price229 exceeds maximum210 by more than3%.
Pack05:40% advance exceeds20%.
Pack09: the document states322,000, while50,000 times6.40 is320,000.
Open each original page excerpt. The parser preserves wrong figures, never repairs
source text or invents a missing value.

## 2:30-3:30: Explain the correction

The earlier baseline reached10/10 by depending on document-specific text order and
sentence patterns. I replaced that with table boundaries/column concepts and
explicit term components. Reordering columns or PDF insertion order no longer
changes field meanings in the tested structures. Unknown wording stays unresolved.
Policy still uses ordinary Python checks. The model will not choose business rules.

## 3:30-4:30: Honest limits and next comparison

All ten PDFs were visible during development. Property tests check transformations,
not unseen accuracy. A small deterministic grammar cannot understand arbitrary
contract wording. The current baseline escalates unfamiliar wording and unproven
absence, and produces no approvals on this set. That limits automatic coverage.
Next compare an AI extractor with this baseline through exactly the same rules
and evaluate both on new documents. Record Loom yourself; this is a speaking guide.
