# webapi — FastAPI backend for the TradingAgents dashboard

REST for control, WebSocket for progress. All trading logic stays in `tradingagents/`;
this package only drives `TradingAgentsGraph` on a worker thread and mirrors what
`cli/run.py` derives for the terminal.

User-facing documentation (panels, screenshots, log switches) lives in the
[root README](../README.md#web-gui). This file is for people changing the backend.

## Run it

One command, from the repository root — `../scripts/start_web.py` checks the prerequisites,
builds `../webui/dist` when it is missing, and serves API + UI on one port:

```bash
python scripts/start_web.py            # http://127.0.0.1:8788, Ctrl+C to stop
python scripts/start_web.py --dev      # this server with --reload + Vite on 5173
python scripts/start_web.py --check    # prerequisites only, start nothing
```

By hand — there is no `pyproject.toml` in this directory, so an editable install has to
point at the repository root. From `webapi/`:

```bash
pip install -e "..[web]"                # fastapi + uvicorn
cd .. && python -m webapi.server        # http://127.0.0.1:8788
# or, from the repository root:
#   pip install -e ".[web]"
#   python -m webapi.server            (also: tradingagents-web, pyproject [project.scripts])
```

`pip install -e ".[web]"` run *inside* `webapi/` fails with
`does not appear to be a Python project: neither 'setup.py' nor 'pyproject.toml' found`.

`TRADINGAGENTS_WEB_HOST` (default `127.0.0.1`) and `TRADINGAGENTS_WEB_PORT` (default
`8788`) are read straight from the environment in `main()`. OpenAPI is served at
`/api/docs`.

The UI is **not** shipped as a package: `create_app()` serves `webui/dist` only if that
directory exists. Build it first (`cd ../webui && npm install && npm run build`),
otherwise the API works and the browser gets a 404.

## Layout

| File | Responsibility |
|---|---|
| `__init__.py` | Import-light package surface. `RunManager`, `RunRequest`, `create_app`, `setup_logging` resolve lazily through `__getattr__` so importing `webapi` does not pull in the agent stack. |
| `server.py` | `create_app()` (routes are registered inside it), module-level `app`, `main()` running uvicorn. CORS, the request-logging middleware, and the SPA fallback live here. |
| `runs.py` | `RunRecord` (one analysis: status, messages, tool calls, reports, stats, decision) and `RunManager` (dispatch, serialization, retention). Also the UI's own pipeline maps. |
| `schemas.py` | `RunRequest`, the only accepted request body. |
| `history.py` | Reads decisions already written to `{results_dir}/{ticker}/TradingAgentsStrategy_logs/full_states_log_{date}.json`. |
| `messages.py` | LangChain message → flat `(type, text)` records and tool-call pairs. |
| `logging_setup.py` | Rotating handlers, one file per level, plus a `TRACE` level below `DEBUG`. |

## REST surface

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{ok, version, busy}` — `busy` is true while a run is queued or running |
| GET | `/api/config` | Effective provider, endpoint, models, rounds, language, paths, analyst and asset options. Never keys. |
| GET | `/api/runs` | Summaries, newest first (no message bodies) |
| POST | `/api/runs` | 201 with `{id, status, snapshot}`; body is `RunRequest` |
| GET | `/api/runs/{id}` | Full `snapshot()`; 404 for an unknown run |
| POST | `/api/runs/{id}/cancel` | `{cancelled: bool}` — sets the cancel flag, the run stops after its current step |
| DELETE | `/api/runs/{id}` | `{deleted: bool}` — also cancels, then drops it from memory |
| GET | `/api/history?limit=30` | Recorded decisions, newest first |
| GET | `/api/history/{ticker}/{date}` | One decision with all reports; 400 on a malformed ticker, 404 when nothing was recorded |

Request bodies are validated by `RunRequest`; do not add loose `dict` endpoints.

## WebSocket

`/ws/runs/{id}` accepts, then sends one `snapshot` frame (with the run's current `seq`),
then every subsequent event for that run:

```json
{"seq": 12, "type": "message", "data": {...}, "ts": 1761700000.0}
```

| `type` | Payload |
|---|---|
| `snapshot` | The whole `snapshot()` minus `seq` |
| `status` | `{status}` on every transition |
| `agents` | `{agents}` — the full agent→status map, not a delta |
| `message` | `{message: {ts, type, content}}` |
| `tool_call` | `{tool_call: {ts, name, args}}` |
| `report` | `{section, title, agent, content}` |
| `stats` | `{stats}` — llm calls, tool calls, tokens in/out |
| `decision` | `{decision: {rating, is_review, text, fields}}` |
| `error` | `{error}` — the failure text, traceback included |

An unknown run is closed with code **4404** (accepted first, so the client sees a reason
instead of a failed handshake). The socket stays open after the run finishes until the
viewer leaves: a run keeps emitting after its status change.

## Run lifecycle

1. `POST /api/runs` → `RunManager.create()` builds a `RunRecord` (`status="queued"`) and
   seeds the agent and report placeholders for the selected analysts.
2. `RunManager.start()` binds the request's event loop and starts a daemon thread
   (`run-<id>`).
3. The worker takes `_exec_lock` (timeout 1h). **Exactly one graph runs at a time**:
   `TradingAgentsGraph` installs its config process-wide, so overlapping runs would read
   each other's settings. Late arrivals wait here, not in the API.
4. `_run()` builds the graph, reads `graph.stream_run(...)`, and feeds each chunk to
   `_handle_chunk` / `_handle_messages`. Titles, statuses and report sections are mapped
   from state keys — the graph does not name its nodes in the stream.
5. Completion: every agent marked `completed`, report sections reconciled from the final
   union of chunks, `decision` extracted from the Portfolio Manager's markdown,
   `record_decision` + `save_reports` write to `results_dir`, checkpoint cleared.
6. Cancellation is cooperative: the loop checks `cancel_requested` before each chunk.
   A run that never completes writes no report and no decision.

Retention: at most `max_history=20` **finished** runs stay in memory (constructor
argument of `RunManager`); live runs survive until dropped or the process restarts.
Messages and tool calls are capped at 500 each (`MAX_MESSAGES`, `MAX_TOOL_CALLS`).

## The UI's pipeline maps

`runs.py` keeps its own view of the pipeline rather than importing it from the engine:

| Name | Meaning |
|---|---|
| `ANALYST_ORDER` | Canonical analyst keys (`market`, `social`, `news`, `fundamentals`) |
| `ANALYST_AGENT_NAMES` | key → display name used by the graph and the UI (`social` → `Sentiment Analyst`) |
| `ANALYST_REPORT_MAP` | key → report section the analyst files |
| `FIXED_AGENTS`, `TEAMS` | The non-analyst teams and their members, for the pipeline board |
| `SECTIONS` | state key → `(title, signing agent)` for the report tabs |

Adding an analyst or a report section means editing these **and**
`tradingagents/reporting._SECTIONS`. Missing one leaves the dashboard without a panel.

## Logging

`create_app()` and `main()` both call `setup_logging()`; the second call is a no-op
because handlers are installed once per settings signature. Files land in
`TRADINGAGENTS_LOG_DIR`, defaulting to `{results_dir}/web`:

| File | Threshold |
|---|---|
| `trace.log` | `TRACE` (5) and up — off unless `TRADINGAGENTS_LOG_TRACE=1` |
| `debug.log` | `DEBUG` and up |
| `info.log` | `INFO` and up |
| `error.log` | `ERROR` and up |

- `TRACE` is registered at level 5 and exposed as `logging.Logger.trace`; bodies are
  written only when `TRADINGAGENTS_LOG_PAYLOADS=1` (`payloads_enabled()`).
- `TRADINGAGENTS_LOG_LIBRARIES=0` (default) clamps httpx, langchain, langgraph, uvicorn
  and friends at `WARNING`; uvicorn's per-socket protocol trace is the reason.
- uvicorn runs with `access_log=False, log_config=None`: its own records join the
  rotating files, and access lines come from the middleware instead (5xx → `ERROR`,
  4xx → `WARNING`, `/assets/*` and `/favicon*` → `DEBUG`, the rest → `INFO`).
- These switches are environment-only **by design** — they are not `_ENV_OVERRIDES`
  config keys, because logging is installed before config exists.

## Operating notes

- The SPA fallback (`GET /{full_path:path}`) is registered **after** every API route and
  only when `webui/dist` is a directory. Keep that order or it swallows `/api`.
- CORS allows any origin: the Vite dev server (5173) proxies `/api` and `/ws` here.
- `RunManager` is process-local. A restart forgets live runs; the History tab still reads
  what was written to `results_dir`.

## Tests

Run from the repository root (the test paths are relative to it):

```bash
pip install -e ".[web]"     # the modules import fastapi at import time
pytest tests/test_webapi_server.py tests/test_webapi_runs.py tests/test_webapi_logging.py
```

No `-m unit` here: these files carry no `pytestmark`, and the marker expression would
deselect all of them (they run offline anyway — the suite's autouse guard blocks sockets,
with a loopback exception so the in-process test client can start an event loop).

- `tests/test_webapi_server.py` — effective config, request validation, run listing/reading, the
  WebSocket snapshot-then-deltas contract, unknown-run rejection, cancellation. Runs are created
  directly in the manager, so no graph, model or network is involved.
- `tests/test_webapi_runs.py` — the progress mapping: parallel analysts filing reports, the
  debate → trader → risk chain, messages recorded once and classified like the terminal view,
  tool-call capture, and decision-headline extraction.
- `tests/test_webapi_logging.py` — default levels, per-level files, rotation and backups, blank
  values falling back, the disabled switch, and payload gating (`TRACE` bodies only when asked).

## Changing behaviour

Procedures and invariants (three-place rule for events, serial execution, `seq`
ordering) live in `../.codebuddy/skills/tradingagents-web/SKILL.md`. Keep this file and
that skill in step when the surface changes.
