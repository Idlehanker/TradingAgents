"""Daily OHLCV from 腾讯自选股 (Tencent), for A-share, HK and US listings.

Two public endpoints, no key, no auth:

* ``https://web.ifzq.gtimg.cn/appstock/app/fqkline/get`` — daily bars, forward
  adjusted (``qfq``), over a date range or a trailing count.
* ``https://qt.gtimg.cn`` — the quote record that spells a US listing's venue.

A row is ``[date, open, close, high, low, volume]`` — note the order: the close
is the third field, before the high and the low. Hong Kong rows carry a seventh
field of corporate-action notes, which is dropped. A-share volume is reported in
手 (lots of 100 shares) and converted to shares, so a bar reads the same
whichever vendor served it.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Annotated

import pandas as pd
import requests

from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.net import vendor_reachable
from tradingagents.dataflows.symbols import normalize_symbol
from tradingagents.dataflows.vendors.tencent.codes import candidate_codes
from tradingagents.dataflows.vendors.yahoo.common import price_text
from tradingagents.dataflows.vendors.yahoo.ohlcv import _assert_ohlcv_not_stale

logger = logging.getLogger(__name__)

KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
KLINE_HOST = "https://web.ifzq.gtimg.cn"

# Network timeout (seconds), consistent with the other vendors.
REQUEST_TIMEOUT = 20

# Bars asked for when a full history is needed (indicators, the verified
# snapshot): enough for a 200-day average over the longest holiday run.
DEFAULT_BARS = 1200

# Tencent reports Shanghai and Shenzhen volume in 手 (lots of 100 shares).
_LOT_MARKETS = ("sh", "sz")

_PRICE_COLUMNS = ("Open", "High", "Low", "Close")

# How long one fetch serves the rest of the process. A run reads the same window
# once per indicator plus once for the verified snapshot; without this, those are
# a dozen requests, each answering with a slightly different intraday bar — so the
# report would quote two closes for the same session, and the vendor sees a burst.
FETCH_TTL_SECONDS = 900

_FETCHED: dict[tuple, tuple[float, pd.DataFrame]] = {}

# Analysts issue their tool calls in parallel, so the first reads of one symbol
# race. One fetch at a time keeps them from each making their own.
_FETCH_LOCK = threading.Lock()


def _remember(key: tuple, frame: pd.DataFrame) -> pd.DataFrame:
    _FETCHED[key] = (time.monotonic(), frame)
    return frame


def _recall(key: tuple) -> pd.DataFrame | None:
    hit = _FETCHED.get(key)
    if hit is None or time.monotonic() - hit[0] > FETCH_TTL_SECONDS:
        return None
    return hit[1]


def _request(code: str, start: str = "", end: str = "", count: int = DEFAULT_BARS) -> list[list]:
    """Raw daily rows for a Tencent code, or [] when it has none in the window."""
    param = f"{code},day,{start},{end},{count},qfq"
    try:
        response = requests.get(KLINE_URL, params={"param": param}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # A failure in transit says nothing about the symbol.
        raise VendorUnavailableError(
            f"Tencent kline request failed for {code}: {type(exc).__name__}: {exc}"
        ) from exc

    data = payload.get("data")
    node = data.get(code) if isinstance(data, dict) else None
    if not isinstance(node, dict):
        return []
    # An adjusted series comes back as ``qfqday``; an unadjusted one as ``day``.
    rows = node.get("qfqday") or node.get("day") or []
    return [row for row in rows if isinstance(row, list) and len(row) >= 6]


def _frame(rows: list[list], code: str) -> pd.DataFrame:
    """Rows as a date-sorted OHLCV frame with numeric prices."""
    frame = pd.DataFrame(
        [row[:6] for row in rows],
        columns=["Date", "Open", "Close", "High", "Low", "Volume"],
    )
    frame = frame[["Date", "Open", "High", "Low", "Close", "Volume"]]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in (*_PRICE_COLUMNS, "Volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    # A row without a close is a session that has not settled; it is not a price.
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    if code[:2] in _LOT_MARKETS:
        frame["Volume"] = frame["Volume"] * 100
    return frame.reset_index(drop=True)


def _raise_for_empty(symbol: str, canonical: str, start: str | None, end: str | None) -> None:
    """Report an empty answer as an absence, or as an outage if it is one."""
    window = f" between {start} and {end}" if start or end else ""
    if not vendor_reachable(KLINE_HOST):
        raise VendorUnavailableError(
            f"Tencent is unreachable; no price rows were retrieved{window}"
        )
    raise NoMarketDataError(symbol, canonical, f"no Tencent price rows{window}")


def fetch_daily(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    count: int = DEFAULT_BARS,
) -> tuple[str, pd.DataFrame]:
    """Daily bars for a Yahoo-style symbol: the Tencent code that served them, and the frame.

    Raises VendorUnavailableError when Tencent could not be reached and
    NoMarketDataError when it answered with nothing — the same taxonomy the
    router reacts on, whatever the vendor.

    A fetch is remembered for ``FETCH_TTL_SECONDS``: one run reads the same
    window for every indicator and the snapshot, and the vendor's newest bar
    moves while the market is open.
    """
    canonical = normalize_symbol(symbol)
    key = (canonical, start_date or "", end_date or "", count)
    # An analyst issues its tool calls together, so the first reads of one symbol
    # race each other; without the lock each would fetch, and each fetch can return
    # a different intraday bar for the same session.
    with _FETCH_LOCK:
        remembered = _recall(key)
        if remembered is not None:
            return remembered.attrs["code"], remembered
        for code in candidate_codes(canonical):
            rows = _request(code, start_date or "", end_date or "", count)
            if rows:
                frame = _frame(rows, code)
                frame.attrs["code"] = code
                return code, _remember(key, frame)
    _raise_for_empty(symbol, canonical, start_date, end_date)
    raise AssertionError("unreachable")  # _raise_for_empty always raises


def get_stock_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """OHLCV over a date range, as the CSV the market analyst reads."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    # Read the window out of the run's history fetch rather than asking for it
    # again: two fetches of the same session return a close that differs by a
    # cent while the market is open, and a report may not quote both. A range
    # older than the history window is asked for directly instead.
    code, history = fetch_daily(symbol)
    data = history[(history["Date"] >= start) & (history["Date"] <= end)]
    if data.empty and start < history["Date"].min():
        code, window = fetch_daily(symbol, start_date, end_date)
        data = window[(window["Date"] >= start) & (window["Date"] <= end)]
    if data.empty:
        _raise_for_empty(symbol, normalize_symbol(symbol), start_date, end_date)

    # A frame whose newest bar predates the request by weeks is not this window.
    _assert_ohlcv_not_stale(data, end_date, symbol, code)

    out = data.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    for column in _PRICE_COLUMNS:
        out[column] = out[column].map(price_text, na_action="ignore")
    out["Volume"] = out["Volume"].round()
    if out["Volume"].notna().all():
        out["Volume"] = out["Volume"].astype("int64")

    label = code if code == symbol.strip().upper() else f"{code} (from {symbol})"
    header = f"# Stock data for {label} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(out)}\n\n"
    return header + out.set_index("Date").to_csv()


