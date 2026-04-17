import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.schemas.research import IndexChart, IndexChartPoint, MarketInstrument
from app.storage.market_history import (
    count_ohlc_points,
    latest_ohlc_source,
    load_ohlc_points,
    save_ohlc_points,
)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
MIN_HISTORY_POINTS = 1800

TRACKED_INSTRUMENTS = [
    ("BTC-USD", "Bitcoin", "Crypto", "Global", "USD", 65000.0, 0.0),
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

TRACKED_INDEX_CHARTS = [
    ("BTC-USD", "Bitcoin", "USD", [62000, 63500, 65000, 64200, 66800, 69000, 70500, 69800]),
    ("^GSPC", "S&P 500", "USD", [5000, 5070, 5120, 5090, 5180, 5240, 5310, 5275]),
    ("^IXIC", "Nasdaq Composite", "USD", [15800, 16050, 16240, 16120, 16480, 16810, 17050, 16920]),
    ("^KS11", "KOSPI", "KRW", [2550, 2585, 2610, 2590, 2640, 2675, 2700, 2688]),
    ("^N225", "Nikkei 225", "JPY", [37500, 38100, 38600, 38250, 39000, 39700, 40200, 39900]),
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


def _fallback_index_chart(
    symbol: str,
    name: str,
    currency: str,
    closes: list[float],
) -> IndexChart:
    points = [
        IndexChartPoint(
            date=f"Fallback {index + 1}",
            open=closes[index - 1] if index else close * 0.995,
            high=close * 1.01,
            low=close * 0.99,
            close=close,
        )
        for index, close in enumerate(closes)
    ]

    return IndexChart(
        symbol=symbol,
        name=name,
        currency=currency,
        points=points,
        data_source="Local fallback",
    )


def _fetch_yahoo_index_chart(
    symbol: str,
    name: str,
    currency: str,
    fallback_closes: list[float],
) -> IndexChart:
    request = Request(
        f"{YAHOO_CHART_URL}/{quote(symbol, safe='')}?range=10y&interval=1d",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8"))

        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote_data = result["indicators"]["quote"][0]
        opens = quote_data["open"]
        highs = quote_data["high"]
        lows = quote_data["low"]
        closes = quote_data["close"]
        points = []

        for timestamp, open_price, high, low, close in zip(timestamps, opens, highs, lows, closes):
            if open_price is None or high is None or low is None or close is None:
                continue

            points.append(
                IndexChartPoint(
                    date=datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                    open=float(open_price),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                )
            )

        if len(points) < 2:
            return _fallback_index_chart(symbol, name, currency, fallback_closes)

        save_ohlc_points(symbol=symbol, points=points, source="Yahoo Finance")

        return IndexChart(
            symbol=symbol,
            name=name,
            currency=result["meta"].get("currency") or currency,
            points=points,
            data_source=f"Yahoo Finance DB ({len(points)} rows)",
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError):
        return _fallback_index_chart(symbol, name, currency, fallback_closes)


def _get_index_chart(
    symbol: str,
    name: str,
    currency: str,
    fallback_closes: list[float],
) -> IndexChart:
    if count_ohlc_points(symbol) < MIN_HISTORY_POINTS:
        return _fetch_yahoo_index_chart(symbol, name, currency, fallback_closes)

    points = load_ohlc_points(symbol)
    return IndexChart(
        symbol=symbol,
        name=name,
        currency=currency,
        points=points,
        data_source=f"{latest_ohlc_source(symbol) or 'SQLite'} DB ({len(points)} rows)",
    )


def get_global_markets() -> list[MarketInstrument]:
    return [
        _fetch_yahoo_instrument(*instrument)
        for instrument in TRACKED_INSTRUMENTS
    ]


def get_index_charts() -> list[IndexChart]:
    return [
        _get_index_chart(*chart)
        for chart in TRACKED_INDEX_CHARTS
    ]
