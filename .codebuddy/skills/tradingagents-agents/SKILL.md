---
name: tradingagents-agents
description: Procedures for creating and editing TradingAgents agent nodes — the create_* factories, prompts, bound tools, structured-output schemas, and rating extraction. This skill should be used when adding an agent, rewriting a prompt, changing which tools an analyst can call, or when structured-output parsing, NO_EXTERNAL_TOOLS, or sentiment/rating fields misbehave.
---

# TradingAgents agent nodes

An "agent" here is a LangGraph node factory, not an autonomous loop. The graph owns sequencing; the agent owns one reasoning step and returns a state delta.

## Canonical shape

```python
def create_<name>(llm):
    def node(state: AgentState) -> dict:
        ...
        return {"messages": [...], "<report_key>": report}
    return node
```

Never return the full state, and never mutate `state` in place.

## Two archetypes

### 1. Tool-using analyst

Members: `market_analyst`, `news_analyst`, `fundamentals_analyst`, `sentiment_analyst`.

- Declare `TOOLS: tuple = (...)` at module level, drawn from `tradingagents/agents/tools.py`.
- Build the prompt with `ChatPromptTemplate.from_messages` and a module-local `system_message`.
- Delegate the loop to `take_turn(prompt, llm, TOOLS, state["messages"])` from `agents/analysts/turn.py`. `WRAP_UP` forces a final report when the tool-round budget runs out.
- Return `{"messages": [...], "<x>_report": text}`.

### 2. Structured agent

Members: `research_manager`, `trader`, `portfolio_manager`.

- `structured_llm = bind_structured(llm, Schema, "<name>")` in the factory.
- Call `invoke_structured_or_freetext(...)` in the node; the Portfolio Manager additionally writes `final_rating`.
- The prompt **must** include `NO_EXTERNAL_TOOLS`, otherwise the model attempts a tool call and schema parsing fails.
- Render the schema back to markdown with the matching `render_*` helper so downstream sections keep the existing shape.

## Prompt rules

- Prompts are inline in each module; there is no central prompt directory.
- Always state the as-of date and forbid numbers that are not in the provided data.
- Use `get_language_instruction()` (`agents/context.py`) — never hardcode an output language.
- Use `report_or_absent(...)` and `opponent_argument_or_opening(...)` for the "missing input" phrasing; `tests/test_i18n_coverage.py` checks these.
- Keep headings stable: reporting, HTML rendering, and the memory log all parse them.

## Tools

`tradingagents/agents/tools.py` is the only data entry point. Each tool:

- injects context via `Annotated[str, InjectedState("company_of_interest")]` / `("trade_date")`
- clamps dates with `as_of` / `as_of_window` before calling `route_to_vendor`
- converts exceptions into sentinel strings rather than raising, so a bad vendor does not kill the run

Adding a tool means: implement the vendor method (`tradingagents-dataflows` skill), add the `@tool`, then register it in the analyst's `TOOLS` tuple.

## Ratings

`agents/rating.py` owns `RATINGS_5_TIER`, `RATING_REVIEW`, `extract_rating`, `parse_rating`, `run_rating`, `is_review`. Any change to rating vocabulary must be mirrored in the memory log parser and the backtest `_DIRECTION` map.

## Registering a new agent

1. `tradingagents/agents/<group>/<name>.py` with `create_<name>(llm)`.
2. Export from `tradingagents/agents/__init__.py` (import + `__all__`).
3. Wire into the graph — analysts via `AnalystNodeSpec`, everything else via `setup.py` (see `tradingagents-graph` skill).
4. Add the report field to `AgentState` and to `reporting._SECTIONS` if it is user-visible.

## Verify

```bash
pytest -m unit tests/test_structured_agents.py tests/test_prompt_integrity.py tests/test_i18n_coverage.py
pytest -m unit
```

Symbol-level detail: `references/symbol-map.md`.
