# Review Room Frontend Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task.

**Goal:** Build the approved desktop Review room as a deployable frontend demo.
**Architecture:** Server-rendered story with small client components for theme,
pack drawer and live checks. A separate Node mock server implements the backend
contract; development rewrites preserve the same browser URLs for mock and live.
**Tech Stack:** Next.js App Router, TypeScript, React, plain CSS, Node test runner.
**Spec:** brief.md, amended by direction-approved.md.

## Global constraints
- Write only inside web/; no Python changes.
- Desktop focused; user removed mobile layout work.
- No external fonts, analytics, runtime third-party scripts or browser API calls.
- React-memory-only key, header only, HTTPS for live keyed requests, A1 omits key.
- Keep all supplied scores, matrix answers, six limits and the policy caveat.

## Review focus
- NDJSON split across chunks or missing final result must fail clearly.
- Raw backend error messages may contain keys: display only fixed mapped messages.
- Cancel/restart/unmount must abort and prevent stale events from changing results.
- Backend unavailable must leave recorded results and replay usable.
- Evidence quotes are untrusted text; render as text, with literal highlighting.

### Task 1: Data and stream boundary
Files: package.json, tsconfig.json, next.config.ts, lib/types.ts, lib/api.ts,
lib/results.ts, public/data/results.json, checks/api.test.ts.
Interface: runCheck(sample,approach,key,onEvent,signal), getSamples(signal),
consumeEvents(response,onEvent), friendlyError(code); typed Sample/RunResult/Event.
- [x] Write failing Node tests for chunking, EOF, error redaction, header omission,
      redirect blocking and HTTPS keyed-request enforcement.
- [x] Implement readable typed boundary and exact supplied recorded data.
- [x] Run tests and TypeScript checks.

### Task 2: Approved story and recorded results
Files: app/layout.tsx, app/page.tsx, app/globals.css, components/theme-toggle.tsx,
components/verdict.tsx, components/results-explorer.tsx, components/report.tsx.
- [x] Port the approved design into semantic React with desktop typography.
- [x] Add native dialog and exact 10x4 matrix with 13 explicit mismatch labels.
- [x] Render supplied findings honestly; missing findings are labeled unavailable.
- [x] Verify all matrix matches 6/5/7/9 and keyboard dialog behavior in browser.

### Task 3: Run panel and mock service
Files: components/live-run.tsx, scripts/mock-server.mjs, .env.example.
- [x] Add separate recorded replay and API run modes; default approach4.
- [x] Implement key visibility/forget controls, progress, elapsed timer, cancellation,
      errors and result/fact/evidence views, with no raw error interpolation.
- [x] Mock the exact sample/run endpoints, chunked NDJSON and selectable failures;
      label all synthetic progress and unavailable per-pack timing/cost honestly.
- [x] Browser-test header privacy, storage, errors, replay and cancellation.

### Task 4: Verification and handoff
Files: README.md, design/verification.md, design/execution-ledger.md, screenshots.
- [x] Run npm test, lint, build; inspect production desktop browser, keyboard/themes.
- [x] Run desktop Lighthouse and address material accessibility/performance failures.
- [x] Request one fresh-context review, fix material findings and rerun affected checks.
- [x] Document mock/live configuration, Vercel backend routing and remaining limits.

Ruling: Execute inline after the approved design. Keep all planning artifacts within
web/ to honor the explicit scope. No worktree or branch switch while another person
works on the shared backend; web/ is the isolated ownership boundary. No publication.
