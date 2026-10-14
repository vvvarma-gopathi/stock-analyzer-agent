
from datetime import datetime, timezone

import httpx

from config import settings


BASE_URL = "https://api.twelvedata.com"

PERIOD_DAYS = {
    "1wk": 7,
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
}


class StockDataError(Exception):
    pass


async def _get_json(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict,
) -> dict:
    try:
        response = await client.get(
            f"{BASE_URL}/{endpoint}",
            params={
                **params,
                "apikey": settings.twelve_data_api_key,
            },
        )
        response.raise_for_status()
        data = response.json()

    except httpx.TimeoutException as exc:
        raise StockDataError(
            "The stock data provider timed out."
        ) from exc
    except httpx.HTTPStatusError as exc:
        try:
            body = exc.response.json()
            message = body.get(
                "message",
                body.get("code", "Unknown provider error"),
            )
        except ValueError:
            message = "Non-JSON error response"

        raise StockDataError(
            f"Twelve Data HTTP {exc.response.status_code}: "
            f"{message}"
        ) from exc
    except httpx.RequestError as exc:
        raise StockDataError(
            "Could not connect to the stock data provider."
        ) from exc

    if not isinstance(data, dict):
        raise StockDataError("Invalid stock provider response.")

    # Twelve Data may return provider errors in a JSON response.
    if data.get("status") == "error" or data.get("code"):
        message = data.get("message", "Unknown provider error")
        raise StockDataError(str(message))

    return data


async def get_stock_data(
    symbol: str,
    exchange: str | None,
    period: str,
) -> dict:
    params = {"symbol": symbol}

    if exchange:
        params["exchange"] = exchange

    async with httpx.AsyncClient(timeout=20.0) as client:
        quote, series = await _fetch_market_data(
            client, params, period
        )

    values = series.get("values")
    if not isinstance(values, list) or not values:
        raise StockDataError(
            "No historical prices found for this symbol."
        )

    # Twelve Data generally returns newest observations first.
    # The frontend chart needs chronological order.
    history = [
    {
        "datetime": item.get("datetime"),
        "open": _number(item.get("open")),
        "high": _number(item.get("high")),
        "low": _number(item.get("low")),
        "close": _number(item.get("close")),
        "volume": _number(item.get("volume")),
    }
        for item in values
    ]

    history.sort(key=lambda item: item["datetime"] or "")
    latest = history[-1]
    stock = {
        "symbol": quote.get("symbol", symbol),
        "name": quote.get("name"),
        "exchange": quote.get("exchange", exchange),
        "currency": quote.get("currency"),
    }

    return {
        "stock": stock,
        "quote": {
            "price": _number(quote.get("close", quote.get("price"))),
            "open": _number(quote.get("open")),
            "high": _number(quote.get("high")),
            "low": _number(quote.get("low")),
            "previous_close": _number(
                quote.get("previous_close")
            ),
            "change": _number(quote.get("change")),
            "percent_change": _number(
                quote.get("percent_change")
            ),
            "volume": _number(quote.get("volume")),
            "latest_daily_close": latest["close"],
            "latest_daily_date": latest["datetime"],
        },
        "history": history,
        "data_timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


async def _fetch_market_data(
    client: httpx.AsyncClient,
    params: dict,
    period: str,
) -> tuple[dict, dict]:
    import asyncio

    quote_task = _get_json(client, "quote", params)

    history_params = {
        **params,
        "interval": "1day",
        "outputsize": PERIOD_DAYS[period],
        "order": "ASC",
    }
    history_task = _get_json(
        client, "time_series", history_params
    )

    quote, series = await asyncio.gather(
        quote_task, history_task
    )
    return quote, series


def _number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
