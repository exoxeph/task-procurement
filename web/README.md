# Supplier Document Checker / Review room

Desktop Next.js frontend; use a window at least 1080 px wide (1440 px recommended).

## Development

```powershell
npm ci
npm run dev
```

Open http://127.0.0.1:3000. Development defaults to `API_MODE=mock` and starts a
mock API on port 4311. Run mock check exercises streaming; no AI or key is used.
Replay saved answer always works in the browser without the API.

## Live build and Vercel

```powershell
$env:API_MODE = 'live'
$env:BACKEND_ORIGIN = 'https://task-procurement.vercel.app'
npm run build
npm start
```

Set both variables before building; rebuild after changing either. `npm start`
uses the built mode. Set `PORT` to choose another local port.

| Vercel setting   | Value                                 |
| ---------------- | ------------------------------------- |
| Root Directory   | `web`                                 |
| Framework        | Next.js                               |
| Build Command    | `npm run build`                       |
| `API_MODE`       | `live`                                |
| `BACKEND_ORIGIN` | `https://task-procurement.vercel.app` |

The Python API is deployed separately. Vercel supplies HTTPS.

A live build starts in **Mock (no key)**: the key field is disabled and checks
replay saved answers in the browser, never calling `/api/run`. **Live (your key)**
calls the backend through the same-origin `/api` rewrite. Approach 1 needs no
key. Approaches 2-4 enable the key field and require an HTTPS frontend;
localhost HTTP can run Approach 1. Recorded replay works in either mode.

Keys stay in React memory and disappear on reload. Only live approaches 2-4
send `X-OpenRouter-Key`; keys never enter storage, URLs, request bodies or logs.
Never put provider keys in frontend environment variables. Errors discard
provider text, and empty responses show a clear no-answer message. Cancel and
the 120-second timeout abort the check.

## Checks

```powershell
npm run typecheck
npm run lint
npm test
```

Keep mock development on port 3000 and live production on port 3001, then run
`node checks/browser.mjs`. Installed Microsoft Edge checks both themes with axe,
keyboard controls, mode switching, streaming, cancellation, replay, key privacy,
and HTTP/provider/empty-body errors using intercepted HTTPS and a dummy key.

`node checks/live-backend.mjs` checks production on port 3001 against the real
backend: samples, browser-only Mock, and Live Approach 1 through the rewrite.
It records backend failures and the fallback UI in `design/production/`.
Neither script calls a paid model or uses a real key.

## Saved results

`public/data/results.json` holds the supplied development results (6/5/7/9
matched verdicts). Approach 4 includes saved facts, findings and exact source
quotes; approaches 1-3 have verdict-only replays. All ten PDFs were visible during
development, and Approach 4 includes a later policy change. These are not unseen
accuracy scores. Mock progress is illustrative; time and cost refer to saved runs.
