import test from "node:test";
import assert from "node:assert/strict";
import { startupMode } from "../lib/build-mode.mjs";

test("production uses its built mode and rejects conflicting runtime settings", () => {
  assert.equal(startupMode("start", undefined, "mock"), "mock");
  assert.equal(startupMode("start", undefined, "live"), "live");
  assert.throws(() => startupMode("start", "mock", "live"), /Rebuild/);
  assert.equal(startupMode("dev", undefined, undefined), "mock");
  assert.equal(startupMode("dev", "live", undefined), "live");
});
