"""Yahoo-style symbols as 腾讯自选股 (Tencent) codes.

    Yahoo symbol     Tencent code    market
    --------------   -------------   --------------------------------
    600519.SS        sh600519        Shanghai (Yahoo spells it .SS)
    000001.SZ        sz000001        Shenzhen
    0700.HK          hk00700         Hong Kong, padded to five digits
    ^HSI             hkHSI           Hang Seng index
    NVDA             usNVDA.OQ       US, exchange suffix resolved below

A US listing needs its exchange suffix: Tencent serves history for
``usNVDA.OQ`` but answers ``usNVDA`` with the first and last bar only. The
suffix differs by venue (``.OQ`` Nasdaq, ``.N`` NYSE, ``.AM`` NYSE American),
so it is read from the quote record rather than guessed — the record's code
field spells the whole thing (``NVDA.OQ``, ``SPY.AM``, ``BRK.B.N``).
"""

from __future__ import annotations

import logging
import re

import requests

from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError

logger = logging.getLogger(__name__)

QUOTE_HOST = "https://qt.gtimg.cn"

# Network timeout (seconds), consistent with the other vendors.
REQUEST_TIMEOUT = 15

# Tried in order when a US code could not be resolved from its quote record.
_US_FALLBACK_SUFFIXES = (".OQ", ".N", ".AM")

# Resolved US codes, so a sweep of the same ticker asks for the suffix once.
_US_CODE_CACHE: dict[str, str] = {}

_HK_CODE = re.compile(r"^(\d{1,5})\.HK$")
_SHANGHAI = re.compile(r"^(\d{6})\.SS$")
_SHENZHEN = re.compile(r"^(\d{6})\.SZ$")

# Tencent spells an index as a bare market code; the ones the benchmark map asks
# for (``^HSI`` for a .HK ticker) are listed, the rest fall through as unknown.
_INDEX_CODES = {
    "^HSI": "hkHSI",
    "^SSE": "sh000001",
    "^SZSE": "sz399001",
}

# A US ticker: letters first, then letters/digits, with the dot of a share class
# (BRK.B). Anything else is a symbol Tencent does not quote.
_US_TICKER = re.compile(r"^[A-Z][A-Z0-9]{0,7}(\.[A-Z]{1,2})?$")


def _snapshot_code(code: str) -> str | None:
    """The exchange-qualified code Tencent's quote record spells for ``code``.

    The record is GBK-encoded and ``~``-delimited; its third field is the code
    with its venue (``NVDA.OQ``). An unknown symbol comes back with an empty
    record, which is reported as None — no venue to try.
    """
    try:
        response = requests.get(QUOTE_HOST, params={"q": code}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = "gb18030"
        text = response.text
    except requests.RequestException as exc:
        raise VendorUnavailableError(
            f"Tencent quote lookup failed for {code}: {type(exc).__name__}: {exc}"
        ) from exc

    for line in text.strip().splitlines():
        if not line.startswith(f"v_{code}="):
            continue
        fields = line.split('"')[1].split("~")
        if len(fields) > 2 and fields[2]:
            return fields[2]
    return None


def _us_code(ticker: str) -> str:
    """``NVDA`` -> ``usNVDA.OQ``, resolving the venue once per ticker."""
    cached = _US_CODE_CACHE.get(ticker)
    if cached:
        return cached
    canonical = _snapshot_code(f"us{ticker}")
    code = f"us{canonical}" if canonical else f"us{ticker}"
    if canonical:
        _US_CODE_CACHE[ticker] = code
        logger.info("Resolved US ticker %r to Tencent code %r", ticker, code)
    return code


def to_tencent_code(symbol: str) -> str:
    """Map a Yahoo-style symbol to the Tencent code that quotes it.

    Raises NoMarketDataError for a symbol Tencent does not carry (a metal
    future, a forex pair, a crypto pair): this vendor answers for equities,
    ETFs and the indices above, and the router needs an absence it can report
    rather than a request it would make in vain.
    """
    s = (symbol or "").strip().upper()
    if not s:
        raise NoMarketDataError(symbol or "", symbol, "empty symbol")
    if s in _INDEX_CODES:
        return _INDEX_CODES[s]
    if sh := _SHANGHAI.match(s):
        return f"sh{sh.group(1)}"
    if sz := _SHENZHEN.match(s):
        return f"sz{sz.group(1)}"
    if hk := _HK_CODE.match(s):
        return f"hk{int(hk.group(1)):05d}"
    if not _US_TICKER.match(s):
        raise NoMarketDataError(symbol, s, "not a symbol Tencent quotes")
    return _us_code(s)


def candidate_codes(symbol: str) -> list[str]:
    """Tencent codes to try for a Yahoo-style symbol, most specific first.

    A US ticker whose venue could not be read keeps its plain code, which
    serves quotes but not history, so the venue suffixes are tried after it.
    """
    code = to_tencent_code(symbol)
    if not code.startswith("us") or "." in code[2:]:
        return [code]
    return [code, *(f"{code}{suffix}" for suffix in _US_FALLBACK_SUFFIXES)]
