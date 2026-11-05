import data from "../public/data/results.json";
import type { Approach, ApproachId, Pack, RunResult } from "./types.ts";

export const approaches = data.approaches as Approach[];
export const packs = data.packs as Pack[];

export function recordedResult(pack: Pack, approach: ApproachId): RunResult {
  return (
    pack.results?.[approach] ?? {
      verdict: pack.answers[approach],
      findings: [],
      facts: [],
      recorded: true,
      note: "Recorded verdict. Detailed findings and per-pack timing for this approach are not included in this replay dataset.",
    }
  );
}

export const limits = [
  [
    "Development scores, not unseen accuracy",
    "All ten PDFs were visible while building. These scores are not a test on unseen documents.",
  ],
  [
    "The policy changed before the final approach",
    "9 of 10 includes a policy decision made after looking at packs 06 and 08: read the rules literally. Approaches 1–3 did not get this change. 9 versus 7 is not like for like.",
  ],
  [
    "Single runs, without independent human auditing",
    "Model output can vary. Fact labels were audited by an AI assistant, not independent humans.",
  ],
  [
    "No code guard on Approach 4’s approvals",
    "Safety rests on the judge model, fail-closed handling and a prompt-injection rule. Injection testing covered only two packs and one model.",
  ],
  [
    "Hosted models receive document text",
    "The text is sent to a third party when hosted models run. These sample documents are fictional.",
  ],
  [
    "Fully local inference was too slow",
    "The reported local experiment on a 12 GB GPU exceeded ten minutes per call. This is separate from the five-PDF rerun.",
  ],
] as const;
