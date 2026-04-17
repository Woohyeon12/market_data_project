import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.schemas.research import MarketSnapshot

COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def _fallback_btc_market_snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTC",
        price_usd=65000.0,
        change_24h_pct=1.8,
        volume_24h_usd=28_000_000_000.0,
        data_source="Local fallback",
    )


def get_btc_market_snapshot() -> MarketSnapshot:
    query = urlencode({
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
    })
    request = Request(
        f"{COINGECKO_SIMPLE_PRICE_URL}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=10.0) as response:
            payload = json.loads(response.read().decode("utf-8"))

        bitcoin = payload["bitcoin"]

        return MarketSnapshot(
            symbol="BTC",
            price_usd=float(bitcoin["usd"]),
            change_24h_pct=float(bitcoin["usd_24h_change"]),
            volume_24h_usd=float(bitcoin["usd_24h_vol"]),
            data_source="CoinGecko",
        )
    except (HTTPError, URLError, TimeoutError, KeyError, TypeError, ValueError):
        return _fallback_btc_market_snapshot()
