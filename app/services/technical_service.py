
import numpy as np
import pandas as pd


def calculate_indicators(history: list[dict]) -> dict:
    if not history:
        raise ValueError("Historical price data is empty.")

    df = pd.DataFrame(history)
    df["datetime"] = pd.to_datetime(
        df["datetime"], errors="coerce"
    )
    df["close"] = pd.to_numeric(
        df["close"], errors="coerce"
    )
    df = (
        df.dropna(subset=["datetime", "close"])
        .sort_values("datetime")
        .drop_duplicates(subset=["datetime"])
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError("No valid closing prices were found.")

    close = df["close"]
    daily_returns = close.pct_change().dropna()

    # Simple moving averages.
    sma20 = close.rolling(window=20, min_periods=20).mean()
    sma50 = close.rolling(window=50, min_periods=50).mean()

    # Wilder-style RSI approximation using exponentially weighted means.
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()
    avg_loss = loss.ewm(
        alpha=1 / 14, min_periods=14, adjust=False
    ).mean()

    relative_strength = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))

    # Explicitly handle uninterrupted gains and flat prices.
    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain > 0), 100
    )
    rsi = rsi.mask(
        (avg_loss == 0) & (avg_gain == 0), 50
    )

    def number_or_none(series):
        value = series.iloc[-1]
        return round(float(value), 4) if pd.notna(value) else None

    latest_close = float(close.iloc[-1])
    latest_sma20 = number_or_none(sma20)
    latest_sma50 = number_or_none(sma50)

    if latest_sma20 is not None:
        price_vs_sma20 = (
            "above" if latest_close > latest_sma20
            else "below" if latest_close < latest_sma20
            else "equal"
        )
    else:
        price_vs_sma20 = "insufficient_data"

    if latest_sma50 is not None:
        price_vs_sma50 = (
            "above" if latest_close > latest_sma50
            else "below" if latest_close < latest_sma50
            else "equal"
        )
    else:
        price_vs_sma50 = "insufficient_data"

    returns_20 = (
        (close.iloc[-1] / close.iloc[-21] - 1) * 100
        if len(close) >= 21 and close.iloc[-21] != 0
        else None
    )

    volatility_20 = (
        daily_returns.tail(20).std(ddof=1) * np.sqrt(252) * 100
        if len(daily_returns) >= 20
        else None
    )

    return {
        "observations": len(close),
        "latest_close": round(latest_close, 4),
        "sma_20": latest_sma20,
        "sma_50": latest_sma50,
        "price_vs_sma20": price_vs_sma20,
        "price_vs_sma50": price_vs_sma50,
        "rsi_14": number_or_none(rsi),
        "return_20_sessions_pct": (
            round(float(returns_20), 4)
            if returns_20 is not None else None
        ),
        "annualized_volatility_20_sessions_pct": (
            round(float(volatility_20), 4)
            if pd.notna(volatility_20) else None
        ),
        "latest_history_date": df["datetime"].iloc[-1].date().isoformat(),
        "interpretation_note": (
            "Indicators describe historical price behavior. "
            "They do not guarantee future returns."
        ),
    }
