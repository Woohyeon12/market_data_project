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

export type MarketsOverview = {
  generated_at: string;
  instruments: MarketInstrument[];
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
    { symbol: "AAPL", name: "Apple", category: "US Stocks", market: "United States", currency: "USD", price: 190, change_pct: 0, data_source: "Local fallback" },
    { symbol: "MSFT", name: "Microsoft", category: "US Stocks", market: "United States", currency: "USD", price: 420, change_pct: 0, data_source: "Local fallback" },
    { symbol: "NVDA", name: "NVIDIA", category: "US Stocks", market: "United States", currency: "USD", price: 900, change_pct: 0, data_source: "Local fallback" },
    { symbol: "005930.KS", name: "Samsung Electronics", category: "Korea Stocks", market: "South Korea", currency: "KRW", price: 75000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "7203.T", name: "Toyota Motor", category: "Japan Stocks", market: "Japan", currency: "JPY", price: 3000, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^GSPC", name: "S&P 500", category: "Indices", market: "United States", currency: "USD", price: 5200, change_pct: 0, data_source: "Local fallback" },
    { symbol: "^KS11", name: "KOSPI", category: "Indices", market: "South Korea", currency: "KRW", price: 2700, change_pct: 0, data_source: "Local fallback" },
    { symbol: "XAUUSD=X", name: "Gold Spot", category: "Commodities", market: "Global", currency: "USD", price: 2300, change_pct: 0, data_source: "Local fallback" },
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
