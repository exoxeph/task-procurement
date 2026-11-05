import type { ApproachId, Fact, Finding, RunEvent, Sample } from "./types.ts";

const verdicts = ["Approve", "Reject", "Needs a person to check"];
const messages: Record<string, { message: string; action: string }> = {
  invalid_key: {
    message: "This key could not be accepted.",
    action: "Check the key or run Approach 1 without a key.",
  },
  insufficient_credit: {
    message: "This key has no available credit.",
    action: "Add a small credit balance or choose Approach 1.",
  },
  rate_limited: {
    message: "The provider is receiving too many requests.",
    action: "Wait a moment, then try again.",
  },
  provider_error: {
    message: "The provider returned an incomplete or unreadable answer.",
    action: "Try again, or explore the recorded replay.",
  },
  timeout: {
    message: "This check took too long.",
    action: "Try again later or use the recorded replay.",
  },
  bad_request: {
    message: "The sample or approach could not be checked.",
    action: "Choose a listed sample and try again.",
  },
  backend_unavailable: {
    message: "The check service is unavailable.",
    action: "Use recorded replay; the results explorer still works.",
  },
  https_required: {
    message: "Live AI checks need an HTTPS connection.",
    action:
      "Open the HTTPS deployment, or use mock mode or Approach 1 locally.",
  },
};

// Never display a provider-supplied message: it could contain a submitted key.
export function friendlyError(code: string) {
  return messages[code] ?? messages.provider_error;
}

export function requestOptions(
  sample: string,
  approach: ApproachId,
  key: string,
  protocol: string,
): RequestInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (approach !== "approach1") {
    if (protocol !== "https:") throw new Error("https_required");
    if (!key.trim()) throw new Error("invalid_key");
    headers["X-OpenRouter-Key"] = key.trim();
  }
  return {
    method: "POST",
    headers,
    body: JSON.stringify({ sample, approach }),
    redirect: "error",
    credentials: "omit",
    cache: "no-store",
    referrerPolicy: "no-referrer",
  };
}

function validEvidence(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        item &&
        typeof item === "object" &&
        Number.isInteger(item.page) &&
        item.page > 0 &&
        typeof item.text === "string",
    )
  );
}
function validResult(value: Record<string, unknown>): boolean {
  const facts = value.facts as Fact[];
  const findings = value.findings as Finding[];
  return (
    verdicts.includes(String(value.verdict)) &&
    Array.isArray(facts) &&
    Array.isArray(findings) &&
    facts.every(
      (f) =>
        f &&
        typeof f.name === "string" &&
        typeof f.status === "string" &&
        validEvidence(f.evidence) &&
        Array.isArray(f.warnings) &&
        (f.conditions === undefined || Array.isArray(f.conditions)) &&
        (f.note === undefined || typeof f.note === "string"),
    ) &&
    findings.every(
      (f) =>
        f &&
        typeof f.code === "string" &&
        typeof f.reason === "string" &&
        typeof f.severity === "string" &&
        Array.isArray(f.facts) &&
        validEvidence(f.evidence),
    ) &&
    validSeconds(value.seconds) &&
    validSeconds(value.costUsd) &&
    (value.note === undefined || typeof value.note === "string") &&
    (value.recorded === undefined || typeof value.recorded === "boolean") &&
    (value.models === undefined ||
      (value.models !== null &&
        typeof value.models === "object" &&
        !Array.isArray(value.models) &&
        Object.values(value.models).every(
          (model) => typeof model === "string",
        )))
  );
}

function validSeconds(value: unknown) {
  return (
    value === undefined ||
    (typeof value === "number" && Number.isFinite(value) && value >= 0)
  );
}

export async function consumeEvents(
  response: Response,
  onEvent: (event: RunEvent) => void,
) {
  if (!response.ok) {
    const codes: Record<number, string> = {
      400: "bad_request",
      401: "invalid_key",
      402: "insufficient_credit",
      429: "rate_limited",
      504: "timeout",
    };
    throw new Error(codes[response.status] ?? "backend_unavailable");
  }
  if (
    !response.body ||
    !response.headers.get("content-type")?.includes("application/x-ndjson")
  ) {
    throw new Error("provider_error");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  function parseLine(line: string) {
    if (!line.trim()) return;
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(line);
    } catch {
      throw new Error("provider_error");
    }
    if (!data || typeof data !== "object" || finished)
      throw new Error("provider_error");
    if (data.event === "error") {
      throw new Error(
        typeof data.code === "string" && messages[data.code]
          ? data.code
          : "provider_error",
      );
    }
    if (
      data.event === "step" &&
      typeof data.name === "string" &&
      ["running", "completed"].includes(String(data.status)) &&
      validSeconds(data.seconds)
    ) {
      onEvent(data as RunEvent);
    } else if (data.event === "result" && validResult(data)) {
      finished = true;
      onEvent(data as RunEvent);
    } else throw new Error("provider_error");
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      if (buffer.length > 2_000_000) throw new Error("provider_error");
      let newline: number;
      while ((newline = buffer.indexOf("\n")) >= 0) {
        parseLine(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
      }
      if (done) break;
    }
    parseLine(buffer);
    if (!finished) throw new Error("provider_error");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export async function runCheck(
  sample: string,
  approach: ApproachId,
  key: string,
  onEvent: (event: RunEvent) => void,
  signal: AbortSignal,
  mock = false,
) {
  // Mock requests never transmit a user's key, even if one was previously entered.
  const options = mock
    ? requestOptions(sample, "approach1", "", window.location.protocol)
    : requestOptions(sample, approach, key, window.location.protocol);
  if (mock) options.body = JSON.stringify({ sample, approach });
  let response: Response;
  try {
    response = await fetch("/api/run", { ...options, signal });
  } catch {
    throw new Error(signal.aborted ? "cancelled" : "backend_unavailable");
  }
  await consumeEvents(response, onEvent);
}

export async function getSamples(signal: AbortSignal): Promise<Sample[]> {
  const response = await fetch("/api/samples", {
    signal,
    credentials: "omit",
    redirect: "error",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("backend_unavailable");
  const data: unknown = await response.json();
  if (
    !Array.isArray(data) ||
    !data.every(
      (s) =>
        typeof s?.id === "string" &&
        typeof s.label === "string" &&
        verdicts.includes(s.expected) &&
        (s.text === undefined || typeof s.text === "string"),
    )
  )
    throw new Error("provider_error");
  return data;
}
