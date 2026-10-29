"""The 东方财富 (Eastmoney) news vendor.

Covers what a run depends on and what a mistake would break silently: which
secid a symbol maps to, that only in-window articles are served (a backtest must
not read later news), that a window the feed cannot see is reported as a gap
rather than as an absence, and the error taxonomy the router reacts on.
"""
import copy
from unittest import mock

import pytest
import requests

import tradingagents.dataflows.config as config_module
import tradingagents.default_config as default_config
from tradingagents.dataflows import router
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.dataflows.vendors.eastmoney import news

pytestmark = pytest.mark.unit


def _item(title, published, summary="", media="财联社"):
    return {
        "Art_Title": title,
        "Art_ShowTime": published,
        "summary": summary,
        "mediaName": media,
        "Art_Url": f"http://finance.eastmoney.com/a/{abs(hash(title))}.html",
    }


ITEMS = [
    _item("英伟达发布新一代芯片", "2026-06-01 10:00:00", "营收指引上调"),
    _item("英伟达与云厂商扩大合作", "2026-06-02 09:30:00"),
    _item("未来才发生的一条新闻", "2026-06-20 08:00:00"),
]


@pytest.fixture(autouse=True)
def _reset_state():
    config_module._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    news._SECID_CACHE.clear()
    yield
    config_module._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    news._SECID_CACHE.clear()


def _fake_get(pages, captured=None):
    """A fake ``requests.get`` serving ``pages(page)`` as one endpoint's list."""
    def fake(url, params=None, timeout=None):
        if captured is not None:
            captured.append((url, dict(params or {})))
        response = mock.Mock()
        response.json.return_value = {
            "code": 1, "message": "success",
            "data": {"list": pages(int((params or {}).get("pageIndex", 1)))},
        }
        return response
    return fake


def test_symbol_maps_to_secid():
    assert news.candidate_secids("600519.SS") == ["1.600519"]
    assert news.candidate_secids("000001.SZ") == ["0.000001"]
    assert news.candidate_secids("0700.HK") == ["116.00700"]
    # A US listing answers on exactly one venue, so all three are tried.
    assert news.candidate_secids("NVDA") == ["105.NVDA", "106.NVDA", "107.NVDA"]


def test_unserved_symbol_is_no_data():
    with pytest.raises(NoMarketDataError):
        news.resolve_secid("GC=F")


def test_only_articles_inside_the_window_are_served():
    with mock.patch.object(news.requests, "get", side_effect=_fake_get(
        lambda page: ITEMS if page == 1 else []
    )):
        out = news.get_news("NVDA", "2026-06-01", "2026-06-05")

    assert "英伟达发布新一代芯片" in out
    assert "英伟达与云厂商扩大合作" in out
    # Look-ahead: the June 20 article is after the run's window.
    assert "未来才发生的一条新闻" not in out
    assert "Published: 2026-06-01 10:00 CST" in out


def test_window_the_feed_cannot_reach_is_a_gap_not_an_absence():
    # Every item is newer than the window: the walk cannot prove there was no
    # news back then, so the report must not claim there was none.
    with mock.patch.object(news.requests, "get", side_effect=_fake_get(
        lambda page: ITEMS if page == 1 else []
    )):
        out = news.get_news("NVDA", "2026-01-05", "2026-01-09")

    assert "unavailable" in out
    assert "not an absence" in out


def test_resolve_secid_uses_the_venue_that_answers():
    # 105 (Nasdaq) has nothing for a NYSE listing; 106 does.
    def pages_for(secid):
        def page(_):
            return ITEMS[:1] if secid == "106.JNJ" else []
        return page

    def fake(url, params=None, timeout=None):
        response = mock.Mock()
        response.json.return_value = {
            "code": 1,
            "data": {"list": pages_for(params["mTypeAndCode"])(1)},
        }
        return response

    with mock.patch.object(news.requests, "get", side_effect=fake):
        assert news.resolve_secid("JNJ") == "106.JNJ"


def test_empty_feed_for_every_venue_is_no_data():
    with mock.patch.object(news.requests, "get", side_effect=_fake_get(lambda page: [])), \
            pytest.raises(NoMarketDataError):
        news.get_news("NVDA", "2026-06-01", "2026-06-05")


def test_failed_request_is_an_outage():
    boom = requests.ConnectionError("boom")
    with mock.patch.object(news.requests, "get", side_effect=boom), \
            pytest.raises(VendorUnavailableError):
        news.get_news("NVDA", "2026-06-01", "2026-06-05")


def test_error_code_from_the_endpoint_is_an_outage():
    response = mock.Mock()
    response.json.return_value = {"code": 0, "message": "Required String parameter 'req_trace'"}
    with mock.patch.object(news.requests, "get", return_value=response), \
            pytest.raises(VendorUnavailableError):
        news.get_global_news("2026-06-05")


def test_global_news_carries_the_correlation_id_the_endpoint_requires():
    column_items = [{
        "title": "央行开展逆回购操作", "summary": "流动性保持合理充裕",
        "mediaName": "财联社", "showTime": "2026-06-03 09:00:00",
        "url": "http://finance.eastmoney.com/news/1.html",
    }]
    captured: list[tuple[str, dict]] = []
    with mock.patch.object(news.requests, "get", side_effect=_fake_get(
        lambda page: column_items if page == 1 else [], captured
    )):
        out = news.get_global_news("2026-06-05", 7, 5)

    assert "央行开展逆回购操作" in out
    assert "Global Market News" in out
    # The column endpoint answers "Required String parameter 'req_trace'" without it.
    assert captured and captured[0][1]["req_trace"]


def test_eastmoney_is_registered_for_news():
    set_config({"data_vendors": {"news_data": "eastmoney"}})
    with mock.patch.dict(
        router.VENDOR_METHODS["get_news"], {"eastmoney": lambda *a: "EM_NEWS"}
    ), mock.patch.dict(
        router.VENDOR_METHODS["get_global_news"], {"eastmoney": lambda *a: "EM_MACRO"}
    ):
        assert router.route_to_vendor("get_news", "NVDA", "2026-06-01", "2026-06-05") == "EM_NEWS"
        assert router.route_to_vendor("get_global_news", "2026-06-05") == "EM_MACRO"
