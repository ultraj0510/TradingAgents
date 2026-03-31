# Japan Market Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TradingAgents を日本株（`.T` サフィックス銘柄）に対応させ、yfinance を最大活用しつつ日本語RSS ニュース・JPX 市場カレンダー・市場コンテキスト注入を追加する。

**Architecture:** `.T` サフィックス検出で Japan プロファイルを自動選択。`propagate()` 呼び出し時にグローバル config を market-aware に更新し、`route_to_vendor` が自動的に `news_japan_rss` ベンダーを使用する。株価・テクニカル・ファンダメンタルズは yfinance そのまま。

**Tech Stack:** yfinance (既存), feedparser (RSS), jpholiday (JPX祝日), Python dataclasses

---

## File Map

| File | 変更種別 | 責務 |
|------|----------|------|
| `pyproject.toml` | 修正 | `jpholiday`, `feedparser` 依存追加 |
| `tradingagents/dataflows/market_profile.py` | 新規 | 市場判定・MarketProfile dataclass |
| `tradingagents/dataflows/market_calendar.py` | 新規 | JPX 取引日判定 |
| `tradingagents/dataflows/news_japan_rss.py` | 新規 | RSS ニュース取得（yfinance フォールバック付き） |
| `tradingagents/dataflows/interface.py` | 修正 | `news_japan_rss` ベンダー登録 |
| `tradingagents/default_config.py` | 修正 | `market: "auto"`, `output_language: "auto"` 追加 |
| `tradingagents/agents/utils/agent_utils.py` | 修正 | `build_instrument_context()` に市場コンテキスト注入 |
| `tradingagents/graph/trading_graph.py` | 修正 | `propagate()` で市場検出・config 更新 |
| `tests/test_japan_market.py` | 新規 | 全コンポーネントのテスト |

---

## Task 1: 依存ライブラリの追加

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: `pyproject.toml` の dependencies に追加**

`pyproject.toml` の `dependencies` リストに以下の2行を追加する（既存の `"yfinance>=0.2.63",` の直後）：

```toml
    "jpholiday>=0.1.8",
    "feedparser>=6.0.11",
```

結果として dependencies は以下のようになる（抜粋）：
```toml
    "yfinance>=0.2.63",
    "jpholiday>=0.1.8",
    "feedparser>=6.0.11",
```

- [ ] **Step 2: インストールして動作確認**

```bash
cd /Users/fujie/code/TradingAgents
pip install jpholiday feedparser
python -c "import jpholiday; import feedparser; print('OK')"
```

期待出力: `OK`

- [ ] **Step 3: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add pyproject.toml
git commit -m "feat: add jpholiday and feedparser dependencies"
```

---

## Task 2: `market_profile.py` の作成

**Files:**
- Create: `tradingagents/dataflows/market_profile.py`
- Test: `tests/test_japan_market.py`（新規作成、このタスクで最初のテストを書く）

- [ ] **Step 1: テストファイルを作成して失敗するテストを書く**

`tests/test_japan_market.py` を新規作成：

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py::test_detect_market_japan -v
```

期待出力: `FAILED` または `ModuleNotFoundError`

- [ ] **Step 3: `market_profile.py` を実装**

`tradingagents/dataflows/market_profile.py` を新規作成：

```python
"""Market profile detection and configuration."""
from dataclasses import dataclass
from typing import Dict


@dataclass
class MarketProfile:
    market: str
    currency: str
    language_default: str
    exchange_tz: str
    trading_hours: Dict[str, str]


_PROFILES = {
    "japan": MarketProfile(
        market="japan",
        currency="JPY",
        language_default="japanese",
        exchange_tz="Asia/Tokyo",
        trading_hours={"open": "09:00", "close": "15:30"},
    ),
    "us": MarketProfile(
        market="us",
        currency="USD",
        language_default="english",
        exchange_tz="America/New_York",
        trading_hours={"open": "09:30", "close": "16:00"},
    ),
}


def detect_market(ticker: str) -> str:
    """Detect the market from a ticker symbol.

    Returns "japan" for tickers ending with ".T" (TSE/JPX).
    Returns "us" for all other tickers.
    """
    if ticker.upper().endswith(".T"):
        return "japan"
    return "us"


def get_profile(market: str) -> MarketProfile:
    """Return the MarketProfile for the given market.

    Falls back to "us" profile for unknown markets.
    """
    return _PROFILES.get(market, _PROFILES["us"])
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py::test_detect_market_japan tests/test_japan_market.py::test_detect_market_japan_lowercase tests/test_japan_market.py::test_detect_market_us tests/test_japan_market.py::test_detect_market_other_exchange tests/test_japan_market.py::test_get_profile_japan tests/test_japan_market.py::test_get_profile_us -v
```

