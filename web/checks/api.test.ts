import test from "node:test";
import assert from "node:assert/strict";
import { consumeEvents, friendlyError, requestOptions } from "../lib/api.ts";

const result = {
  event: "result",
  verdict: "Reject",
  seconds: 1,
  findings: [],
  facts: [],
};
function stream(chunks: string[]) {
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const chunk of chunks)
          controller.enqueue(new TextEncoder().encode(chunk));
        controller.close();
      },
    }),
    { headers: { "Content-Type": "application/x-ndjson" } },
  );
}
test("NDJSON survives arbitrary chunks, CRLF and final line without newline", async () => {
  const line = JSON.stringify(result);
  const events: unknown[] = [];
  await consumeEvents(
    stream([
      '{"event":"step","name":"Read ',
      'PDF","status":"completed"}\r\n',
      line.slice(0, 17),
      line.slice(17),
    ]),
    (event) => events.push(event),
  );
  assert.equal(events.length, 2);
  assert.deepEqual(events[1], result);
});
test("unfinished and malformed streams fail rather than inventing success", async () => {
  await assert.rejects(
    consumeEvents(stream([]), () => {}),
    /^Error: empty_response$/,
  );
  await assert.rejects(
    consumeEvents(stream(["not json\n"]), () => {}),
    /provider_error/,
  );
  await assert.rejects(
    consumeEvents(stream(['{"event":"result","verdict":"Maybe"}\n']), () => {}),
    /provider_error/,
  );
});
test("empty 200 responses finish with a clear, safe error", async () => {
  for (const response of [
    new Response(null),
    new Response(""),
    stream(["\n  \r\n"]),
  ]) {
    await assert.rejects(
      consumeEvents(response, () => assert.fail("No event expected")),
      /^Error: empty_response$/,
    );
  }
  assert.match(friendlyError("empty_response").message, /no answer/i);
  assert.match(friendlyError("empty_response").action, /replay/i);
});
test("provider errors use fixed startup guidance and discard supplied text", async () => {
  await assert.rejects(
    consumeEvents(
      stream([
        '{"event":"error","code":"provider_error","message":"secret-key"}\n',
      ]),
      () => assert.fail("No event expected"),
    ),
    /^Error: provider_error$/,
  );
  assert.equal(
    friendlyError("provider_error").message,
    "The check could not start.",
  );
  assert.equal(
    friendlyError("provider_error").action,
    "Try again, or use the recorded replay.",
  );
});
test("error events discard provider message and never reveal the key", async () => {
  await assert.rejects(
    consumeEvents(
      stream([
        '{"event":"error","code":"invalid_key","message":"secret-key"}\n',
      ]),
      () => {},
    ),
    /^Error: invalid_key$/,
  );
  assert.ok(!friendlyError("secret-key").message.includes("secret-key"));
});
test("baseline omits key, AI sends header only, redirects are blocked", () => {
  const baseline = requestOptions(
    "supplier-pack-03",
    "approach1",
    "secret-key",
    "http:",
  );
  assert.equal(new Headers(baseline.headers).has("X-OpenRouter-Key"), false);
  const ai = requestOptions(
    "supplier-pack-03",
    "approach4",
    "secret-key",
    "https:",
  );
  assert.equal(new Headers(ai.headers).get("X-OpenRouter-Key"), "secret-key");
  assert.ok(!String(ai.body).includes("secret-key"));
  assert.equal(ai.redirect, "error");
  assert.equal(ai.credentials, "omit");
  assert.throws(
    () =>
      requestOptions("supplier-pack-03", "approach4", "secret-key", "http:"),
    /https_required/,
  );
});
test("live AI needs a key and maps credit/provider errors to actionable messages", () => {
  assert.throws(
    () => requestOptions("supplier-pack-03", "approach4", "", "https:"),
    /invalid_key/,
  );
  assert.match(
    friendlyError("insufficient_credit").action,
    /credit|Approach 1/i,
  );
  assert.match(friendlyError("backend_unavailable").action, /replay/i);
});

test("malformed optional result and step fields fail before reaching React", async () => {
  const variants = [
    { ...result, note: { provider: "unreadable" } },
    { ...result, models: { judge: { model: "wrong shape" } } },
    {
      ...result,
      facts: [
        {
          name: "quantity",
          status: "found",
          evidence: [],
          warnings: [],
          conditions: "subject to review",
        },
      ],
    },
    {
      ...result,
      facts: [
        {
          name: "quantity",
          status: "found",
          evidence: [],
          warnings: [],
          note: { invalid: true },
        },
      ],
    },
    { event: "step", name: "Read PDF", status: "running", seconds: "1.2" },
  ];
  for (const value of variants) {
    const chunks = [JSON.stringify(value) + "\n"];
    if (value.event === "step") chunks.push(JSON.stringify(result) + "\n");
    await assert.rejects(
      consumeEvents(stream(chunks), () => {}),
      /^Error: provider_error$/,
    );
  }
});
