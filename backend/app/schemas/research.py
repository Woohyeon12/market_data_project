from datetime import datetime
from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    symbol: str
    price_usd: float
    change_24h_pct: float
    volume_24h_usd: float
    data_source: str = "Local fallback"


class MarketInstrument(BaseModel):
    symbol: str
    name: str
    category: str
    market: str
    currency: str
    price: float
    change_pct: float
    data_source: str = "Local fallback"


class IndexChartPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float


class IndexChart(BaseModel):
    symbol: str
    name: str
    currency: str
    points: list[IndexChartPoint]
    data_source: str = "Local fallback"


class NewsItem(BaseModel):
    title: str
    source: str
    url: str | None = None
    summary: str | None = None
    published_at: str | None = None
    sentiment: str = "neutral"
    data_source: str = "Local fallback"


class Scenario(BaseModel):
    label: str
    probability_pct: int = Field(ge=0, le=100)
    rationale: str


class ResearchReport(BaseModel):
    asset: str
    generated_at: datetime
    market: MarketSnapshot
    summary: list[str]
    scenarios: list[Scenario]
    risks: list[str]
    news: list[NewsItem]
    disclaimer: str


class MarketsOverview(BaseModel):
    generated_at: datetime
    instruments: list[MarketInstrument]
    index_charts: list[IndexChart]
    summary: list[str]
    disclaimer: str
