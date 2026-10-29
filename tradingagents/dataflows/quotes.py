"""Where a price read comes from: the configured quotes chain.

Every price path asks here — the CSV the market analyst reads, the technical
indicators, the verified snapshot, and the closes a decision is settled against
— so choosing a quotes vendor once (``core_stock_apis``) switches all of them.
Routing them separately would leave a run pricing from one source and settling
against another.

The category is a chain, not a single name: each vendor is tried in the order
configured, and one that fails in transit — or does not quote the symbol at all
— hands the read to the next. The default ``tencent,yfinance`` reads 腾讯自选股
first (no key, and reachable where Yahoo's API is not) and keeps Yahoo as the
fallback for the symbols Tencent does not quote.
"""

from __future__ import annotations

import logging

import pandas as pd

from tradingagents.dataflows.errors import (
    NoMarketDataError,
    VendorError,
    VendorUnavailableError,
)
from tradingagents.dataflows.vendors.tencent import (
    get_closes as tencent_closes,
    load_ohlcv as tencent_ohlcv,
)
from tradingagents.dataflows.vendors.yahoo.ohlcv import load_ohlcv as yahoo_ohlcv

logger = logging.getLogger(__name__)

# Vendors that can serve a price read, in the order a chain naming none of them
# falls back to. A vendor without a price implementation (alpha_vantage serves
# quotes but not an OHLCV frame) cannot serve these paths at all.
_PRICE_VENDORS = ("tencent", "yfinance")
_NO_VENDOR_NAMED = ("yfinance",)


def _price_chain() -> list[str]:
    """The configured quotes chain, keeping only the vendors that read prices."""
    # Imported here, not at module scope: the router imports every vendor, so a
    # top-level import would circle back into a half-initialized module.
    from tradingagents.dataflows.router import get_vendor

    chain = [v.strip() for v in get_vendor("core_stock_apis", "get_stock_data").split(",")]
    vendors = [vendor for vendor in chain if vendor in _PRICE_VENDORS]
    return vendors or list(_NO_VENDOR_NAMED)


def _no_vendor_answered(symbol: str, unavailable: VendorError | None, last_error: VendorError | None):
    """The error to raise once every vendor in the chain has been tried.

    A vendor that throttled or failed in transit never said whether it has the
    symbol, so its failure outranks another vendor's "no data": reporting the
    symbol as absent would be a claim nobody checked.
    """
    return unavailable or last_error or NoMarketDataError(symbol, symbol, "no price vendor answered")


def load_ohlcv(symbol: str, as_of_date: str, fill_gaps: bool = True) -> pd.DataFrame:
    """OHLCV on or before ``as_of_date``, from the first quotes vendor that answers."""
    readers = {"tencent": tencent_ohlcv, "yfinance": yahoo_ohlcv}
    unavailable: VendorError | None = None
    last_error: VendorError | None = None

    for vendor in _price_chain():
        try:
            return readers[vendor](symbol, as_of_date, fill_gaps=fill_gaps)
        except NoMarketDataError as exc:
            logger.warning("Quotes vendor %r has no OHLCV for %s: %s; trying next vendor.", vendor, symbol, exc)
            last_error = exc
        except VendorUnavailableError as exc:
            logger.warning("Quotes vendor %r unavailable for %s: %s; trying next vendor.", vendor, symbol, exc)
            unavailable = last_error = exc

    raise _no_vendor_answered(symbol, unavailable, last_error)


def get_closes(symbol: str, start_date: str, end_date: str) -> pd.Series:
    """Daily closes from ``start_date`` up to, not including, ``end_date``."""
    # Imported here for the same reason as above: this module is imported by
    # yahoo.market, which the router imports.
    from tradingagents.dataflows.vendors.yahoo.market import get_closes as yahoo_closes

    readers = {"tencent": tencent_closes, "yfinance": yahoo_closes}
    unavailable: VendorError | None = None
    last_error: VendorError | None = None

    for vendor in _price_chain():
        try:
            return readers[vendor](symbol, start_date, end_date)
        except NoMarketDataError as exc:
            logger.warning("Quotes vendor %r has no closes for %s: %s; trying next vendor.", vendor, symbol, exc)
            last_error = exc
        except VendorUnavailableError as exc:
            logger.warning("Quotes vendor %r unavailable for %s: %s; trying next vendor.", vendor, symbol, exc)
            unavailable = last_error = exc

    raise _no_vendor_answered(symbol, unavailable, last_error)
