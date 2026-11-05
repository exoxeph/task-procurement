# Build the frontend for the "Supplier Document Checker" demo

Use the **huashu-design** skill for visual direction and craft. The goal is a sleek,
calm, premium-feeling single-page site, not a generic AI-tool template.

## 1. What this is

A garment company receives supplier quotations (PDFs). Our system reads each one,
checks it against a purchase request and company rules, and answers
**Approve**, **Reject** or **Needs a person to check**, with reasons and exact quotes.
We built four approaches and measured them on 10 sample PDFs:
1. plain Python rules (no AI)
2. first AI attempt
3. AI with a strict output contract
4. two AI agents: a careful reader and a judge

This site is a showcase for interviewers at BIAI (a Bangladeshi AI company). Many are
non-technical. A non-technical person must understand the story in under a minute.
They will also look for honesty about what does not work.

## 2. Scope

Build ONLY the frontend, in a new folder `web/`. Do not touch `procurement/`, `tests/`,
`config/` or any Python. A separate Python backend (Vercel function at `/api/...`) is
being built by someone else. Call it with relative URLs and build against mocks first
(a small mock server or MSW) so the UI works before the backend exists.

Tech: Next.js (App Router) + TypeScript, deployable to Vercel. Tailwind is fine. Keep
dependencies few and justified. No analytics, no third-party scripts, no external fonts
loaded from a CDN at runtime (self-host or use next/font).

## 3. Page structure (one scrolling page, with a sticky minimal nav)

1. **Hero.** One-line promise, a short subline, and 3 headline stats (see data below).
   A quiet animated visual of the pipeline is welcome, but nothing flashy.
2. **How it works.** The fixed pipeline: Read PDF -> Extract facts -> Check -> Decide ->
   Report / ask a person. Make "always the same order, never guesses, asks a person when
   unsure" obvious. Subtle step-by-step animation on scroll.
3. **The journey.** Four approach cards in order, each with: name, one-sentence idea,
   what it got right, what went wrong, and its numbers. A simple bar chart of
   "verdicts correct": 6, 5, 7, 9. Tone: a story of honest questions
   ("Do we even need AI?" -> "Where does AI help?" -> "Can it be dependable?" -> "Can it judge safely?").
4. **Results explorer.** A 10 x 4 matrix (packs x approaches) showing each approach's
   verdict against the expected one. Wrong cells must be clearly marked WITHOUT relying
   on colour alone. Clicking a pack opens a detail drawer: what the pack tests, the
   expected verdict, each approach's answer, and (for approach 4) its findings with reasons.
5. **Live run.** See section 5. This is the interactive centrepiece.
6. **Honest limits.** A visible, well-designed section (not a footnote). Content in section 7.
7. **Footer.** Link to the GitHub repo (placeholder `#`) and the roadmap document.

## 4. Visual direction

- Mood: quiet confidence, editorial, precise. Think "well-made developer/finance tool",
  not "AI startup". Generous whitespace, strong typographic hierarchy, restrained colour.
- Support **dark and light** themes (follow system, with a toggle).
- Verdict colours must be semantic and accessible: Approve = green, Reject = red,
  Needs a person to check = amber. Always pair colour with an icon and a text label.
- Motion: purposeful and subtle (200-400 ms easing). Respect `prefers-reduced-motion`.
- Responsive, mobile-first. Everything usable at 360 px wide.
- WCAG AA contrast, full keyboard navigation, visible focus rings, semantic HTML, proper
  labels and ARIA for the drawer, stepper and form.
- Avoid: stock gradients on everything, glassmorphism overload, emoji as icons,
  lorem ipsum, fake testimonials, generic "powered by AI" sparkles.

## 5. Live run panel (important)

A card with:
- **Sample picker:** the 10 sample PDFs (supplier-pack-01 ... 10), each with a short label
  of what it tests. Show a text preview of the PDF if the API provides it.
- **Approach picker:** 1, 2, 3, 4 (default 4). **Approach 1 runs with NO key** (it uses no
  AI). Approaches 2-4 need an OpenRouter key.
- **API key field (bring your own key).** Rules, all required:
  - `type="password"` with a **show/hide toggle** so the user can view what they pasted.
  - Keep the key **in memory only** (React state). NEVER localStorage, sessionStorage,
    cookies, URL or query string. A "Forget key" button clears it. It disappears on reload.
  - Send it only in the request header `X-OpenRouter-Key` of `POST /api/run` over HTTPS.
    Never log it, never put it in an error message, never send it to any other host.
  - Helper text: "Your key is sent only to run this check and is never stored. Use a
    throwaway key with a small spending limit." Link to https://openrouter.ai/keys.
  - Note that a key with no credit will fail on paid models.
- **Run button**, disabled until a sample is chosen (and a key, for approaches 2-4).
- **Progress stepper** driven by streamed events (the run can take 30-90 seconds).
  Steps for approach 4: Read PDF, Agent 1 extracts, Code annotates warnings,
  Agent 2 judges, Report. Show elapsed time.
- **Result view:** big verdict badge, the reasons, and a findings list. Each finding shows
  its code, severity, reasoning and the **exact quote** from the page, highlighted inside
  the PDF text. A collapsible "extracted facts" table (name, value, status, quote,
  warning). Show model names, time and estimated cost if provided.
- **Friendly errors** mapped from the API error codes (section 6): invalid key, no credit
  (402), rate limited, provider problem, timeout, backend unavailable. Each with one
  clear next step. If the backend is down, the rest of the site (replay) still works.

