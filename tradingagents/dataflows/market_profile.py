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
