
from typing import Any
from pydantic import BaseModel, Field, field_validator
from app.schema_analy import StockAnalysis

class StockResearchRequest(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=30,
        description="Stock ticker, e.g. AAPL or MSFT",
    )
    company_name: str | None = Field(
        default=None,
        max_length=150,
        description="Optional company name to improve news search",
    )
    exchange: str | None = Field(default=None, max_length=30)
    period: str = Field(default="1mo")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: str) -> str:
        allowed = {"1wk", "1mo", "3mo", "6mo", "1y"}
        if value not in allowed:
            raise ValueError(
                f"period must be one of {sorted(allowed)}"
            )
        return value


class StockResearchResponse(BaseModel):
    stock: dict[str, Any]
    quote: dict[str, Any]
    history: list[dict[str, Any]]
    news: list[dict[str, Any]]
    data_timestamp: str

class StockResearchResponse(BaseModel):
    stock: dict[str, Any]
    quote: dict[str, Any]
    history: list[dict[str, Any]]
    news: list[dict[str, Any]]
    technical_indicators: dict[str, Any]
    analysis: StockAnalysis
    data_timestamp: str