---
name: tradingagents-web
description: Procedures for the TradingAgents web stack — FastAPI backend in webapi/ and the React frontend in webui/. This skill should be used when adding REST endpoints or WebSocket events, changing run lifecycle, cancellation and history retention, wiring new UI panels, or debugging the 5173 to 8788 dev proxy and SPA serving.
---

# TradingAgents web platform

Two halves: `webapi/` orchestrates runs and streams progress; `webui/` renders them. All trading logic stays in `tradingagents/`.

## Backend — `webapi/`

- `server.py` — `create_app()` (routes registered inside), module-level `app`, `main()` for `uvicorn`. Defaults: `TRADINGAGENTS_WEB_HOST=127.0.0.1`, `TRADINGAGENTS_WEB_PORT=8788`. OpenAPI at `/api/docs`. In production `webui/dist` is served with an `index.html` SPA fallback route registered **after** the API routes.
- `runs.py` — `RunRecord` (status, messages, tool calls, reports, stats; `subscribe`, `emit`, `snapshot`) and `RunManager` (serial execution, keeps at most 20 runs). `ANALYST_ORDER` and `ANALYST_AGENT_NAMES` translate analyst keys into graph node names.
- `schemas.py` — `RunRequest` and response models.
- `history.py` — reads saved reports for the history endpoints.
- `messages.py` — converts graph stream payloads into UI events.

### REST surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/config` | provider, models, analyst and asset options |
| GET | `/api/runs` | list runs |
| POST | `/api/runs` | create run (201) |
| GET | `/api/runs/{id}` | run snapshot |
| POST | `/api/runs/{id}/cancel` | request cancellation |
| DELETE | `/api/runs/{id}` | drop a run |
| GET | `/api/history` | recent saved decisions (`limit`, default 30) |
| GET | `/api/history/{ticker}/{trade_date}` | one saved decision from `results_dir`; 400 on a malformed date, 404 when nothing was recorded |

History is read from saved run output through `webapi/history.py` (`list_decisions`, `get_decision`), not from the memory log. Do not present derived counts as facts the source does not provide.

### WebSocket

`/ws/runs/{run_id}`: send a `snapshot` frame first, then incremental events, each carrying a monotonically increasing `seq`. Event kinds include `snapshot`, `message`, `tool_call`, `agents`, `report`, `stats`, `error`.

## Frontend — `webui/`

- `src/api.ts` — REST client.
- `src/types.ts` — mirrors backend payloads and the event union.
- `src/useRunStream.ts` — WebSocket connection and event reducer.
- `src/App.tsx`, `src/components/*.tsx` — `RunForm`, `RunsList`, `AgentBoard`, `ActivityStream`, `DecisionPanel`, `HistoryPanel`, `ReportPanel`, `StatsBar`, `ui`.
- `vite.config.ts` — dev server on `5173`, proxies `/api` and `/ws` to `http://127.0.0.1:8788`; `VITE_BACKEND` overrides the target.

## Rules

1. **Three-place rule for events.** A new event needs the emit site (`runs.py` / `messages.py`), the `types.ts` union, and a `useRunStream.ts` reducer branch. Miss the reducer and the event is silently dropped.
2. **Serial execution.** Runs go through `RunManager`; a route handler must never start a graph directly.
3. **Cancellation is real.** A cancelled run stops streaming and is not recorded as complete.
4. **`seq` is per-run and increasing** — that is what lets a reconnecting client resume.
5. `webui/dist` is build output. Rebuild with `npm run build`; never hand-edit it.
6. Validate request bodies through `schemas.py`; do not accept loose dicts.

## Procedure — add a REST endpoint

1. Model request/response in `schemas.py`.
2. Implement inside `create_app()` in `server.py`, delegating to `RunManager` or `history`.
3. Add the client function in `src/api.ts` and the type in `src/types.ts`.
4. Cover with `tests/test_webapi_server.py` (route registered with `RunManager` stubbed).

## Procedure — add a WebSocket event

1. Emit at the source of truth via `RunRecord.emit`.
2. Extend the `types.ts` union and handle it in `useRunStream.ts`.
3. Render in the relevant component.
4. Assert shape and ordering in `tests/test_webapi_runs.py`.

## Run locally

```bash
pip install -e ".[web]"
tradingagents-web                        # backend 127.0.0.1:8788
cd webui && npm install && npm run dev   # frontend 5173, proxying to 8788
```

## Verify

```bash
pytest -m unit tests/test_webapi_server.py tests/test_webapi_runs.py
cd webui && npm run build
```

Report endpoints or events touched, whether the SPA needs rebuilding, and the test output.
