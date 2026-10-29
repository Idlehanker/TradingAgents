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
| `get_indicators` | alpha_vantage, yfinance |
| `get_fundamentals` | alpha_vantage, yfinance |
| `get_balance_sheet` | alpha_vantage, sec_edgar, yfinance |
| `get_cashflow` | alpha_vantage, sec_edgar, yfinance |
| `get_income_statement` | alpha_vantage, sec_edgar, yfinance |
| `get_news` | alpha_vantage, yfinance, eastmoney |
| `get_global_news` | yfinance, alpha_vantage, eastmoney |
| `get_insider_transactions` | alpha_vantage, yfinance |
| `get_macro_indicators` | fred |
| `get_prediction_markets` | polymarket |

Note: `get_stock_data` keeps tencent last so a `"default"` chain reads Yahoo first, matching historical behaviour.

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
| `dataflows/quotes.py` | `load_ohlcv(symbol, as_of_date, fill_gaps=True)`, `get_closes(symbol, start, end)`, `_PRICE_VENDORS = ("tencent", "yfinance")` |
| `dataflows/files.py` | `replace_file`, `locked` |
| `dataflows/net.py` | `get_scrubbed`, `vendor_reachable` |
| `dataflows/errors.py` | `NoMarketDataError`, `VendorUnavailableError`, `VendorNotConfiguredError` |

## Vendor packages

`vendors/yahoo/` (market, ohlcv, fundamentals, news, snapshot, common), `vendors/alpha_vantage/` (stock, indicator, fundamentals, news, common), `vendors/tencent/` (kline, codes), `vendors/eastmoney/news.py`, `vendors/fred.py`, `vendors/reddit.py`, `vendors/stocktwits.py`, `vendors/polymarket.py`, `vendors/sec_edgar.py`.

## Default chains (`tradingagents/default_config.py`)

- `core_stock_apis`: `yfinance`
- `fundamental_data`: `sec_edgar,yfinance`
- `news_data`: `yfinance`
- `macro_data`: `fred`
- `prediction_markets`: `polymarket`
