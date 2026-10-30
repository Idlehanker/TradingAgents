# webui — React dashboard for TradingAgents

A single-page console over the `webapi` backend: start an analysis, watch the agent
pipeline, read reports as they are filed, and browse decisions already recorded on disk.
React 18 + TypeScript + Vite, no router and no state library.

User-facing documentation (panels, screenshots) lives in the
[root README](../README.md#web-gui). This file is for people changing the frontend.

## Develop

Backend + Vite with hot reload, one command from the repository root:

```bash
python scripts/start_web.py --dev     # backend 8788 (--reload) + dashboard localhost:5173
```

Or run this half yourself:

```bash
npm install
npm run dev                     # http://localhost:5173
```

The dev server needs a backend. The project is packaged from the repository root, so from
this directory the editable install has to point at it — `pip install -e "..[web]"` — then
`cd .. && python -m webapi.server` in another terminal. `vite.config.ts` proxies `/api`
and `/ws` to `http://127.0.0.1:8788`, so the app is same-origin in dev exactly as in
production.

```bash
npm run build                   # tsc --noEmit && vite build -> dist/
npm run preview                 # serve the built dist on its own port
```

`dist/` is git-ignored. The backend serves it when present (`webapi/server.py` resolves
`../webui/dist`), so a release is: build here, then start `tradingagents-web`.

## Environment

Vite only exposes `VITE_*` variables, and all three are optional — the defaults assume
the API is on the same origin:

| Variable | Used for | Default |
|---|---|---|
| `VITE_BACKEND` | Dev-proxy target for `/api` and `/ws`; the `ws` target is derived by swapping the scheme | `http://127.0.0.1:8788` |
| `VITE_API_BASE` | Prefix for REST calls in `api.ts` | `''` (relative) |
| `VITE_WS_BASE` | Base for the WebSocket URL in `useRunStream.ts` | `''` (same host as the page) |

## Layout

| File | Responsibility |
|---|---|
| `index.html` | Vite entry; mounts `#root` |
| `src/main.tsx` | `createRoot` + `StrictMode`; imports `styles.css` |
| `src/App.tsx` | Owns the whole UI state: config, run list, selected run, `live`/`history` view, polling, elapsed clock |
| `src/api.ts` | The REST client; one function per endpoint, errors thrown as `"<status>: <body>"` |
| `src/types.ts` | Every payload shape the backend sends, including the `StreamEvent` union |
| `src/useRunStream.ts` | WebSocket lifecycle and the event reducer |
| `src/components/*.tsx` | The panels below |
| `src/styles.css` | The only stylesheet: plain CSS, BEM-ish class names, no framework |

## Panels

| Component | Renders |
|---|---|
| `RunForm` | Ticker, analysis date (capped at today), asset type, analyst chips, and a collapsed "Model settings" block for model overrides, round counts, language and checkpoint |
| `RunsList` | This session's runs with status pills and an agent-completion count; selecting one opens it |
| `AgentBoard` | The teams from `snapshot.teams` with each agent's `pending` / `in_progress` / `completed` / `error` state |
| `ActivityStream` | Messages and tool calls interleaved by stream `seq`; filters `all`/`agent`/`tool`/`data`/`system`, a newest-first toggle, and expandable long rows |
| `ReportPanel` | One tab per report section; a not-yet-filed section names the agent still working on it |
| `DecisionPanel` | Rating badge, the bold headline fields, and the decision text |
| `HistoryPanel` | Decisions read from `{results_dir}` on the server, with the full report set for one date |
| `StatsBar` | Elapsed time, LLM/tool calls, tokens in/out, agents and reports done, stream status |
| `ui.tsx` | `StatusPill`, `RatingBadge` and the formatting helpers (`formatClock`, `formatTokens`, `formatTime`) |

`App` polls `GET /api/runs` every 3 s while any run is queued or running, and ticks once a
second so the elapsed clock moves without server involvement. Everything else arrives on
the socket.

## Data flow

1. On mount: `GET /api/config` (options and defaults) and `GET /api/runs`.
2. `POST /api/runs` returns the run id; `App` selects it and switches to the live view.
3. `useRunStream(runId)` opens `WS /ws/runs/{id}`. The server sends a `snapshot` frame
   first, then deltas.
4. `applyEvent` merges each event into the previous `RunSnapshot`: `status` and `agents`
   replace a field, `message`/`tool_call` append (capped at `MAX_ROWS = 400`), `report`
   overwrites one section, `error` sets the failure text. Events arriving before the
   snapshot are dropped.
5. Reconnects: 1.5 s apart, at most 5 attempts, and never after close code `4404`
   (the server forgot the run, so a retry would repeat the failure).

Because the reducer is a `switch` on the event union, a new event type must be added in
**three** places — `types.ts`, the `useRunStream.ts` reducer, and whichever component
renders it — or it is silently dropped.

## Conventions

- TypeScript is `strict` with `noUnusedLocals` / `noUnusedParameters`; `npm run build`
  type-checks (`tsc --noEmit`) before bundling, so a type error fails the build.
- All HTTP goes through `api.ts`. Panels receive their data as props from `App`, except
  `HistoryPanel`, which owns its own fetch (nothing else needs the recorded decisions)
  and still calls `api.*` rather than `fetch`.
- Markdown from the backend is rendered with `react-markdown` + `remark-gfm`; do not
  inject HTML.
- Styling goes in `styles.css` next to the classes it serves — no inline style sheets, no
  CSS-in-JS.

## Verify

There is no test runner configured for this package: `npm run build` (type-check +
bundle) is the check. Behaviour-level coverage lives on the backend in
`tests/test_webapi_runs.py` and `tests/test_webapi_server.py`.

```bash
npm run build
```

## Changing behaviour

Procedures and invariants live in `../.codebuddy/skills/tradingagents-web/SKILL.md`.
Keep this file and that skill in step when panels, events or build output change.
