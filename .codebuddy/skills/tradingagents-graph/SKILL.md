---
name: tradingagents-graph
description: Procedures for changing the TradingAgents LangGraph workflow in tradingagents/graph — adding analyst nodes, wiring conditional edges, seeding AgentState keys, and keeping checkpoint signatures valid. This skill should be used when editing setup.py, analyst_execution.py, conditional_logic.py, propagation.py, checkpointer.py, or trading_graph.py, or when debugging graph wiring, recursion-limit, and stale-checkpoint errors.
---

# TradingAgents graph workflow

The graph is assembled in `tradingagents/graph/setup.py` and driven by `tradingagents/graph/trading_graph.py`. Nothing in this layer produces content — it only sequences agents and routes state.

## Lay of the land

| File | Responsibility |
|---|---|
| `setup.py` | `GraphSetup.setup_graph(selected_analysts, memory_node=None)` → uncompiled `StateGraph(AgentState)`; all `add_node` / `add_edge` / `add_conditional_edges` calls and the `*_PATH_MAP` constants |
| `analyst_execution.py` | `AnalystNodeSpec`, `ANALYST_NODE_SPECS`, `build_analyst_execution_plan()` |
| `conditional_logic.py` | `should_continue_debate`, `should_continue_risk_analysis` |
| `propagation.py` | `Propagator.create_initial_state(...)`, `get_graph_args()` |
| `checkpointer.py` | `thread_id`, `get_checkpointer`, `checkpoint_step`, `clear_checkpoint` |
| `trading_graph.py` | `TradingAgentsGraph`: validation, compilation, `propagate`, `stream_run`, checkpoint scopes, memory step, report saving |

Execution order: `START` fans out to every selected analyst **and** the `Memory Log` node in parallel; the first analyst to finish opens the bull/bear debate; the Research Manager then hands the plan to the Trader; risk debators rotate; the Portfolio Manager terminates with `END`.

## Adding an analyst

Edit these files in this order — a partial edit produces a graph that imports but fails at runtime:

1. `tradingagents/agents/state.py` — add the `<x>_report` field to `AgentState`.
2. `tradingagents/agents/analysts/<x>_analyst.py` — implement `create_<x>_analyst(llm)` with a module-level `TOOLS` tuple.
3. `tradingagents/agents/__init__.py` — export the factory.
4. `tradingagents/graph/analyst_execution.py` — append an `AnalystNodeSpec(key=..., agent_node=..., report_key=..., tools=...)` to `ANALYST_NODE_SPECS`.
5. `tradingagents/graph/propagation.py` — seed the new report key in `create_initial_state`.
6. `tradingagents/graph/setup.py` — register the factory in `analyst_factories`; the loop over the execution plan wires the node and its edge.
7. `tradingagents/reporting.py` — add the section to `_SECTIONS` so it reaches disk.

Note the naming split: the selection key is `social`, the graph node is the sentiment analyst, and the state field is `sentiment_report`.

## Adding a non-analyst node

1. Declare the state field(s) in `agents/state.py`.
2. Seed them in `propagation.create_initial_state`.
3. `setup.add_node("<Display Name>", factory(llm))`.
4. Wire `add_edge` / `add_conditional_edges` with a path map that covers **every** value the router can return.
5. If the node becomes a new routing target, add that target to the originating router's path map.

## Changing debate length or routing

- Round counts come from `max_debate_rounds` and `max_risk_discuss_rounds` in `default_config.py`; the routers stop at `2 * max_debate_rounds` and `3 * max_risk_discuss_rounds` messages respectively.
- The debate router distinguishes speakers by the `current_response` prefix. Changing that prefix convention in `agents/researchers/*` breaks routing — update both sides together.

## Hard constraints

- `2 * max_tool_rounds + 2` must be smaller than `max_recur_limit`; otherwise `TradingAgentsGraph.__init__` raises before any work starts.
- Analyst subgraphs write only their own report key. Shared writes under parallelism corrupt state.
- Any shape change must change `_run_signature()` so `thread_id()` differs and old checkpoints stop resuming.
- `stream_run` uses `stream_mode=["values","tasks"]` with `subgraphs=True`; the web layer consumes those events, so renaming nodes changes UI labels via `webapi/runs.py`.

## Verify

```bash
pytest -m unit tests/test_analyst_execution.py tests/test_graph_end_to_end.py tests/test_risk_router_path_map.py
pytest -m unit
```

`tests/test_risk_router_path_map.py` exists specifically to catch path-map gaps — if a new route is not covered there, extend that test rather than relying on the end-to-end run.

Symbol-level detail: `references/symbol-map.md`.
