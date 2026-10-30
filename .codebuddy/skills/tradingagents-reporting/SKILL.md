---
name: tradingagents-reporting
description: Procedures for TradingAgents output and configuration surfaces — report markdown tree, self-contained HTML report, portfolio input, backtest scoring, and default config with env overrides. This skill should be used when adding a report section, changing HTML rendering, adding a config key or TRADINGAGENTS_ env override, or extending backtest grid and scoring behaviour.
---

# TradingAgents reporting, portfolio, backtest, config

Four small modules shared by the CLI and the web API. Everything here is output or configuration — no agent reasoning.

## Report tree — `tradingagents/reporting.py`

`write_report_tree(final_state, ticker, save_path, settings=None, html=True) -> Path`

- Writes numbered folders `1_analysts` … `5_portfolio` plus `complete_report.md`, and `complete_report.html` when `html=True`.
- `_SECTIONS` is the single source of truth: title, filename, and the `AgentState` path each section reads. The HTML renderer iterates the same constant.
- `analyst_names()` maps the internal key `social` to the display name `sentiment`. Keep both spellings straight.
- Used by both `cli/run.py` and `TradingAgentsGraph.save_reports()`.

### Add a section

1. Confirm the data already exists in `AgentState` — otherwise it is a graph change first (`tradingagents-graph` skill).
2. Append to `_SECTIONS` with a stable filename and the correct state path.
3. Check the numbered ordering and that the HTML page picks it up automatically.
4. Add the same state key to `SECTIONS` in `webapi/runs.py` (and `ANALYST_REPORT_MAP` for an analyst section), or the web UI never shows it — see `tradingagents-web`.
5. Extend `tests/test_reporting.py` and `tests/test_report_html.py`.

Never maintain a second section list inside `report_html.py`.

## HTML — `tradingagents/report_html.py`

`render_report(ticker, final_state, settings, parts) -> str` emits one self-contained page (inline CSS, no external assets). Markdown conversion uses `markdown-it-py` via `_markdown()`. Escape user- or model-supplied text; the report includes LLM output.

## Portfolio — `tradingagents/portfolio.py`

- `Position`, `PortfolioContext` (`positions_in`, `position_in`, `render(ticker)`, `fingerprint()`).
- `load_portfolio(path)` backs the CLI `--portfolio` flag. Validation errors must surface before any analysis begins — never mid-run.
- `fingerprint()` feeds checkpoint signatures; changing its output invalidates checkpoints.

## Backtest — `tradingagents/backtest.py`

- `iter_grid(start_date, end_date, every_n_days=1) -> list[str]` builds the date grid.
- `run_backtest(tickers, dates, config, asset_type="stock", portfolio=None, selected_analysts=("market","social","news","fundamentals"), run_id=None, progress=None) -> BacktestResult`. `progress(done, total, ticker, date)` fires before each cell; cells already present in the run's own log are skipped, so re-running resumes.
- `summarize(source) -> BacktestSummary`, which renders per-rating scores (`RatingScore`); direction comes from `_DIRECTION`.
- Backtests must use their own memory log and `run_id`, never `~/.tradingagents/memory/trading_memory.md`.
- `_alpha()` parses memory entries — it must stay in sync with the memory entry format.

## Config — `tradingagents/default_config.py`

Two pieces:

- `_ENV_OVERRIDES` — the **only** env→config mapping (`TRADINGAGENTS_*`). Never read `os.environ` at a call site.
- `build_default_config()` → `DEFAULT_CONFIG`. Runtime merging happens in `dataflows.config.set_config` (one-level deep merge over the defaults).

Documented exception: `TRADINGAGENTS_WEB_HOST` / `TRADINGAGENTS_WEB_PORT` (uvicorn, `webapi/server.py`) and the `TRADINGAGENTS_LOG_*` switches (`webapi/logging_setup.py`) are read straight from the environment because they configure the server before any config exists. They are not config keys — do not add them to `_ENV_OVERRIDES`, and keep `.env.example` in step.

`data_vendors` defaults are documented inline and mirrored in `.env.example`: `core_stock_apis` = `tencent,yfinance`, `technical_indicators` = `local`, `fundamental_data` = `sec_edgar,yfinance`, `news_data` = `yfinance`. `GET /api/config` exposes the effective provider/models/analyst options the web form renders.

### Add a config key

1. Add the default. The type of the default drives env coercion, so choose deliberately (`None` means "unset", not `False`).
2. Add the `TRADINGAGENTS_*` entry to `_ENV_OVERRIDES`.
3. Consume it via `dataflows.config.get_config()`.
4. Confirm `tests/conftest.py` blanks `TRADINGAGENTS_*` before import — a new env key must not leak across tests.

## Verify

```bash
pytest -m unit tests/test_reporting.py tests/test_report_html.py tests/test_backtest.py
python -m cli.main --ticker AAPL --date 2026-01-15 --analysts market --save --no-show
```

Report which sections or config keys changed and whether previously saved reports and memory entries remain readable.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
