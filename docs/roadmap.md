# Roadmap: from fixed rules to AI agents

**Project:** Supplier document checker (BIAI AI Engineer, Round 2, Task 1)
**What this file is:** the full story of the build, in the order it happened, with the reasoning behind each step and the measured results. Each approach is described in its **final form**. Numbers come from the saved evaluation runs; where a number is an estimate it says so.

---

## 0. One-minute summary

| | Idea | Who reads the document | Who decides | Verdicts correct (of 10) |
|---|---|---|---|---|
| **Approach 1** | No AI: plain Python rules | Python code | Python rules | **6** |
| **Approach 2** | First AI attempt: ask a model for the facts | AI model, one pass | Python rules | **5** |
| **Approach 3** | Fix the contract between AI and code | AI model, strictly typed | Python rules | **7** |
| **Approach 4** | Two agents: a careful reader and a judge | AI agent 1, step by step | AI agent 2 (the judge) | **9** |

The headline is not "AI wins". It is a sequence of honest questions:

1. **Do we even need AI here?** Approach 1 answers this with a baseline that already gets 6 of 10 and 267 of 270 facts, for free, in milliseconds.
2. **Where does AI help?** Approach 2 shows it can read wording that fixed rules cannot, but it breaks in boring ways (formats, quotes).
3. **Can we make AI dependable?** Approach 3 fixes those boring breakages with a stricter contract, and gets to 7 of 10.
4. **Can AI do the judgment too, safely?** Approach 4 separates "read carefully" from "decide", and reaches 9 of 10 with no unsafe approvals.

Two caveats frame everything below, and the presentation should say them out loud:

- **All ten PDFs were visible while we built.** These are development scores, not a test on unseen documents.
- **The jump from 7 to 9 is partly a policy decision** (two packs where the company rules text was read more literally), made after looking at those packs. See section 11.

### The journey in one picture

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  A1["Approach 1<br/>No AI, plain rules<br/>6 of 10 correct"]:::code
  A2["Approach 2<br/>First AI attempt<br/>5 of 10 correct"]:::ai
  A3["Approach 3<br/>Strict contract<br/>7 of 10 correct"]:::ai
  A4["Approach 4<br/>Reader and judge<br/>9 of 10 correct"]:::good
  A1 -->|"Reads 98.9 percent of facts, but cannot read new wording"| A2
  A2 -->|"AI understands, but its output shape breaks"| A3
  A3 -->|"Reads well, but fixed code cannot judge the whole document"| A4
```

Verdicts correct, out of 10 (same ten PDFs every time):

```
Approach 1  ######      6   plain rules, no AI
Approach 2  #####       5   first AI attempt
Approach 3  #######     7   strict contract
Approach 4  #########   9   reader + judge   (includes a policy decision, see section 11)
```

**Colour key used in every diagram below:** grey = code, blue = AI step, amber = a person,
red = where something goes wrong, green = the good outcome. Mermaid renders on GitHub and in most
Markdown viewers. To get an image for slides, paste a block into https://mermaid.live and export SVG or PNG.

---

## 1. The task and how it is judged

### What the brief asks (Task 1)

A garment company receives supplier quotations. Build a system that:

1. Reads each quote and pulls out supplier, item, quantity, price and delivery.
2. Compares the quote with the company's **purchase request** and points out wrong quantities or prices.
3. Checks the contract against a short list of **company rules** (payment terms, VAT and so on).
4. Gives a final answer per document: **Approve**, **Reject** or **Needs a person to check**, with the reason.
5. **When unsure, stops and asks a person. Never guesses.**

Constraints that shaped every decision:

- **"Clear fixed steps, one after another"**, not "one agent that runs freely". Our pipeline is a fixed sequence in code (read, extract, validate, decide, report), in every approach.
- **"Show us how many of the 10 you got right."** We report this for all four approaches, always on the same ten files.
- **Honesty is scored** (10% of the grade): the one-page note must say what does not work.

### How it is scored (from the brief)

| What | Weight |
|---|---|
| Loom presentation (clear, explains the why, a non-technical person can follow) | 20% |
| Works correctly on the sample files | 25% |
| Built in a clear, sensible way and handles mistakes | 20% |
| How well the hardest part was solved | 15% |
| Clean code runnable from the README | 10% |
| Honesty about what does not work | 10% |

This is why the roadmap keeps the failures and trade-offs in the story: a build that only reports wins loses on honesty and on "handles mistakes".

---

## 2. The data and the ground truth

**Inputs** (in `sample-data/engineer/task1-procurement/`):

- `supplier-pack-01.pdf` to `supplier-pack-10.pdf`: ten fictional supplier quotations, one page each (some correct, some with deliberate mistakes). In this document **"pack 03"** simply means `supplier-pack-03.pdf`.
- `purchase-request.csv`: five requested items (A to E) with description, unit, quantity and the **maximum unit price**.
- `company-rules.md`: the rule list.

**The company rules, in plain terms**

| Outcome | Condition |
|---|---|
| **Reject** | unit price more than 3% above the maximum; advance payment above 20%; no late-delivery penalty clause; TIN or BIN missing; delivery later than 45 days after the purchase order |
| **Needs a person to check** | price above the maximum but within 3%; quantity differs by more than 5%; payment terms unclear or outside 30 to 60 days after delivery; delivery in 31 to 45 days; VAT not shown separately at 15%; numbers that do not add up; quotation valid under 30 days |
| **Approve** | none of the above |

Extra notes in the rules: the penalty must be at least 0.5% of order value per week; always quote the exact supporting text; **if unsure, the answer is "Needs a person to check", never guess.**

**What each pack is designed to test** (from the manual labels)

| Pack | Expected | What it tests |
|---|---|---|
| 01 | Approve | A clean pack (but its payment clause says "after delivery **and acceptance of goods**") |
| 02 | Approve | Clean, but delivery wording is "at your factory" |
| 03 | Reject | Unit price far above the maximum |
| 04 | Needs a person to check | Price slightly above the maximum (within 3%) |
| 05 | Reject | 40% advance |
| 06 | Reject | **No late-delivery penalty clause at all** |
| 07 | Needs a person to check | Quantity differs from the request |
| 08 | Reject | **No TIN/BIN** ("registration details available on request") and an unclear penalty basis |
| 09 | Needs a person to check | Payment "30 to 90 days as agreed" and a line amount that is arithmetically wrong |
| 10 | Reject | Delivery in 60 days, and VAT "included" rather than shown separately |

---

## 3. How we measure

All approaches are scored the same way against the manual labels (`config/manual-labels.json`) and an audit of the individual facts (`config/manual-facts.json`).

| Metric | Meaning |
|---|---|
| **Verdicts correct** | The final answer (Approve / Reject / Needs a person to check) matches the label. This is the number the brief asks for. |
| **Full rule sets** | The *list of findings* (price, advance, delivery and so on) matches the expected list exactly. Stricter than the verdict: one extra finding fails the whole document. |
| **Facts matching the audit** | Out of 270 facts (27 per PDF) read from the sources: does the extracted value, event, conditions and quote match? |
| **Unsafe approvals / wrong rejections** | An Approve or Reject that should not have been automatic. The most important safety number. |
| **Failed calls** | Model or network failures. A failure counts against the score; it is never hidden. |
| **Time and cost** | Total seconds for 10 PDFs and the model cost. |

**Honest limits of this measurement**

- The ten PDFs were visible during development: **no held-out test**.
- The 270 fact labels were audited from the sources by an AI assistant, **not independent human annotation**.
- Each number is **one run**. Model runs can vary even at temperature 0, and one model (Claude Haiku) was run without a pinned temperature.
- Ten documents is a small sample.

---

## 4. The foundation shared by every approach

Before any approach, we built the parts that do not depend on AI. All four approaches reuse them, which is what makes the comparison fair.

### The fixed workflow (`procurement/review.py`)

```
PDF  ->  read the document  ->  extract facts  ->  validate  ->  decide  ->  report + human handoff
```

Every approach is a variation of the *extract* and *decide* steps inside this fixed sequence. No agent ever chooses its own next step.

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  P["PDF"]:::code --> R["1 Read<br/>pages and tables"]:::code
  R --> E["2 Extract facts<br/>each with an exact quote"]:::ai
  E --> V["3 Validate<br/>quotes, formats, events"]:::code
  V --> D["4 Decide<br/>verdict and findings"]:::ai
  D --> O["5 Report<br/>and human hand-off"]:::code
  E -.->|"any failure"| H["Needs a person to check"]:::person
  V -.->|"unsure"| H
  D -.->|"unsure or failure"| H
  H --> HR["Human review<br/>questions, response file,<br/>recorded correction"]:::person
```

