"""The quotes chain falls back, and the default chain leads with Tencent.

A run may not be priced by a vendor that cannot answer while another configured
one can: ``core_stock_apis`` is an ordered chain, and every price path — the
analyst's CSV, the indicators, the verified snapshot, settlement — reads through
it here, so one place falling back is what keeps a whole run working.
"""

from unittest import mock

import pandas as pd
import pytest

from tradingagents.dataflows import quotes
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.errors import NoMarketDataError, VendorUnavailableError
from tradingagents.default_config import DEFAULT_CONFIG

FRAME = pd.DataFrame({"Date": [pd.Timestamp("2026-06-01")], "Close": [1.0]})


@pytest.fixture
def readers(monkeypatch):
    """Both price readers, patched, in the order the chain may call them."""
    tencent = mock.Mock(return_value=FRAME)
    yahoo = mock.Mock(return_value=FRAME)
    monkeypatch.setattr(quotes, "tencent_ohlcv", tencent)
    monkeypatch.setattr(quotes, "yahoo_ohlcv", yahoo)
    return tencent, yahoo


@pytest.mark.unit
def test_the_default_chain_leads_with_tencent():
    """Yahoo's API is unreachable from networks it withdrew from; Tencent is not."""
    assert DEFAULT_CONFIG["data_vendors"]["core_stock_apis"].split(",")[0] == "tencent"


@pytest.mark.unit
def test_indicators_are_computed_locally_not_from_a_vendor_api():
    from tradingagents.dataflows.router import VENDOR_METHODS

    assert DEFAULT_CONFIG["data_vendors"]["technical_indicators"] == "local"
    assert "local" in VENDOR_METHODS["get_indicators"]


@pytest.mark.unit
def test_an_unavailable_primary_hands_the_read_to_the_next_vendor(readers):
    tencent, yahoo = readers
    tencent.side_effect = VendorUnavailableError("blocked")
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    quotes.load_ohlcv("NVDA", "2026-06-01")

    yahoo.assert_called_once()


@pytest.mark.unit
def test_a_symbol_the_primary_does_not_quote_falls_through(readers):
    """Tencent answers for equities, ETFs and a few indices; a future is not one."""
    tencent, yahoo = readers
    tencent.side_effect = NoMarketDataError("GC=F", "GC=F", "not a symbol Tencent quotes")
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    quotes.load_ohlcv("GC=F", "2026-06-01")

    yahoo.assert_called_once()


@pytest.mark.unit
def test_the_primary_answering_skips_the_fallback(readers):
    tencent, yahoo = readers
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    quotes.load_ohlcv("NVDA", "2026-06-01")

    tencent.assert_called_once()
    yahoo.assert_not_called()


@pytest.mark.unit
def test_a_pinned_vendor_is_not_a_chain(readers):
    """One name stays one name: the chain is what the user wrote, in order."""
    tencent, yahoo = readers
    tencent.side_effect = VendorUnavailableError("blocked")
    set_config({"data_vendors": {"core_stock_apis": "tencent"}})

    with pytest.raises(VendorUnavailableError):
        quotes.load_ohlcv("NVDA", "2026-06-01")
    yahoo.assert_not_called()


@pytest.mark.unit
def test_a_failure_in_transit_outranks_another_vendors_absence(readers):
    """A vendor that never answered cannot say the symbol has no data."""
    tencent, yahoo = readers
    tencent.side_effect = NoMarketDataError("NVDA", "NVDA", "no Tencent price rows")
    yahoo.side_effect = VendorUnavailableError("Yahoo Finance is not reachable")
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    with pytest.raises(VendorUnavailableError):
        quotes.load_ohlcv("NVDA", "2026-06-01")


@pytest.mark.unit
def test_no_vendor_at_all_still_reports_the_symbol_as_absent(readers):
    tencent, yahoo = readers
    tencent.side_effect = NoMarketDataError("ZZZZ", "ZZZZ", "no Tencent price rows")
    yahoo.side_effect = NoMarketDataError("ZZZZ", "ZZZZ", "no Yahoo price rows")
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    with pytest.raises(NoMarketDataError):
        quotes.load_ohlcv("ZZZZ", "2026-06-01")


@pytest.mark.unit
def test_closes_follow_the_same_chain(monkeypatch):
    tencent = mock.Mock(side_effect=VendorUnavailableError("blocked"))
    yahoo = mock.Mock(return_value=pd.Series([1.0], index=pd.DatetimeIndex(["2026-06-01"])))
    monkeypatch.setattr(quotes, "tencent_closes", tencent)
    # get_closes imports the Yahoo reader lazily, from the module that imports this one.
    import tradingagents.dataflows.vendors.yahoo.market as yahoo_market

    monkeypatch.setattr(yahoo_market, "get_closes", yahoo)
    set_config({"data_vendors": {"core_stock_apis": "tencent,yfinance"}})

    assert quotes.get_closes("NVDA", "2026-06-01", "2026-06-05").tolist() == [1.0]
    yahoo.assert_called_once()
