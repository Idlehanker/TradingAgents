---
name: tradingagents-web
description: Procedures for the TradingAgents web stack — FastAPI backend in webapi/ and the React frontend in webui/. This skill should be used when adding REST endpoints or WebSocket events, changing run lifecycle, cancellation and history retention, wiring new UI panels, adjusting the rotating TRADINGAGENTS_LOG_* logging, or debugging the 5173 to 8788 dev proxy and SPA serving.
---

# TradingAgents web platform

Two halves: `webapi/` orchestrates runs and streams progress; `webui/` renders them. All trading logic stays in `tradingagents/`.

Each half has its own developer README — `webapi/README.md` (endpoints, run lifecycle, threading, logging) and `webui/README.md` (panels, event flow, build). They are part of the documentation contract below: keep them in step with this skill.

## Backend — `webapi/`

- `server.py` — `create_app()` (routes registered inside), module-level `app`, `main()` for `uvicorn`. Defaults: `TRADINGAGENTS_WEB_HOST=127.0.0.1`, `TRADINGAGENTS_WEB_PORT=8788`. OpenAPI at `/api/docs`. In production `webui/dist` is served with an `index.html` SPA fallback route registered **after** the API routes.
- `runs.py` — `RunRecord` (status, messages, tool calls, reports, stats; `subscribe`, `emit`, `snapshot`) and `RunManager` (dispatches each run on a daemon `threading.Thread`, keeps at most 20 runs). `RunRecord.emit` is called from the worker thread and hands events to the loop with `loop.call_soon_threadsafe`, so it is the only allowed emit path.
- `runs.py` also owns the UI's own copy of the pipeline shape: `ANALYST_ORDER`, `ANALYST_AGENT_NAMES`, `ANALYST_REPORT_MAP`, `FIXED_AGENTS`, `TEAMS`, and `SECTIONS` (state key → `(title, signing agent)`). Adding an analyst or a report section means editing these **as well as** `reporting._SECTIONS`; the API deliberately keeps display labels here rather than importing them from the engine.
- `schemas.py` — `RunRequest` and response models.
- `history.py` — reads saved reports for the history endpoints.
- `messages.py` — converts graph stream payloads into UI events.
- `logging_setup.py` — rotating, level-split file logging, installed by `create_app()` and by `main()` (both calls are idempotent; see below).

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

`/ws/runs/{run_id}`: send a `snapshot` frame first, then incremental events, each carrying a monotonically increasing `seq`. Event kinds: `snapshot`, `status`, `agents`, `message`, `tool_call`, `report`, `stats`, `decision`, `error` — `status` and `decision` come from `RunRecord.set_status`/`finish` and `_build_decision`, and the `StreamEvent` union in `src/types.ts` must match this list exactly. An unknown run is closed with code `4404`.

### Logging — `logging_setup.py`

One `RotatingFileHandler` per level in `TRADINGAGENTS_LOG_DIR` (default `{results_dir}/web`): `trace.log`, `debug.log`, `info.log`, `error.log`, each also receiving everything above its threshold. `TRACE` is registered at level 5, below `DEBUG`, for the per-message/per-chunk business trace, and exposed as `logging.Logger.trace`.

- `LoggingSettings.from_env()` reads `TRADINGAGENTS_LOG_*` straight from `os.environ` — these are **not** `_ENV_OVERRIDES` entries, because logging is installed before config exists. Every switch is documented in the module docstring and `.env.example`; a blank value means "unset" and keeps the default.
- `setup_logging(settings=None, force=False)` is idempotent by settings signature; `force=True` rebuilds the handlers, which is how tests point at a temp directory.
- `payloads_enabled()` gates message and report bodies (default off): call it before `log.trace(... body=...)`, never log a body unconditionally.
- Third-party loggers in `_NOISY_LOGGERS` (httpx, langchain, langgraph, uvicorn, …) are clamped at `WARNING` unless `TRADINGAGENTS_LOG_LIBRARIES=1`.
- Root level is set to the most permissive handler threshold; each handler then filters for itself. Keep that invariant when adding a handler.

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
7. **Log settings come from the environment, config comes from `dataflows.config`.** Adding a log switch means the `LoggingSettings` field, the docstring, and `.env.example`; it must not go into `_ENV_OVERRIDES`.
8. Message and report bodies are payloads: write them at `TRACE` only, behind `payloads_enabled()`.

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

One command, from the repository root: `python scripts/start_web.py` checks the
prerequisites, builds `webui/dist` when missing, and serves API + UI on `127.0.0.1:8788`.
`--dev` runs the backend with `--reload` alongside Vite on 5173 (`VITE_BACKEND` set for the
proxy); `--check` reports prerequisites without starting anything. Running the pieces by hand:

```bash
# from the repository root — pyproject.toml is there, not in webapi/ or webui/
pip install -e ".[web]"
tradingagents-web                        # backend 127.0.0.1:8788
cd webui && npm install && npm run dev   # frontend 5173, proxying to 8788
```

If you change the launcher's flags or its preflight, update `scripts/start_web.py`,
`README.md` (one-key start), and the two module READMEs together.

## Verify

```bash
pip install -e ".[web]"   # the test modules import fastapi at module scope; without it collection errors
pytest tests/test_webapi_server.py tests/test_webapi_runs.py tests/test_webapi_logging.py
cd webui && npm run build
```

Do not add `-m unit` to that pytest line: the webapi test modules carry no `pytestmark`, so the
marker expression deselects every test in them and the run looks green while testing nothing.

Report endpoints or events touched, whether the SPA needs rebuilding, and the test output.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
