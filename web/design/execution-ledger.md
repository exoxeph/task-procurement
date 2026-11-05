# Review room execution ledger

- User approved Review room: "review room, forget mobile layout".
- Ruling: desktop ownership is web/; no worktree/branch switch while a separate
  backend is being built in the shared project. No edits outside web/.
- Ruling: proceed with the already authorized build after the design choice;
  no additional plan-approval gate.
- Implemented typed stream API boundary; tests first failed on missing module,
  then passed. Invalid/incomplete responses and raw provider messages fail closed.
- Imported exact supplied metrics/matrix and whitelisted saved Approach 4 facts,
  checks, models, timing, cost and PDF text from reports/v14/a4 (read-only).
  Every copied quote was tested against the saved document text.
- Implemented desktop approved layout, native details drawer, theme toggle,
  key-memory form, progress, cancellation and offline recorded replay.
- Mock server is separate from app routes and never calls providers. Its stream
  progress is synthetic; results and any shown cost/time belong to saved runs.
- Fresh review found optional payload fields were under-validated. Added a
  regression that failed before implementing type validation; all nine tests pass.
- Fresh review found build/runtime API mode mismatch. Added failing startup-mode
  test, compiled the UI mode with rewrites, and blocked conflicting startup values.
- Browser acceptance passed themes with zero axe WCAG A/AA violations, dialog
  Enter/focus/Escape, quote highlighting, mock stream, cancellation, offline replay,
  HTTPS header-only key, baseline omission, empty storage, forget/reload, and
  actionable HTTP 401/402/429/500/504 errors. Tests use a dummy key and intercept all
  requests to the HTTPS test origin; no real key or provider was used.
- Final build/Lighthouse and documentation results follow in verification.md.

- Final production build, lint and typecheck pass; nine tests pass.
- Final desktop Lighthouse: performance100/accessibility100; automated browser
  acceptance passes. Fresh reviewer rechecked both Important fixes and cleared them.
- Delivered desktop-only Review room; live backend integration remains external.
