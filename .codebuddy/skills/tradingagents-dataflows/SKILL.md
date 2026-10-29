---
name: tradingagents-dataflows
description: Procedures for adding and fixing market data vendors in tradingagents/dataflows — routing tables, vendor contract, point-in-time date rules, and error semantics. This skill should be used when adding a vendor or data method, changing data_vendors fallback order, fixing rate-limit or missing-data handling, or diagnosing look-ahead and ticker-normalization bugs.
---

# TradingAgents dataflows

`tradingagents/dataflows/` maps a method name to an ordered chain of vendor implementations and enforces point-in-time correctness. Agents never call vendors directly — they call tools in `agents/tools.py`, which call `route_to_vendor`.

## Routing model

- `router.TOOLS_CATEGORIES` — 6 categories: `core_stock_apis`, `technical_indicators`, `fundamental_data`, `news_data`, `macro_data`, `prediction_markets`. The last two are in `router.OPTIONAL_CATEGORIES`.
- `router.VENDOR_METHODS[method][vendor]` — the complete dispatch table; a method that is absent here cannot be routed to at all.
- `router.get_category_for_method(method)` → category; `router.get_vendor(category, method)` → configured vendor string. Per-tool `tool_vendors` beats per-category `data_vendors`; the string `"default"` means "every vendor registered for this method".
- `router.route_to_vendor(method, *args, **kwargs)` tries the configured chain **in order and only that chain**.

Consequence: if a user configures only `yfinance`, a failure does **not** silently fall back to alpha_vantage. Multiple vendors must be written comma-separated in the config.

## Vendor contract

```python
def get_something(ticker: str, ..., as_of_date: str | None = None) -> str | pd.DataFrame:
    ...
```

- Register under the **method name**, not the module name.
- Accept and honour `as_of_date` (or an explicit start/end pair) — no implicit "today".
- LLM-facing output is markdown/`str`; computational helpers return `pandas.DataFrame` / `Series`.
- Raise `NoMarketDataError` when the symbol genuinely has no data, `VendorUnavailableError` on rate limits/outages, `VendorNotConfiguredError` when a key is missing (`dataflows/errors.py`).
- Prices go through `quotes.load_ohlcv` / `quotes.get_closes`; only `_PRICE_VENDORS = ("tencent", "yfinance")` participate.
- File writes use `files.replace_file()`; shared files are guarded by `files.locked()`.

## Date rules

`dataflows/date_window.py` is mandatory for anything dated:

- `as_of(...)`, `as_of_window(...)` — clamp requested ranges to the run's trade date
- `in_window`, `coverage_gap` — validate the vendor actually covers the range
- `is_historical`, `withhold_live_profile` — suppress live-only fields in historical runs

Bypassing these is the usual cause of look-ahead failures (`tests/test_*lookahead*.py`).

## Procedure — add a vendor

1. Create `vendors/<name>/` or `vendors/<name>.py`; export the public surface from `__init__.py`.
2. Import in `router.py`, then add entries under each supported `VENDOR_METHODS[method]`.
3. Add it to `quotes._PRICE_VENDORS` only if it provides OHLCV.
4. Update default chains and the vendor comments in `tradingagents/default_config.py`.
5. Follow the error contract above; never leak API keys (`net.get_scrubbed()`).

## Procedure — add a data method

1. `router.TOOLS_CATEGORIES` → add or reuse a category.
2. `router.VENDOR_METHODS[method] = {"vendor": fn, ...}`.
3. Implement in at least one vendor, using `as_of` clamping.
4. Expose an `@tool` in `agents/tools.py` (with `InjectedState`) and register it in the analyst's `TOOLS` tuple.
5. Add a default chain to `default_config.py`.

## Symbols

`symbols.normalize_symbol()` handles aliases, FX, crypto, HK and A-share suffixes; `symbols.safe_ticker_component()` prevents path traversal in cache paths. Always normalize before hitting a vendor and before building a filename.

## Verify

```bash
pytest -m unit tests/test_vendor_routing.py tests/test_vendor_errors.py tests/test_no_data_handling.py tests/test_tool_date_enforcement.py
```

`tests/conftest.py` blocks sockets and `curl_cffi` unless a test is marked `integration`. Network assertions belong behind that marker.

Symbol-level detail: `references/router-map.md`.
