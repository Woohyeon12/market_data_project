from datetime import datetime, timezone

from app.collectors.global_markets import (
    build_correlation_analysis,
    get_bond_charts,
    get_global_markets,
    get_index_charts,
)
from app.collectors.financials import get_equity_fundamentals, score_fundamental_models
from app.collectors.market_data import get_btc_market_snapshot
from app.collectors.news import get_btc_news
from app.models.scenario_model import generate_scenarios
from app.schemas.research import MarketsOverview, ResearchReport
from app.services.model_backtest import MODEL_FOLDER


def build_btc_report() -> ResearchReport:
    market = get_btc_market_snapshot()
    news = get_btc_news()
    scenarios = generate_scenarios(market=market, news=news)
    news_sources = sorted({item.data_source for item in news})

    return ResearchReport(
        asset="Bitcoin",
        generated_at=datetime.now(timezone.utc),
        market=market,
        summary=[
            f"BTC market data is currently sourced from {market.data_source}.",
            f"News signals are currently sourced from {', '.join(news_sources)}.",
            "Major BTC news summaries are cached for three hours to keep the research feed fresh without overusing public feeds.",
            "The initial model favors scenario-based research over direct investment advice.",
            "Add report history and backtests before public launch.",
        ],
        scenarios=scenarios,
        risks=[
            "Predictions are untested until a backtesting pipeline is added.",
            "Crypto markets can move sharply around macro data, liquidity changes, and exchange events.",
            "Public APIs need rate limits and authentication before production use.",
        ],
        news=news,
        disclaimer="Research output only. Not financial advice or a guarantee of future returns.",
    )


def build_markets_overview() -> MarketsOverview:
    instruments = get_global_markets()
    index_charts = get_index_charts()
    bond_charts = get_bond_charts()
    equity_fundamentals = get_equity_fundamentals()
    fundamental_model_scores = score_fundamental_models(equity_fundamentals, MODEL_FOLDER)
    correlations = build_correlation_analysis(index_charts + bond_charts)
    sources = sorted({item.data_source for item in instruments})
    fundamental_sources = sorted({item.data_source for item in equity_fundamentals})

    return MarketsOverview(
        generated_at=datetime.now(timezone.utc),
        instruments=instruments,
        index_charts=index_charts,
        bond_charts=bond_charts,
        equity_fundamentals=equity_fundamentals,
        fundamental_model_scores=fundamental_model_scores,
        correlations=correlations,
        summary=[
            "Global market overview includes selected US, Korea, and Japan equities.",
            "Major indices, gold spot, and government bond yields are included for macro context around BTC research.",
            "Equity fundamentals include annual statements plus derived profitability, leverage, growth, and cash-flow metrics.",
            "Feature correlation heatmap compares BTC returns, market returns, yield changes, RSI, volatility, and drawdown factors.",
            "Lead-lag correlation checks whether features tend to move before BTC over 1, 5, and 20 trading day windows.",
            f"Market data is currently sourced from {', '.join(sources)}.",
            f"Fundamental data is currently sourced from {', '.join(fundamental_sources)}.",
        ],
        disclaimer="Market overview is for research only. Not investment advice.",
    )
