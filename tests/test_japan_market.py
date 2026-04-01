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


# ── market_calendar ─────────────────────────────────────────────────────────

def test_is_trading_day_saturday_japan():
    from tradingagents.dataflows.market_calendar import is_trading_day
    saturday = datetime.date(2025, 1, 4)  # 土曜日
    assert is_trading_day(saturday, "japan") is False

def test_is_trading_day_sunday_japan():
    from tradingagents.dataflows.market_calendar import is_trading_day
    sunday = datetime.date(2025, 1, 5)  # 日曜日
    assert is_trading_day(sunday, "japan") is False

def test_is_trading_day_holiday_japan():
    from tradingagents.dataflows.market_calendar import is_trading_day
    # 2025-01-01 は元日
    new_years = datetime.date(2025, 1, 1)
    assert is_trading_day(new_years, "japan") is False

def test_is_trading_day_weekday_japan():
    from tradingagents.dataflows.market_calendar import is_trading_day
    # 2025-01-06 は月曜日（祝日でない）
    monday = datetime.date(2025, 1, 6)
    assert is_trading_day(monday, "japan") is True

def test_last_trading_day_from_saturday():
    from tradingagents.dataflows.market_calendar import last_trading_day
    # 2025-01-04 is Saturday; 01-03 and 01-02 are year-end closures
    saturday = datetime.date(2025, 1, 4)
    result = last_trading_day(saturday, "japan")
    assert result == datetime.date(2024, 12, 30)

def test_last_trading_day_from_holiday():
    from tradingagents.dataflows.market_calendar import last_trading_day
    # 2025-01-01 元日 → 直前の営業日は 2024-12-30（月）
    new_years = datetime.date(2025, 1, 1)
    result = last_trading_day(new_years, "japan")
    assert result == datetime.date(2024, 12, 30)

def test_last_trading_day_us_uses_weekends_only():
    from tradingagents.dataflows.market_calendar import is_trading_day
    # US市場: 平日は常にTrueを返す（祝日チェックは現在対象外）
    friday = datetime.date(2025, 1, 3)
    assert is_trading_day(friday, "us") is True
