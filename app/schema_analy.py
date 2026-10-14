
from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    claim: str = Field(
        description="A factual claim supporting or contradicting the assessment."
    )
    source: str = Field(
        description="Source name or market-data indicator."
    )
    url: str | None = Field(
        default=None,
        description="Source URL when applicable."
    )


class StockAnalysis(BaseModel):
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: int = Field(ge=0, le=100)
    summary: str
    reasons: list[str]
    risks: list[str]
    technical_outlook: Literal[
        "BULLISH", "NEUTRAL", "BEARISH", "INSUFFICIENT_DATA"
    ]
    news_sentiment: Literal[
        "POSITIVE", "MIXED", "NEGATIVE", "NEUTRAL", "INSUFFICIENT_DATA"
    ]
    evidence: list[EvidenceItem]
    data_limitations: list[str]
    investment_horizon: Literal[
        "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "UNSPECIFIED"
    ]
