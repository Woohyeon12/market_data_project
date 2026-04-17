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


class CorrelationCell(BaseModel):
    x: str
    y: str
    value: float


class LagCorrelation(BaseModel):
    feature: str
    lag_days: int
    value: float


class CorrelationAnalysis(BaseModel):
    lookback_days: int
    assets: list[str]
    matrix: list[CorrelationCell]
    lag_correlations: list[LagCorrelation] = []
    commentary: list[str] = []
    insights: list[str]
    data_source: str = "Local fallback"


class ModelEquityPoint(BaseModel):
    date: str
    equity: float
    daily_return_pct: float
    position: float


class ModelBacktestResult(BaseModel):
    name: str
    model_type: str
    file_name: str
    status: str
    message: str
    sharpe_ratio: float
    win_rate_pct: float
    total_return_pct: float
    max_drawdown_pct: float
    trades: int
    exposure_pct: float
    observations: int
    backtest_start: str | None = None
    backtest_end: str | None = None
    features: list[str] = []
    equity_curve: list[ModelEquityPoint] = []


class ModelBacktestOverview(BaseModel):
    generated_at: datetime
    model_folder: str
    evaluation_window: str
    available_features: list[str]
    results: list[ModelBacktestResult]
    instructions: list[str]
    disclaimer: str


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
    bond_charts: list[IndexChart]
    correlations: CorrelationAnalysis
    summary: list[str]
    disclaimer: str