Steps 2 and 4 are the only ones that change between approaches (in approaches 1 to 3, step 4 is
always the Python rules engine). The order, and the route to a person on any failure, never change.

### The pieces

| Piece | What it does | Where |
|---|---|---|
| **PDF reader** | Pulls each page's text and detects tables (PyMuPDF), with no AI | `procurement/shared/pdf_text.py`, `table_layout.py` |
| **Fact contract** | 32 named facts (supplier, item, quantity, prices, VAT, TIN/BIN, advance, payment days, delivery days, penalty, validity and so on). Each fact has a **status** (`found`, `not_found`, `ambiguous`, `unrecognized`), a value, the printed wording, a reference event, conditions and **an exact quote from the page** | `shared/extraction.py` |
| **Validation** | Checks quotes really appear in the page, numbers are well formed, and reference events agree | `shared/extraction.py` |
| **Rules engine** | Applies the company rules to the facts and produces **findings** (price, advance, delivery, payment, penalty and so on) and a verdict. Reject outranks review outranks approve. **All findings are kept** even after a Reject. | `shared/rules.py`, `config/company-rules.json`, `docs/policy-mapping.md` |
| **Human handoff** | For anything uncertain: source-backed questions, a response file with reviewer name, time and reason, and a recorded correction. Corrected runs are excluded from accuracy scores. | `shared/human_review.py` |
| **Saved runs** | Every extraction is saved with a unique ID, the PDF's SHA-256, the raw model answer and metadata. Nothing is overwritten. | `shared/runs.py` |
| **Reports** | One HTML report per run, and a side-by-side comparison | `shared/report.py` |
| **Evaluation** | The scoring above | `shared/evaluation.py` |

### The three design rules behind it

1. **Exact evidence.** Every found fact must carry a quote that really is in the document.
2. **Fail closed.** Any failure (bad format, missing quote, model error, timeout) becomes "Needs a person to check", never an approval.
3. **Conservative policy.** The rules text says "if not sure, review". Where the text is silent, we choose review, and write that choice down (`docs/policy-mapping.md`).

---

## 5. Approach 1: the deterministic baseline ("do we need AI at all?")

### Why we started here

The brief says "build an AI system", but the first honest question is whether AI is needed. If plain code can already read these documents, then:

- AI adds cost, latency and a new way to be wrong, and
- we could not claim AI helped without something to compare it against.

So approach 1 is a **baseline**: the bar every AI approach has to beat. It also gives us a reference implementation of the decision rules, which every later approach reuses.

### What it is

Python only, no model calls. `procurement/approach1/`:

| File | Role |
|---|---|
| `financial_details.py` | Finds the item table and its columns by concept (description, quantity, unit price and so on), reads the labelled totals, VAT and currency |
| `supplier_details.py` | Reads quotation metadata and TIN/BIN labels |
| `terms.py` | Reads the labelled terms clauses (payment, delivery, penalty, validity), with explicit-component rules and a check for unexplained words |
| `extractor.py` | Collects the facts from the three readers into the shared contract |

