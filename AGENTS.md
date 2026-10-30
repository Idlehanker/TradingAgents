# AGENTS.md

Entry point for AI coding agents working in this repository.

TradingAgents is a multi-agent LLM trading framework: a LangGraph pipeline of analysts,
researchers, risk debators and managers, backed by a pluggable market-data layer and a
provider-agnostic LLM client layer.

## Project facts

- Python `>=3.11`; install with `pip install -e ".[dev]"` (`[web]` adds FastAPI/uvicorn, `[bedrock]` adds langchain-aws).
- Console scripts: `tradingagents` → `cli.main:app`, `tradingagents-web` → `webapi.server:main`.
- Tests: `pytest` (runs `-m "not integration"` by default), `pytest -m unit` for the fast offline subset, `pytest -m integration` needs live vendors.
- Lint: `ruff` with `line-length = 100`. Network is blocked in tests unless marked `integration`.
- Default vendors: `core_stock_apis` = `tencent,yfinance` (an ordered chain), `technical_indicators` = `local` (computed from the quotes OHLCV), `fundamental_data` = `sec_edgar,yfinance`, `news_data` = `yfinance`.
- Web logging: `TRADINGAGENTS_LOG_*` switches in `.env`, read directly by `webapi/logging_setup.py` (rotating `trace/debug/info/error.log`; `TRACE` sits below `DEBUG`).
- Web dashboard: `python scripts/start_web.py` — preflights, builds `webui/dist` on demand, serves
  API + UI on `127.0.0.1:8788`; `--dev` adds `--reload` + Vite on 5173; `--check` reports
  prerequisites only.

## Module map

Each module has a dedicated agent definition (`.codebuddy/agents/`) and a skill with the
detailed edit procedures (`.codebuddy/skills/`).

| Module | Agent | Skill | Use when |
|---|---|---|---|
| `tradingagents/graph/` | `graph-workflow-engineer` | `tradingagents-graph` | adding/removing nodes, rewiring edges or conditional routing, checkpoints, recursion limits |
| `tradingagents/agents/` | `agent-node-engineer` | `tradingagents-agents` | editing a `create_*` factory, prompts, bound tools, structured-output schemas, ratings |
| `tradingagents/dataflows/` | `dataflow-vendor-engineer` | `tradingagents-dataflows` | adding a vendor or data method, vendor chains, point-in-time and look-ahead bugs |
| `tradingagents/llm_clients/` | `llm-client-engineer` | `tradingagents-llm-clients` | new provider/model, tier resolution, per-provider tool-calling or JSON failures |
| `tradingagents/memory/` | `memory-settlement-engineer` | `tradingagents-memory` | memory entry format, settlement window, benchmarks, past-context retrieval |
| `reporting.py`, `report_html.py`, `portfolio.py`, `backtest.py`, `default_config.py` | `reporting-engineer` | `tradingagents-reporting` | report sections, HTML output, config keys and `TRADINGAGENTS_*` overrides, backtest scoring |
| `cli/` | `cli-engineer` | `tradingagents-cli` | CLI flags, subcommands, interactive prompts, Rich output, headless parity |
| `webapi/`, `webui/` | `web-platform-engineer` | `tradingagents-web` | REST endpoints, WebSocket events, run lifecycle, UI panels, Vite proxy, rotating logs |

Skills load automatically when a matching file is edited. Agents are invoked by name, for
example: `Use dataflow-vendor-engineer to add a Tiingo vendor for get_stock_data`.

## Rule — agents and skills track the code

**A code change is not finished until the matching agent definition and skill describe the new
state.** Documentation drift is a defect in this repository, not cleanup for later.

Mandatory trigger — if you changed any of these, update the module's agent (`.codebuddy/agents/`),
its skill (`.codebuddy/skills/`, including `references/`), and the module README where one exists
(`webapi/README.md`, `webui/README.md`) in the same change set:

| Code change | What the docs must say afterwards |
|---|---|
| new, renamed, or deleted public symbol / module / factory | the affected symbol lists, file tables, and procedure steps |
| new or changed config key, default, or `TRADINGAGENTS_*` hint | the defaults list, the env-override section, `.env.example` cross-reference |
| new vendor, data method, provider, model, or endpoint | the routing/endpoint table and the "add a …" procedure |
| new caching, retry, TTL, or error-precedence behaviour | the module's quirks/invariants section |
| changed invariant, contract, or ordering rule | the invariant list here **and** in the owning agent |
| new or renamed test file that a doc cites | the `Verify` block of that skill |
| new cross-module coupling (a change that forces edits elsewhere) | a step in both skills' procedures |