期待出力: 6 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/dataflows/market_profile.py tests/test_japan_market.py
git commit -m "feat: add market_profile with Japan/US detection"
```

---

## Task 3: `market_calendar.py` の作成

**Files:**
- Create: `tradingagents/dataflows/market_calendar.py`
- Modify: `tests/test_japan_market.py`（テスト追記）

- [ ] **Step 1: テストを追加（`tests/test_japan_market.py` に追記）**

`tests/test_japan_market.py` の末尾に追記：

```python
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
    saturday = datetime.date(2025, 1, 4)
    result = last_trading_day(saturday, "japan")
    # 前の金曜日 = 2025-01-03（ただし年始の場合は前営業日）
    assert result < saturday
    assert result.weekday() < 5  # 月〜金

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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py::test_is_trading_day_saturday_japan -v
```

期待出力: `FAILED` または `ModuleNotFoundError`

- [ ] **Step 3: `market_calendar.py` を実装**

`tradingagents/dataflows/market_calendar.py` を新規作成：

```python
"""JPX/TSE market calendar utilities."""
import datetime
import logging
import warnings

logger = logging.getLogger(__name__)

try:
    import jpholiday
    _JPHOLIDAY_AVAILABLE = True
except ImportError:
    _JPHOLIDAY_AVAILABLE = False
    warnings.warn(
        "jpholiday is not installed. Japanese holiday checks will be skipped. "
        "Install with: pip install jpholiday",
        stacklevel=2,
    )

# JPX 年末年始休業日（12/31, 1/2, 1/3 は jpholiday に含まれないため手動定義）
_JPX_EXTRA_CLOSURES = {
    (12, 31),  # 大晦日
    (1, 2),    # 年始
    (1, 3),    # 年始
}


def _is_jpx_holiday(date: datetime.date) -> bool:
    """Return True if the date is a JPX holiday (national holiday or year-end/new-year closure)."""
    # 土日
    if date.weekday() >= 5:
        return True
    # 年末年始
    if (date.month, date.day) in _JPX_EXTRA_CLOSURES:
        return True
    # 祝日
    if _JPHOLIDAY_AVAILABLE:
        return jpholiday.is_holiday(date)
    return False


def is_trading_day(date: datetime.date, market: str) -> bool:
    """Return True if the given date is a trading day for the specified market.

    For "japan": excludes weekends, Japanese national holidays, and JPX year-end closures.
    For "us": excludes weekends only (US holiday support not implemented).
    """
    if market == "japan":
        return not _is_jpx_holiday(date)
    # Default / "us": only exclude weekends
    return date.weekday() < 5


def last_trading_day(date: datetime.date, market: str) -> datetime.date:
    """Return the most recent trading day on or before the given date."""
    current = date
    while not is_trading_day(current, market):
        current -= datetime.timedelta(days=1)
    return current
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py -k "calendar" -v
```

期待出力: 7 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/dataflows/market_calendar.py tests/test_japan_market.py
git commit -m "feat: add JPX market calendar with holiday support"
```

---

## Task 4: `news_japan_rss.py` の作成

**Files:**
- Create: `tradingagents/dataflows/news_japan_rss.py`
- Modify: `tests/test_japan_market.py`（テスト追記）

- [ ] **Step 1: テストを追加（`tests/test_japan_market.py` に追記）**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py::test_extract_code_from_ticker -v
```

期待出力: `FAILED` または `ModuleNotFoundError`

- [ ] **Step 3: `news_japan_rss.py` を実装**

`tradingagents/dataflows/news_japan_rss.py` を新規作成：

```python
"""Japanese news fetching via RSS feeds (Yahoo Finance Japan, NHK Economics)."""
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

import feedparser

from .yfinance_news import get_news_yfinance, get_global_news_yfinance

logger = logging.getLogger(__name__)

_YAHOO_FINANCE_JP_RSS = "https://finance.yahoo.co.jp/rss/stocks/{code}.xml"
_NHK_ECONOMICS_RSS = "https://www3.nhk.or.jp/rss/news/cat5.xml"


def _extract_stock_code(ticker: str) -> str:
    """Extract the numeric stock code from a ticker like '7203.T' → '7203'."""
    return ticker.split(".")[0]