Its principle: **recognize a small set of known wordings; anything else stays "unresolved"** rather than being guessed. Unresolved becomes "Needs a person to check".

### Diagram

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  P["PDF"]:::code --> R["Read pages and tables<br/>PyMuPDF"]:::code
  R --> F["Python extractors<br/>financial details, supplier details, terms"]:::code
  F --> V["Validate<br/>quotes, formats, events"]:::code
  V --> RU["Rules engine<br/>thresholds and arithmetic"]:::code
  RU --> O["Verdict, findings, report"]:::good
  F -.->|"wording not recognised"| U["Fact left unresolved"]:::problem
  U --> H["Needs a person to check"]:::person
```

No AI anywhere. Fast, free and repeatable. Its only weakness is wording it was never programmed for.

### Results

| Metric | Result |
|---|---|
| Verdicts correct | **6 / 10** |
| Full rule sets | 6 / 10 |
| Facts matching the audit | **267 / 270** (98.9%) |
| Unsafe approvals / wrong rejections | 0 / 0 |
| Failures | 0 |
| Time | about 0.04 s for all 10 (no network, no cost) |

Wrong verdicts: packs **01, 02, 06, 08**. It never approved anything wrongly.

### What it taught us

- **The reading is already very good** on this template: 267/270. The three missed facts are in the payment and delivery clauses.
- **It cannot read wording outside its grammar.** Pack 02 says delivery "at your factory"; the baseline cannot map that to "21 days after the purchase order", so it stops and asks a person.
- **Four wrong verdicts are not all about reading.** Packs 01, 06 and 08 are cases where our *policy* is stricter than the labels (section 11). Pack 02 is the one genuine reading gap, and it is where AI could help.
- **It is the fairest benchmark.** A system that must beat 267/270 at reading has to show where it adds value, not just that it works.

**Presentation line:** "Before using AI, I checked whether we needed it. Plain code reads 98.9% of the facts correctly. AI has to earn its place on the remaining wording problems."

---

## 6. Approach 2: the first AI attempt (a local model reads the document)

### Why

The baseline's real weakness is wording it was never programmed for. A language model can, in principle, read any phrasing. So approach 2 asks the model to do the extraction and leaves everything else (validation, rules, reports) unchanged. This isolates one question: **does AI reading beat code reading?**

### What it is

- **Steps 1 to 3 unchanged:** the PDF reader, the fact contract and the rules engine.
- **Step 2, extract:** one model call per PDF. The page text and detected tables go in; the model returns **JSON** following the 32-fact contract (value, status, quote, and so on).
- **Model:** first a **local** model through Ollama (Qwen2.5 7B, then Qwen3 14B), so no document leaves the machine. Later, the same Qwen3 14B hosted on OpenRouter for speed.
- **Prompt:** zero-shot general instructions (no sample answers, no company thresholds).
- **Safety:** localhost-only network guard, no proxies or redirects, no silent fallback to another model, truncation and context checks, and every failure becomes a visible failed run.

### Diagram

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  P["PDF"]:::code --> R["Read pages and tables"]:::code
  R --> M["One AI call<br/>Qwen, general prompt<br/>answers as JSON facts"]:::ai
  M --> V["Strict validator<br/>erases a fact if any check fails"]:::code
  V --> RU["Rules engine"]:::code
  RU --> O["Verdict, findings, report"]:::code
  M -.->|"wrong number format,<br/>quote not literal,<br/>invented detail"| X["Correct answers lost<br/>or wrong ones passed on"]:::problem
  X --> H["Needs a person to check"]:::person
```

The only change from approach 1 is the extract step. What this showed: the AI understood the
documents, but the hand-off to the code was where it broke.

### Results

| Run | Verdicts | Rule sets | Facts | Time (10 PDFs) |
|---|---|---|---|---|
| Local Qwen2.5 7B, first full run | 5 / 10 | 0 / 10 | 224 / 270 | about 574 s |
| Local Qwen3 14B (first 5 PDFs only) | (see note) | | 112 / 135 | about 1,484 s for 5 |
| **Hosted Qwen3 14B, latest** | **5 / 10** | **3 / 10** | **246 / 270** | about 374 s |

Note: the local 14B run was an extraction-only comparison on PDFs 1 to 5. It matched the 7B model on facts (112 of 135 each) at five times the time.

Zero unsafe approvals in every run. Neither the AI nor the baseline approved anything wrongly.

### What went right

- **A real win on pack 02.** Qwen read "delivery at your factory" as **21 days after the purchase order**, something the baseline cannot do. This is the evidence that AI can add value on wording.
- **Safe failure.** Every error became a review, never a wrong approval.

### What went wrong (and why it drove approach 3)

The model understood most of the content. It lost points on **how it handed the answer to the code**:

| Failure | Example | Why it happened |
|---|---|---|
| Wrong number format | `"s800"` for a quantity; `"15%"` where `"15"` was needed; `"20,000"` | The prompt said both "preserve printed amounts" and "decimal strings". The schema accepted any text. |
| Quote not literal | A quote with a space where the page had a line break, or an event name quoted instead of a sentence | Exact-substring checking was strict and the prompt did not say how to quote |
| Payment event confusion | The advance's event ("with the purchase order") written as the balance's event | One `payment_reference` fact covered a clause with two parts |
| Invented or junk data | A penalty basis stated that the document does not state; "within" recorded as a condition | Nothing prevented it |
| One bad quote erased a correct value | A right quantity dropped because its quote was imperfect | The validator removed the whole fact |
| Run-to-run variation | Different results at temperature 0 | Normal for local models |
| Slow locally | about 5 minutes per PDF for the 14B model on a 12 GB GPU | Hardware limit |

