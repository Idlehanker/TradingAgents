"""Where a price read comes from: the configured quotes vendor.

Every price path asks here — the CSV the market analyst reads, the technical
indicators, the verified snapshot, and the closes a decision is settled against
— so choosing a quotes vendor once (``core_stock_apis``) switches all of them.
Routing them separately would leave a run pricing from one source and settling
against another.

Only vendors that implement a price read are honored: a chain naming one that
does not (alpha_vantage serves quotes but not an OHLCV frame) falls through to
Yahoo, which every path was reading before.
"""

from __future__ import annotations

import pandas as pd

from tradingagents.dataflows.vendors.tencent import (
    get_closes as tencent_closes,
    load_ohlcv as tencent_ohlcv,
)
from tradingagents.dataflows.vendors.yahoo.ohlcv import load_ohlcv as yahoo_ohlcv

# Vendors that can serve a price read, in the order a mixed chain is tried.
_PRICE_VENDORS = ("tencent", "yfinance")


def _quotes_vendor() -> str:
    """The configured quotes vendor that has a price implementation."""
    # Imported here, not at module scope: the router imports every vendor, so a
    # top-level import would circle back into a half-initialized module.
    from tradingagents.dataflows.router import get_vendor

    chain = [v.strip() for v in get_vendor("core_stock_apis", "get_stock_data").split(",")]
    for vendor in chain:
        if vendor in _PRICE_VENDORS:
            return vendor
    return "yfinance"


def load_ohlcv(symbol: str, as_of_date: str, fill_gaps: bool = True) -> pd.DataFrame:
    """OHLCV on or before ``as_of_date``, from the configured quotes vendor."""
    if _quotes_vendor() == "tencent":
        return tencent_ohlcv(symbol, as_of_date, fill_gaps=fill_gaps)
    return yahoo_ohlcv(symbol, as_of_date, fill_gaps=fill_gaps)


def get_closes(symbol: str, start_date: str, end_date: str) -> pd.Series:
    """Daily closes from ``start_date`` up to, not including, ``end_date``."""
    if _quotes_vendor() == "tencent":
        return tencent_closes(symbol, start_date, end_date)
    # Imported here for the same reason as above: this module is imported by
    # yahoo.market, which the router imports.
    from tradingagents.dataflows.vendors.yahoo.market import get_closes as yahoo_closes

    return yahoo_closes(symbol, start_date, end_date)
