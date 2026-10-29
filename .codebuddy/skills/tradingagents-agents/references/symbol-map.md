# agents symbol map

Verified against `v0.7.1` sources.

## Factories exported by `tradingagents/agents/__init__.py`

| Factory | Module | Archetype | Writes |
|---|---|---|---|
| `create_market_analyst` | `analysts/market_analyst.py` | tools | `market_report` |
| `create_sentiment_analyst` | `analysts/sentiment_analyst.py` | tools + prefetch | `sentiment_report` |
| `create_news_analyst` | `analysts/news_analyst.py` | tools | `news_report` |
| `create_fundamentals_analyst` | `analysts/fundamentals_analyst.py` | tools | `fundamentals_report` |
| `create_bull_researcher` | `researchers/bull_researcher.py` | prompt | `investment_debate_state` |
| `create_bear_researcher` | `researchers/bear_researcher.py` | prompt | `investment_debate_state` |
| `create_research_manager` | `managers/research_manager.py` | structured (`ResearchPlan`) | `investment_plan` |
| `create_trader` | `trader/trader.py` | structured (`TraderProposal`) | `trader_investment_plan` |
| `create_aggressive_debator` | `risk_mgmt/aggressive_debator.py` | prompt | `risk_debate_state` |
| `create_conservative_debator` | `risk_mgmt/conservative_debator.py` | prompt | `risk_debate_state` |
| `create_neutral_debator` | `risk_mgmt/neutral_debator.py` | prompt | `risk_debate_state` |
| `create_portfolio_manager` | `managers/portfolio_manager.py` | structured (`PortfolioDecision`) | `final_trade_decision`, `final_rating` |

## `tradingagents/agents/state.py`

`AgentState(MessagesState)` fields: `company_of_interest`, `asset_type`, `instrument_context`, `trade_date`, `market_report`, `sentiment_report`, `news_report`, `fundamentals_report`, `investment_debate_state`, `investment_plan`, `trader_investment_plan`, `risk_debate_state`, `final_trade_decision`, `final_rating`, `past_context`, `memory_note`, `portfolio_context`.

`InvestDebateState` and `RiskDebateState` hold `history`, `current_response`, `count`, plus judge/plan fields.

## `tradingagents/agents/tools.py` (`@tool` functions)

`get_stock_data`, `get_indicators`, `get_verified_market_snapshot`, `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement`, `get_news`, `get_global_news`, `get_insider_transactions`, `get_macro_indicators`, `get_prediction_markets`.

All inject `company_of_interest` / `trade_date` from state and end in `route_to_vendor(<method>, ...)`.

## `tradingagents/agents/context.py`

`get_language_instruction`, `opponent_argument_or_opening`, `report_or_absent`, `resolve_instrument_identity`, `build_instrument_context`, `get_instrument_context_from_state`, `get_portfolio_context_from_state`.

## `tradingagents/agents/schemas.py`

Enums: `PortfolioRating`, `TraderAction`, `SentimentBand`.
Models: `ResearchPlan`, `TraderProposal`, `PortfolioDecision`, `SentimentReport`.
Renderers: `render_research_plan`, `render_trader_proposal`, `render_pm_decision`, `render_sentiment_report`.

## `tradingagents/agents/structured.py`

`bind_structured(llm, schema, agent_name)`, `invoke_structured(...)`, `invoke_structured_or_freetext(...)`, `NO_EXTERNAL_TOOLS`.

## `tradingagents/agents/post_screen.py`

`jev_screen(ticker)` → `screen(posts) -> (keep_flags, note)` or `None` when `TYPESAFE_API_KEY` is unset.
