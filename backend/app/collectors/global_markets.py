import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.schemas.research import CorrelationAnalysis, CorrelationCell, IndexChart, IndexChartPoint, MarketInstrument
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
    ("GC=F", "Gold Futures", "Commodities", "Global", "USD", 2300.0, 0.0),
    ("^TNX", "US 10Y Treasury Yield", "Government Bonds", "United States", "USD", 4.5, 0.0),
    ("^TYX", "US 30Y Treasury Yield", "Government Bonds", "United States", "USD", 4.7, 0.0),
    ("^FVX", "US 5Y Treasury Yield", "Government Bonds", "United States", "USD", 4.3, 0.0),
    ("JP10YT=XX", "Japan 10Y Government Bond Yield", "Government Bonds", "Japan", "Yield", 2.4, 0.0),
    ("DE10YT=XX", "Germany 10Y Bund Yield", "Government Bonds", "Germany", "Yield", 2.7, 0.0),
    ("GB10YT=XX", "UK 10Y Gilt Yield", "Government Bonds", "United Kingdom", "Yield", 4.6, 0.0),
]

TRACKED_INDEX_CHARTS = [
    ("BTC-USD", "Bitcoin", "USD", [62000, 63500, 65000, 64200, 66800, 69000, 70500, 69800]),
    ("^GSPC", "S&P 500", "USD", [5000, 5070, 5120, 5090, 5180, 5240, 5310, 5275]),
    ("^IXIC", "Nasdaq Composite", "USD", [15800, 16050, 16240, 16120, 16480, 16810, 17050, 16920]),
    ("^KS11", "KOSPI", "KRW", [2550, 2585, 2610, 2590, 2640, 2675, 2700, 2688]),
    ("^N225", "Nikkei 225", "JPY", [37500, 38100, 38600, 38250, 39000, 39700, 40200, 39900]),
    ("XAUUSD=X", "Gold Spot", "USD", [2300, 2325, 2310, 2350, 2380, 2405, 2390, 2420]),
    ("GC=F", "Gold Futures", "USD", [2300, 2325, 2310, 2350, 2380, 2405, 2390, 2420]),
]

TRACKED_BOND_CHARTS = [
    ("^TNX", "US 10Y Treasury Yield", "Yield", [4.1, 4.2, 4.28, 4.35, 4.31, 4.42, 4.5, 4.47]),
    ("^TYX", "US 30Y Treasury Yield", "Yield", [4.3, 4.4, 4.48, 4.56, 4.52, 4.62, 4.7, 4.68]),
    ("^FVX", "US 5Y Treasury Yield", "Yield", [3.9, 4.0, 4.08, 4.16, 4.11, 4.24, 4.3, 4.28]),
    ("JP10YT=XX", "Japan 10Y Government Bond Yield", "Yield", [1.3, 1.45, 1.6, 1.75, 1.9, 2.05, 2.2, 2.4]),
    ("DE10YT=XX", "Germany 10Y Bund Yield", "Yield", [2.1, 2.18, 2.25, 2.34, 2.42, 2.5, 2.62, 2.7]),
    ("GB10YT=XX", "UK 10Y Gilt Yield", "Yield", [3.8, 3.9, 4.05, 4.18, 4.3, 4.42, 4.52, 4.6]),
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


def get_bond_charts() -> list[IndexChart]:
    return [
        _get_index_chart(*chart)
        for chart in TRACKED_BOND_CHARTS
    ]


def _daily_changes(points: list[IndexChartPoint], lookback_days: int) -> dict[str, float]:
    recent_points = points[-(lookback_days + 1):]
    changes = {}

    for previous, current in zip(recent_points, recent_points[1:]):
        if previous.close == 0:
            continue
        changes[current.date] = ((current.close - previous.close) / previous.close) * 100

    return changes


def _correlation(first: list[float], second: list[float]) -> float:
    if len(first) < 20 or len(second) < 20:
        return 0.0

    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    covariance = sum((x - first_mean) * (y - second_mean) for x, y in zip(first, second))
    first_variance = sum((x - first_mean) ** 2 for x in first)
    second_variance = sum((y - second_mean) ** 2 for y in second)

    if first_variance == 0 or second_variance == 0:
        return 0.0

    return covariance / (first_variance ** 0.5 * second_variance ** 0.5)


def build_correlation_analysis(
    charts: list[IndexChart],
    lookback_days: int = 252,
) -> CorrelationAnalysis:
    changes_by_asset = {
        chart.name: _daily_changes(chart.points, lookback_days)
        for chart in charts
        if len(chart.points) > 30
    }
    assets = list(changes_by_asset)
    matrix = []

    for y_asset in assets:
        for x_asset in assets:
            common_dates = sorted(set(changes_by_asset[x_asset]) & set(changes_by_asset[y_asset]))
            x_values = [changes_by_asset[x_asset][date] for date in common_dates]
            y_values = [changes_by_asset[y_asset][date] for date in common_dates]
            matrix.append(
                CorrelationCell(
                    x=x_asset,
                    y=y_asset,
                    value=round(_correlation(x_values, y_values), 2),
                )
            )

    btc_pairs = [cell for cell in matrix if cell.y == "Bitcoin" and cell.x != "Bitcoin"]
    strongest_positive = max(btc_pairs, key=lambda cell: cell.value, default=None)
    strongest_negative = min(btc_pairs, key=lambda cell: cell.value, default=None)
    insights = [
        f"Correlation uses daily percentage changes over the latest {lookback_days} trading days.",
        "Only assets with at least 30 overlapping daily observations are included in the heatmap.",
    ]
    if strongest_positive:
        insights.append(f"Bitcoin is most positively linked with {strongest_positive.x} at {strongest_positive.value:.2f}.")
    if strongest_negative:
        insights.append(f"Bitcoin is most negatively linked with {strongest_negative.x} at {strongest_negative.value:.2f}.")

    return CorrelationAnalysis(
        lookback_days=lookback_days,
        assets=assets,
        matrix=matrix,
        insights=insights,
        data_source="SQLite OHLC daily changes",
    )