def load_ohlcv(symbol: str, as_of_date: str, fill_gaps: bool = True) -> pd.DataFrame:
    """OHLCV on or before ``as_of_date``, for indicators and the verified snapshot.

    The Tencent counterpart of Yahoo's loader: rows after ``as_of_date`` are
    dropped so nothing read from it can look ahead, and ``fill_gaps`` carries
    prices over a missing session the way that loader does.
    """
    canonical = normalize_symbol(symbol)
    code, data = fetch_daily(symbol)
    data = data[data["Date"] <= pd.Timestamp(as_of_date)]
    if data.empty:
        _raise_for_empty(symbol, canonical, None, as_of_date)

    data = data.copy()
    if fill_gaps:
        data[["Open", "High", "Low", "Close", "Volume"]] = (
            data[["Open", "High", "Low", "Close", "Volume"]].ffill().bfill()
        )
    else:
        data = data.dropna(subset=["Close"])

    # Reject a stale frame rather than feeding year-old prices to indicators.
    _assert_ohlcv_not_stale(data, as_of_date, symbol, code)
    return data.reset_index(drop=True)


def get_closes(symbol: str, start_date: str, end_date: str) -> pd.Series:
    """Daily closes from ``start_date`` up to, not including, ``end_date``."""
    _, data = fetch_daily(symbol, start_date, end_date)
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    data = data[(data["Date"] >= start) & (data["Date"] < end)]
    if data.empty:
        return pd.Series(dtype=float)
    return data.set_index("Date")["Close"]