Also a hosting lesson: on the hosted service, one backend (**NextBit**) returned empty or broken replies and failed 5 calls in one run. Excluding it (`OPENROUTER_IGNORE_PROVIDERS`) removed those failures. This is why the final numbers use a pinned set of backends.

**Presentation line:** "The model understood the documents. It failed at the hand-off: it gave right answers in the wrong shape, and our validator threw them away."

---

## 7. Approach 3: fix the contract between the AI and the code

### Why

Approach 2's failures were mostly **communication failures**, not reading failures. So approach 3 changes nothing about the model. It makes the *contract* strict enough that the model physically cannot produce those formats, and it fixes the places where our validator was too harsh.

### What changed

**1. A typed schema (generation-time rules).** The model's output is constrained while it writes:

- Whole-number facts (quantity, days) accept only digits; amounts accept digits with an optional decimal point. `"s800"` and `"15%"` cannot be produced.
- Dates must be `YYYY-MM-DD`.
- Reference events must come from a fixed list (`delivery`, `purchase_order`, `quotation_date`, `invoice`, `other`).
- Numeric bounds and reference events are only allowed on the duration facts; every other fact has them as null.
- **Field order is the model's writing order:** quote first, then status, printed wording, then the cleaned value. Each reference fact is written right after the duration it explains.

**2. A better prompt.** It states the exact format of every field, with wrong-and-right examples; separates the advance from the balance payment; says to read the currency from column headers; says a found fact is never null; and says the evidence for an event fact is the *sentence* that states it, not the event name.

**3. Three deliberate loosenings of the validator**, each narrow and each keeping the audit trail:

- A quote that differs from the page only in whitespace is accepted, and replaced with the exact page text.
- A fact survives if at least one of its quotes is genuine (bad quotes are dropped, not the fact).
- A `%` on a percent field or `days` on a duration field is stripped only when the printed wording contains the same number. The printed wording is kept.
- An invented quote is still rejected.

**4. Rules clean-up.** `pdf_issue` now means a problem with the *document*, not a repeat of a single-fact error. The redundant delivery and validity reference findings no longer raise findings, because the rules already check the event on the days fact.

### Diagram

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  subgraph C["The contract (new)"]
    S["Typed schema<br/>digits only, fixed event list,<br/>null-only bounds, quote first"]:::ai
    PR["Stricter prompt<br/>exact formats with examples"]:::ai
  end
  P["PDF"]:::code --> R["Read pages and tables"]:::code
  R --> M["One AI call<br/>Qwen, constrained while it writes"]:::ai
  S --> M
  PR --> M
  M --> V["Looser validator<br/>whitespace-tolerant quotes,<br/>keeps a fact if one quote is real,<br/>strips percent and days"]:::code
  V --> RU["Rules engine<br/>tidied findings"]:::code
  RU --> O["Verdict, findings, report"]:::good
  M -.->|"failure"| H["Needs a person to check"]:::person
```

Same steps as approach 2. The change is inside two boxes: what the model is allowed to write, and
what the validator accepts.

**Worked example, pack 02 (reading wording that fixed rules cannot):**

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  T["Delivery clause mentions<br/>delivery at the buyer's factory"]:::code
  T --> B1["Approach 1<br/>wording not recognised,<br/>delivery left unresolved"]:::problem
  B1 --> B2["Needs a person to check"]:::person
  T --> C1["Approach 3<br/>reads it as 21 days after the<br/>purchase order, factory is the place"]:::ai
  C1 --> C2["Approve"]:::good
```

### Results

| Metric | Approach 3 (hosted Qwen3 14B) |
|---|---|
| Verdicts correct | **7 / 10** |
| Full rule sets | **7 / 10** |
| Facts matching the audit | **262 / 270** |
| Unsafe approvals / wrong rejections | 0 / 0 |
| Failures | 0 |
| Time | about 356 s (about 36 s per PDF) |

The gain over approach 2 is large: 246 to 262 facts, 5 to 7 verdicts, 3 to 7 rule sets. Pack 02 is now an automatic, correct Approve, which the baseline cannot do.

### What was still wrong

- **Packs 01, 06, 08** are still wrong. They are policy-versus-label differences, shared by every approach (section 11).
- **Pack 08** also shows two real extraction problems: the model **invented a penalty basis** ("order value per week", which the document never states), and its TIN/BIN quotes failed the check.
- **The ceiling is the rules.** The decision logic is fixed code. It is excellent at thresholds and arithmetic, and it cannot read between the lines ("this clause does not exist in the document").

**Presentation line:** "I did not change the model. I fixed the contract: constrain the output while it is being written, and stop the validator discarding right answers. Seven correct, up from five."

---

## 8. Approach 4: two agents, one reads and one judges

### Why

Approach 3 left two problems that no schema can fix:

1. **Reading carefully** still produced the occasional invented fact and dropped qualifier.
2. **Judging** needs to read the whole document ("is there any penalty wording anywhere?"), but the code only sees extracted fields. A field can say "not found", never "this clause is absent".

A natural idea: let an AI agent read carefully, then let a second AI agent check the facts against the document and apply the rules. This needs to stay a **fixed sequence** (the brief), and **fail closed**.

### The final design

```
PDF
 |  code: read pages and tables
 v
AGENT 1  The careful reader (Qwen3 14B)
 |  works through 8 ordered stages; writes a one-line note before each fact
 v
CODE  Annotate warnings (nothing is erased)
 |  failed quote or format check -> keep the value, attach a warning
 v
AGENT 2  The judge (Claude Haiku 5.5)
 |  sees: page text + a plain-text fact sheet (built by code) + warnings + company rules
 |  writes one check per rule: reasoning first, then pass / review / reject
 v
Verdict + findings with reasons  ->  report + human handoff
```

