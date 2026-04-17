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

export type MarketsOverview = {
  generated_at: string;
  instruments: MarketInstrument[];
  index_charts: IndexChart[];
  summary: string[];
  disclaimer: string;
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
    { symbol: "005930.KS", name: "Samsung Electronics", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 75000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "7203.T", name: "Toyota Motor", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 3000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^GSPC", name: "S&P 500", category: "Indices", market: "United States", currency: "USD", price: 5200, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^KS11", name: "KOSPI", category: "Indices", market: "South Korea", currency: "KRW", price: 2700, change_pct: 0, data_source: "Local fallback" },
    { symbol: "XAUUSD=X", name: "Gold Spot", category: "Commodities", market: "Global", currency: "USD", price: 2300, change_pct: 0, data_source: "Local fallback" },
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
  ],
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
