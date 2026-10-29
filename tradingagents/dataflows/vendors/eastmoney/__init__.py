"""东方财富 (Eastmoney) news vendor.

Serves per-ticker and market-wide Chinese-language news for Shanghai, Shenzhen,
Hong Kong and US listings from Eastmoney's public JSON endpoints — no key, and
reachable where Yahoo Finance is throttled. Selected with
``data_vendors={"news_data": "eastmoney"}``.
"""

from .news import get_global_news, get_news

__all__ = ["get_global_news", "get_news"]
