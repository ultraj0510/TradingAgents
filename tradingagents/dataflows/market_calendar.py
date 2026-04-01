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
