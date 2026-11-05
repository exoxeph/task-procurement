"use client";

import { useRef, useState } from "react";
import { approaches, packs, recordedResult } from "../lib/results";
import type { Pack } from "../lib/types";
import { Verdict } from "./verdict";
import { Report } from "./report";

export function ResultsExplorer() {
  const [selected, setSelected] = useState<Pack>(packs[2]);
  const dialog = useRef<HTMLDialogElement>(null);
  function open(pack: Pack) {
    setSelected(pack);
    dialog.current?.showModal();
  }
  return (
    <>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label="Ten samples compared across four approaches"
      >
        <table className="matrix">
          <caption className="sr-only">
            Expected and recorded verdicts for each development sample
          </caption>
          <thead>
            <tr>
              <th>Sample / what it tests</th>
              <th>Expected</th>
              {approaches.map((a, i) => (
                <th key={a.id}>
                  {i + 1} · {a.name}
                  {i === 3 ? "*" : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {packs.map((pack, index) => (
              <tr key={pack.id}>
                <th scope="row">
                  <button
                    className="pack-button"
                    onClick={() => open(pack)}
                    aria-haspopup="dialog"
                  >
                    <strong>Pack {String(index + 1).padStart(2, "0")} ↗</strong>
                    <span>{pack.label}</span>
                  </button>
                </th>
                <td>
                  <Verdict value={pack.expected} />
                </td>
                {approaches.map((a) => (
                  <td key={a.id}>
                    <Verdict value={pack.answers[a.id]} />
                    {pack.answers[a.id] !== pack.expected && (
                      <span className="mismatch">≠ Mismatch</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-legend">
        <span>
          <b>≠ Mismatch</b> differs from the expected verdict. Select a sample
          for details.
        </span>
        <span>*Later policy. Development-visible samples.</span>
      </div>
      <dialog
        ref={dialog}
        className="pack-dialog"
        aria-labelledby="pack-dialog-title"
        onClick={(e) => {
          if (e.target !== e.currentTarget) return;
          const bounds = e.currentTarget.getBoundingClientRect();
          if (
            e.clientX < bounds.left ||
            e.clientX > bounds.right ||
            e.clientY < bounds.top ||
            e.clientY > bounds.bottom
          )
            e.currentTarget.close();
        }}
      >
        <div className="dialog-heading">
          <div>
            <span className="eyebrow">Recorded development result</span>
            <h2 id="pack-dialog-title">{selected.id}.pdf</h2>
          </div>
          <button
            autoFocus
            onClick={() => dialog.current?.close()}
            aria-label="Close pack details"
          >
            Close ×
          </button>
        </div>
        <div className="dialog-content">
          <p>
            <strong>What this pack tests:</strong> {selected.tests}
          </p>
          <p className="expected-line">
            Expected <Verdict value={selected.expected} />
          </p>
          <div className="dialog-answers">
            {approaches.map((a) => (
              <div key={a.id}>
                <strong>{a.name}</strong>
                <Verdict value={selected.answers[a.id]} />
                {selected.answers[a.id] !== selected.expected && (
                  <span className="mismatch">≠ Mismatch</span>
                )}
              </div>
            ))}
          </div>
          <h3>Approach 4 / saved findings</h3>
          <Report
            result={recordedResult(selected, "approach4")}
            text={selected.text}
          />
          <p className="policy-note">
            Approach 4 includes the policy change after packs 06 and 08. These
            results are not unseen-document accuracy or a like-for-like
            comparison.
          </p>
        </div>
      </dialog>
    </>
  );
}
