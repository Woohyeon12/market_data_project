from datetime import datetime, timezone

from app.collectors.global_markets import get_global_markets
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
    sources = sorted({item.data_source for item in instruments})

    return MarketsOverview(
        generated_at=datetime.now(timezone.utc),
        instruments=instruments,
        summary=[
            "Global market overview includes selected US, Korea, and Japan equities.",
            "Major indices and gold spot are included for macro context around BTC research.",
            f"Market data is currently sourced from {', '.join(sources)}.",
        ],
        disclaimer="Market overview is for research only. Not investment advice.",
    )
