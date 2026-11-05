# Supplier Document Checker / Review room

Desktop-focused Next.js App Router + TypeScript frontend for the BIAI interview demo.
The user selected Review room and removed mobile layout work. Use a desktop window
at least 1080 px wide; 1440 px is the reference size.

## Run locally

Use Node.js 24 LTS and npm. From the project root:

```powershell
cd web
npm ci
npm run dev
```

Open http://127.0.0.1:3000. Development starts the frontend and a mock API on
loopback port 4311. Browser requests stay on port 3000 through /api rewrites.
No provider is called, no credit is spent and no API key is needed. Ctrl+C stops
both processes. Set PORT before starting if 3000 is occupied.

Run mock check exercises the NDJSON contract. Its progress is accelerated and
illustrative. Replay saved answer uses bundled data and works without the API.

## What is real

The headline metrics and all forty answers are exactly the supplied development
results: 6, 5, 7 and 9 matched verdicts. Approach 4's saved findings, facts, PDF
text, model names, original time and estimated cost were copied from
reports/v14/a4/runs using a whitelist. Backend artifacts were only read. Every
copied quote is checked against its document text by npm test.

Approaches 1–3 have verdict-only replays; unavailable detailed findings and per-pack
metrics are labeled. Mock progress is synthetic, never a fresh inference run.
All ten PDFs were development-visible. The 9/10 run includes a later policy change
after packs 06 and 08; 9 versus 7 is not like for like. Six limits remain visible.

Recorded data is public/data/results.json, served at /data/results.json. Static
imports let the story and replay render without an API. Replace that file to update
the recorded dataset.

## Connect the separate Python backend

The browser calls only relative URLs:

```text
GET  /api/samples
POST /api/run   application/json -> application/x-ndjson
```

Body: {"sample":"supplier-pack-03","approach":"approach4"}. See design/brief.md
for the complete contract. This frontend contains no Python or provider SDK. The
separate mock server implements the same contract.

For local backend development in PowerShell:

```powershell
$env:API_MODE = 'live'
$env:BACKEND_ORIGIN = 'https://your-trusted-backend.example'
npm run dev
```

BACKEND_ORIGIN is an optional server-side proxy to your own backend, never a
browser API base URL. Leave it unset if deployment routing already serves Python
functions at /api/*. No UI changes are needed. Do not point this proxy at a model
provider; only the Python backend calls providers.

Live AI needs an HTTPS frontend. HTTP localhost supports mock checks and Approach 1;
the client blocks keyed requests over HTTP. Use an HTTPS preview/deployment for real
AI checks. No live inference was made during this build.

Keys stay in React state and disappear on reload. They are sent only as
X-OpenRouter-Key on the same-origin HTTPS POST /api/run, with credentials omitted
and redirects blocked. Approach 1 omits that header. There is no persistence,
logging, analytics or runtime font CDN. Provider error messages are discarded;
fixed messages explain the next action. Cancel and a 120-second timeout abort the
request; stale events cannot overwrite a later run.

## Production and Vercel

```powershell
$env:API_MODE = 'live'
# Set BACKEND_ORIGIN first when the Python API is deployed separately.
npm run build
npm start
```

Rewrites and the displayed mode are compiled together. Set API_MODE and
BACKEND_ORIGIN before building; rebuild when changing either. npm start uses the
built mode and rejects a conflicting API_MODE. To test a production mock build,
build with API_MODE=mock; npm start then starts its mock server too.

In Vercel choose web/ as Root Directory, Next.js framework, npm run build and
API_MODE=live. Configure BACKEND_ORIGIN for the separate Python deployment, or
same-origin /api routing. Python files outside web/ are not automatically included
by that project root. Vercel supplies HTTPS. Never put an OpenRouter key in project
environment variables or NEXT_PUBLIC_* values. Nothing has been published.

## Checks

```powershell
npm test
npm run lint
npm run typecheck
npm run build
```

Tests cover split NDJSON, missing/malformed answers, optional field validation,
fixed errors, HTTPS/header rules, built-mode consistency, the complete matrix and
exact source quotes.

For browser acceptance, keep the mock dev server on 3000 and a live production
build running on 3001, then run node checks/browser.mjs. It uses installed Microsoft
Edge through Playwright, a dummy key and an intercepted HTTPS origin. It checks
themes/axe, keyboard dialogs, streaming, cancellation, offline replay, key/header
privacy, empty storage, forget/reload and HTTP errors. No external request or paid
inference is made. Install Edge or change the browser channel for other environments.

Screenshots, browser evidence and Lighthouse results live in design/production/.
See design/verification.md for measurements and limits.

## Read the code

- app/page.tsx: story, workflow, metrics and limits.
- app/globals.css: desktop Review room styling and system/light/dark themes.
- components/results-explorer.tsx: matrix and native details drawer.
- components/live-run.tsx: form, memory-only key, progress, cancellation and replay.
- components/report.tsx: findings, literal quote highlighting and facts table.
- lib/api.ts: request policy, NDJSON parser, response validation and fixed errors.
- lib/results.ts / public/data/results.json: recorded data and replay helpers.
- scripts/mock-server.mjs: mock contract only; no AI or business-rule engine.

Initial previews remain in design-demos/ as design history. The running application
is the Next.js app, not those static previews.
