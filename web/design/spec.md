# Supplier Document Checker: shared visual brief

Status: visual direction exploration, before the user chooses a direction.
The complete user brief is in brief.md. It governs the final implementation.

Audience: BIAI interviewers, including nontechnical readers. Understand the problem,
the four experiments and the limitations in under a minute. Product: check fictional
supplier quotations against a purchase request and company rules, with evidence.

Final technology: Next.js App Router and TypeScript inside web/ only. Relative API
URLs, streaming NDJSON, mock-first implementation, deployable to Vercel. No edits
outside web/, no Python edits. No analytics, third-party scripts or runtime font CDN.
Current deliverable: three standalone HTML visual drafts, screenshots at 1440x900
and mobile 360x800, a six-candidate board, and a documented direction choice request.
Do not present these drafts as the completed Next.js application.

Common content, in order: sticky navigation; hero with short promise; five-step
fixed workflow; four-approach journey and 6/5/7/9 verdict bar chart; 10x4 results
matrix with pack detail dialog; live-run layout; visible honest limits; footer.
Hero facts: 10 fictional PDFs; 4 approaches; 9/10 final development verdict matches.
Immediately qualify the 9/10: policy changed for the last approach; not like-for-like.
Avoid claiming the model cannot guess. Describe the intended human-review behavior.

Exact approach metrics:
1 Plain rules: verdicts 6/10, rule sets 6/10, facts 267/270, 0.04 seconds, $0.
2 First AI attempt: verdicts 5/10, rule sets 3/10, facts 246/270, about 374 seconds, cents.
3 Strict contract: verdicts 7/10, rule sets 7/10, facts 262/270, about 356 seconds, cents.
4 Reader + judge: verdicts 9/10, rule sets 8/10, facts 261/270, about 816 seconds, about $0.04.
All four observed runs: zero unsafe approvals. Narrow development evidence, not a guarantee.

Expected and per-approach answers; ? means Needs a person to check:
01 expected A: ?,?,?,?; payment after delivery and acceptance of goods.
02 expected A: ?,?,A,A; delivery at your factory.
03 expected R: R,?,R,R; price far above maximum.
04 expected ?: ?,?,?,?; price slightly above maximum.
05 expected R: R,R,R,R; 40% advance.
06 expected R: ?,?,?,R; no late-delivery penalty clause.
07 expected ?: ?,?,?,?; quantity differs.
08 expected R: ?,?,?,R; no TIN/BIN, available on request.
09 expected ?: ?,?,?,?; payment 30 to 90 days as agreed and wrong arithmetic.
10 expected R: R,R,R,R; delivery 60 days and VAT included.

All six limitations must be visible:
- Ten PDFs were development-visible; scores are not unseen-document accuracy.
- 9/10 includes a policy change after viewing packs 06 and 08; earlier approaches
  did not get that policy change, so 9 versus 7 is not like for like.
- Single runs vary; an AI assistant audited fact labels, without independent humans.
- Approach 4 has no code guard on approvals. Safety rests on the judge, fail-closed
  handling and a prompt-injection rule; injection testing covered two packs, one model.
- Hosted models send text to a third party; samples are fictional.
- Fully local inference was too slow on a 12 GB GPU, exceeding ten minutes per call
  in the reported local experiment. Do not confuse this with the separate five-PDF rerun.

Visual/interaction requirements: restrained and precise, accessible semantic verdict
colors paired with icons and full text, dark/light themes, visible focus rings,
reduced-motion support, native keyboard-operable controls, readable at 360px.
Each draft should have real local interactions: navigation, theme toggle, pack
selection/dialog and a clearly labeled mock replay. No real AI calls, API keys
or fabricated model-run metrics. Replays use the supplied recorded answers.
If a preview contains a key field, memory only, password/show/forget controls and
no outbound request or storage. Mark replay mode so users do not enter a real key.
Do not invent unsupported findings: the known pack03 example has unit_price 229.00,
requested maximum 210, and exact source excerpt '229.00'. Other findings may be
left out with an honest note that API data will populate them in implementation.

Assets: the document excerpt and real experiment values are the visual material.
Use system fonts and inline SVG/CSS; do not invent logos or endorsements. Brand names
in a prose hyperlink are attribution/instructions, not a sponsor strip. No external
resources or libraries in standalone drafts. Final API key instructions link to
https://openrouter.ai/keys; no network requests are triggered by merely rendering.

Form rationale: this is evidence-led procurement work. Show actual quotation text,
the decision and its uncertainty together. The eye should move from document to
finding, rather than to decorative imagery. Authority comes from legibility and
traceability, with generous whitespace and honest labels.
