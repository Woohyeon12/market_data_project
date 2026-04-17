import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.schemas.research import MarketInstrument

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

TRACKED_INSTRUMENTS = [
    ("AAPL", "Apple", "US Stocks", "United States", "USD", 190.0, 0.0),
    ("MSFT", "Microsoft", "US Stocks", "United States", "USD", 420.0, 0.0),
    ("NVDA", "NVIDIA", "US Stocks", "United States", "USD", 900.0, 0.0),
    ("SPY", "SPDR S&P 500 ETF", "US Stocks", "United States", "USD", 500.0, 0.0),
    ("005930.KS", "Samsung Electronics", "Korea Stocks", "South Korea", "KRW", 75000.0, 0.0),
    ("000660.KS", "SK hynix", "Korea Stocks", "South Korea", "KRW", 170000.0, 0.0),
    ("005380.KS", "Hyundai Motor", "Korea Stocks", "South Korea", "KRW", 230000.0, 0.0),
    ("7203.T", "Toyota Motor", "Japan Stocks", "Japan", "JPY", 3000.0, 0.0),
    ("6758.T", "Sony Group", "Japan Stocks", "Japan", "JPY", 13000.0, 0.0),
    ("8306.T", "Mitsubishi UFJ", "Japan Stocks", "Japan", "JPY", 1500.0, 0.0),
    ("^GSPC", "S&P 500", "Indices", "United States", "USD", 5200.0, 0.0),
    ("^IXIC", "Nasdaq Composite", "Indices", "United States", "USD", 16500.0, 0.0),
    ("^KS11", "KOSPI", "Indices", "South Korea", "KRW", 2700.0, 0.0),
    ("^N225", "Nikkei 225", "Indices", "Japan", "JPY", 39000.0, 0.0),
    ("XAUUSD=X", "Gold Spot", "Commodities", "Global", "USD", 2300.0, 0.0),
]


def _fallback_instrument(
    symbol: str,
    name: str,
    category: str,
    market: str,
    currency: str,
    price: float,
    change_pct: float,
) -> MarketInstrument:
    return MarketInstrument(
        symbol=symbol,
        name=name,
        category=category,
        market=market,
        currency=currency,
        price=price,
        change_pct=change_pct,
        data_source="Local fallback",
    )


def _fetch_yahoo_instrument(
    symbol: str,
    name: str,
    category: str,
    market: str,
    currency: str,
    fallback_price: float,
    fallback_change_pct: float,
) -> MarketInstrument:
    request = Request(
        f"{YAHOO_CHART_URL}/{quote(symbol, safe='')}?range=2d&interval=1d",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8"))

        result = payload["chart"]["result"][0]
        meta = result["meta"]
        closes = [
            close
            for close in result["indicators"]["quote"][0]["close"]
            if close is not None
        ]
        price = float(meta.get("regularMarketPrice") or closes[-1])
        previous = float(meta.get("chartPreviousClose") or closes[0])
        change_pct = ((price - previous) / previous) * 100 if previous else 0.0

        return MarketInstrument(
            symbol=symbol,
            name=name,
            category=category,
            market=market,
            currency=meta.get("currency") or currency,
            price=price,
            change_pct=change_pct,
            data_source="Yahoo Finance",
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError):
        return _fallback_instrument(
            symbol,
            name,
            category,
            market,
            currency,
            fallback_price,
            fallback_change_pct,
        )


def get_global_markets() -> list[MarketInstrument]:
    return [
        _fetch_yahoo_instrument(*instrument)
        for instrument in TRACKED_INSTRUMENTS
    ]
