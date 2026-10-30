# dataflows router map

Verified against `v0.7.1` — `tradingagents/dataflows/router.py`.

## `TOOLS_CATEGORIES`

| Category | Methods | Optional |
|---|---|---|
| `core_stock_apis` | `get_stock_data` | no |
| `technical_indicators` | `get_indicators` | no |
| `fundamental_data` | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` | no |
| `news_data` | `get_news`, `get_global_news`, `get_insider_transactions` | no |
| `macro_data` | `get_macro_indicators` | **yes** |
| `prediction_markets` | `get_prediction_markets` | **yes** |

`OPTIONAL_CATEGORIES = {"macro_data", "prediction_markets"}` — failures degrade to a sentinel; core failures raise.

## `VENDOR_METHODS`

| Method | Vendors (insertion order = `"default"` order) |
|---|---|
| `get_stock_data` | alpha_vantage, yfinance, tencent |
| `get_indicators` | alpha_vantage, local, yfinance |
| `get_fundamentals` | alpha_vantage, yfinance |
| `get_balance_sheet` | alpha_vantage, sec_edgar, yfinance |
| `get_cashflow` | alpha_vantage, sec_edgar, yfinance |
| `get_income_statement` | alpha_vantage, sec_edgar, yfinance |
| `get_news` | alpha_vantage, yfinance, eastmoney |
| `get_global_news` | yfinance, alpha_vantage, eastmoney |
| `get_insider_transactions` | alpha_vantage, yfinance |
| `get_macro_indicators` | fred |
| `get_prediction_markets` | polymarket |

Note: `get_stock_data` keeps tencent last so a `"default"` chain reads Yahoo first, matching historical behaviour — the `tencent`-first ordering lives in the configured chain, not in this table.

Note: `get_indicators` maps both `local` and `yfinance` to `get_stock_stats_indicators_window`. Indicators are computed from the OHLCV that `core_stock_apis` served; `yfinance` is an alias kept for old configs. Only `alpha_vantage` is a real indicator API.

## Functions

- `get_category_for_method(method) -> str`
- `get_vendor(category, method=None) -> str` — returns a comma-separated chain, or `"default"`
- `route_to_vendor(method, *args, **kwargs)` — walks the chain in order; the first success wins
- `vendor_unavailable(...)` / `no_data_available(...)` — sentinel builders prefixed `DATA_UNAVAILABLE:` / `NO_DATA_AVAILABLE:`

## Supporting modules

| Module | API |
|---|---|
| `dataflows/config.py` | `set_config`, `get_config`, `run_config(config)`, `run_config_context(config)` — ContextVar scoped |
| `dataflows/symbols.py` | `normalize_symbol`, `safe_ticker_component` |
| `dataflows/date_window.py` | `as_of`, `as_of_window`, `in_window`, `coverage_gap`, `get_current_date`, `is_historical`, `withhold_live_profile` |
| `dataflows/quotes.py` | `load_ohlcv(symbol, as_of_date, fill_gaps=True)`, `get_closes(symbol, start, end)`, `_price_chain()`, `_PRICE_VENDORS = ("tencent", "yfinance")`, `_NO_VENDOR_NAMED = ("yfinance",)` |
| `dataflows/files.py` | `replace_file`, `locked` |
| `dataflows/net.py` | `get_scrubbed`, `vendor_reachable` |
| `dataflows/errors.py` | `NoMarketDataError`, `VendorUnavailableError`, `VendorNotConfiguredError` |

## Vendor packages

`vendors/yahoo/` (market, ohlcv, fundamentals, news, snapshot, common), `vendors/alpha_vantage/` (stock, indicator, fundamentals, news, common), `vendors/tencent/` (kline, codes), `vendors/eastmoney/news.py`, `vendors/fred.py`, `vendors/reddit.py`, `vendors/stocktwits.py`, `vendors/polymarket.py`, `vendors/sec_edgar.py`.

Vendor-specific behaviour that changes how a chain behaves:

| Vendor | Module | Behaviour |
|---|---|---|
| tencent | `vendors/tencent/kline.py` | `fetch_daily` caches one response for `FETCH_TTL_SECONDS = 900` behind `_FETCH_LOCK`, keyed on `(symbol, start, end, count)`; rows are `[date, open, close, high, low, volume]`; sh/sz volume ×100; `_assert_ohlcv_not_stale` on every read |
| yahoo | `vendors/yahoo/common.py` | `yahoo_geo_blocked()` probes `CRUMB_URL` once per process; a 403 carrying `GEO_BLOCK_MARKER` turns `YFRateLimitError` into `VendorUnavailableError(GEO_BLOCK_MESSAGE)` — no retry helps |

## Default chains (`tradingagents/default_config.py`)

- `core_stock_apis`: `tencent,yfinance` — Tencent first (no key, reachable where Yahoo's API is blocked), Yahoo behind it for symbols Tencent does not quote
- `technical_indicators`: `local` — computed from whatever `core_stock_apis` served
- `fundamental_data`: `sec_edgar,yfinance`
- `news_data`: `yfinance`
- `macro_data`: `fred`
- `prediction_markets`: `polymarket`

`.env.example` documents the same block; keep the two in step.
