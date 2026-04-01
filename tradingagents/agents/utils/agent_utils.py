from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)


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

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
