import type { Verdict as VerdictType } from "../lib/types";

export function Verdict({ value }: { value: VerdictType }) {
  const kind =
    value === "Approve" ? "approve" : value === "Reject" ? "reject" : "review";
  return (
    <span className={`verdict ${kind}`}>
      <span aria-hidden="true">
        {kind === "approve" ? "✓" : kind === "reject" ? "×" : "!"}
      </span>
      {value}
    </span>
  );
}
