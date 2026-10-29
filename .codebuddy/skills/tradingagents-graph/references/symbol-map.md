# graph symbol map

Verified against `v0.7.1` sources.

## `tradingagents/graph/setup.py`

- `DEBATE_PATH_MAP` (line ~35) — maps `should_continue_debate` return values to node names.
- `RISK_ANALYSIS_PATH_MAP` (line ~40) — maps `should_continue_risk_analysis` return values to node names.
- `class GraphSetup` (line ~93)
  - `.setup_graph(selected_analysts, memory_node=None) -> StateGraph`
  - internal `. _analyst_graph(spec, agent, max_tool_rounds)` builds the `agent` → `tools` → `wrap_up` subgraph.
- Node display names: `"Memory Log"`, `"Bull Researcher"`, `"Bear Researcher"`, `"Research Manager"`, `"Trader"`, `"Aggressive Analyst"`, `"Conservative Analyst"`, `"Neutral Analyst"`, `"Portfolio Manager"`.

## `tradingagents/graph/analyst_execution.py`

- `AnalystNodeSpec(key, agent_node, report_key, tools)` — frozen dataclass.
- `ANALYST_NODE_SPECS` — keys `market`, `social`, `news`, `fundamentals`.
- `build_analyst_execution_plan(selected)` — raises `ValueError` on unknown or empty selection.

## `tradingagents/graph/conditional_logic.py`

- `ConditionalLogic(config)`
  - `.should_continue_debate(state) -> str`
  - `.should_continue_risk_analysis(state) -> str`

## `tradingagents/graph/propagation.py`

- `Propagator.create_initial_state(company_name, trade_date, asset_type, past_context=None, instrument_context=None, portfolio_context=None) -> dict`
- `get_graph_args() -> {"stream_mode": "values", "config": {"recursion_limit": ...}}`

Initial dict keys: `messages`, `company_of_interest`, `asset_type`, `trade_date`, `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`, `investment_debate_state`, `investment_plan`, `trader_investment_plan`, `risk_debate_state`, `final_trade_decision`, `past_context`.

## `tradingagents/graph/checkpointer.py`

- `thread_id(ticker, trade_date, signature)` — stable hash of the run shape.
- `get_checkpointer(data_dir, ticker)` — `SqliteSaver` at `<data_cache_dir>/checkpoints/<TICKER>.db`.
- `checkpoint_step()`, `clear_checkpoint()`, `clear_all_checkpoints()`.

## `tradingagents/graph/trading_graph.py`

`TradingAgentsGraph(selected_analysts=("market","social","news","fundamentals"), debug=False, config=None, callbacks=None)`

- `propagate(company_name, trade_date, asset_type="stock", portfolio=None) -> (final_state, signal)`
- `stream_run(...)` — yields `(mode, chunk)` pairs, `subgraphs=True`.
- `begin_checkpoint` / `end_checkpoint` / `checkpoint_scope` / `checkpoint_input` / `clear_checkpoint_on_success`
- `_run_signature()`, `create_run_state()`, `resolve_instrument_context()`, `_memory_step()`
- `settle_pending()`, `settle_all_pending()`, `record_decision()`
- `run_settings()`, `save_reports()`, `default_report_path()`
