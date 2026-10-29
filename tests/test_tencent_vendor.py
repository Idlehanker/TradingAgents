"""The 腾讯自选股 (Tencent) quotes vendor.

Covers what is easy to get wrong and invisible in a happy-path run: the code a
symbol maps to, the row order Tencent sends (close before high/low), the
window a read covers, and the error taxonomy the router reacts on — an empty
answer is an absence, a failed request is an outage.
"""
import copy
from unittest import mock

import pandas as pd
import pytest
import requests

import tradingagents.dataflows.config as config_module
import tradingagents.default_config as default_config
from tradingagents.dataflows import quotes, router
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.vendors.tencent import codes, kline

pytestmark = pytest.mark.unit


# A Tencent daily row: [date, open, close, high, low, volume] — the close is the
# third field, before the high and the low.
_ROWS = [
    ["2026-06-01", "100.00", "102.00", "103.00", "99.00", "12345"],
    ["2026-06-02", "102.00", "104.00", "105.00", "101.00", "23456"],
    ["2026-06-05", "104.00", "103.00", "106.00", "102.00", "34567"],
]


def _payload(rows, key="qfqday"):
    return {"code": 0, "msg": "", "data": {"sh600519": {key: rows}}}


def _response(payload):
    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = payload
    return response


@pytest.fixture(autouse=True)
def _reset_config():
    config_module._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    # A fetched window is remembered for the process; each test starts with none.
    kline._FETCHED.clear()
    yield
    config_module._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    kline._FETCHED.clear()


def test_symbol_maps_to_tencent_code():
    assert codes.to_tencent_code("600519.SS") == "sh600519"
    assert codes.to_tencent_code("000001.SZ") == "sz000001"
    assert codes.to_tencent_code("0700.HK") == "hk00700"
    assert codes.to_tencent_code("^HSI") == "hkHSI"


def test_us_code_reads_venue_from_quote_record():
    # Tencent serves history for usNVDA.OQ and only the ends for usNVDA, so the
    # venue is read from the quote record rather than guessed.
    with mock.patch.object(codes, "_snapshot_code", return_value="SPY.AM"):
        assert codes.to_tencent_code("SPY") == "usSPY.AM"
        assert codes.candidate_codes("SPY") == ["usSPY.AM"]


def test_us_code_falls_back_to_venues_when_unresolved():
    with mock.patch.object(codes, "_snapshot_code", return_value=None):
        assert codes.candidate_codes("NVDA") == ["usNVDA", "usNVDA.OQ", "usNVDA.N", "usNVDA.AM"]


def test_symbol_tencent_does_not_quote_is_no_data():
    # A metal future or a crypto pair: reported as an absence, not requested.
    with pytest.raises(NoMarketDataError):
        codes.to_tencent_code("GC=F")


def test_get_stock_data_renders_ohlcv_csv():
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload(_ROWS))):
        out = kline.get_stock_data("600519.SS", "2026-06-01", "2026-06-06")

    assert "Stock data for sh600519" in out
    assert "# Total records: 3" in out
    assert "Date,Open,High,Low,Close,Volume" in out
    # Row order: the third field is the close, not the high.
    assert "2026-06-01,100.00,103.00,99.00,102.00,1234" in out
    # A-share volume is reported in 手 (lots of 100 shares) and read in shares.
    assert "1234500" in out


def test_get_closes_stops_before_end_date():
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload(_ROWS))):
        closes = kline.get_closes("600519.SS", "2026-06-01", "2026-06-05")

    assert list(closes.index.strftime("%Y-%m-%d")) == ["2026-06-01", "2026-06-02"]
    assert list(closes.values) == [102.0, 104.0]


def test_load_ohlcv_excludes_rows_after_as_of_date():
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload(_ROWS))):
        data = kline.load_ohlcv("600519.SS", "2026-06-02")

    assert data["Date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-06-01", "2026-06-02"]
    assert data["Close"].tolist() == [102.0, 104.0]


def test_one_fetch_serves_the_rest_of_the_run():
    """A run reads the same window for every indicator plus the snapshot; the
    vendor's newest bar moves intraday, so a second fetch would contradict the first."""
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload(_ROWS))) as get:
        first = kline.load_ohlcv("600519.SS", "2026-06-02")
        second = kline.load_ohlcv("600519.SS", "2026-06-02")

    assert get.call_count == 1
    assert first["Close"].tolist() == second["Close"].tolist()


def test_the_csv_and_the_snapshot_quote_one_close():
    """Both read the session out of the run's single fetch: a report that quotes
    the CSV's close in one paragraph and the snapshot's in the next is not
    reporting one market."""
    later = _payload([[*row] for row in _ROWS])
    later["data"]["sh600519"]["qfqday"][-1][2] = "999.00"   # a second print moved
    with mock.patch.object(kline.requests, "get",
                           side_effect=[_response(_payload(_ROWS)), _response(later)]) as get:
        csv = kline.get_stock_data("600519.SS", "2026-06-01", "2026-06-06")
        data = kline.load_ohlcv("600519.SS", "2026-06-06")

    assert get.call_count == 1
    assert "103.00" in csv                  # the first fetch's close, not 999.00
    assert data["Close"].tolist()[-1] == 103.0


