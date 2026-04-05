"""
recent_context.py — Generate a recent price context summary injected into analyst prompts.

This module computes key short-term statistics (5d/20d returns, 52-week position,
volume spikes, large single-day moves) and formats them into a concise text block
that helps analysts avoid lagging-indicator bias and peak-anchoring bias.
"""

import pandas as pd
from .stockstats_utils import load_ohlcv


def generate_recent_context(ticker: str, curr_date: str) -> str:
    """
    Compute recent price statistics and return a formatted context string
    for injection into analyst prompts.

    The output surfaces:
    - 5-day and 20-day price returns
    - 52-week position score (0% = 52wk low, 100% = 52wk high)
    - Any single-day moves >5% in the last 10 trading days (with volume context)
    - A plain-language assessment label (e.g., OVERSOLD BOUNCE SCENARIO)

    This information is forward-placed in the conversation so all analyst
    agents weight recent price action appropriately alongside lagging indicators.
    """
    try:
        data = load_ohlcv(ticker, curr_date)
    except Exception as e:
        return f"[RECENT PRICE CONTEXT] Could not load price data for {ticker}: {e}"

    if data.empty or len(data) < 5:
        return f"[RECENT PRICE CONTEXT] Insufficient price data for {ticker}."

    close = data["Close"]
    volume = data["Volume"]

    # --- 5-day return ---
    ret_5d = None
    if len(close) >= 6:
        ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100

    # --- 20-day return ---
    ret_20d = None
    if len(close) >= 21:
        ret_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100

    # --- 52-week position ---
    window = min(252, len(close))
    high_52w = close.iloc[-window:].max()
    low_52w = close.iloc[-window:].min()
    pos_52w = None
    if high_52w != low_52w:
        pos_52w = (close.iloc[-1] - low_52w) / (high_52w - low_52w) * 100

    # --- Large single-day moves in last 10 trading days ---
    daily_returns = close.pct_change() * 100
    recent_dates = data["Date"].dt.strftime("%Y-%m-%d").tolist()
    avg_vol = volume.rolling(20, min_periods=1).mean()
    vol_ratio = volume / avg_vol.replace(0, float("nan"))

    notable_moves = []
    lookback = min(10, len(data) - 1)
    for i in range(len(data) - lookback, len(data)):
        if i < 1:
            continue
        ret = daily_returns.iloc[i]
        if abs(ret) >= 5.0:
            vr = vol_ratio.iloc[i]
            vr_str = f"{vr:.1f}x avg vol" if not pd.isna(vr) else "vol N/A"
            direction = "surge" if ret > 0 else "drop"
            notable_moves.append(
                f"  • {recent_dates[i]}: {ret:+.1f}% single-day {direction} ({vr_str})"
            )

    # --- Assessment label ---
    assessment_parts = []
    if ret_5d is not None and ret_5d > 5:
        assessment_parts.append("recent recovery momentum")
    if ret_20d is not None and ret_20d < -15:
        assessment_parts.append("significant monthly decline")
    if pos_52w is not None and pos_52w < 20:
        assessment_parts.append("near 52-week low — potential mean-reversion zone")
    if pos_52w is not None and pos_52w > 80:
        assessment_parts.append("near 52-week high — watch for resistance")

    if pos_52w is not None and pos_52w < 25 and ret_20d is not None and ret_20d < -10:
        scenario = "OVERSOLD BOUNCE SCENARIO — weight mean-reversion signals heavily"
    elif ret_5d is not None and ret_5d > 5 and ret_20d is not None and ret_20d < -10:
        scenario = "RECOVERY AFTER DECLINE — evaluate if reversal is sustained"
    elif pos_52w is not None and pos_52w > 75:
        scenario = "NEAR 52-WEEK HIGH — trend-following environment, watch for exhaustion"
    else:
        scenario = "NORMAL RANGE — standard trend analysis applies"

    # --- Format output ---
    lines = [
        f"[RECENT PRICE CONTEXT FOR {ticker} as of {curr_date} — READ THIS FIRST]",
    ]

    if ret_5d is not None:
        label = "(strong recovery)" if ret_5d > 5 else ("(weak)" if ret_5d < -5 else "")
        lines.append(f"- 5-day return  : {ret_5d:+.1f}% {label}".strip())
    else:
        lines.append("- 5-day return  : N/A (insufficient data)")

    if ret_20d is not None:
        label = "(monthly recovery)" if ret_20d > 10 else ("(significant decline)" if ret_20d < -10 else "")
        lines.append(f"- 20-day return : {ret_20d:+.1f}% {label}".strip())
    else:
        lines.append("- 20-day return : N/A (insufficient data)")

    if pos_52w is not None:
        if pos_52w < 20:
            zone = "(near 52-week LOW — value zone)"
        elif pos_52w > 80:
            zone = "(near 52-week HIGH — resistance zone)"
        else:
            zone = "(mid-range)"
        lines.append(f"- 52-week position: {pos_52w:.0f}% {zone}")
        lines.append(f"  52-week range: {low_52w:.0f} – {high_52w:.0f}, current: {close.iloc[-1]:.0f}")
    else:
        lines.append("- 52-week position: N/A")

    if notable_moves:
        lines.append(f"- Notable single-day moves (last 10 days):")
        lines.extend(notable_moves)
    else:
        lines.append("- Notable single-day moves: none >5% in last 10 trading days")

    lines.append(f"- Scenario assessment: {scenario}")
    lines.append(
        "NOTE: Lagging indicators (RSI, MACD, SMA) reflect past trends. "
        "Reconcile them with the RECENT data above before drawing conclusions."
    )

    return "\n".join(lines)
