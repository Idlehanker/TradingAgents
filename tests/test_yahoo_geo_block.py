"""A geographically blocked Yahoo is reported as blocked, not as a rate limit.

yfinance raises ``YFRateLimitError`` whenever it cannot get a cookie or crumb,
which is also what happens where Yahoo answers with its HTTP 403 "services are
no longer accessible" page. That page never turns into data, so sleeping 2+4+8
seconds per tool call and then telling the agent "rate limited, try later" both
wastes the run and sends the reader after the wrong cause.
"""

from unittest import mock

import pytest
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from tradingagents.dataflows import router
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.errors import VendorUnavailableError
from tradingagents.dataflows.vendors.yahoo import common, ohlcv

DAY = "2026-06-01"


@pytest.fixture(autouse=True)
def reset_probe(monkeypatch, tmp_path):
    """The probe result is cached per process; each test starts unprobed."""
    monkeypatch.setattr(common, "_geo_blocked", None)
    monkeypatch.setattr(common.time, "sleep", mock.Mock())
    set_config({"data_cache_dir": str(tmp_path)})


def _rate_limited(*args, **kwargs):
    raise YFRateLimitError()


def _page(status, text):
    response = mock.Mock()
    response.status_code = status
    response.text = text
    return response


def _blocked_page():
    return _page(403, '<html lang="zh"><p>As of November 1st, 2021 Yahoo\'s suite of services '
                       'will no longer be accessible from mainland China.</p></html>')


@pytest.mark.unit
def test_a_blocked_network_is_not_retried(monkeypatch):
    monkeypatch.setattr(yf.Ticker, "history", _rate_limited)
    probe = mock.Mock(return_value=_blocked_page())
    monkeypatch.setattr("curl_cffi.requests.get", probe)

    with pytest.raises(VendorUnavailableError, match="403"):
        ohlcv.load_ohlcv("SPY", DAY)

    probe.assert_called_once()
    common.time.sleep.assert_not_called()


@pytest.mark.unit
def test_the_message_names_the_cause_and_the_way_out(monkeypatch):
    monkeypatch.setattr(yf.Ticker, "history", _rate_limited)
    monkeypatch.setattr("curl_cffi.requests.get", lambda *a, **k: _blocked_page())

    with pytest.raises(VendorUnavailableError) as caught:
        ohlcv.load_ohlcv("SPY", DAY)

    message = str(caught.value)
    assert "403" in message
    assert "tencent" in message          # the actionable way out
    assert "proxy" in message


@pytest.mark.unit
def test_the_agent_is_told_the_vendor_is_the_problem(monkeypatch):
    """The sentinel must not read "this symbol has no data"."""
    monkeypatch.setattr(yf.Ticker, "history", _rate_limited)
    monkeypatch.setattr("curl_cffi.requests.get", lambda *a, **k: _blocked_page())
    set_config({"data_vendors": {"core_stock_apis": "yfinance"}})

    out = router.route_to_vendor("get_stock_data", "SPY", "2026-05-01", DAY)

    assert out.startswith("DATA_UNAVAILABLE"), out
    assert "403" in out
    assert "delisted" not in out


@pytest.mark.unit
def test_a_second_call_short_circuits_once_the_block_is_known(monkeypatch):
    calls = mock.Mock(side_effect=_rate_limited)
    monkeypatch.setattr(yf.Ticker, "history", calls)
    probe = mock.Mock(return_value=_blocked_page())
    monkeypatch.setattr("curl_cffi.requests.get", probe)

    for _ in range(2):
        with pytest.raises(VendorUnavailableError):
            ohlcv.load_ohlcv("SPY", DAY)

    assert calls.call_count == 1     # the second call does not ask again
    probe.assert_called_once()       # and does not re-probe


@pytest.mark.unit
def test_a_genuine_rate_limit_is_still_retried(monkeypatch):
    """Only the 403 page is a block: a 429 from a reachable Yahoo keeps its retries."""
    monkeypatch.setattr(yf.Ticker, "history", _rate_limited)
    monkeypatch.setattr("curl_cffi.requests.get", lambda *a, **k: _page(200, "abc123"))

    with pytest.raises(VendorUnavailableError, match="rate limited"):
        ohlcv.load_ohlcv("SPY", DAY)

    assert common.time.sleep.call_count == 3


@pytest.mark.unit
def test_a_failed_probe_does_not_claim_a_block(monkeypatch):
    """An unreachable probe is "unknown"; the rate limit keeps its own retries."""
    monkeypatch.setattr(yf.Ticker, "history", _rate_limited)

    def no_probe(*args, **kwargs):
        raise OSError("probe failed")

    monkeypatch.setattr("curl_cffi.requests.get", no_probe)

    with pytest.raises(VendorUnavailableError, match="rate limited"):
        ohlcv.load_ohlcv("SPY", DAY)
    assert common.yahoo_geo_blocked() is False


@pytest.mark.unit
def test_an_empty_answer_from_a_blocked_network_is_an_outage(monkeypatch):
    """A blocked page is an HTTP answer, so a reachability probe would call it data."""
    monkeypatch.setattr(common, "_geo_blocked", True)
    monkeypatch.setattr(common, "vendor_reachable", lambda url: True)

    with pytest.raises(VendorUnavailableError, match="403"):
        common.raise_for_empty("SPY", "SPY", "price rows")
