---
name: tradingagents-cli
description: Procedures for the TradingAgents Typer CLI in cli/ — commands, flags, interactive prompts, Rich live display, and remembered preferences. This skill should be used when adding or renaming a flag or subcommand, changing the interactive selection flow, adjusting terminal output, or when CLI behaviour must stay consistent with the web API and headless runs.
---

# TradingAgents CLI

The CLI is a thin shell over `TradingAgentsGraph`. Preserve that layering: parsing and rendering here, logic in `tradingagents/`.

## Entry points

```bash
tradingagents                    # interactive, no flags
python -m cli.main               # same, from a checkout
tradingagents --ticker NVDA --date 2026-09-23 --analysts market,news --save --no-show
tradingagents backtest NVDA,AAPL --start 2026-01-01 --end 2026-03-01 --every 7
tradingagents login chatgpt
```

Packaging maps `tradingagents = cli.main:app` (`pyproject.toml`), so keep `app` importable with no side effects at module scope.

## Command surface — `cli/main.py`

- `analyze` is bound to `@app.callback(invoke_without_command=True)`, so a bare invocation runs it interactively.
- Flags: `--checkpoint/--no-checkpoint`, `--clear-checkpoints`, `--portfolio`, `--ticker`, `--date`, `--analysts`, `--save/--no-save`, `--show/--no-show`, `--html/--no-html`.
- `backtest` takes **positional** `tickers` (comma-separated) plus `--start`, `--end` (both required), `--every` (default 7), `--analysts`, `--asset-type` (default `stock`), `--portfolio`, `--run-id`.
- `login` / `logout` take a `plan` argument constrained to `SIGNED_IN_PROVIDERS` (currently ChatGPT-plan sign-in).

## Flow — `cli/run.py`

`run_analysis(checkpoint=None, portfolio=None, flags=None)`:

1. Parse selections (`prompts.parse_analysts`, `prompts.filter_analysts_for_asset_type`).
2. `_build_run_config(selections, checkpoint)` builds the config delta.
3. Construct `TradingAgentsGraph`.
4. Drive `graph.stream_run(...)` under a Rich `Live` display.
5. `_offer_reports(final_state, graph, ticker, save=..., show=..., html=...)` persists and optionally opens the report.

Supporting modules: `display.py` (console helpers), `prefs.py` (remembered selection), `stats_handler.py` (run statistics), `updates.py` (once-per-day version check), `models.py` (`AnalystType`, `AssetType`).

## Rules

1. **Headless stays headless.** With `--ticker` and `--date` supplied, nothing may block on input. Note that `tests/conftest.py` forces `isatty=True`, so a careless prompt breaks the suite rather than only interactive use.
2. **Always pass flags explicitly** down the call chain; do not read module-level globals.
3. **Never touch `os.environ`.** Go through `dataflows.config` / `default_config` so the web API sees the same values. (The web server's own host/port and `TRADINGAGENTS_LOG_*` switches are the documented exception and live in `webapi/`.)
4. **Exit non-zero on validation failure** before any graph work starts — this is what makes the CLI usable in scripts.
5. `--no-show` must not launch a browser; `_offer_reports` is the only place that opens anything.
6. Print saved paths once, unescaped and stable — users parse them.

## Procedure — add a flag

1. Declare it in `cli/main.py`.
2. Thread it through `run_analysis`, then either `_build_run_config` (config effect) or `_offer_reports` (output effect).
3. If it needs a config key, coordinate with `reporting-engineer`: default, `TRADINGAGENTS_*` override, doc line.
4. Update the README usage block and the option help text.
5. Add a case in the nearest `tests/test_cli_*.py`.

## Procedure — add a subcommand

1. `@app.command()` in `cli/main.py`.
2. Keep the body to parse → call a `tradingagents` function → render.
3. Reuse `cli/display.py` rather than raw `print`.

## Verify

```bash
pytest -m unit -k cli
python -m cli.main --help
python -m cli.main --ticker AAPL --date 2026-01-15 --analysts market --save --no-show
```

Report the flags or commands touched, whether interactive mode changed, and the smoke-test output.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
