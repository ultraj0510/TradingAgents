"""Tests for Japan market support components."""
import datetime
import pytest


# ── market_profile ──────────────────────────────────────────────────────────

def test_detect_market_japan():
    from tradingagents.dataflows.market_profile import detect_market
    assert detect_market("7203.T") == "japan"

def test_detect_market_japan_lowercase():
    from tradingagents.dataflows.market_profile import detect_market
    assert detect_market("7203.t") == "japan"

def test_detect_market_us():
    from tradingagents.dataflows.market_profile import detect_market
    assert detect_market("AAPL") == "us"

def test_detect_market_other_exchange():
    from tradingagents.dataflows.market_profile import detect_market
    # .TO (Toronto) is not Japan
    assert detect_market("CNC.TO") == "us"

def test_get_profile_japan():
    from tradingagents.dataflows.market_profile import get_profile
    p = get_profile("japan")
    assert p.currency == "JPY"
    assert p.language_default == "japanese"
    assert p.exchange_tz == "Asia/Tokyo"

def test_get_profile_us():
    from tradingagents.dataflows.market_profile import get_profile
    p = get_profile("us")
    assert p.currency == "USD"
    assert p.language_default == "english"
