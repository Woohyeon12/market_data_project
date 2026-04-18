export type MarketSnapshot = {
  symbol: string;
  price_usd: number;
  change_24h_pct: number;
  volume_24h_usd: number;
  data_source: string;
};

export type NewsItem = {
  title: string;
  source: string;
  url?: string | null;
  summary?: string | null;
  published_at?: string | null;
  sentiment: string;
  data_source: string;
};

export type Scenario = {
  label: string;
  probability_pct: number;
  rationale: string;
};

export type ResearchReport = {
  asset: string;
  generated_at: string;
  market: MarketSnapshot;
  summary: string[];
  scenarios: Scenario[];
  risks: string[];
  news: NewsItem[];
  disclaimer: string;
};

export type MarketInstrument = {
  symbol: string;
  name: string;
  category: string;
  market: string;
  currency: string;
  price: number;
  change_pct: number;
  data_source: string;
};

export type IndexChartPoint = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type IndexChart = {
  symbol: string;
  name: string;
  currency: string;
  points: IndexChartPoint[];
  data_source: string;
};

export type FinancialStatementPeriod = {
  fiscal_date: string;
  revenue?: number | null;
  gross_profit?: number | null;
  operating_income?: number | null;
  net_income?: number | null;
  total_assets?: number | null;
  total_liabilities?: number | null;
  shareholder_equity?: number | null;
  total_cash?: number | null;
  total_debt?: number | null;
  operating_cash_flow?: number | null;
  capital_expenditure?: number | null;
  free_cash_flow?: number | null;
};

export type FundamentalMetric = {
  key: string;
  label: string;
  value: number;
  unit: string;
  interpretation: string;
};

export type EquityFundamental = {
  symbol: string;
  name: string;
  market: string;
  currency: string;
  periods: FinancialStatementPeriod[];
  metrics: FundamentalMetric[];
  model_features: Record<string, number>;
  data_source: string;
};

export type FundamentalModelScore = {
  model_name: string;
  model_type: string;
  file_name: string;
  symbol: string;
  company: string;
  score: number;
  status: string;
  message: string;
  features_used: string[];
};

export type CorrelationCell = {
  x: string;
  y: string;
  value: number;
};

export type LagCorrelation = {
  feature: string;
  lag_days: number;
  value: number;
};

export type CorrelationAnalysis = {
  lookback_days: number;
  assets: string[];
  matrix: CorrelationCell[];
  lag_correlations: LagCorrelation[];
  commentary: string[];
  insights: string[];
  data_source: string;
};

export type ModelEquityPoint = {
  date: string;
  equity: number;
  gross_equity?: number | null;
  daily_return_pct: number;
  gross_daily_return_pct?: number | null;
  position: number;
};

export type ModelBacktestResult = {
  name: string;
  model_type: string;
  file_name: string;
  status: string;
  message: string;
  sharpe_ratio: number;
  win_rate_pct: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  trades: number;
  exposure_pct: number;
  observations: number;
  backtest_start?: string | null;
  backtest_end?: string | null;
  features: string[];
  equity_curve: ModelEquityPoint[];
};

export type ModelFeatureImportance = {
  feature: string;
  importance: number;
};

export type ModelSplitMetric = {
  model_name: string;
  split: number;
  start: string;
  end: string;
  sharpe_ratio: number;
  gross_sharpe_ratio?: number | null;
  win_rate_pct: number;
  total_return_pct: number;
  gross_total_return_pct?: number | null;
  max_drawdown_pct: number;
  exposure_pct: number;
  trades: number;
  total_transaction_cost_pct?: number | null;
  observations: number;
  active_observations: number;
};

export type ModelSplitCorrelation = {
  model_name: string;
  split: number;
  feature: string;
  correlation: number;
};

export type KaggleModelResult = {
  name: string;
  model_type: string;
  status: string;
  message: string;
  sharpe_ratio: number;
  gross_sharpe_ratio?: number | null;
  win_rate_pct: number;
  total_return_pct: number;
  gross_total_return_pct?: number | null;
  max_drawdown_pct: number;
  exposure_pct: number;
  trades: number;
  total_transaction_cost_pct?: number | null;
  observations: number;
  active_observations: number;
  backtest_start?: string | null;
  backtest_end?: string | null;
  features: string[];
  feature_engineering: string[];
  feature_count?: number | null;
  interaction_source_count?: number | null;
  selected_threshold?: number | null;
  selected_short_threshold?: number | null;
  strategy_side?: string | null;
  validation_sharpe_ratio?: number | null;
  sharpe_target?: number | null;
  target_met?: boolean | null;
  package_candidate?: boolean | null;
  rejection_reasons?: string[];
  worst_split_sharpe?: number | null;
  positive_split_count?: number | null;
  split_count?: number | null;
  validation_test_sharpe_gap?: number | null;
  transaction_cost_bps?: number | null;
  slippage_bps?: number | null;
  feature_importance: ModelFeatureImportance[];
  split_metrics: ModelSplitMetric[];
  split_correlations: ModelSplitCorrelation[];
  equity_curve: ModelEquityPoint[];
};

