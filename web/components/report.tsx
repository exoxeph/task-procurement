import { Fragment } from "react";
import type { RunResult } from "../lib/types";
import { Verdict } from "./verdict";

function display(value: unknown): string {
  if (value === undefined || value === null || value === "") return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

// Literal slices, never HTML insertion or a regular expression built from PDF text.
function HighlightedSource({
  text,
  quotes,
}: {
  text: string;
  quotes: string[];
}) {
  const pieces = [];
  let cursor = 0;
  const unique = [...new Set(quotes.filter(Boolean))];
  while (cursor < text.length) {
    let start = text.length;
    let quote = "";
    for (const candidate of unique) {
      const position = text.indexOf(candidate, cursor);
      if (position >= 0 && position < start) {
        start = position;
        quote = candidate;
      }
    }
    if (!quote) {
      pieces.push(text.slice(cursor));
      break;
    }
    pieces.push(text.slice(cursor, start), <mark key={start}>{quote}</mark>);
    cursor = start + quote.length;
  }
  return <pre className="source-text">{pieces}</pre>;
}

export function Report({ result, text }: { result: RunResult; text?: string }) {
  const quotes = result.findings.flatMap((f) => f.evidence.map((e) => e.text));
  return (
    <div className="report">
      <Verdict value={result.verdict} />
      <div className="run-metrics">
        {result.recorded && (
          <span className="recorded-tag">Recorded answer</span>
        )}
        {result.seconds !== undefined && (
          <span>
            {result.seconds.toFixed(1)} s{" "}
            {result.recorded ? "original run" : "model run"}
          </span>
        )}
        {result.costUsd !== undefined && (
          <span>Estimated cost ${result.costUsd.toFixed(4)}</span>
        )}
      </div>
      {result.models && (
        <p className="model-line">
          {Object.entries(result.models)
            .map(([role, name]) => `${role}: ${name}`)
            .join(" · ")}
        </p>
      )}
      {result.note && <p className="muted">{result.note}</p>}
      <h4>Findings and reasons</h4>
      {!result.findings.length && (
        <p className="muted">
          {result.verdict === "Approve"
            ? "No failing findings returned."
            : "No detailed findings were supplied for this recorded answer."}
        </p>
      )}
      <div className="findings">
        {result.findings.map((finding, i) => (
          <article className="finding" key={`${finding.code}-${i}`}>
            <div className="finding-heading">
              <code>{finding.code}</code>
              <span>
                {finding.severity === "Reject" ? "×" : "!"} {finding.severity}
              </span>
            </div>
            <p>{finding.reason}</p>
            {finding.evidence.map((e, index) => (
              <blockquote key={index}>
                <span className="quote-page">Page {e.page} / exact quote</span>
                <q>{e.text}</q>
              </blockquote>
            ))}
            {!finding.evidence.length && (
              <p className="muted">
                No source quote supplied for this finding.
              </p>
            )}
          </article>
        ))}
      </div>
      {text && (
        <details className="source-details">
          <summary>PDF text with finding evidence highlighted</summary>
          <HighlightedSource text={text} quotes={quotes} />
        </details>
      )}
      <details className="facts-details">
        <summary>Extracted facts ({result.facts.length})</summary>
        {result.facts.length ? (
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Extracted facts table"
          >
            <table className="facts-table">
              <thead>
                <tr>
                  <th>Fact</th>
                  <th>Value / status</th>
                  <th>Exact source quote</th>
                  <th>Warnings / context</th>
                </tr>
              </thead>
              <tbody>
                {result.facts.map((fact) => (
                  <tr key={fact.name}>
                    <th scope="row">
                      <code>{fact.name}</code>
                    </th>
                    <td>
                      {display(fact.value)}
                      <small>{fact.status}</small>
                      {fact.rawValue !== undefined && (
                        <small>Raw: {display(fact.rawValue)}</small>
                      )}
                    </td>
                    <td>
                      {fact.evidence.map((e, i) => (
                        <Fragment key={i}>
                          <q>{e.text}</q>
                          <small>Page {e.page}</small>
                        </Fragment>
                      ))}
                    </td>
                    <td>
                      {fact.warnings.length
                        ? fact.warnings.map(display).join("; ")
                        : "No warnings returned"}
                      {fact.referenceEvent != null && (
                        <small>Reference: {display(fact.referenceEvent)}</small>
                      )}
                      {!!fact.conditions?.length && (
                        <small>
                          Conditions: {fact.conditions.map(display).join("; ")}
                        </small>
                      )}
                      {fact.note && <small>{fact.note}</small>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">
            Extracted facts were not supplied for this replay.
          </p>
        )}
      </details>
    </div>
  );
}
