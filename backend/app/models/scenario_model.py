from app.schemas.research import MarketSnapshot, NewsItem, Scenario


def generate_scenarios(
    market: MarketSnapshot,
    news: list[NewsItem],
) -> list[Scenario]:
    positive_news = sum(1 for item in news if item.sentiment == "positive")
    negative_news = sum(1 for item in news if item.sentiment == "negative")

    if market.change_24h_pct > 0 and positive_news >= negative_news:
        upside = 45
        sideways = 35
        downside = 20
    else:
        upside = 30
        sideways = 40
        downside = 30

    return [
        Scenario(
            label="Upside continuation",
            probability_pct=upside,
            rationale="Momentum and news tone are constructive, but confirmation requires sustained volume.",
        ),
        Scenario(
            label="Range-bound consolidation",
            probability_pct=sideways,
            rationale="Market may digest recent moves while traders wait for macro or liquidity signals.",
        ),
        Scenario(
            label="Downside retracement",
            probability_pct=downside,
            rationale="High volatility and sudden liquidity shifts can quickly invalidate bullish setups.",
        ),
    ]
