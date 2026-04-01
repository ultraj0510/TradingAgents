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
