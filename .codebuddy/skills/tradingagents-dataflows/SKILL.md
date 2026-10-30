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

Defaults (see `default_config.build_default_config()`): `core_stock_apis` is `"tencent,yfinance"` — 腾讯自选股 leads because it needs no key and answers where Yahoo's API is blocked, Yahoo stays behind it for futures/FX/crypto symbols; `technical_indicators` is `"local"`, computed from whatever the quotes chain served.

## Vendor contract

```python
def get_something(ticker: str, ..., as_of_date: str | None = None) -> str | pd.DataFrame:
    ...
```

- Register under the **method name**, not the module name.
- Accept and honour `as_of_date` (or an explicit start/end pair) — no implicit "today".
- LLM-facing output is markdown/`str`; computational helpers return `pandas.DataFrame` / `Series`.
- Raise `NoMarketDataError` when the symbol genuinely has no data, `VendorUnavailableError` on rate limits/outages, `VendorNotConfiguredError` when a key is missing (`dataflows/errors.py`).
- Prices go through `quotes.load_ohlcv` / `quotes.get_closes`; see *Prices and indicators* below.
- File writes use `files.replace_file()`; shared files are guarded by `files.locked()`.

## Prices and indicators

`quotes.py` is the only price entry point: the market analyst's CSV, the indicators, the verified snapshot, and the closes a decision settles against all read through it, so a run can never price from one vendor and settle against another.

- `_price_chain()` reads `get_vendor("core_stock_apis", "get_stock_data")`, splits on commas, and keeps only `_PRICE_VENDORS = ("tencent", "yfinance")`. A chain naming no price vendor is read as `_NO_VENDOR_NAMED = ("yfinance",)` — alpha_vantage serves quotes but no OHLCV frame, so it cannot appear here.
- The readers are hard-coded dicts (`load_ohlcv` → `tencent_ohlcv`/`yahoo_ohlcv`, `get_closes` → `tencent_closes`/`yahoo_closes`). Adding a price vendor means **both** `_PRICE_VENDORS` and both reader dicts, or the vendor is silently skipped.
- Error precedence: a `VendorUnavailableError` (throttled, in transit) outranks another vendor's `NoMarketDataError`. `_no_vendor_answered()` re-raises the outage, so a symbol is never reported absent by a vendor that never answered.
- `get_indicators` has `local` (default) and `yfinance` — both `get_stock_stats_indicators_window`, which computes from the quotes OHLCV. No indicator API is called; the alias exists so an old `technical_indicators: yfinance` config keeps working.

## Vendor quirks worth knowing

- **Tencent K-line (`vendors/tencent/kline.py`)** caches one fetch for `FETCH_TTL_SECONDS = 900` behind `_FETCH_LOCK`, keyed on `(canonical symbol, start, end, count)`. Analysts issue tool calls in parallel and a run reads the same window a dozen times; without the cache each read returns a slightly different intraday bar and the report quotes two closes for one session. Never bypass `fetch_daily` with a direct request.
- Tencent rows are `[date, open, close, high, low, volume]` — close is third. A-share (`sh`/`sz`) volume arrives in 手 and is multiplied by 100.
- Both loaders end with `_assert_ohlcv_not_stale`: a frame whose newest bar predates the request is an error, not data.
- **Yahoo geo-block (`vendors/yahoo/common.py`)** — Yahoo answers withdrawn networks with an HTTP 403 HTML page (`GEO_BLOCK_MARKER` = "no longer be accessible from mainland China"), which yfinance reports as a rate limit. `yahoo_geo_blocked()` probes the crumb URL once per process; the answer is cached and turns later failures straight into `VendorUnavailableError(GEO_BLOCK_MESSAGE)`. Do not add retries or backoff for this — retrying a 403 page only delays the report.

## Date rules

`dataflows/date_window.py` is mandatory for anything dated:

- `as_of(...)`, `as_of_window(...)` — clamp requested ranges to the run's trade date
- `in_window`, `coverage_gap` — validate the vendor actually covers the range
- `is_historical`, `withhold_live_profile` — suppress live-only fields in historical runs

Bypassing these is the usual cause of look-ahead failures (`tests/test_*lookahead*.py`).

## Procedure — add a vendor

1. Create `vendors/<name>/` or `vendors/<name>.py`; export the public surface from `__init__.py`.
2. Import in `router.py`, then add entries under each supported `VENDOR_METHODS[method]`.
3. Add it to `quotes._PRICE_VENDORS` **and** to both reader dicts in `quotes.load_ohlcv` / `quotes.get_closes` if it provides OHLCV; otherwise its prices only reach the tools that call it directly.
4. Update default chains and the vendor comments in `tradingagents/default_config.py`, plus the `data_vendors` block in `.env.example`.
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
pytest -m unit tests/test_vendor_routing.py tests/test_vendor_errors.py tests/test_no_data_handling.py \
  tests/test_tool_date_enforcement.py tests/test_quotes_fallback.py tests/test_tencent_vendor.py \
  tests/test_yahoo_geo_block.py tests/test_yahoo_rate_limit.py
```

`tests/conftest.py` blocks sockets and `curl_cffi` unless a test is marked `integration`. Network assertions belong behind that marker.

Symbol-level detail: `references/router-map.md`.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