```mermaid
flowchart TB
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  P["PDF"]:::code --> R["Read pages and tables"]:::code
  R --> A1["Agent 1: the careful reader (AI)<br/>8 ordered stages, a one-line note before each fact,<br/>field definitions but no company limits"]:::ai
  A1 --> AN["Code: annotate warnings<br/>failed check keeps the value and adds a warning,<br/>nothing is erased"]:::code
  AN --> A2["Agent 2: the judge (AI)<br/>sees page text, a fact sheet built by code,<br/>warnings and the company rules.<br/>One check per rule: reasoning first, then pass, review or reject"]:::ai
  A2 --> VC["Code validates the answer<br/>known codes, verdict agrees with its own checks"]:::code
  VC --> O["Verdict with reasons and quotes<br/>report and human hand-off"]:::good
  A1 -.->|"error or truncation"| H["Needs a person to check"]:::person
  A2 -.->|"error, truncation or inconsistent answer"| H
  VC -.->|"invalid"| H
```

Two AI steps, one call each, fixed order, fixed output shape. The document text is treated as
untrusted data: the judge is told to ignore any instruction inside it.

### Agent 1: the careful reader

- **A step-by-step procedure** (header, registration, item table, totals, payment, delivery, penalty, validity). It re-reads the relevant part of the text before filling each step.
- **A `notes` line before each value**: one sentence on where it found the fact and any doubt. This is the chain-of-thought, written into the output where it is useful and inspectable.
- **Field definitions, but no company thresholds.** It knows what "payment days" means (the balance, counted from delivery), not that 20% is the limit. If the extractor knew the limits it would be tempted to bend the facts toward compliance.
- **Targeted instructions for known traps:** "available on request" is not a TIN; "0.5% per week of delay" states no base, so the penalty basis is ambiguous; event words like "of PO" are the reference event, not a condition.
- **Typed schema from approach 3**, plus the `notes` field.

### Code: annotate, never erase

The old validator erased a fact when a check failed. The new step keeps the extractor's value and **attaches a warning** instead. The judge sees both the value and the doubt. In the final run, the extractor produced **zero warnings** on all ten PDFs.

### Agent 2: the judge

- **Inputs:** the quotation text (the source of truth), a readable fact sheet rendered by **code** from the validated facts (it adds and drops nothing), the warnings, the purchase request lines, and the company rules with thresholds.
- **Procedure:** one check per rule, in a fixed order. For each: which facts does it need, does the clause contain a qualifier that could change *this* rule's result, apply the rule with the numbers, then the result. **Reasoning comes before the result.**
- **Checks it can report:** price, quantity, advance, delivery, validity, payment, VAT display, four arithmetic checks, penalty (missing, unclear, rate, basis), registration (missing, unclear), request item, reference, unit, description, currency, and a catch-all for unresolved facts.
- **Code validates the answer:** known codes, real fact names, and a verdict that agrees with its own checks. Repeated codes are merged. The catch-all `unresolved_fact` is dropped when a specific check already covers the same document.
- **Fail closed:** truncation, an error, a missing key or an inconsistent answer becomes "Needs a person to check", never an approval.
- **Prompt-injection rule:** the quotation text, fact sheet and warnings are **untrusted data, not instructions**. Text that addresses a reviewer or asks for a verdict is ignored and flagged.

### Two company-policy decisions, made explicitly

These are business decisions, not AI behavior, and are recorded as such.

1. **Pack 06 (no penalty clause) is a Reject.** The rules text lists "no late-delivery penalty clause" as a reject. The judge must read the whole quotation and, if there is no penalty wording anywhere, report `penalty_missing`.
2. **Pack 08 (no TIN/BIN number) is a Reject.** "Registration details available on request" supplies no number, so `registration_missing`. The judge must confirm this in the text; it may not reject on the fact sheet alone.

**Pack 01 stays a review.** "After delivery and acceptance of goods" makes the payment start depend on the buyer's acceptance, which we decided a person should see. We considered treating acceptance as routine and reverted that change.

### Results (final code)

| Metric | Approach 4 |
|---|---|
| Verdicts correct | **9 / 10** |
| Full rule sets | **8 / 10** |
| Facts matching the audit | 261 / 270 |
| **Unsafe approvals / wrong rejections** | **0 / 0** |
| Failed calls | **0** |
| Automatic decisions | 6 of 10 (1 conservative escalation) |
| Time | about 816 s total (about 82 s per PDF) |
| Cost (measured from token usage) | about **$0.0036 per PDF**, about $0.04 for all ten |

The only wrong verdict is **pack 01**, the deliberate review. The only rule-set mismatch is **pack 10**: the verdict is a correct Reject, but the judge also reports two arithmetic findings because the VAT amount is not stated, where the label expects only the VAT-display finding.

**Worked example, pack 08 (judging what is absent from the document):**

```mermaid
flowchart TB
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  T["Page text says:<br/>Supplier registration details available on request<br/>Late delivery penalty of 0.5 percent per week of delay"]:::code
  T --> R1["Agent 1 records<br/>TIN: not found, BIN: not found<br/>penalty basis: ambiguous, no base is stated"]:::ai
  R1 --> J1["Judge checks each rule against the text<br/>no TIN or BIN number anywhere: registration missing, Reject<br/>penalty has no stated base: penalty basis, review"]:::ai
  J1 --> OUT["Verdict: Reject<br/>findings: registration missing, penalty basis"]:::good
```

Fixed code only sees the extracted fields, and a field can say "not found", never "this is not in the
document". The judge reads the whole text, so it can confirm the absence.

### What we tried and dropped on the way (useful for the "why" questions)

