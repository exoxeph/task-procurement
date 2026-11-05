import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const data = JSON.parse(
  readFileSync(new URL("../public/data/results.json", import.meta.url), "utf8"),
);
test("exact supplied matrix yields 6/5/7/9 with 13 explicit mismatches", () => {
  assert.equal(data.packs.length, 10);
  assert.deepEqual(
    data.approaches.map(
      (a: { id: string }) =>
        data.packs.filter(
          (p: { expected: string; answers: Record<string, string> }) =>
            p.answers[a.id] === p.expected,
        ).length,
    ),
    [6, 5, 7, 9],
  );
});
test("recorded findings quote actual PDF text and retain the supplied verdict", () => {
  for (const pack of data.packs) {
    const result = pack.results.approach4;
    assert.equal(result.verdict, pack.answers.approach4);
    for (const fact of result.facts)
      for (const e of fact.evidence) {
        assert.ok(pack.text.includes(e.text), `${pack.id} ${fact.name}`);
      }
    for (const finding of result.findings)
      for (const e of finding.evidence) {
        assert.ok(pack.text.includes(e.text), `${pack.id} ${finding.code}`);
      }
  }
});