export type KaggleModelRun = {
  run_id: string;
  generated_at: string;
  accelerator: string;
  high_volume_rule: string;
  training_window: string;
  validation_window?: string | null;
  backtest_window: string;
  batch_size: number;
  models_requested: number;
  sharpe_target?: number | null;
  transaction_cost_bps?: number | null;
  slippage_bps?: number | null;
  feature_engineering?: string | null;
  base_feature_count?: number | null;
  interaction_source_count?: number | null;
  final_feature_count?: number | null;
  models: KaggleModelResult[];
};

export type ModelBacktestOverview = {
  generated_at: string;
  model_folder: string;
  evaluation_window: string;
  available_features: string[];
  results: ModelBacktestResult[];
  kaggle_runs: KaggleModelRun[];
  instructions: string[];
  disclaimer: string;
};

export type MarketsOverview = {
  generated_at: string;
  instruments: MarketInstrument[];
  index_charts: IndexChart[];
  bond_charts: IndexChart[];
  equity_fundamentals: EquityFundamental[];
  fundamental_model_scores: FundamentalModelScore[];
  correlations: CorrelationAnalysis;
  summary: string[];
  disclaimer: string;
};

export const fallbackModelBacktests: ModelBacktestOverview = {
  generated_at: new Date().toISOString(),
  model_folder: "backend/model_registry",
  evaluation_window: "latest 504 trading observations, approximately two years",
  available_features: [
    "btc_return_1d",
    "btc_rsi_14",
    "btc_volatility_20d",
    "btc_drawdown_60d",
    "sp500_return_1d",
    "nasdaq_return_1d",
    "gold_return_1d",
    "us10y_bp_chg",
    "fundamental_revenue_growth_yoy",
    "fundamental_net_margin",
    "fundamental_roe",
    "fundamental_debt_to_equity",
    "fundamental_fcf_margin",
    "fundamental_market_cap_b",
    "fundamental_trailing_pe",
    "fundamental_forward_pe",
    "fundamental_price_to_book",
    "fundamental_price_to_sales",
    "fundamental_ev_to_ebitda",
    "fundamental_dividend_yield",
    "fundamental_beta",
    "fundamental_target_upside",
  ],
  results: [],
  kaggle_runs: [],
  instructions: [
    "Place enabled JSON model files in backend/model_registry.",
    "Each file should include weights or derived_variables keyed by available feature names.",
    "The backend evaluates each signal against next-day BTC returns.",
  ],
  disclaimer: "Backtests are research diagnostics only. They are not live trading recommendations.",
};

export const fallbackReport: ResearchReport = {
  asset: "Bitcoin",
  generated_at: new Date().toISOString(),
  market: {
    symbol: "BTC",
    price_usd: 65000,
    change_24h_pct: 1.8,
    volume_24h_usd: 28000000000,
    data_source: "Local fallback",
  },
  summary: [
    "Backend is not connected yet, so this dashboard is showing starter data.",
    "Add live market, news, and macro collectors as the next feature modules.",
    "Keep predictions scenario-based until a backtest pipeline exists.",
  ],
  scenarios: [
    {
      label: "Upside continuation",
      probability_pct: 45,
      rationale: "Momentum remains constructive in the starter data.",
    },
    {
      label: "Range-bound consolidation",
      probability_pct: 35,
      rationale: "Markets may wait for stronger liquidity or macro signals.",
    },
    {
      label: "Downside retracement",
      probability_pct: 20,
      rationale: "Crypto volatility can invalidate setups quickly.",
    },
  ],
  risks: [
    "Live data is not wired yet.",
    "Model output has not been backtested.",
    "Public deployment needs API keys and rate limits.",
  ],
  news: [
    {
      title: "Starter feed waiting for real news integration",
      source: "Local fallback",
      summary: "News summaries will appear here after the backend fetches the latest BTC feed.",
      sentiment: "neutral",
      data_source: "Local fallback",
    },
  ],
  disclaimer: "Research output only. Not financial advice or a guarantee of future returns.",
};

