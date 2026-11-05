export type Verdict = "Approve" | "Reject" | "Needs a person to check";
export type ApproachId = "approach1" | "approach2" | "approach3" | "approach4";
export type Evidence = { page: number; text: string };
export type Fact = {
  name: string;
  status: string;
  value: unknown;
  rawValue?: unknown;
  referenceEvent?: unknown;
  conditions?: unknown[];
  evidence: Evidence[];
  warnings: unknown[];
  note?: string;
};
export type Finding = {
  code: string;
  severity: Verdict | string;
  reason: string;
  facts: string[];
  evidence: Evidence[];
};
export type RunResult = {
  verdict: Verdict;
  seconds?: number;
  costUsd?: number;
  models?: Record<string, string>;
  findings: Finding[];
  facts: Fact[];
  recorded?: boolean;
  note?: string;
};
export type StepEvent = {
  event: "step";
  name: string;
  status: "running" | "completed";
  seconds?: number;
};
export type RunEvent = StepEvent | (RunResult & { event: "result" });
export type Sample = {
  id: string;
  label: string;
  expected: Verdict;
  text?: string;
};
export type Approach = {
  id: ApproachId;
  name: string;
  question: string;
  idea: string;
  right: string;
  wrong: string;
  verdicts: number;
  ruleSets: number;
  facts: number;
  factsTotal: number;
  seconds: number;
  costUsd?: number;
  costLabel: string;
  unsafeApprovals: number;
};
export type Pack = {
  id: string;
  label: string;
  tests: string;
  expected: Verdict;
  answers: Record<ApproachId, Verdict>;
  text?: string;
  results?: Partial<Record<ApproachId, RunResult>>;
};
