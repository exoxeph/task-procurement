import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const data = JSON.parse(
  readFileSync(new URL("../public/data/results.json", import.meta.url), "utf8"),
);
const samples = data.packs.map(({ id, label, expected, text }) => ({
  id,
  label,
  expected,
  text,
}));
const steps = [
  "Read PDF",
  "Agent 1: extract facts",
  "Code annotates warnings",
  "Agent 2: judges",
  "Report",
];

createServer(async (request, response) => {
  response.setHeader("Cache-Control", "no-store");
  if (request.method === "GET" && request.url === "/api/samples") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify(samples));
    return;
  }
  if (request.method !== "POST" || request.url !== "/api/run") {
    response.writeHead(404);
    response.end();
    return;
  }
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 4096) {
      response.writeHead(400);
      response.end();
      return;
    }
  }
  let input;
  try {
    input = JSON.parse(body);
  } catch {
    response.writeHead(400);
    response.end();
    return;
  }
  const pack = data.packs.find((pack) => pack.id === input.sample);
  if (!pack || !data.approaches.some((a) => a.id === input.approach)) {
    response.writeHead(400);
    response.end();
    return;
  }
  response.writeHead(200, {
    "Content-Type": "application/x-ndjson",
    "X-Accel-Buffering": "no",
  });
  const send = (event) => {
    if (!response.destroyed) response.write(JSON.stringify(event) + "\n");
  };
  if (process.env.MOCK_ERROR) {
    send({
      event: "error",
      code: process.env.MOCK_ERROR,
      message: "Mock failure",
    });
    response.end();
    return;
  }
  const names =
    input.approach === "approach4"
      ? steps
      : ["Read PDF", "Extract facts", "Check", "Decide", "Report"];
  for (const name of names) {
    if (response.destroyed) return;
    send({ event: "step", name, status: "running" });
    await new Promise((resolve) => setTimeout(resolve, 450));
    send({ event: "step", name, status: "completed" });
  }
  const result = pack.results?.[input.approach] ?? {
    verdict: pack.answers[input.approach],
    facts: [],
    findings: [],
    recorded: true,
    note: "Recorded verdict only. Detailed findings and per-pack metrics for this approach are not in this dataset.",
  };
  send({
    ...result,
    event: "result",
    recorded: true,
    note:
      "Mock API: accelerated playback of a saved development answer. No AI ran and no credits were spent. " +
      (result.note ?? ""),
  });
  response.end();
}).listen(4311, "127.0.0.1", () => {
  console.info(
    "Mock API listening on 127.0.0.1:4311. No model calls or keys required.",
  );
});