def _parse_rss_to_articles(feed_url: str, start_dt: datetime, end_dt: datetime) -> str:
    """Fetch and parse an RSS feed, returning formatted article string."""
    feed = feedparser.parse(feed_url)
    articles = ""

    for entry in feed.entries:
        title = entry.get("title", "No title")
        summary = entry.get("summary", "")
        link = entry.get("link", "")
        published = entry.get("published_parsed")

        if published:
            pub_dt = datetime(*published[:6])
            if not (start_dt <= pub_dt <= end_dt + relativedelta(days=1)):
                continue

        articles += f"### {title}\n"
        if summary:
            articles += f"{summary}\n"
        if link:
            articles += f"Link: {link}\n"
        articles += "\n"

    return articles


def get_news_japan_rss(ticker: str, start_date: str, end_date: str) -> str:
    """Fetch Japanese stock news via Yahoo Finance Japan RSS.

    Falls back to yfinance news on any error.

    Args:
        ticker: Stock ticker with .T suffix (e.g. "7203.T")
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        Formatted string of news articles.
    """
    try:
        code = _extract_stock_code(ticker)
        feed_url = _YAHOO_FINANCE_JP_RSS.format(code=code)

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        articles = _parse_rss_to_articles(feed_url, start_dt, end_dt)

        if not articles.strip():
            logger.info("No RSS articles found for %s, falling back to yfinance", ticker)
            return get_news_yfinance(ticker, start_date, end_date)

        return f"## {ticker} ニュース ({start_date} 〜 {end_date}):\n\n{articles}"

    except Exception as exc:
        logger.warning("RSS news fetch failed for %s: %s — falling back to yfinance", ticker, exc)
        return get_news_yfinance(ticker, start_date, end_date)


def get_global_news_japan(
    curr_date: str,
    look_back_days: int = 7,
    limit: int = 10,
) -> str:
    """Fetch Japanese macro/economic news via NHK Economics RSS.

    Falls back to yfinance global news on any error.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of articles

    Returns:
        Formatted string of global news articles.
    """
    try:
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - relativedelta(days=look_back_days)

        feed = feedparser.parse(_NHK_ECONOMICS_RSS)
        articles = ""
        count = 0

        for entry in feed.entries:
            if count >= limit:
                break

            title = entry.get("title", "No title")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")

            if published:
                pub_dt = datetime(*published[:6])
                if pub_dt < start_dt or pub_dt > curr_dt + relativedelta(days=1):
                    continue

            articles += f"### {title}\n"
            if summary:
                articles += f"{summary}\n"
            if link:
                articles += f"Link: {link}\n"
            articles += "\n"
            count += 1

        if not articles.strip():
            logger.info("No NHK RSS articles found, falling back to yfinance global news")
            return get_global_news_yfinance(curr_date, look_back_days, limit)

        start_date = start_dt.strftime("%Y-%m-%d")
        return f"## 日本市場マクロニュース ({start_date} 〜 {curr_date}):\n\n{articles}"

    except Exception as exc:
        logger.warning("NHK RSS fetch failed: %s — falling back to yfinance", exc)
        return get_global_news_yfinance(curr_date, look_back_days, limit)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py -k "rss or news_japan" -v
```

期待出力: 3 tests PASSED

- [ ] **Step 5: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/dataflows/news_japan_rss.py tests/test_japan_market.py
git commit -m "feat: add Japanese RSS news fetcher with yfinance fallback"
```

---

## Task 5: `interface.py` に `news_japan_rss` ベンダーを登録

**Files:**
- Modify: `tradingagents/dataflows/interface.py`

- [ ] **Step 1: import を追加**

`interface.py` の既存 import ブロックの末尾（`from .alpha_vantage_common import ...` の後）に追加：

```python
from .news_japan_rss import get_news_japan_rss, get_global_news_japan
```

- [ ] **Step 2: `VENDOR_LIST` に追加**

`VENDOR_LIST` を以下のように変更（`"alpha_vantage"` の後に追加）：

```python
VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "news_japan_rss",
]
```

- [ ] **Step 3: `VENDOR_METHODS` の `get_news` と `get_global_news` に追加**

`VENDOR_METHODS` の `"get_news"` エントリを：

```python
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
        "news_japan_rss": get_news_japan_rss,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
        "news_japan_rss": get_global_news_japan,
    },
```

- [ ] **Step 4: インポートが通ることを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -c "from tradingagents.dataflows.interface import VENDOR_METHODS; print('news_japan_rss' in VENDOR_METHODS['get_news'])"
```

期待出力: `True`

- [ ] **Step 5: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/dataflows/interface.py
git commit -m "feat: register news_japan_rss vendor in interface"
```