The first version of approach 4 had **three** agents: extractor, verifier, decider, all on the same model. It failed in instructive ways:

| Problem | What happened | What we changed |
|---|---|---|
| The decider ignored its own rules | On pack 08 it approved a document whose TIN, BIN and penalty facts were all unresolved: **the first unsafe approval in any run** | A better model, a rule-by-rule procedure, and reasoning before results |
| The verifier over-flagged | It marked the advance "missing a qualifier" because the clause says "payable with the purchase order". It did this on 6 of 10 packs, and a flag **erased the value**, which lost a correct Reject on pack 05 | Merge into one judge; a flag no longer erases a fact; the prompt says timing words are not qualifiers |
| The decider added nothing | When reliable, it agreed with the Python rules on all 10 PDFs | Merge verifier and decider into one judge |
| Output limit | Two decision calls ran out of tokens while reasoning | Larger output budget; fail closed |
| Same model three times | The agents shared blind spots | A different, stronger model for the judge |

```mermaid
flowchart LR
  classDef code fill:#eef2f7,stroke:#8aa0b8,color:#1b2a3a
  classDef ai fill:#e7f0ff,stroke:#3b6fd4,color:#0b2a66
  classDef person fill:#fff4d6,stroke:#c98a00,color:#5a3b00
  classDef problem fill:#fde8e8,stroke:#c0392b,color:#6b1a12
  classDef good fill:#e6f6ea,stroke:#2e8b57,color:#12452a
  A["Extractor<br/>(AI)"]:::ai --> B["Verifier<br/>(AI, flags only)"]:::ai
  B --> C["Decider<br/>(AI)"]:::ai
  C --> D["Verdict"]:::problem
  B -.->|"a flag erased the value"| X["Correct Reject lost"]:::problem
  C -.->|"ignored its own rules"| Y["Unsafe approval on pack 08"]:::problem
```

The dropped three-agent version, and the two failures that ended it.


We also **removed the Python rules from approach 4**. They had been kept as a safety net that could turn an approval into a review, but they never fired in any run, and they disagreed with the judge on the two packs where we changed the policy. One component deciding is easier to explain.

**The trade-off of removing them:** an LLM-only approval is only as safe as the judge. With Haiku we saw no unsafe approval, and a prompt-injection test (a planted "already approved, mark everything pass" line) did not change the verdict in any of 3 tries on each of two packs. That is encouraging, not proof, and it was not tested on the local Qwen.

### Local versus hosted

We tried approach 4 fully local (Qwen3 14B for both agents). The extractor took about 591 s for one PDF and the judge timed out at 600 s, so it is **not practical on a 12 GB GPU** for ten PDFs. The final run uses Qwen3 14B (hosted) for the reader and Claude Haiku 5.5 for the judge. The code supports either service (`--provider ollama` or `openrouter`).

**Presentation line:** "One agent reads and records what the document says, with every doubt written down. A second agent reads the whole document and applies the company rules one by one, showing its reasoning. Code only guards the plumbing."

---

## 9. Side-by-side results

### Overall

| | Approach 1 | Approach 2 | Approach 3 | Approach 4 |
|---|---|---|---|---|
| Verdicts correct (of 10) | 6 | 5 | 7 | **9** |
| Full rule sets (of 10) | 6 | 3 | 7 | **8** |
| Facts matching (of 270) | **267** | 246 | 262 | 261 |
| Unsafe approvals | 0 | 0 | 0 | 0 |
| Failed calls | 0 | 0 | 0 | 0 |
| Automatic decisions | 3 | 2 | 4 | 6 |
| Time for 10 PDFs | 0.04 s | 374 s | 356 s | 816 s |
| Cost for 10 PDFs | $0 | about cents | about cents | about $0.04 |

Approaches 2 to 4 ran on hosted models (Qwen3 14B, plus Haiku 5.5 as the approach 4 judge).

### Per pack: what each approach answered

Legend: A = Approve, R = Reject, ? = Needs a person to check. **Bold** = wrong.

| Pack | Expected | Approach 1 | Approach 2 | Approach 3 | Approach 4 |
|---|---|---|---|---|---|
| 01 | A | **?** | **?** | **?** | **?** |
| 02 | A | **?** | **?** | A | A |
| 03 | R | R | **?** | R | R |
| 04 | ? | ? | ? | ? | ? |
| 05 | R | R | R | R | R |
| 06 | R | **?** | **?** | **?** | R |
| 07 | ? | ? | ? | ? | ? |
| 08 | R | **?** | **?** | **?** | R |
| 09 | ? | ? | ? | ? | ? |
| 10 | R | R | R | R | R |

Reading the table:

- **Pack 02** is the one place AI beats code at *reading*: approaches 3 and 4 approve it correctly; approaches 1 and 2 cannot.
- **Packs 06 and 08** flip only in approach 4, because of the two policy decisions, not because of a better model. The same decisions would likely lift the other approaches too (not tested).
- **Pack 01** is wrong everywhere, by decision.
- **No approach ever approved a wrong document.** Every wrong verdict is a safe "ask a person".

---

## 10. The decision log (why the system is shaped this way)