## 6. API contract (backend is built separately; mock it)

Static data, loaded at build or runtime:  `GET /data/results.json`
```json
{
  "approaches": [
    {"id": "approach1", "name": "Plain rules", "verdicts": 6, "ruleSets": 6,
     "facts": 267, "factsTotal": 270, "seconds": 0.04, "costUsd": 0, "unsafeApprovals": 0, "failures": 0}
  ],
  "packs": [
    {"id": "supplier-pack-01", "tests": "Clean, but payment 'after delivery and acceptance of goods'",
     "expected": "Approve",
     "answers": {"approach1": "Needs a person to check", "approach2": "...", "approach3": "...", "approach4": "..."}}
  ]
}
```
Samples:  `GET /api/samples` -> `[{ "id": "supplier-pack-03", "label": "...", "expected": "Reject", "text": "..." }]`

Run (streaming newline-delimited JSON, `Content-Type: application/x-ndjson`):
`POST /api/run`  header `X-OpenRouter-Key` (omit for approach1), body `{ "sample": "supplier-pack-03", "approach": "approach4" }`
```
{"event":"step","name":"Read PDF","status":"completed"}
{"event":"step","name":"Agent 1: extract facts","status":"running"}
{"event":"step","name":"Agent 1: extract facts","status":"completed","seconds":47.2}
{"event":"result","verdict":"Reject","seconds":81.4,"costUsd":0.0036,
 "models":{"extractor":"qwen/qwen3-14b","judge":"anthropic/claude-haiku-5.5"},
 "findings":[{"code":"price","severity":"Reject","reason":"...","facts":["unit_price"],
              "evidence":[{"page":1,"text":"229.00"}]}],
 "facts":[{"name":"quantity","status":"found","value":"800","rawValue":"800",
           "referenceEvent":null,"conditions":[],"evidence":[{"page":1,"text":"800"}],
           "warnings":[],"note":"item table"}]}
```
Errors: `{"event":"error","code":"invalid_key|insufficient_credit|rate_limited|provider_error|timeout|bad_request","message":"..."}`
Verdict strings are exactly: `Approve`, `Reject`, `Needs a person to check`.

## 7. Content and numbers (use exactly; do not invent others)

| Approach | Verdicts (of 10) | Rule sets (of 10) | Facts (of 270) | Time, 10 PDFs | Cost |
|---|---|---|---|---|---|
| 1 Plain rules (no AI) | 6 | 6 | 267 | 0.04 s | $0 |
| 2 First AI attempt | 5 | 3 | 246 | about 374 s | cents |
| 3 Strict contract | 7 | 7 | 262 | about 356 s | cents |
| 4 Reader + judge | 9 | 8 | 261 | about 816 s | about $0.04 |

No approach ever approved a wrong document (0 unsafe approvals in every run).

Per-pack answers (A = Approve, R = Reject, ? = Needs a person to check):
pack | expected | a1 | a2 | a3 | a4
01 | A | ? | ? | ? | ?   (payment "after delivery and acceptance of goods")
02 | A | ? | ? | A | A   (delivery "at your factory")
03 | R | R | ? | R | R   (price far above maximum)
04 | ? | ? | ? | ? | ?   (price slightly above maximum)
05 | R | R | R | R | R   (40% advance)
06 | R | ? | ? | ? | R   (no late-delivery penalty clause)
07 | ? | ? | ? | ? | ?   (quantity differs)
08 | R | ? | ? | ? | R   (no TIN/BIN, "available on request")
09 | ? | ? | ? | ? | ?   (payment "30 to 90 days as agreed", wrong arithmetic)
10 | R | R | R | R | R   (delivery 60 days, VAT "included")

Honest limits section must state plainly:
- All ten PDFs were visible while building: these are development scores, not a test on unseen documents.
- 9 of 10 includes a policy decision made after looking at packs 06 and 08 (read the rules text literally).
  Approaches 1-3 did not get that change, so 9 vs 7 is not like for like.
- Single runs; model output can vary. Fact labels were audited by an AI assistant, not independent humans.
- Approach 4 has no code guard on its approvals: safety rests on the judge model, fail-closed handling
  and a prompt-injection rule. Injection testing was narrow (two packs, one model).
- Hosted models send document text to a third party. The samples are fictional.
- Running fully local is too slow on a 12 GB GPU (over 10 minutes per call).

Story lines (use or adapt):
- A1: "Before using AI, we checked whether we needed it. Plain code reads 98.9% of the facts."
- A2: "The model understood the documents. It failed at the hand-off: right answers in the wrong shape."
- A3: "We did not change the model. We fixed the contract between the AI and the code."
- A4: "One agent reads and writes down every doubt. A second reads the whole document and applies the company rules one by one, showing why."

## 8. Acceptance criteria

- `npm run build` passes with no TypeScript or lint errors; Lighthouse accessibility >= 95 and performance >= 90 on desktop.
- Works with the mock API; swapping to the real `/api` needs no UI changes.
- The key is never written to storage, URL, logs or console; no network requests to any host except same-origin.
- Every colour-coded state also has an icon and text label.
- Works at 360 px, 768 px and 1440 px; keyboard-only run of the live panel is possible.
- A short `web/README.md` explains how to run it, how to point it at the real API, and how to deploy.

Do not: invent metrics, add tracking, store the key anywhere, claim more accuracy than the data shows,
or modify anything outside `web/`.
