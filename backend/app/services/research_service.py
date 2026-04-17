from datetime import datetime, timezone

from app.collectors.global_markets import (
    build_correlation_analysis,
    get_bond_charts,
    get_global_markets,
    get_index_charts,
)
from app.collectors.market_data import get_btc_market_snapshot
from app.collectors.news import get_btc_news
from app.models.scenario_model import generate_scenarios
from app.schemas.research import MarketsOverview, ResearchReport


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
    correlations = build_correlation_analysis(index_charts + bond_charts)
    sources = sorted({item.data_source for item in instruments})

    return MarketsOverview(
        generated_at=datetime.now(timezone.utc),
        instruments=instruments,
        index_charts=index_charts,
        bond_charts=bond_charts,
        correlations=correlations,
        summary=[
            "Global market overview includes selected US, Korea, and Japan equities.",
            "Major indices, gold spot, and government bond yields are included for macro context around BTC research.",
            "Correlation analysis compares daily percentage changes across BTC, equities, gold, and bond yields.",
            f"Market data is currently sourced from {', '.join(sources)}.",
        ],
        disclaimer="Market overview is for research only. Not investment advice.",
    )
