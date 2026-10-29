"""腾讯自选股 (Tencent) quotes vendor.

Serves daily OHLCV for Shanghai, Shenzhen, Hong Kong and US listings from
Tencent's public quote endpoints, which need no key and are not rate-limited
the way Yahoo throttles a multi-cell sweep. Selected with
``data_vendors={"core_stock_apis": "tencent"}``.
"""

from .kline import get_closes, get_stock_data, load_ohlcv

__all__ = ["get_closes", "get_stock_data", "load_ohlcv"]