def test_concurrent_first_reads_make_one_fetch():
    """An analyst issues its tool calls together; the parallel reads of one
    symbol must not each fetch, or the report quotes several closes for it."""
    import threading
    import time

    calls = []

    def slow_get(*args, **kwargs):
        calls.append(1)
        time.sleep(0.05)          # long enough for the other thread to arrive too
        return _response(_payload(_ROWS))

    results = []

    def read():
        results.append(kline.load_ohlcv("600519.SS", "2026-06-02"))

    with mock.patch.object(kline.requests, "get", side_effect=slow_get):
        threads = [threading.Thread(target=read) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(calls) == 1
    assert all(frame["Close"].tolist() == results[0]["Close"].tolist() for frame in results)


def test_a_window_older_than_the_history_is_asked_for_directly():
    """A history fetch reaches back a few years; a backtest window before it is
    not silently served as empty."""
    old = _payload([["2019-01-02", "10.00", "11.00", "12.00", "9.00", "100"]])
    with mock.patch.object(kline.requests, "get",
                           side_effect=[_response(_payload(_ROWS)), _response(old)]) as get:
        out = kline.get_stock_data("600519.SS", "2019-01-01", "2019-01-05")

    assert get.call_count == 2
    assert "2019-01-02" in out


def test_a_remembered_fetch_expires(monkeypatch):
    """A quote vendor is not a snapshot service: the cache must not outlive a run."""
    clock = [1000.0]
    monkeypatch.setattr(kline.time, "monotonic", lambda: clock[0])
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload(_ROWS))) as get:
        kline.load_ohlcv("600519.SS", "2026-06-02")
        clock[0] += kline.FETCH_TTL_SECONDS + 1
        kline.load_ohlcv("600519.SS", "2026-06-02")

    assert get.call_count == 2


def test_empty_answer_is_reported_as_absence():
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload([]))), \
            mock.patch.object(kline, "vendor_reachable", return_value=True), \
            pytest.raises(NoMarketDataError):
        kline.get_stock_data("600519.SS", "2026-06-01", "2026-06-06")


def test_failed_request_is_reported_as_outage():
    boom = requests.ConnectionError("boom")
    with mock.patch.object(kline.requests, "get", side_effect=boom), \
            pytest.raises(VendorUnavailableError):
        kline.get_stock_data("600519.SS", "2026-06-01", "2026-06-06")


def test_unreachable_host_is_an_outage_not_an_absence():
    # An empty answer from a host that cannot be reached says nothing about the
    # symbol, so it must not be reported as "no data for this ticker".
    with mock.patch.object(kline.requests, "get", return_value=_response(_payload([]))), \
            mock.patch.object(kline, "vendor_reachable", return_value=False), \
            pytest.raises(VendorUnavailableError):
        kline.get_stock_data("600519.SS", "2026-06-01", "2026-06-06")


def test_quotes_follow_the_configured_vendor():
    frame = pd.DataFrame({"Date": [pd.Timestamp("2026-06-01")], "Close": [1.0]})
    tencent = mock.Mock(return_value=frame)
    yahoo = mock.Mock(return_value=frame)
    with mock.patch.object(quotes, "tencent_ohlcv", tencent), \
            mock.patch.object(quotes, "yahoo_ohlcv", yahoo):
        set_config({"data_vendors": {"core_stock_apis": "tencent"}})
        quotes.load_ohlcv("NVDA", "2026-06-01")
        tencent.assert_called_once()
        yahoo.assert_not_called()

        set_config({"data_vendors": {"core_stock_apis": "yfinance"}})
        quotes.load_ohlcv("NVDA", "2026-06-01")
        yahoo.assert_called_once()


def test_vendor_without_a_price_read_falls_back_to_yahoo():
    # alpha_vantage serves quotes but no OHLCV frame; the price paths keep
    # reading Yahoo rather than failing the run.
    yahoo = mock.Mock(return_value=pd.DataFrame())
    with mock.patch.object(quotes, "yahoo_ohlcv", yahoo):
        set_config({"data_vendors": {"core_stock_apis": "alpha_vantage"}})
        quotes.load_ohlcv("NVDA", "2026-06-01")
    yahoo.assert_called_once()


def test_tencent_is_registered_for_get_stock_data():
    set_config({"data_vendors": {"core_stock_apis": "tencent"}})
    with mock.patch.dict(
        router.VENDOR_METHODS["get_stock_data"], {"tencent": lambda *a: "TENCENT"}
    ):
        assert router.route_to_vendor("get_stock_data", "NVDA", "2026-06-01", "2026-06-05") == "TENCENT"
