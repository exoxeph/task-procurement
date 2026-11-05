"use client";

import { useEffect, useRef, useState } from "react";
import { getSamples, friendlyError, runCheck } from "../lib/api";
import { approaches, packs, recordedResult } from "../lib/results";
import type { ApproachId, RunEvent, RunResult, Sample } from "../lib/types";
import { Report } from "./report";

const agentSteps = [
  "Read PDF",
  "Agent 1 extracts",
  "Code annotates warnings",
  "Agent 2 judges",
  "Report",
];
const otherSteps = ["Read PDF", "Extract facts", "Check", "Decide", "Report"];
function stepIndex(name: string, agentic: boolean) {
  const value = name.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (value.startsWith("readpdf")) return 0;
  if (value.startsWith("report")) return 4;
  if (agentic) {
    if (value.startsWith("agent1")) return 1;
    if (value.startsWith("code")) return 2;
    if (value.startsWith("agent2")) return 3;
  } else {
    if (value.startsWith("extract")) return 1;
    if (value.startsWith("check")) return 2;
    if (value.startsWith("decid")) return 3;
  }
  return -1;
}

export function LiveRun({ mock: buildMock }: { mock: boolean }) {
  // A mock build always uses the mock server. A live build can still be switched to Mock, which
  // answers from saved results in the browser and never calls the backend or sends a key.
  const [demo, setDemo] = useState(true);
  const mock = buildMock || demo;
  const [samples, setSamples] = useState<Sample[]>(
    packs.map((p) => ({
      id: p.id,
      label: p.label,
      expected: p.expected,
      text: p.text,
    })),
  );
  const [sample, setSample] = useState("supplier-pack-03");
  const [approach, setApproach] = useState<ApproachId>("approach4");
  const [key, setKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Ready to check");
  const [error, setError] = useState<string | null>(null);
  const [samplesOffline, setSamplesOffline] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [source, setSource] = useState<string | undefined>();
  const [progress, setProgress] = useState<
    Record<number, { status: string; seconds?: number }>
  >({});
  const [elapsed, setElapsed] = useState(0);
  const started = useRef(0);
  const active = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const steps = approach === "approach4" ? agentSteps : otherSteps;
  const selected = samples.find((s) => s.id === sample);

  useEffect(() => {
    const controller = new AbortController();
    const requestGeneration = generation;
    getSamples(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setSamples(data);
          setSamplesOffline(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setSamplesOffline(true);
      });
    return () => {
      controller.abort();
      active.current?.abort();
      requestGeneration.current++;
    };
  }, []);
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(
      () => setElapsed((Date.now() - started.current) / 1000),
      200,
    );
    return () => clearInterval(timer);
  }, [busy]);

  function cancel() {
    generation.current++;
    active.current?.abort();
    setBusy(false);
    setResult(null);
    setProgress({});
    setStatus("Check cancelled. Ready when you are.");
  }
  function reset() {
    setResult(null);
    setError(null);
    setProgress({});
    setStatus("Ready to check");
  }

  async function run(replay: boolean) {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    const current = ++generation.current;
    started.current = Date.now();
    const local = replay || (mock && !buildMock);
    setElapsed(0);
    setError(null);
    setResult(null);
    setProgress({});
    setBusy(true);
    setStatus(
      local
        ? "Replaying a saved answer"
        : mock
          ? "Running the mock API workflow"
          : "Checking the document",
    );
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 120_000);
    function receive(event: RunEvent) {
      if (generation.current !== current || controller.signal.aborted) return;
      if (event.event === "step") {
        const index = stepIndex(event.name, approach === "approach4");
        if (index >= 0)
          setProgress((previous) => ({
            ...previous,
            [index]: { status: event.status, seconds: event.seconds },
          }));
        setStatus(`${event.name}: ${event.status}`);
      } else setResult(event);
    }
    try {
      if (local) {
        const pack = packs.find((p) => p.id === sample);
        if (!pack) throw new Error("bad_request");
        setSource(pack.text);
        const reduced = window.matchMedia(
          "(prefers-reduced-motion: reduce)",
        ).matches;
        for (const [index, name] of steps.entries()) {
          if (controller.signal.aborted) return;
          receive({ event: "step", name, status: "running" });
          if (!reduced)
            await new Promise((resolve) => setTimeout(resolve, 200));
          setProgress((previous) =>
            generation.current === current
              ? { ...previous, [index]: { status: "completed" } }
              : previous,
          );
        }
        if (!controller.signal.aborted)
          receive({ ...recordedResult(pack, approach), event: "result" });
      } else {
        setSource(selected?.text);
        await runCheck(
          sample,
          approach,
          key,
          receive,
          controller.signal,
          buildMock,
        );
      }
      if (current === generation.current && !controller.signal.aborted) {
        setProgress(
          Object.fromEntries(
            steps.map((_, index) => [index, { status: "completed" }]),
          ),
        );
        setStatus(
          local
            ? "Saved answer ready. No AI ran."
            : mock
              ? "Mock check complete. No AI ran or credit was spent."
              : "Check complete",
        );
      }
    } catch (failure) {
      if (current === generation.current) {
        setResult(null);
        setError(
          timedOut
            ? "timeout"
            : failure instanceof Error
              ? failure.message
              : "provider_error",
        );
        setStatus("Check did not complete");
      }
    } finally {
      clearTimeout(timeout);
      if (current === generation.current) {
        setBusy(false);
        setElapsed((Date.now() - started.current) / 1000);
      }
    }
  }

  const needsKey = approach !== "approach1" && !mock;
  return (
    <div className="run-workspace">
      <div className="workspace-heading">
        <strong className="replay-label">
          {mock
            ? "Mock API / recorded answers"
            : "Live API / bring your own key"}
        </strong>
        <span className="tag">
          {mock ? "No model calls or charges" : "Same-origin /api"}
        </span>
      </div>
      {!buildMock && (
        <div className="mode-switch" role="group" aria-label="Check mode">
          <button
            type="button"
            aria-pressed={demo}
            disabled={busy}
            onClick={() => {
              setDemo(true);
              reset();
            }}
          >
            Mock (no key)
          </button>
          <button
            type="button"
            aria-pressed={!demo}
            disabled={busy}
            onClick={() => {
              setDemo(false);
              reset();
            }}
          >
            Live (your key)
          </button>
        </div>
      )}
      {samplesOffline && (
        <p className="service-notice" role="status">
          Sample service unavailable. Showing the ten saved samples; recorded
          replay still works.
        </p>
      )}
      <div className="run-grid">
        <form
          className="run-controls"
          onSubmit={(e) => {
            e.preventDefault();
            void run(false);
          }}
        >
          <label htmlFor="sample">Fictional supplier PDF</label>
          <select
            id="sample"
            value={sample}
            disabled={busy}
            onChange={(e) => {
              setSample(e.target.value);
              reset();
            }}
          >
            {samples.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id.slice(-2)} · {s.label}
              </option>
            ))}
          </select>
          <label htmlFor="approach">Approach</label>
          <select
            id="approach"
            value={approach}
            disabled={busy}
            onChange={(e) => {
              setApproach(e.target.value as ApproachId);
              reset();
            }}
          >
            {approaches.map((a, index) => (
              <option key={a.id} value={a.id}>
                {index + 1} · {a.name}
                {index === 0 ? " (no key)" : ""}
              </option>
            ))}
          </select>
          {approach !== "approach1" && (
            <div className="key-controls">
              <label htmlFor="api-key">OpenRouter API key</label>
              <input
                id="api-key"
                type={showKey ? "text" : "password"}
                value={key}
                disabled={mock}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                aria-describedby="key-help"
                placeholder={
                  mock ? "Not needed in mock mode" : "Paste a temporary key"
                }
                onChange={(e) => setKey(e.target.value)}
              />
              <div className="key-actions">
                <button
                  type="button"
                  disabled={mock}
                  onClick={() => setShowKey(!showKey)}
                  aria-pressed={showKey}
                >
                  {showKey ? "Hide" : "Show"} key
                </button>
                <button
                  type="button"
                  disabled={!key}
                  onClick={() => {
                    setKey("");
                    setShowKey(false);
                  }}
                >
                  Forget key
                </button>
              </div>
              <p id="key-help" className="helper">
                Your key is sent only to run this check and is never stored. Use
                a throwaway key with a small spending limit.
              </p>
              <p className="helper">
                <a
                  href="https://openrouter.ai/keys"
                  target="_blank"
                  rel="noreferrer"
                >
                  Get an OpenRouter key ↗
                </a>
                . Paid models need credit. Hosted checks send sample text to a
                third party.
              </p>
            </div>
          )}
          {approach === "approach1" && (
            <p className="helper">
              Plain Python rules. No AI, API key or model charges.
            </p>
          )}
          <button
            type="submit"
            className="primary run-button"
            disabled={busy || !selected || (needsKey && !key.trim())}
          >
            {busy
              ? "Check in progress…"
              : mock
                ? "Run mock check →"
                : "Run document check →"}
          </button>
          <button
            type="button"
            className="replay-button"
            disabled={busy || !packs.some((p) => p.id === sample)}
            onClick={() => void run(true)}
          >
            Replay saved answer
          </button>
          {busy && (
            <button type="button" onClick={cancel}>
              Cancel check
            </button>
          )}
          <p className="helper">
            Replay is local and free. Its progress is accelerated; any displayed
            model time and cost belong to the original saved run.
          </p>
          {selected?.text && (
            <details className="input-preview">
              <summary>Preview selected PDF text</summary>
              <pre className="source-text">{selected.text}</pre>
            </details>
          )}
        </form>
        <div className="run-stage">
          <div className="run-intro">
            <h3>{sample}.pdf</h3>
            <span>
              {elapsed.toFixed(1)} s {mock ? "demo elapsed" : "elapsed"}
            </span>
          </div>
          <ol className="stepper" aria-label="Check progress">
            {steps.map((name, index) => (
              <li
                key={name}
                className={progress[index]?.status ?? "pending"}
                aria-current={
                  progress[index]?.status === "running" ? "step" : undefined
                }
              >
                <span aria-hidden="true">
                  {progress[index]?.status === "completed"
                    ? "✓ "
                    : progress[index]?.status === "running"
                      ? "→ "
                      : "○ "}
                </span>
                {name}
                <small>
                  {progress[index]?.status ?? "pending"}
                  {progress[index]?.seconds !== undefined
                    ? ` / ${progress[index].seconds?.toFixed(1)} s`
                    : ""}
                </small>
              </li>
            ))}
          </ol>
          <p className="run-status" role="status" aria-live="polite">
            {status}
          </p>
          {error && (
            <div className="error-box" role="alert">
              <strong>{friendlyError(error).message}</strong>
              <p>{friendlyError(error).action}</p>
            </div>
          )}
          <div className="run-output" aria-busy={busy}>
            {result ? (
              <Report result={result} text={source} />
            ) : (
              <div className="empty-result">
                <span className="document-icon" aria-hidden="true">
                  ≡
                </span>
                <h4>A decision with a paper trail.</h4>
                <p>
                  {mock
                    ? "Run the mock API to inspect a real saved answer through the streaming contract, or replay it without a server."
                    : "Choose a sample and run a check. The result will show its reasons and exact source quotes."}
                </p>
                <span className="muted">
                  Live checks can take 30–90 seconds. Unresolved cases should go
                  to a person.
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