| Decision | Why |
|---|---|
| Fixed pipeline, no free-running agent | The brief asks for clear fixed steps. Even approach 4's two agents run in a fixed order with fixed inputs. |
| Build the no-AI baseline first | To know whether AI is needed, and to have something to beat. |
| Keep everything except extraction identical across approaches 1 to 3 | So a score change is attributable to one thing. |
| Require an exact quote for every found fact | Auditability, and an easy way to catch invented data. |
| Fail closed everywhere | The brief says never guess. A failure is a review, never an approval. |
| Constrain the model's output while it writes | Cheaper and more reliable than hoping it follows format advice. |
| Loosen the validator narrowly, never the evidence rule | A right value should not be lost over spacing or a `%`. An invented quote must still fail. |
| Annotate instead of erasing (approach 4) | Lets the judge see the value *and* the doubt, and decide. |
| Keep thresholds out of the extractor's prompt | So the reader records what the document says, not what would pass. |
| Separate reading from judging (approach 4) | They need different information: the reader needs field definitions; the judge needs the rules and the full text. |
| Pick a stronger model for the judge | It is the step where a skipped rule would be an unsafe approval. |
| Treat document text as untrusted data in the judge | Prompt-injection defence now that no code guards the approval. |
| Pin the hosting backends | One flaky backend caused several failed runs; failures count against the score. |
| Never tune silently | Results are reported as they came out; changes are described and the earlier numbers kept. |
| Policy decisions are the business owner's | The 06/08 rejects and the 01 review are recorded as decisions, not model improvements. |

---

## 11. The three packs that differ from the labels (01, 06, 08)

This is the most important section for honesty.

For approaches 1 to 3, packs 01, 06 and 08 were wrong in the same way. They are **not extraction failures**. The extraction was right; our *policy* was stricter than the labels.

| Pack | The document | The rules text | What approaches 1 to 3 did | What approach 4 does now |
|---|---|---|---|---|
| 01 | Payment "after delivery **and acceptance of goods**" | Needs review only if payment terms are unclear or outside 30 to 60 days | Review (a qualified payment term is unclear) | **Review** (decision: a person should see it) |
| 06 | No penalty clause at all | **Reject** if there is no late-delivery penalty clause | Review (reject only on an explicit "no penalty" statement) | **Reject** |
| 08 | "Registration details available on request" (no TIN/BIN) | **Reject** if TIN or BIN is missing | Review (reject only on an explicit "missing" statement) | **Reject** |

In every case our system was *more cautious* than the labels, never less. That is the "never guess" principle working, but it also means the first three approaches under-score against these labels for a policy reason.

**What this means for the 9/10:**

- The improvement from 7 to 9 is a **policy interpretation** (read the rules text literally for 06 and 08), not purely a better AI.
- That decision was made **after** looking at these packs.
- It made the system **less cautious**: it now auto-rejects in two situations that previously went to a person.
- The same change was **not** applied to approaches 1 to 3 (their rules code is unchanged), so the 9 versus 7 comparison is not like for like. Applying it to them would probably raise their scores too. That has not been tested.

Presented honestly, this is a strength: the team found where the score was limited by policy, not by AI, and made an explicit decision.

---

## 12. Safety and honesty: what does not work

- **Development-set scores only.** No held-out test. A fair claim is "works on these ten documents", not "is 90% accurate on supplier quotes".
- **Prompts and policy tuned on the same ten PDFs**, especially approach 4's judge prompt for packs 06 and 08.
- **Single runs.** Model output can vary between runs; the headline numbers are one run each.
- **Labels audited by an AI assistant,** not independent human annotation.
- **Approach 4 has no code guard on its approvals.** Its safety rests on the judge model, fail-closed handling, and the untrusted-data rule. The Python-rules guard was removed by decision after it never fired.
- **Prompt-injection testing was narrow:** two packs, one injected line, one judge model (Haiku), three tries each.
- **The judge's arithmetic is the judge's own.** Language models can slip on arithmetic; the earlier code-based arithmetic was exact. Approach 4 trades that exactness for being able to read the whole document.
- **Pack 10's rule set** has two extra arithmetic findings that the label does not expect.
- **`penalty_basis` is the weakest fact** (6 of 10 match in approach 4).
- **Hosted models send document text to a third party.** The sample PDFs are fictional; for real documents the local route or a contract with the provider would matter.
- **Local approach 4 is too slow** on a 12 GB GPU (over 10 minutes per call at the extreme).

---

## 13. Cost, speed, and where to run it

| Approach | Time for 10 PDFs | Cost | Runs where |
|---|---|---|---|
| 1 | 0.04 s | $0 | local, no network |
| 2 | about 374 s (hosted); about 5 min per PDF on a local 14B model | cents | local or hosted |
| 3 | about 356 s (hosted) | cents | local or hosted |
| 4 | about 816 s (hosted) | about $0.04 (about $0.0036 per PDF) | hosted in practice |

Model choices were checked against the OpenRouter catalogue; the pricing at the time was about $0.12 / $0.24 per million tokens for Qwen3 14B and $0.10 / $0.50 for Claude Haiku 5.5 (input / output). Approach 4 used about 10,000 input and 7,000 output tokens per PDF across its two agents (measured in the final run: roughly 100,000 input and 71,000 output tokens for all ten).

---

## 14. What we would do next

1. **A held-out test.** Collect or write new quotations (some tricky ones: partial penalties, multiple items, unusual layouts), freeze the prompts, and run once.
2. **Repeat runs.** Run approach 4 several times and report the spread, since model output varies.
3. **A broader injection test set** against whichever judge is used in production, including the local model.
4. **Fix the pack 10 rule-set gap.** Tell the judge not to report arithmetic checks when the VAT amount is not stated, because the VAT-display finding already covers it.
5. **Align the code rules with the policy decisions** for 06 and 08 (a text-level "is there any penalty or TIN/BIN wording" check), so approaches 1 to 3 can be compared fairly.
6. **Cheaper reading for easy documents.** Use the baseline reader when it is confident, and call the AI only for clauses it leaves unresolved (a hybrid). This keeps the 267/270 reading and the AI's wording strength.
7. **A real review screen.** The human-review handoff exists (questions, responses, audit trail); a small UI over it would complete the workflow.
8. **An independent label audit** by a person, not an AI assistant.

---

## 15. Presentation guide

The brief asks for a **5-minute Loom** that a non-technical person can follow, and explains the choices and what you would improve. Suggested structure:

| Time | Slide | Say |
|---|---|---|
| 0:00 | The problem | "A garment company gets supplier quotes. A person checks each one against the purchase request and the company rules. We want a system that does it step by step and never guesses." |
| 0:30 | Fixed steps | Show the pipeline: read, extract, validate, decide, report. "Always the same order. When it is unsure, it asks a person." |
| 1:00 | Approach 1, the baseline | "First I asked whether we need AI at all. Plain code reads 98.9% of the facts and gets 6 of 10. Nothing wrong gets approved." |
| 1:45 | Approach 2, first AI | "A model reads the document. It understood wording the code could not, for example delivery 'at your factory' means 21 days. But it broke on formats, and our checker threw correct answers away. 5 of 10." |
| 2:30 | Approach 3, fix the contract | "I did not change the model. I made the output shape strict and stopped discarding right answers. 7 of 10." |
| 3:15 | Approach 4, two agents | Diagram of reader plus judge. "One agent reads and writes down every doubt. A second agent reads the whole document and applies the company rules one by one, showing why." |
| 4:00 | Results | The per-pack table. "9 of 10, and nothing wrong was approved." |
| 4:30 | Honesty | "These are the ten files I built on. 9 of 10 includes a policy decision I made after looking at them. Here is what does not work yet." |
| 5:00 | Next | A held-out test, repeat runs, a hybrid reader. |

### Likely questions, with answers

- **Why not one big AI agent?** The brief asks for fixed steps. Fixed steps are also easier to test, audit and fail safely. Even approach 4's agents run in a fixed order.
- **Did you use LangGraph or n8n?** Yes, LangGraph. Each approach is a small straight-line graph (no branches, no loops, no tools); the diagrams are in the README and are generated from the code.
- **Is 9 of 10 real?** It is real on these ten files. It is a development score, and part of the jump is a policy decision. A held-out test is the next step.
- **Why not stop at approach 1?** It cannot read wording outside its grammar (pack 02), and it cannot tell that a clause is *absent* from the whole document. AI helps there. For documents that fit the template, code is better.
- **Why did you remove the code rules from approach 4?** They never fired, they duplicated the judge, and two deciders made the system harder to explain. The trade-off is that approval safety now rests on the judge, which I tested with an injection check but not exhaustively.
- **How do you stop the AI making things up?** Every found fact needs an exact quote that code checks against the page; invented quotes fail; the output format is constrained while the model writes; and every failure becomes a review.
- **What if the model is down or slow?** Every model failure is caught, recorded and turned into "Needs a person to check". The failed run is saved, not hidden.
- **What would you change live?** The thresholds live in `config/company-rules.json`, and the rules text is passed to the approach 4 judge, so a policy change is a config and prompt edit, with tests for the rules engine.
- **Why a local model, and why not?** Local keeps documents on the machine (the brief's second task stresses this), but the 14B model needs about 5 minutes per PDF per agent on a 12 GB GPU. Hosted is fast and cheap; the code supports both.

### Visual ideas

- The pipeline diagram (section 4) and the approach 4 diagram (section 8).
- The per-pack table (section 9), colouring wrong cells.
- A single bar chart of verdicts correct: 6, 5, 7, 9.
- One pack as a worked example: pack 02 (the "factory" wording) for reading, and pack 08 for judging ("available on request" is not a TIN).

---

## 16. Appendix

### Repository map

| Path | What is in it |
|---|---|
| `procurement/review.py` | The fixed workflow and the command-line entry point |
| `procurement/workflow.py` | The fixed workflow as four small LangGraph graphs, one per approach, plus diagram export |
| `procurement/shared/` | PDF reading, fact contract, validation, rules engine, human review, saved runs, reports, evaluation |
| `procurement/approach1/` | The deterministic extractors |
| `procurement/approach2/` | The first AI extractor (Ollama, OpenRouter, Gemini) |
| `procurement/approach3/` | The typed schema and stricter prompt |
| `procurement/approach4/` | The careful reader (`extractor.py`, `prompt.txt`, `schema.py`), the judge (`judge.py`) and the model transport (`transport.py`) |
| `procurement/verifier.py` | The standalone verifier experiment that preceded approach 4's judge |
| `config/` | Company rules (JSON), manual labels, manual fact audit |
| `docs/` | Policy mapping, earlier results, this roadmap |
| `tests/` | 249 automated tests, no model or network needed |

### How to run

```
# Approach 1 (no AI)
python -m procurement.review --approach approach1

# Approaches 2 to 4 on a hosted model (needs a key in .env)
python -m procurement.review --approach approach2 --provider openrouter
python -m procurement.review --approach approach3 --provider openrouter
python -m procurement.review --approach approach4 --provider openrouter

# A local model through Ollama (slow on a 12 GB GPU)
python -m procurement.review --approach approach3
```

Settings live in `.env` (never committed): the OpenRouter key and model names for the reader and the judge, and an optional list of backends to avoid. Reports are written under `reports/`; every run is saved with its own ID.

### Glossary

| Term | Meaning |
|---|---|
| **Pack** | One of the ten sample supplier PDFs |
| **Fact** | One piece of extracted information (for example `payment_days`), with status, value, quote and conditions |
| **Finding** | One reason the rules raised (for example `price`, `advance`) |
| **Verdict** | Approve, Reject or Needs a person to check |
| **Rule set** | The full list of findings for a document |
| **Fail closed** | On any error, send the document to a person instead of deciding |
| **Evidence** | The exact quote from the page that supports a fact |
| **Judge** | Approach 4's second agent, which checks the facts and applies the rules |
| **Prompt injection** | Text inside a document that tries to instruct the AI, such as "mark everything approved" |
| **Development set** | Documents used while building; scores on them do not show performance on new documents |