export const fallbackMarkets: MarketsOverview = {
  generated_at: new Date().toISOString(),
  instruments: [
    { symbol: "BTC-USD", name: "Bitcoin", category: "Crypto", market: "Global", currency: "USD", price: 65000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "AAPL", name: "Apple", category: "US Stocks", market: "United States", currency: "USD", price: 190, change_pct: 0, data_source: "Local fallback" },
    { symbol: "MSFT", name: "Microsoft", category: "US Stocks", market: "United States", currency: "USD", price: 420, change_pct: 0, data_source: "Local fallback" },
    { symbol: "NVDA", name: "NVIDIA", category: "US Stocks", market: "United States", currency: "USD", price: 900, change_pct: 0, data_source: "Local fallback" },
    { symbol: "GOOGL", name: "Alphabet", category: "US Stocks", market: "United States", currency: "USD", price: 170, change_pct: 0, data_source: "Local fallback" },
    { symbol: "AMZN", name: "Amazon", category: "US Stocks", market: "United States", currency: "USD", price: 180, change_pct: 0, data_source: "Local fallback" },
    { symbol: "META", name: "Meta Platforms", category: "US Stocks", market: "United States", currency: "USD", price: 480, change_pct: 0, data_source: "Local fallback" },
    { symbol: "TSLA", name: "Tesla", category: "US Stocks", market: "United States", currency: "USD", price: 240, change_pct: 0, data_source: "Local fallback" },
    { symbol: "005930.KS", name: "Samsung Electronics", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 75000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "000660.KS", name: "SK hynix", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 170000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "005380.KS", name: "Hyundai Motor", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 230000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "373220.KS", name: "LG Energy Solution", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 400000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "7203.T", name: "Toyota Motor", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 3000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "6758.T", name: "Sony Group", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 13000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "9984.T", name: "SoftBank Group", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 8500, change_pct: 0, data_source: "Local fallback" },
    { symbol: "6861.T", name: "Keyence", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 70000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^GSPC", name: "S&P 500", category: "Indices", market: "United States", currency: "USD", price: 5200, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^KS11", name: "KOSPI", category: "Indices", market: "South Korea", currency: "KRW", price: 2700, change_pct: 0, data_source: "Local fallback" },
    { symbol: "XAUUSD=X", name: "Gold Spot", category: "Commodities", market: "Global", currency: "USD", price: 2300, change_pct: 0, data_source: "Local fallback" },
    { symbol: "GC=F", name: "Gold Futures", category: "Commodities", market: "Global", currency: "USD", price: 2300, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^TNX", name: "US 10Y Treasury Yield", category: "Government Bonds", market: "United States", currency: "USD", price: 4.5, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^TYX", name: "US 30Y Treasury Yield", category: "Government Bonds", market: "United States", currency: "USD", price: 4.7, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^FVX", name: "US 5Y Treasury Yield", category: "Government Bonds", market: "United States", currency: "USD", price: 4.3, change_pct: 0, data_source: "Local fallback" },
    { symbol: "JP10YT=XX", name: "Japan 10Y Government Bond Yield", category: "Government Bonds", market: "Japan", currency: "Yield", price: 2.4, change_pct: 0, data_source: "Local fallback" },
    { symbol: "DE10YT=XX", name: "Germany 10Y Bund Yield", category: "Government Bonds", market: "Germany", currency: "Yield", price: 2.7, change_pct: 0, data_source: "Local fallback" },
    { symbol: "GB10YT=XX", name: "UK 10Y Gilt Yield", category: "Government Bonds", market: "United Kingdom", currency: "Yield", price: 4.6, change_pct: 0, data_source: "Local fallback" },
  ],
  index_charts: [
    { symbol: "BTC-USD", name: "Bitcoin", currency: "USD", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 61690, high: 62620, low: 61380, close: 62000 },
      { date: "Fallback 2", open: 62000, high: 64135, low: 62865, close: 63500 },
      { date: "Fallback 3", open: 63500, high: 65650, low: 64350, close: 65000 },
      { date: "Fallback 4", open: 65000, high: 64842, low: 63558, close: 64200 },
      { date: "Fallback 5", open: 64200, high: 67468, low: 66132, close: 66800 },
      { date: "Fallback 6", open: 66800, high: 69690, low: 68310, close: 69000 },
      { date: "Fallback 7", open: 69000, high: 71205, low: 69795, close: 70500 },
    ] },
    { symbol: "^GSPC", name: "S&P 500", currency: "USD", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 4975, high: 5050, low: 4950, close: 5000 },
      { date: "Fallback 2", open: 5000, high: 5121, low: 5019, close: 5070 },
      { date: "Fallback 3", open: 5070, high: 5171, low: 5069, close: 5120 },
      { date: "Fallback 4", open: 5120, high: 5141, low: 5039, close: 5090 },
      { date: "Fallback 5", open: 5090, high: 5232, low: 5128, close: 5180 },
      { date: "Fallback 6", open: 5180, high: 5292, low: 5188, close: 5240 },
      { date: "Fallback 7", open: 5240, high: 5363, low: 5257, close: 5310 },
    ] },
    { symbol: "^IXIC", name: "Nasdaq Composite", currency: "USD", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 15721, high: 15958, low: 15642, close: 15800 },
      { date: "Fallback 2", open: 15800, high: 16211, low: 15890, close: 16050 },
      { date: "Fallback 3", open: 16050, high: 16402, low: 16078, close: 16240 },
      { date: "Fallback 4", open: 16240, high: 16281, low: 15959, close: 16120 },
      { date: "Fallback 5", open: 16120, high: 16645, low: 16315, close: 16480 },
      { date: "Fallback 6", open: 16480, high: 16978, low: 16642, close: 16810 },
      { date: "Fallback 7", open: 16810, high: 17221, low: 16880, close: 17050 },
    ] },
    { symbol: "^KS11", name: "KOSPI", currency: "KRW", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 2537, high: 2576, low: 2525, close: 2550 },
      { date: "Fallback 2", open: 2550, high: 2611, low: 2559, close: 2585 },
      { date: "Fallback 3", open: 2585, high: 2636, low: 2584, close: 2610 },
      { date: "Fallback 4", open: 2610, high: 2636, low: 2564, close: 2590 },
      { date: "Fallback 5", open: 2590, high: 2666, low: 2614, close: 2640 },
      { date: "Fallback 6", open: 2640, high: 2702, low: 2648, close: 2675 },
      { date: "Fallback 7", open: 2675, high: 2727, low: 2673, close: 2700 },
    ] },
    { symbol: "^N225", name: "Nikkei 225", currency: "JPY", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 37312, high: 37875, low: 37125, close: 37500 },
      { date: "Fallback 2", open: 37500, high: 38481, low: 37719, close: 38100 },
      { date: "Fallback 3", open: 38100, high: 38986, low: 38214, close: 38600 },
      { date: "Fallback 4", open: 38600, high: 39038, low: 37868, close: 38250 },
      { date: "Fallback 5", open: 38250, high: 39390, low: 38610, close: 39000 },
      { date: "Fallback 6", open: 39000, high: 40097, low: 39303, close: 39700 },
      { date: "Fallback 7", open: 39700, high: 40602, low: 39798, close: 40200 },
    ] },
    { symbol: "GC=F", name: "Gold Futures", currency: "USD", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 2288, high: 2323, low: 2277, close: 2300 },
      { date: "Fallback 2", open: 2300, high: 2348, low: 2302, close: 2325 },
      { date: "Fallback 3", open: 2325, high: 2333, low: 2287, close: 2310 },
      { date: "Fallback 4", open: 2310, high: 2374, low: 2327, close: 2350 },
      { date: "Fallback 5", open: 2350, high: 2404, low: 2356, close: 2380 },
      { date: "Fallback 6", open: 2380, high: 2429, low: 2381, close: 2405 },
      { date: "Fallback 7", open: 2405, high: 2414, low: 2366, close: 2390 },
    ] },
  ],
  bond_charts: [
    { symbol: "^TNX", name: "US 10Y Treasury Yield", currency: "Yield", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 4.08, high: 4.14, low: 4.06, close: 4.1 },
      { date: "Fallback 2", open: 4.1, high: 4.24, low: 4.16, close: 4.2 },
      { date: "Fallback 3", open: 4.2, high: 4.32, low: 4.24, close: 4.28 },
      { date: "Fallback 4", open: 4.28, high: 4.39, low: 4.31, close: 4.35 },
      { date: "Fallback 5", open: 4.35, high: 4.35, low: 4.27, close: 4.31 },
      { date: "Fallback 6", open: 4.31, high: 4.46, low: 4.38, close: 4.42 },
      { date: "Fallback 7", open: 4.42, high: 4.55, low: 4.46, close: 4.5 },
    ] },
    { symbol: "^TYX", name: "US 30Y Treasury Yield", currency: "Yield", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 4.28, high: 4.34, low: 4.26, close: 4.3 },
      { date: "Fallback 2", open: 4.3, high: 4.44, low: 4.36, close: 4.4 },
      { date: "Fallback 3", open: 4.4, high: 4.52, low: 4.44, close: 4.48 },
      { date: "Fallback 4", open: 4.48, high: 4.6, low: 4.51, close: 4.56 },
      { date: "Fallback 5", open: 4.56, high: 4.57, low: 4.47, close: 4.52 },
      { date: "Fallback 6", open: 4.52, high: 4.66, low: 4.57, close: 4.62 },
      { date: "Fallback 7", open: 4.62, high: 4.75, low: 4.65, close: 4.7 },
    ] },
    { symbol: "JP10YT=XX", name: "Japan 10Y Government Bond Yield", currency: "Yield", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 1.29, high: 1.31, low: 1.27, close: 1.3 },
      { date: "Fallback 2", open: 1.3, high: 1.47, low: 1.43, close: 1.45 },
      { date: "Fallback 3", open: 1.45, high: 1.62, low: 1.58, close: 1.6 },
      { date: "Fallback 4", open: 1.6, high: 1.77, low: 1.72, close: 1.75 },
      { date: "Fallback 5", open: 1.75, high: 1.92, low: 1.87, close: 1.9 },
      { date: "Fallback 6", open: 1.9, high: 2.07, low: 2.02, close: 2.05 },
      { date: "Fallback 7", open: 2.05, high: 2.23, low: 2.17, close: 2.2 },
    ] },
    { symbol: "DE10YT=XX", name: "Germany 10Y Bund Yield", currency: "Yield", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 2.09, high: 2.12, low: 2.07, close: 2.1 },
      { date: "Fallback 2", open: 2.1, high: 2.2, low: 2.16, close: 2.18 },
      { date: "Fallback 3", open: 2.18, high: 2.27, low: 2.22, close: 2.25 },
      { date: "Fallback 4", open: 2.25, high: 2.36, low: 2.31, close: 2.34 },
      { date: "Fallback 5", open: 2.34, high: 2.44, low: 2.39, close: 2.42 },
      { date: "Fallback 6", open: 2.42, high: 2.52, low: 2.47, close: 2.5 },
      { date: "Fallback 7", open: 2.5, high: 2.65, low: 2.59, close: 2.62 },
    ] },
    { symbol: "GB10YT=XX", name: "UK 10Y Gilt Yield", currency: "Yield", data_source: "Local fallback", points: [
      { date: "Fallback 1", open: 3.78, high: 3.84, low: 3.76, close: 3.8 },
      { date: "Fallback 2", open: 3.8, high: 3.94, low: 3.86, close: 3.9 },
      { date: "Fallback 3", open: 3.9, high: 4.09, low: 4.01, close: 4.05 },
      { date: "Fallback 4", open: 4.05, high: 4.22, low: 4.13, close: 4.18 },
      { date: "Fallback 5", open: 4.18, high: 4.34, low: 4.26, close: 4.3 },
      { date: "Fallback 6", open: 4.3, high: 4.46, low: 4.38, close: 4.42 },
      { date: "Fallback 7", open: 4.42, high: 4.56, low: 4.48, close: 4.52 },
    ] },
  ],
  equity_fundamentals: [
    {
      symbol: "AAPL",
      name: "Apple",
      market: "United States",
      currency: "USD",
      data_source: "Local fallback fundamentals",
      periods: [
        {
          fiscal_date: "2025-12-31",
          revenue: 383285000000,
          gross_profit: 160979700000,
          operating_income: 91988400000,
          net_income: 96995000000,
          total_assets: 352583000000,
          total_liabilities: 290437000000,
          shareholder_equity: 62146000000,
          total_cash: 42309960000,
          total_debt: 19886720000,
          operating_cash_flow: 76657000000,
          capital_expenditure: -22997100000,
          free_cash_flow: 53659900000,
        },
      ],
      metrics: [
        { key: "revenue_growth_yoy", label: "Revenue growth YoY", value: 7.5, unit: "%", interpretation: "Top-line growth from the prior fiscal year." },
        { key: "net_margin", label: "Net margin", value: 25.3, unit: "%", interpretation: "Bottom-line profitability after all costs." },
        { key: "roe", label: "ROE", value: 156.1, unit: "%", interpretation: "Net income generated per unit of equity." },
        { key: "debt_to_equity", label: "Debt / equity", value: 0.32, unit: "x", interpretation: "Balance-sheet leverage." },
        { key: "market_cap_b", label: "Market cap", value: 2327.9, unit: "B", interpretation: "Equity market value in local-currency billions." },
        { key: "trailing_pe", label: "PER (TTM)", value: 24.0, unit: "x", interpretation: "Price divided by trailing earnings per share." },
        { key: "price_to_book", label: "P/B", value: 37.5, unit: "x", interpretation: "Price relative to book value." },
        { key: "dividend_yield", label: "Dividend yield", value: 1.2, unit: "%", interpretation: "Dividend yield from current market pricing." },
      ],
      model_features: {
        fundamental_revenue_growth_yoy: 7.5,
        fundamental_net_margin: 25.3,
        fundamental_roe: 156.1,
        fundamental_debt_to_equity: 0.32,
        fundamental_market_cap_b: 2327.9,
        fundamental_trailing_pe: 24.0,
        fundamental_price_to_book: 37.5,
        fundamental_dividend_yield: 1.2,
      },
    },
  ],
  fundamental_model_scores: [],
  correlations: {
    lookback_days: 252,
    assets: ["BTC return", "S&P 500 return", "US 10Y bp chg", "BTC RSI(14)"],
    matrix: [
      { x: "BTC return", y: "BTC return", value: 1 },
      { x: "S&P 500 return", y: "BTC return", value: 0.35 },
      { x: "US 10Y bp chg", y: "BTC return", value: -0.12 },
      { x: "BTC RSI(14)", y: "BTC return", value: 0.18 },
      { x: "BTC return", y: "S&P 500 return", value: 0.35 },
      { x: "S&P 500 return", y: "S&P 500 return", value: 1 },
      { x: "US 10Y bp chg", y: "S&P 500 return", value: -0.18 },
      { x: "BTC RSI(14)", y: "S&P 500 return", value: 0.12 },
      { x: "BTC return", y: "US 10Y bp chg", value: -0.12 },
      { x: "S&P 500 return", y: "US 10Y bp chg", value: -0.18 },
      { x: "US 10Y bp chg", y: "US 10Y bp chg", value: 1 },
      { x: "BTC RSI(14)", y: "US 10Y bp chg", value: -0.08 },
      { x: "BTC return", y: "BTC RSI(14)", value: 0.18 },
      { x: "S&P 500 return", y: "BTC RSI(14)", value: 0.12 },
      { x: "US 10Y bp chg", y: "BTC RSI(14)", value: -0.08 },
      { x: "BTC RSI(14)", y: "BTC RSI(14)", value: 1 },
    ],
    lag_correlations: [
      { feature: "S&P 500 return", lag_days: 1, value: 0.18 },
      { feature: "US 10Y bp chg", lag_days: 5, value: -0.1 },
      { feature: "BTC RSI(14)", lag_days: 20, value: 0.08 },
    ],
    commentary: [
      "This is an explanatory research signal map, not a causal model or investment recommendation.",
      "Live commentary will appear after the backend feature engine responds.",
    ],
    insights: [
      "Feature heatmap is waiting for backend data.",
      "Fallback values are placeholders for layout continuity.",
    ],
    data_source: "Local fallback",
  },
  summary: [
    "Global market overview is waiting for backend data.",
    "Fallback prices are placeholders for layout continuity.",
  ],
  disclaimer: "Market overview is for research only. Not investment advice.",
};

export async function fetchBtcResearch(): Promise<ResearchReport> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}/research/btc`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return fallbackReport;
    }

    return response.json();
  } catch {
    return fallbackReport;
  }
}

export async function fetchMarketsOverview(): Promise<MarketsOverview> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}/research/markets`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return fallbackMarkets;
    }

    return response.json();
  } catch {
    return fallbackMarkets;
  }
}

export async function fetchModelBacktests(): Promise<ModelBacktestOverview> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${baseUrl}/research/model-backtests`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return fallbackModelBacktests;
    }

    return response.json();
  } catch {
    return fallbackModelBacktests;
  }
}
