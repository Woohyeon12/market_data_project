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


class FinancialStatementPeriod(BaseModel):
    fiscal_date: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    shareholder_equity: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None


class FundamentalMetric(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    interpretation: str


class EquityFundamental(BaseModel):
    symbol: str
    name: str
    market: str
    currency: str
    periods: list[FinancialStatementPeriod]
    metrics: list[FundamentalMetric]
    model_features: dict[str, float]
    data_source: str = "Local fallback"


class FundamentalModelScore(BaseModel):
    model_name: str
    model_type: str
    file_name: str
    symbol: str
    company: str
    score: float
    status: str
    message: str
    features_used: list[str]


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
    gross_equity: float | None = None
    daily_return_pct: float
    gross_daily_return_pct: float | None = None
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


class ModelFeatureImportance(BaseModel):
    feature: str
    importance: float


class ModelSplitMetric(BaseModel):
    model_name: str
    split: int
    start: str
    end: str
    sharpe_ratio: float
    gross_sharpe_ratio: float | None = None
    win_rate_pct: float
    total_return_pct: float
    gross_total_return_pct: float | None = None
    max_drawdown_pct: float
    exposure_pct: float
    trades: int
    total_transaction_cost_pct: float | None = None
    observations: int
    active_observations: int


class ModelSplitCorrelation(BaseModel):
    model_name: str
    split: int
    feature: str
    correlation: float


class KaggleModelResult(BaseModel):
    name: str
    model_type: str
    status: str
    message: str
    sharpe_ratio: float
    gross_sharpe_ratio: float | None = None
    win_rate_pct: float
    total_return_pct: float
    gross_total_return_pct: float | None = None
    max_drawdown_pct: float
    exposure_pct: float
    trades: int
    total_transaction_cost_pct: float | None = None
    observations: int
    active_observations: int
    backtest_start: str | None = None
    backtest_end: str | None = None
    features: list[str] = []
    feature_engineering: list[str] = []
    feature_count: int | None = None
    feature_candidate_count: int | None = None
    selected_feature_count: int | None = None
    feature_selection: dict[str, float | int | str | bool | None] = {}
    interaction_source_count: int | None = None
    regime_features: list[str] = []
    regime_feature_count: int | None = None
    regime_up_train_observations: int | None = None
    regime_down_train_observations: int | None = None
    bull_train_observations: int | None = None
    bear_train_observations: int | None = None
    bull_model_count: int | None = None
    bear_model_count: int | None = None
    ensemble_component_count: int | None = None
    test_regime_up_pct: float | None = None
    regime_notes: list[str] = []
    selected_threshold: float | None = None
    selected_short_threshold: float | None = None
    selected_score_margin: float | None = None
    selected_min_hold_days: int | None = None
    selected_cooldown_days: int | None = None
    selected_uncertainty_margin: float | None = None
    strategy_side: str | None = None
    selected_candidate: str | None = None
    selected_candidate_index: int | None = None
    candidate_count: int | None = None
    selected_validation_score: float | None = None
    selected_hyperparameters: dict = {}
    candidate_trials: list[dict] = []
    validation_sharpe_ratio: float | None = None
    validation_worst_split_sharpe: float | None = None
    validation_last_split_sharpe: float | None = None
    validation_positive_split_count: int | None = None
    validation_split_count: int | None = None
    validation_split_sharpe_std: float | None = None
    validation_recent_decay_penalty: float | None = None
    validation_uncertainty_suppressed_pct: float | None = None
    uncertainty_suppressed_pct: float | None = None
    sharpe_target: float | None = None
    target_met: bool | None = None
    package_candidate: bool | None = None
    rejection_reasons: list[str] = []
    worst_split_sharpe: float | None = None
    positive_split_count: int | None = None
    split_count: int | None = None
    validation_test_sharpe_gap: float | None = None
    transaction_cost_bps: float | None = None
    slippage_bps: float | None = None
    feature_importance: list[ModelFeatureImportance] = []
    split_metrics: list[ModelSplitMetric] = []
    split_correlations: list[ModelSplitCorrelation] = []
    equity_curve: list[ModelEquityPoint] = []


class KaggleModelRun(BaseModel):
    run_id: str
    generated_at: str
    accelerator: str
    high_volume_rule: str
    training_window: str
    validation_window: str | None = None
    backtest_window: str
    batch_size: int
    models_requested: int
    candidate_count_total: int | None = None
    sharpe_target: float | None = None
    transaction_cost_bps: float | None = None
    slippage_bps: float | None = None
    feature_engineering: str | None = None
    base_feature_count: int | None = None
    interaction_source_count: int | None = None
    regime_feature_count: int | None = None
    feature_candidate_count: int | None = None
    selected_feature_count: int | None = None
    final_feature_count: int | None = None
    feature_selection: dict[str, float | int | str | bool | None] = {}
    models: list[KaggleModelResult] = []


class ModelBacktestOverview(BaseModel):
    generated_at: datetime
    model_folder: str
    evaluation_window: str
    available_features: list[str]
    results: list[ModelBacktestResult]
    kaggle_runs: list[KaggleModelRun] = []
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
    equity_fundamentals: list[EquityFundamental] = []
    fundamental_model_scores: list[FundamentalModelScore] = []
    correlations: CorrelationAnalysis
    summary: list[str]
    disclaimer: str