Procedure:

1. Map the edit to its row in the module map above; more than one row means more than one skill.
2. Update the agent definition first (scope, ground truth, invariants, procedures), then the skill
   (procedures, tables, quirks), then any `references/*.md` detail page.
3. Run the `Verify` command that the skill documents, and only claim it worked if it did.
4. If code and docs disagree and you cannot tell which is right, say so explicitly — never leave a
   skill describing behaviour you know is stale.

Anti-patterns: adding a feature and leaving the skill's procedure one step short; documenting a
default that `default_config.py` no longer uses; copying a symbol name from a skill into an answer
without checking it still exists.

## Invariants worth knowing before any edit

1. **Graph shape is a contract.** Every value a router returns must appear in `DEBATE_PATH_MAP` /
   `RISK_ANALYSIS_PATH_MAP`, and shape changes must change `_run_signature()` so stale checkpoints
   stop resuming.
2. **`2 * max_tool_rounds + 2 < max_recur_limit`**, enforced at `TradingAgentsGraph.__init__`.
3. **Agents return state deltas.** Analyst subgraphs write only their own report key.
4. **Structured agents need `NO_EXTERNAL_TOOLS`** in the prompt, or schema parsing fails.
5. **`dataflows.router` never silently falls back.** The configured chain is the whole chain, walked
   in order; a vendor the user did not configure is never tried.
6. **Point-in-time is mandatory.** Route every dated lookup through `dataflows/date_window.py`;
   the same rule applies to memory `past_context` via `as_of`.
7. **`reporting._SECTIONS` is the single source of truth** for both the markdown tree and the HTML page.
8. **Config is `default_config.py` + `TRADINGAGENTS_*`**, read through `dataflows.config.get_config()`
   — never `os.environ` at a call site. Exception: the `TRADINGAGENTS_LOG_*` switches in
   `webapi/logging_setup.py`, which are installed before config exists.
9. **Web events need three edits**: emit site, `webui/src/types.ts` union, `useRunStream.ts` reducer.
   `RunRecord.emit` is the only emit path — it runs on the worker thread and hops to the loop.
10. **Prices have one entry point.** Every price read goes through `quotes.load_ohlcv` /
    `quotes.get_closes`; a new price vendor must join `_PRICE_VENDORS` and both reader dicts.

## Repository layout

```
tradingagents/     engine: agents, graph, dataflows, llm_clients, memory, reporting, backtest, config
cli/               Typer CLI and interactive run flow
webapi/            FastAPI backend + WebSocket stream (README.md: endpoints, run lifecycle, logging)
webui/             React + Vite frontend (README.md: panels, event flow, build)
tests/             flat pytest suite mirroring module boundaries
scripts/           operational entry points: start_web.py (dashboard launcher)
.codebuddy/        agent definitions and skills for this repository
```

## Before opening a pull request

```bash
pytest -m unit
ruff check .
```

`tests/test_webapi_*.py` import `fastapi` at module scope, so the `[web]` extra must be installed
or collection fails. Frontend changes also need `cd webui && npm run build`.

Those webapi modules carry no `pytestmark`, so `-m unit` deselects all of them — run them by
name (`pytest tests/test_webapi_server.py tests/test_webapi_runs.py tests/test_webapi_logging.py`)
rather than trusting a green `-m unit` run to cover the web surface.

Also confirm the doc-sync rule above: every module the diff touches has its agent and skill updated,
and the skill's `Verify` command was run.

Report what changed, which invariant it touches, which agents/skills were updated, and the exact
verification output.

## Appendix — doc-sync checklist

Run this before saying a change is done (rule: *agents and skills track the code*, above).

- [ ] Every module touched in the diff has its `.codebuddy/agents/` definition updated.
- [ ] Every matching `.codebuddy/skills/*/SKILL.md` updated, including any `references/*.md` page.
- [ ] Defaults, config keys and env switches quoted in docs still match `default_config.py` / `.env.example`.
- [ ] Every test file a doc cites still exists, and that skill's `Verify` command was run and passed.
- [ ] The invariant list above updated if a contract changed.
- [ ] The final report names the agents and skills touched; genuine code/doc conflicts are stated,
      not silently resolved.
