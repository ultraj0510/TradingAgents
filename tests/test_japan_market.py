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


# ── news_japan_rss ───────────────────────────────────────────────────────────

def test_extract_code_from_ticker():
    from tradingagents.dataflows.news_japan_rss import _extract_stock_code
    assert _extract_stock_code("7203.T") == "7203"
    assert _extract_stock_code("6758.T") == "6758"

def test_get_news_japan_rss_fallback_on_error(monkeypatch):
    """When RSS fetch fails, should fall back to yfinance news."""
    import tradingagents.dataflows.news_japan_rss as mod

    # Force feedparser to raise an exception
    def bad_parse(url, *a, **kw):
        raise RuntimeError("network error")

    monkeypatch.setattr(mod.feedparser, "parse", bad_parse)

    # Fallback should return a string (not raise)
    result = mod.get_news_japan_rss("7203.T", "2024-01-01", "2024-01-31")
    assert isinstance(result, str)

def test_get_global_news_japan_returns_string(monkeypatch):
    """Should always return a string."""
    import tradingagents.dataflows.news_japan_rss as mod

    # Simulate empty RSS feed
    class FakeResult:
        entries = []

    monkeypatch.setattr(mod.feedparser, "parse", lambda *a, **kw: FakeResult())

    result = mod.get_global_news_japan("2024-01-15")
    assert isinstance(result, str)

def test_parse_rss_to_articles_filters_by_date(monkeypatch):
    """_parse_rss_to_articles should only include articles within the date window."""
    import time
    import tradingagents.dataflows.news_japan_rss as mod

    # Build two fake entries: one in-range, one out-of-range
    in_range_time = time.strptime("2024-01-10", "%Y-%m-%d")
    out_of_range_time = time.strptime("2024-01-20", "%Y-%m-%d")

    class FakeEntry:
        def __init__(self, title, published_parsed):
            self.title = title
            self.published_parsed = published_parsed
        def get(self, key, default=""):
            return getattr(self, key, default)

    class FakeFeed:
        entries = [
            FakeEntry("In-range article", in_range_time),
            FakeEntry("Out-of-range article", out_of_range_time),
        ]

    monkeypatch.setattr(mod.feedparser, "parse", lambda *a, **kw: FakeFeed())

    from datetime import datetime
    result = mod._parse_rss_to_articles(
        "http://fake.url",
        datetime(2024, 1, 8),
        datetime(2024, 1, 15),
    )
    assert "In-range article" in result
    assert "Out-of-range article" not in result

def test_parse_rss_skips_undated_entries(monkeypatch):
    """Entries with no published_parsed should be skipped."""
    import tradingagents.dataflows.news_japan_rss as mod

    class FakeEntry:
        def __init__(self, title):
            self.title = title
            self.published_parsed = None
        def get(self, key, default=""):
            return getattr(self, key, default)

    class FakeFeed:
        entries = [FakeEntry("Undated article")]

    monkeypatch.setattr(mod.feedparser, "parse", lambda *a, **kw: FakeFeed())

    from datetime import datetime
    result = mod._parse_rss_to_articles(
        "http://fake.url",
        datetime(2024, 1, 1),
        datetime(2024, 1, 31),
    )
    assert "Undated article" not in result


# ── integration: trading_graph config resolution ────────────────────────────

def test_build_run_config_japan():
    """_build_run_config should produce Japan-specific config for .T tickers."""
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.dataflows.config import set_config

    set_config(DEFAULT_CONFIG.copy())

    # Build a minimal TradingAgentsGraph instance without initializing LLMs
    # by directly testing _build_run_config logic via the class method
    from unittest.mock import MagicMock, patch

    with patch("tradingagents.graph.trading_graph.create_llm_client") as mock_llm:
        mock_llm.return_value.get_llm.return_value = MagicMock()
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        graph = TradingAgentsGraph.__new__(TradingAgentsGraph)
        graph.config = DEFAULT_CONFIG.copy()

        result = graph._build_run_config("7203.T")

    assert result["market"] == "japan"
    assert result["data_vendors"]["news_data"] == "news_japan_rss"
    assert result["output_language"] == "Japanese"


def test_build_run_config_us():
    """_build_run_config should not change vendor config for US tickers."""
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.dataflows.config import set_config

    set_config(DEFAULT_CONFIG.copy())

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    graph = TradingAgentsGraph.__new__(TradingAgentsGraph)
    graph.config = DEFAULT_CONFIG.copy()

    result = graph._build_run_config("AAPL")

    assert result["market"] == "us"
    assert result["data_vendors"]["news_data"] == "yfinance"
