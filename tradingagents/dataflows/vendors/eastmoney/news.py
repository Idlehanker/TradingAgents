"""东方财富 news vendor: Chinese-language coverage for A-share, HK and US listings.

Two public JSON endpoints, no key and no auth:

* ``getListInfo`` — a listing's own news tab, keyed by Eastmoney's ``secid``
  (``105.NVDA`` Nasdaq, ``106.JNJ`` NYSE, ``107.SPY`` NYSE American,
  ``116.00700`` HK, ``1.600519`` Shanghai, ``0.000001`` Shenzhen).
* ``getNewsByColumns`` — the market-wide 财经导读 column, for macro/global news.

Both answer newest-first with no date filter, paging by ``pageIndex`` only, so a
window is served by walking back a bounded number of pages. A window the pages
never reach is reported as a coverage gap rather than an absence — the same rule
Yahoo news follows, and the reason a backtest dated months ago is told the feed
cannot see that far instead of being told there was no news.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

import requests

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.date_window import coverage_gap, in_window
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.symbols import normalize_symbol

logger = logging.getLogger(__name__)

LIST_URL = "https://np-listapi.eastmoney.com/comm/web/getListInfo"
COLUMN_URL = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"

# Network timeout (seconds), consistent with the other vendors.
REQUEST_TIMEOUT = 20

# Items per page, and how far back a walk may page. A listing posts a few items
# a day, so eight pages reach weeks back — enough for a recent window, bounded so
# a window it cannot reach is reported instead of scanned forever.
PAGE_SIZE = 100
MAX_PAGES = 8

# The 财经导读 column: the market-wide feed behind get_global_news.
MARKET_COLUMN = "345"

# Eastmoney stamps its items in Beijing time; the window rules work in UTC.
_CST = ZoneInfo("Asia/Shanghai")

_HK_CODE = re.compile(r"^(\d{1,5})\.HK$")
_SHANGHAI = re.compile(r"^(\d{6})\.SS$")   # normalize_symbol spells .SH as .SS
_SHENZHEN = re.compile(r"^(\d{6})\.SZ$")
_US_TICKER = re.compile(r"^[A-Z][A-Z0-9]{0,7}(\.[A-Z]{1,2})?$")

# Eastmoney's market numbers for US listings, tried in order: Nasdaq, NYSE,
# NYSE American. A listing answers on exactly one of them (105.JNJ is empty,
# 106.JNJ is Johnson & Johnson's own feed), and the wrong one can answer with a
# generic market column, so the first non-empty feed is the listing's own.
_US_MARKETS = ("105", "106", "107")

# Resolved secids, so a sweep of the same ticker probes the markets once.
_SECID_CACHE: dict[str, str] = {}


def candidate_secids(symbol: str) -> list[str]:
    """Eastmoney secids a Yahoo-style symbol may answer on, in try order."""
    s = (symbol or "").strip().upper()
    if sh := _SHANGHAI.match(s):
        return [f"1.{sh.group(1)}"]
    if sz := _SHENZHEN.match(s):
        return [f"0.{sz.group(1)}"]
    if hk := _HK_CODE.match(s):
        return [f"116.{int(hk.group(1)):05d}"]
    if _US_TICKER.match(s):
        return [f"{market}.{s}" for market in _US_MARKETS]
    return []


def _get(url: str, params: dict) -> list[dict]:
    """Raw items from an Eastmoney list endpoint."""
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # A failure in transit says nothing about the symbol.
        raise VendorUnavailableError(
            f"Eastmoney request failed: {type(exc).__name__}: {exc}"
        ) from exc
    # The endpoints spell success as 1 — as a number on one, as a string on the
    # other, so the comparison is textual.
    if str(payload.get("code")) != "1":
        raise VendorUnavailableError(
            f"Eastmoney answered {payload.get('code')}: {payload.get('message') or payload.get('msg')}"
        )
    items = (payload.get("data") or {}).get("list")
    return [item for item in items or [] if isinstance(item, dict)]


def _fetch_list(secid: str, page: int, page_size: int = PAGE_SIZE) -> list[dict]:
    """One page of a listing's own news."""
    return _get(LIST_URL, {
        "client": "web",
        "type": "1",
        "pageSize": str(page_size),
        "pageIndex": str(page),
        "mTypeAndCode": secid,
    })


def _fetch_column(page: int, page_size: int = PAGE_SIZE) -> list[dict]:
    """One page of the market-wide column.

    ``req_trace`` is a per-request correlation id the endpoint insists on: it
    answers "Required String parameter 'req_trace' is not present" without one.
    """
    return _get(COLUMN_URL, {
        "client": "web",
        "biz": "web_news_col",
        "column": MARKET_COLUMN,
        "pageSize": str(page_size),
        "pageIndex": str(page),
        "sortEnd": "",
        "sort": "time",
        "req_trace": str(uuid.uuid4()),
    })


