
import asyncio

from fastapi import APIRouter, HTTPException

from schemas import (
    StockResearchRequest,
    StockResearchResponse,
)
import logging

from services.stock_service import (
    get_stock_data,
    StockDataError,
)
from services.news_service import (
    get_stock_news,
    NewsDataError,
)
from services.technical_service import calculate_indicators
from services.analysis_service import analyze_stock


router = APIRouter(prefix="/api/v1/stocks", tags=["Stocks"])
logger = logging.getLogger(__name__)

@router.post("/research", response_model=StockResearchResponse)
async def research_stock(request: StockResearchRequest):
    # Step 1: Fetch market data and news concurrently.
    market_task = get_stock_data(
        symbol=request.symbol,
        exchange=request.exchange,
        period=request.period,
    )
    news_task = get_stock_news(
        symbol=request.symbol,
        company_name=request.company_name,
    )

    try:
        market_data, news = await asyncio.gather(
            market_task, news_task
        )
    except StockDataError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Stock data error: {exc}",
        ) from exc
    except NewsDataError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"News data error: {exc}",
        ) from exc

    # Step 2: Calculate indicators locally.
    try:
        indicators = await asyncio.to_thread(
            calculate_indicators,
            market_data["history"],
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not calculate indicators: {exc}",
        ) from exc

    # Step 3: Ask Gemini to interpret the evidence.
    try:
        analysis = await analyze_stock(
            stock=market_data["stock"],
            quote=market_data["quote"],
            indicators=indicators,
            news=news,
        )
    except Exception:
        logger.exception("Gemini stock analysis failed")
        raise HTTPException(
            status_code=502,
            detail="AI analysis failed. Check the backend terminal logs.",
        )

    return StockResearchResponse(
        stock=market_data["stock"],
        quote=market_data["quote"],
        history=market_data["history"],
        news=news,
        technical_indicators=indicators,
        analysis=analysis,
        data_timestamp=market_data["data_timestamp"],
    )