---

## Task 6: `default_config.py` に market / output_language 設定を追加

**Files:**
- Modify: `tradingagents/default_config.py`

- [ ] **Step 1: 設定項目を追加**

`default_config.py` の `DEFAULT_CONFIG` を修正する。

既存の `"output_language": "English",` を以下に変更：

```python
    # Market configuration
    # "auto" detects market from ticker suffix (.T → japan, others → us)
    "market": "auto",
    # Output language: "auto" uses market profile default, or specify "English" / "Japanese"
    "output_language": "auto",
```

- [ ] **Step 2: 動作確認**

```bash
cd /Users/fujie/code/TradingAgents
python -c "from tradingagents.default_config import DEFAULT_CONFIG; print(DEFAULT_CONFIG.get('market'), DEFAULT_CONFIG.get('output_language'))"
```

期待出力: `auto auto`

- [ ] **Step 3: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/default_config.py
git commit -m "feat: add market and output_language auto-detection config"
```

---

## Task 7: `agent_utils.py` に市場コンテキスト注入

**Files:**
- Modify: `tradingagents/agents/utils/agent_utils.py`

- [ ] **Step 1: `get_language_instruction()` を `"auto"` に対応させる**

現在の `get_language_instruction()` を以下に置き換える（`"auto"` の場合は config の `"market"` を見て判断）：

```python
def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    from tradingagents.dataflows.config import get_config
    config = get_config()
    lang = config.get("output_language", "auto")

    if lang.lower() == "auto":
        # Derive from detected market
        market = config.get("market", "us")
        if market == "japan":
            lang = "Japanese"
        else:
            return ""

    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."
