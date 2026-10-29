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
| `webapi/`, `webui/` | `web-platform-engineer` | `tradingagents-web` | REST endpoints, WebSocket events, run lifecycle, UI panels, Vite proxy |

Skills load automatically when a matching file is edited. Agents are invoked by name, for
example: `Use dataflow-vendor-engineer to add a Tiingo vendor for get_stock_data`.

## Invariants worth knowing before any edit

1. **Graph shape is a contract.** Every value a router returns must appear in `DEBATE_PATH_MAP` /
   `RISK_ANALYSIS_PATH_MAP`, and shape changes must change `_run_signature()` so stale checkpoints
   stop resuming.
2. **`2 * max_tool_rounds + 2 < max_recur_limit`**, enforced at `TradingAgentsGraph.__init__`.
3. **Agents return state deltas.** Analyst subgraphs write only their own report key.
4. **Structured agents need `NO_EXTERNAL_TOOLS`** in the prompt, or schema parsing fails.
5. **`dataflows.router` never silently falls back.** The configured chain is the whole chain.
6. **Point-in-time is mandatory.** Route every dated lookup through `dataflows/date_window.py`;
   the same rule applies to memory `past_context` via `as_of`.
7. **`reporting._SECTIONS` is the single source of truth** for both the markdown tree and the HTML page.
8. **Config is `default_config.py` + `TRADINGAGENTS_*`**, read through `dataflows.config.get_config()`
   — never `os.environ` at a call site.
9. **Web events need three edits**: emit site, `webui/src/types.ts` union, `useRunStream.ts` reducer.

## Repository layout

```
tradingagents/     engine: agents, graph, dataflows, llm_clients, memory, reporting, backtest, config
cli/               Typer CLI and interactive run flow
webapi/            FastAPI backend and WebSocket stream
webui/             React + Vite frontend
tests/             flat pytest suite mirroring module boundaries
.codebuddy/        agent definitions and skills for this repository
```

## Before opening a pull request

```bash
pytest -m unit
ruff check .
```

Report what changed, which invariant it touches, and the exact verification output.