def _parse_time(value) -> datetime | None:
    """An Eastmoney timestamp in Beijing time, or None when unreadable."""
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CST)
    except (TypeError, ValueError):
        return None


def _article(item: dict) -> dict:
    """An item as the field set the report renders, whichever endpoint sent it."""
    published = item.get("Art_ShowTime") or item.get("showTime")
    return {
        "title": (item.get("Art_Title") or item.get("title") or "No title").strip(),
        "summary": (item.get("summary") or "").strip(),
        "publisher": (item.get("mediaName") or "东方财富").strip(),
        "link": item.get("Art_Url") or item.get("url") or item.get("uniqueUrl") or "",
        "pub_date": _parse_time(published),
    }


def _format_articles(articles: list[dict]) -> str:
    out = ""
    for data in articles:
        out += f"### {data['title']} (source: {data['publisher']})\n"
        if data["summary"]:
            out += f"{data['summary']}\n"
        if data["pub_date"] is not None:
            out += f"Published: {data['pub_date']:%Y-%m-%d %H:%M} CST\n"
        if data["link"]:
            out += f"Link: {data['link']}\n"
        out += "\n"
    return out


def _collect(fetch_page, start_dt: datetime, end_dt: datetime, limit: int):
    """Articles inside the window, walking back until the window is reached.

    Returns the articles and the oldest timestamp seen, which is what bounds how
    far back the feed was observed. Walking stops on the limit, on the window's
    start, or on MAX_PAGES, whichever comes first.
    """
    found: list[dict] = []
    seen: set[str] = set()
    oldest: datetime | None = None

    for page in range(1, MAX_PAGES + 1):
        items = fetch_page(page)
        if not items:
            break
        for item in items:
            data = _article(item)
            if data["pub_date"] is not None:
                oldest = data["pub_date"] if oldest is None else min(oldest, data["pub_date"])
            if not in_window(data["pub_date"], start_dt, end_dt):
                continue
            if not data["title"] or data["title"] in seen:
                continue
            seen.add(data["title"])
            found.append(data)
        if len(found) >= limit:
            break
        if oldest is not None and oldest <= start_dt.astimezone(_CST):
            break   # the walk has reached the window's first day: nothing older helps
    return found[:limit], oldest


def resolve_secid(symbol: str) -> str:
    """The secid whose feed is this listing's own news."""
    cached = _SECID_CACHE.get(symbol)
    if cached:
        return cached
    candidates = candidate_secids(symbol)
    if not candidates:
        raise NoMarketDataError(symbol, symbol, "not a listing Eastmoney serves news for")
    for secid in candidates:
        if _fetch_list(secid, 1, page_size=5):
            _SECID_CACHE[symbol] = secid
            return secid
    raise NoMarketDataError(symbol, symbol, "no Eastmoney news items for this listing")


def get_news(
    ticker: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """News about ``ticker`` published in the window, from 东方财富."""
    limit = get_config()["news_article_limit"]
    canonical = normalize_symbol(ticker)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    resolved = "" if canonical == ticker else f" (resolved to {canonical})"
    subject = f"news for {ticker}{resolved}"

    secid = resolve_secid(canonical)
    articles, oldest = _collect(lambda page: _fetch_list(secid, page), start_dt, end_dt, limit)

    if articles:
        heading = f"## {ticker}{resolved} News, from {start_date} to {end_date}:\n\n"
        return heading + _format_articles(articles)

    gap = coverage_gap([oldest], start_date, end_date, "Eastmoney news", subject)
    return gap or f"No news found for {ticker}{resolved} between {start_date} and {end_date}"


def get_global_news(
    as_of_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int | None, "Days to look back; omit to use the configured default"] = None,
    limit: Annotated[int | None, "Max articles to return; omit to use the configured default"] = None,
) -> str:
    """Market-wide Chinese financial news for the trailing window, from 东方财富."""
    config = get_config()
    if look_back_days is None:
        look_back_days = config["global_news_lookback_days"]
    if limit is None:
        limit = config["global_news_article_limit"]

    curr_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
    start_dt = curr_dt - timedelta(days=look_back_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    articles, oldest = _collect(_fetch_column, start_dt, curr_dt, limit)

    if articles:
        heading = f"## Global Market News, from {start_date} to {as_of_date}:\n\n"
        return heading + _format_articles(articles)

    gap = coverage_gap([oldest], start_date, as_of_date, "Eastmoney global news", "market news")
    return gap or f"No global news found between {start_date} and {as_of_date}"