```

- [ ] **Step 2: `build_instrument_context()` に市場コンテキストを追加**

現在の `build_instrument_context()` を以下に置き換える：

```python
def build_instrument_context(ticker: str) -> str:
    """Describe the exact instrument and market context so agents interpret data correctly."""
    from tradingagents.dataflows.config import get_config
    from tradingagents.dataflows.market_profile import detect_market, get_profile

    config = get_config()
    market = config.get("market", "auto")
    if market == "auto":
        market = detect_market(ticker)

    profile = get_profile(market)

    base = (
        f"The instrument to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )

    if market == "japan":
        base += (
            f" This is a Japanese stock traded on the Tokyo Stock Exchange (TSE/JPX). "
            f"All prices and financial figures are denominated in Japanese Yen (JPY). "
            f"Trading unit is typically 100 shares (単元株). "
            f"Market hours are 09:00–15:30 JST (Asia/Tokyo timezone)."
        )

    return base
```

- [ ] **Step 3: 動作確認**

```bash
cd /Users/fujie/code/TradingAgents
python -c "
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG
set_config(DEFAULT_CONFIG)
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
print(build_instrument_context('7203.T'))
print('---')
print(repr(get_language_instruction()))
"
```

期待出力（抜粋）:
```
The instrument to analyze is `7203.T`. ... This is a Japanese stock ... JPY ...
---
' Write your entire response in Japanese.'
```

- [ ] **Step 4: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/agents/utils/agent_utils.py
git commit -m "feat: inject Japan market context into agent prompts"
```

---

## Task 8: `trading_graph.py` の `propagate()` で市場検出・config 更新

**Files:**
- Modify: `tradingagents/graph/trading_graph.py`

- [ ] **Step 1: `propagate()` に市場検出ロジックを追加**

`trading_graph.py` の `propagate()` メソッドを修正する。

現在の `propagate()` の先頭部分（`self.ticker = company_name` の直後）に以下を追加：

```python
    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # ── Japan market auto-detection ──────────────────────────────────────
        from tradingagents.dataflows.market_profile import detect_market
        resolved_market = self.config.get("market", "auto")
        if resolved_market == "auto":
            resolved_market = detect_market(company_name)

        if resolved_market == "japan":
            # Build a run-specific config that activates Japan-specific vendors
            run_config = dict(self.config)
            run_config["market"] = resolved_market
            run_config["data_vendors"] = dict(self.config.get("data_vendors", {}))
            run_config["data_vendors"]["news_data"] = "news_japan_rss"
            # Resolve output language if still "auto"
            if run_config.get("output_language", "auto").lower() == "auto":
                run_config["output_language"] = "Japanese"
            set_config(run_config)
        # ────────────────────────────────────────────────────────────────────

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()
        # ... (rest of the method unchanged)
```

**注意**: `set_config` は既に `from tradingagents.dataflows.config import set_config` としてインポート済み（`trading_graph.py` line 22）。

- [ ] **Step 2: 動作確認（ドライラン）**

```bash
cd /Users/fujie/code/TradingAgents
python -c "
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.config import get_config, set_config
set_config(DEFAULT_CONFIG)

# Simulate what propagate() does for 7203.T
from tradingagents.dataflows.market_profile import detect_market
ticker = '7203.T'
market = detect_market(ticker)
config = get_config()
run_config = dict(config)
run_config['market'] = market
run_config['data_vendors'] = dict(config.get('data_vendors', {}))
run_config['data_vendors']['news_data'] = 'news_japan_rss'
run_config['output_language'] = 'Japanese'
set_config(run_config)

final = get_config()
print('market:', final['market'])
print('news_data vendor:', final['data_vendors']['news_data'])
print('output_language:', final['output_language'])
"
```

期待出力:
```
market: japan
news_data vendor: news_japan_rss
output_language: Japanese
```

- [ ] **Step 3: テストを追加（`tests/test_japan_market.py` に追記）**

```python
# ── integration: trading_graph config resolution ────────────────────────────

def test_propagate_sets_japan_config(monkeypatch):
    """When ticker ends with .T, propagate() should set japan config."""
    from tradingagents.dataflows.config import set_config, get_config
    from tradingagents.default_config import DEFAULT_CONFIG
    set_config(DEFAULT_CONFIG.copy())

    from tradingagents.dataflows.market_profile import detect_market
    from tradingagents.dataflows.config import set_config as sc

    ticker = "7203.T"
    market = detect_market(ticker)
    assert market == "japan"

    config = get_config()
    run_config = dict(config)
    run_config["market"] = market
    run_config["data_vendors"] = dict(config.get("data_vendors", {}))
    run_config["data_vendors"]["news_data"] = "news_japan_rss"
    if run_config.get("output_language", "auto").lower() == "auto":
        run_config["output_language"] = "Japanese"
    sc(run_config)

    final = get_config()
    assert final["market"] == "japan"
    assert final["data_vendors"]["news_data"] == "news_japan_rss"
    assert final["output_language"] == "Japanese"
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py::test_propagate_sets_japan_config -v
```

期待出力: PASSED

- [ ] **Step 5: コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add tradingagents/graph/trading_graph.py tests/test_japan_market.py
git commit -m "feat: auto-detect Japan market in propagate() and update config"
```

---

## Task 9: 全テスト実行と最終確認

**Files:**
- Read: `tests/test_japan_market.py`（確認のみ）

- [ ] **Step 1: 全テストを実行**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/test_japan_market.py -v
```

期待出力: 全テスト PASSED（失敗があれば修正してから次へ）

- [ ] **Step 2: 既存テストが壊れていないことを確認**

```bash
cd /Users/fujie/code/TradingAgents
python -m pytest tests/ -v --ignore=tests/test_japan_market.py
```

期待出力: 既存テストがすべて PASSED（または既存の失敗数が増えていないこと）

- [ ] **Step 3: エンドツーエンド動作確認（インポートレベル）**

```bash
cd /Users/fujie/code/TradingAgents
python -c "
from tradingagents.dataflows.market_profile import detect_market, get_profile
from tradingagents.dataflows.market_calendar import is_trading_day, last_trading_day
from tradingagents.dataflows.news_japan_rss import get_news_japan_rss
from tradingagents.dataflows.interface import VENDOR_METHODS
from tradingagents.agents.utils.agent_utils import build_instrument_context
import datetime

print('detect_market:', detect_market('7203.T'))
print('profile:', get_profile('japan'))
print('is_trading_day(2025-01-01):', is_trading_day(datetime.date(2025, 1, 1), 'japan'))
print('last_trading_day(2025-01-01):', last_trading_day(datetime.date(2025, 1, 1), 'japan'))
print('vendor registered:', 'news_japan_rss' in VENDOR_METHODS['get_news'])
print('instrument_context:', build_instrument_context('7203.T')[:80])
print()
print('All checks passed!')
"
```

期待出力:
```
detect_market: japan
profile: MarketProfile(market='japan', currency='JPY', ...)
is_trading_day(2025-01-01): False
last_trading_day(2025-01-01): 2024-12-30
vendor registered: True
instrument_context: The instrument to analyze is `7203.T`. ... Japanese stock ...
All checks passed!
```

- [ ] **Step 4: 最終コミット**

```bash
cd /Users/fujie/code/TradingAgents
git add -A
git commit -m "test: verify all Japan market support components"
```
