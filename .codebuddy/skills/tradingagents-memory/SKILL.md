---
name: tradingagents-memory
description: Procedures for the TradingAgents trading memory in tradingagents/memory — appending decisions, settling pending entries against benchmark returns, and retrieving point-in-time past context. This skill should be used when changing the memory entry format, settlement window or benchmark mapping, debugging duplicate or missing memory entries, or reviewing look-ahead contamination in past-context retrieval.
---

# TradingAgents memory

The memory log closes the feedback loop: every run appends its decision, later runs settle it against realised returns, and the Portfolio Manager receives both in `past_context`.

## Three stages

1. **Write** — `TradingMemoryLog.store_decision(ticker, trade_date, final_trade_decision, rating=None)` appends a markdown entry with header `[date | ticker | rating | pending]`. Idempotent per ticker+date.
2. **Settle** — `settlement.settle_pending(...)` / `settle_all_pending(...)` fetch the price move over `holding_period_days`, compare with a benchmark, and rewrite the entry with raw and alpha returns plus a reflection.
3. **Read** — `get_past_context(ticker, n_same=5, n_cross=3, as_of=None)` returns the lessons injected into the next run.

## Storage

- Location: `~/.tradingagents/memory/trading_memory.md`, override with `TRADINGAGENTS_MEMORY_LOG_PATH`.
- Format: plain markdown, entries separated by `_SEPARATOR = "\n\n<!-- ENTRY_END -->\n\n"`.
- Concurrency: every mutation runs under `TradingMemoryLog.settling()` and `dataflows.files.locked()`.
- Backtests write to an isolated log with their own `run_id`; the user's log is never touched.

## Settlement rules

- `settlement.resolve_benchmark(ticker, config)` — explicit `benchmark_ticker` wins, otherwise the `benchmark_map` suffix rules decide (`.T` → `^N225`, and so on).
- `settlement.fetch_returns(ticker, trade_date, holding_days=5, benchmark="SPY")` → `(raw, alpha, holding_days, resolution_date)`.
- `Reflector(quick_thinking_llm).reflect_on_final_decision(...)` produces 2–4 plain sentences. This is the only LLM call in the memory path — keep it on the quick tier.
- Trigger points: the `Memory Log` graph node (runs in parallel with analysts) and the external `TradingAgentsGraph.settle_pending` / `settle_all_pending` API.

## Invariants

1. **Writer and parser change together.** A format change must update `store_decision`, the entry parser, `get_past_context`, and `backtest._alpha()` in the same change.
2. **Point-in-time retrieval.** With `as_of` set, only lessons knowable on that date may be returned. Violating this is a silent look-ahead bug — the highest-severity defect in this module.
3. **Idempotency.** Re-running the same ticker+date must not duplicate an entry; settlement must not double-apply a return.
4. The memory node must not write any analyst report key.

## Procedure — change the holding window or benchmark

1. Edit `holding_period_days` / `benchmark_ticker` / `benchmark_map` in `tradingagents/default_config.py` (`TRADINGAGENTS_*` env overrides exist for the scalar ones).
2. Keep suffix mapping exclusively in `resolve_benchmark`.
3. Re-check date arithmetic in `fetch_returns` when the resolution date can cross weekends or holidays.

## Procedure — change the entry format

1. Write a reader that accepts both old and new shapes, or migrate existing files.
2. Keep `_SEPARATOR` stable, or document the migration.
3. Verify backtest scoring still parses rating and the pending flag.

## Verify

```bash
pytest -m unit tests/test_memory_log.py tests/test_memory_pointintime.py tests/test_cli_memory_log.py
```

`tests/test_memory_log.py` is the largest test file in the repo — read the relevant case before changing parsing behaviour. Always report whether pre-existing on-disk entries stay readable.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
