# Production frontend verification

Checked 2026-11-05. Approved Review room, desktop only, per the user's latest instruction.
All task-authored files are inside web/. Changes outside web/ belong to concurrent
work and were not staged, edited or reverted by this task.

## Final checks

- npm test: 9 passed, 0 failed. Stream parser, malformed optional fields, key/header
  policy, startup-mode consistency, exact matrix, and all saved evidence quotes.
- npm run lint: passed, no errors or warnings.
- npm run typecheck: passed.
- npm run build: passed, Next.js 16.4.5 / React 19.3.1 / TypeScript 6.0.3.
- Browser acceptance: passed at 1440x1000 using installed Microsoft Edge/Playwright.
  Two themes; zero axe WCAG A/AA and best-practice violations; Enter/focus/Escape
  drawer; all 40 verdict cells and 13 explicit mismatches; highlighted source;
  NDJSON mock run; cancellation; offline replay; memory-only dummy key, HTTPS header
  only, baseline header omission, no storage/cookies, forget/reload; mapped
  401/402/429/500/504 errors. No external browser request in the mock-page check.
- Fresh-context code review: both Important issues fixed using failing regressions,
  then rechecked by the reviewer. No outstanding findings in that scoped recheck.
- Production Lighthouse desktop: performance 100, accessibility 100, version13.6.0,
  final audit 2026-11-05T14:11:04.205Z. No failing accessibility audits.
- npm audit --omit=dev: zero production dependency advisories at verification time.

Evidence files: production/browser-verification.json and
production/lighthouse-desktop.json. Final production screenshots: review-room-hero.png,
review-room-desktop.png, review-room-light.png, review-room-result.png and
review-room-drawer.png. Screenshot capture mocks only the samples endpoint; the
result shown is a saved replay, never a fresh model run.

## Practical limits

The live client was exercised with intercepted HTTPS requests and a dummy key.
It has not been integrated with the separately built Python deployment or used for
paid inference. A real deployment needs that /api routing and HTTPS configuration.
The mock service is separate from production app routes. Build with the intended
API_MODE; production start detects and rejects a conflicting runtime mode.

The first Lighthouse run was performance100/accessibility99. Its heading-order and
visible-label/accessibility-name findings were corrected before the final100/100
run. Lighthouse scores are a local automated snapshot, not an accessibility
certification or a promise across all machines. Browser checks cover behavior, not
all possible provider responses. Mobile layout was explicitly removed from scope.

The earlier standalone direction drafts and their original comparison/readability
checks remain design history. They are not the delivered production application.
