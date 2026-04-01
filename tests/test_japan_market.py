"""Tests for Japan market support components."""
import unittest


# ── market_profile ──────────────────────────────────────────────────────────

class MarketProfileTests(unittest.TestCase):

    def test_detect_market_japan(self):
        from tradingagents.dataflows.market_profile import detect_market
        self.assertEqual(detect_market("7203.T"), "japan")

    def test_detect_market_japan_lowercase(self):
        from tradingagents.dataflows.market_profile import detect_market
        self.assertEqual(detect_market("7203.t"), "japan")

    def test_detect_market_us(self):
        from tradingagents.dataflows.market_profile import detect_market
        self.assertEqual(detect_market("AAPL"), "us")

    def test_detect_market_other_exchange(self):
        from tradingagents.dataflows.market_profile import detect_market
        # .TO (Toronto) is not Japan
        self.assertEqual(detect_market("CNC.TO"), "us")

    def test_get_profile_japan(self):
        from tradingagents.dataflows.market_profile import get_profile
        p = get_profile("japan")
        self.assertEqual(p.currency, "JPY")
        self.assertEqual(p.language_default, "japanese")
        self.assertEqual(p.exchange_tz, "Asia/Tokyo")

    def test_get_profile_us(self):
        from tradingagents.dataflows.market_profile import get_profile
        p = get_profile("us")
        self.assertEqual(p.currency, "USD")
        self.assertEqual(p.language_default, "english")


if __name__ == "__main__":
    unittest.main()
