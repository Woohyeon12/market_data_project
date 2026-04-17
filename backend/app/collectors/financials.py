import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.collectors.global_markets import TRACKED_INSTRUMENTS
from app.schemas.research import (
    EquityFundamental,
    FinancialStatementPeriod,
    FundamentalMetric,
    FundamentalModelScore,
)

YAHOO_SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
YAHOO_TIMESERIES_URL = "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries"
YAHOO_TIMESERIES_TYPES = [
    "annualTotalRevenue",
    "annualGrossProfit",
    "annualOperatingIncome",
    "annualNetIncome",
    "annualTotalAssets",
    "annualTotalLiabilitiesNetMinorityInterest",
    "annualStockholdersEquity",
    "annualCashAndCashEquivalents",
    "annualTotalDebt",
    "annualOperatingCashFlow",
    "annualCapitalExpenditure",
    "trailingMarketCap",
    "quarterlyMarketCap",
    "trailingPeRatio",
    "quarterlyPeRatio",
    "trailingForwardPeRatio",
]
FUNDAMENTAL_MODEL_FEATURES = [
    "fundamental_revenue_growth_yoy",
    "fundamental_gross_margin",
    "fundamental_operating_margin",
    "fundamental_net_margin",
    "fundamental_roe",
    "fundamental_roa",
    "fundamental_debt_to_equity",
    "fundamental_fcf_margin",
    "fundamental_market_cap_b",
    "fundamental_trailing_pe",
    "fundamental_forward_pe",
    "fundamental_price_to_book",
    "fundamental_price_to_sales",
    "fundamental_ev_to_ebitda",
    "fundamental_dividend_yield",
    "fundamental_beta",
    "fundamental_target_upside",
]

STOCK_UNIVERSE = [
    item for item in TRACKED_INSTRUMENTS
    if item[2] in {"US Stocks", "Korea Stocks", "Japan Stocks"} and item[0] != "SPY"
]

FALLBACK_BASES = {
    "AAPL": (383_285_000_000, 96_995_000_000, 352_583_000_000, 62_146_000_000),
    "MSFT": (245_122_000_000, 88_136_000_000, 512_163_000_000, 268_477_000_000),
    "NVDA": (60_922_000_000, 29_760_000_000, 65_728_000_000, 43_009_000_000),
    "GOOGL": (307_394_000_000, 73_795_000_000, 402_392_000_000, 283_379_000_000),
    "AMZN": (574_785_000_000, 30_425_000_000, 527_854_000_000, 201_875_000_000),
    "META": (134_902_000_000, 39_098_000_000, 229_623_000_000, 153_168_000_000),
    "TSLA": (96_773_000_000, 14_974_000_000, 106_618_000_000, 62_634_000_000),
    "BRK-B": (364_482_000_000, 96_223_000_000, 1_069_978_000_000, 561_273_000_000),
    "JPM": (158_104_000_000, 49_552_000_000, 3_875_393_000_000, 327_878_000_000),
    "AVGO": (35_819_000_000, 14_082_000_000, 72_861_000_000, 23_587_000_000),
    "005930.KS": (258_935_000_000_000, 15_487_000_000_000, 455_906_000_000_000, 363_678_000_000_000),
    "000660.KS": (32_766_000_000_000, -9_137_000_000_000, 100_330_000_000_000, 53_290_000_000_000),
    "005380.KS": (162_664_000_000_000, 12_272_000_000_000, 282_463_000_000_000, 106_478_000_000_000),
    "000270.KS": (99_808_000_000_000, 8_777_000_000_000, 79_233_000_000_000, 43_121_000_000_000),
    "373220.KS": (33_745_000_000_000, 1_638_000_000_000, 45_746_000_000_000, 28_310_000_000_000),
    "207940.KS": (3_694_000_000_000, 858_000_000_000, 16_161_000_000_000, 9_558_000_000_000),
    "035420.KS": (9_671_000_000_000, 985_000_000_000, 36_252_000_000_000, 24_762_000_000_000),
    "035720.KS": (7_557_000_000_000, 206_000_000_000, 24_567_000_000_000, 16_187_000_000_000),
    "055550.KS": (14_642_000_000_000, 4_368_000_000_000, 734_779_000_000_000, 58_813_000_000_000),
    "7203.T": (45_095_000_000_000, 4_945_000_000_000, 90_114_000_000_000, 34_338_000_000_000),
    "6758.T": (13_020_000_000_000, 970_000_000_000, 34_107_000_000_000, 7_999_000_000_000),
    "8306.T": (11_890_000_000_000, 1_491_000_000_000, 403_703_000_000_000, 18_272_000_000_000),
    "9984.T": (6_756_000_000_000, 227_000_000_000, 45_512_000_000_000, 12_936_000_000_000),
    "6861.T": (967_000_000_000, 363_000_000_000, 2_996_000_000_000, 2_679_000_000_000),
    "8035.T": (2_209_000_000_000, 363_000_000_000, 2_597_000_000_000, 1_865_000_000_000),
    "9983.T": (2_766_000_000_000, 296_000_000_000, 3_780_000_000_000, 1_817_000_000_000),
    "9432.T": (13_136_000_000_000, 1_279_000_000_000, 29_604_000_000_000, 9_191_000_000_000),
    "8058.T": (19_567_000_000_000, 964_000_000_000, 23_456_000_000_000, 7_442_000_000_000),
}


def _raw(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("raw")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _date(value: object) -> str:
    if isinstance(value, dict):
        if value.get("fmt"):
            return str(value["fmt"])
        raw_value = value.get("raw")
        if raw_value:
            from datetime import datetime, timezone

            return datetime.fromtimestamp(float(raw_value), tz=timezone.utc).date().isoformat()
    return str(value or "Unknown")


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _quote_section(payload: dict, name: str) -> dict:
    result = payload.get("quoteSummary", {}).get("result") or []
    if not result:
        return {}

    section = result[0].get(name, {})
    return section if isinstance(section, dict) else {}


def _percent_from_decimal(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 100 if abs(value) <= 1 else value


def _quote_metrics(payload: dict) -> dict[str, float]:
    summary = _quote_section(payload, "summaryDetail")
    stats = _quote_section(payload, "defaultKeyStatistics")
    financial = _quote_section(payload, "financialData")
    price = _quote_section(payload, "price")
    current_price = _raw(price.get("regularMarketPrice")) or _raw(financial.get("currentPrice"))
    target_price = _raw(financial.get("targetMeanPrice"))
    target_upside = None
    if current_price not in (None, 0) and target_price is not None:
        target_upside = ((target_price - current_price) / current_price) * 100

    values = {
        "market_cap": _raw(price.get("marketCap")) or _raw(summary.get("marketCap")),
        "trailing_pe": _raw(summary.get("trailingPE")) or _raw(stats.get("trailingPE")),
        "forward_pe": _raw(summary.get("forwardPE")) or _raw(stats.get("forwardPE")),
        "price_to_book": _raw(stats.get("priceToBook")),
        "price_to_sales": _raw(stats.get("priceToSalesTrailing12Months")),
        "ev_to_ebitda": _raw(stats.get("enterpriseToEbitda")),
        "dividend_yield": _percent_from_decimal(_raw(summary.get("dividendYield"))),
        "beta": _raw(summary.get("beta")) or _raw(stats.get("beta")),
        "target_upside": target_upside,
        "return_on_equity": _percent_from_decimal(_raw(financial.get("returnOnEquity"))),
    }
    return {key: value for key, value in values.items() if value is not None}


def _timeseries_items(payload: dict, type_name: str) -> list[dict]:
    for item in payload.get("timeseries", {}).get("result", []):
        meta_types = item.get("meta", {}).get("type", [])
        if type_name in meta_types and isinstance(item.get(type_name), list):
            return item[type_name]
    return []


def _timeseries_value(row: dict) -> float | None:
    return _raw(row.get("reportedValue"))


def _timeseries_by_date(payload: dict, type_name: str) -> dict[str, float]:
    values = {}
    for row in _timeseries_items(payload, type_name):
        date = row.get("asOfDate")
        value = _timeseries_value(row)
        if isinstance(date, str) and value is not None:
            values[date] = value
    return values


def _latest_timeseries_value(payload: dict, *type_names: str) -> float | None:
    rows = []
    for type_name in type_names:
        rows.extend(_timeseries_items(payload, type_name))
    dated_rows = [
        row
        for row in rows
        if isinstance(row.get("asOfDate"), str) and _timeseries_value(row) is not None
    ]
    if not dated_rows:
        return None
    latest = max(dated_rows, key=lambda row: row["asOfDate"])
    return _timeseries_value(latest)


def _normalized_capex(value: float | None) -> float | None:
    if value is None:
        return None
    return -abs(value)


def _free_cash_flow(operating_cash_flow: float | None, capital_expenditure: float | None) -> float | None:
    if operating_cash_flow is None or capital_expenditure is None:
        return None
    return operating_cash_flow - abs(capital_expenditure)


def _merge_timeseries_statements(payload: dict) -> list[FinancialStatementPeriod]:
    revenue = _timeseries_by_date(payload, "annualTotalRevenue")
    gross_profit = _timeseries_by_date(payload, "annualGrossProfit")
    operating_income = _timeseries_by_date(payload, "annualOperatingIncome")
    net_income = _timeseries_by_date(payload, "annualNetIncome")
    total_assets = _timeseries_by_date(payload, "annualTotalAssets")
    total_liabilities = _timeseries_by_date(payload, "annualTotalLiabilitiesNetMinorityInterest")
    shareholder_equity = _timeseries_by_date(payload, "annualStockholdersEquity")
    total_cash = _timeseries_by_date(payload, "annualCashAndCashEquivalents")
    total_debt = _timeseries_by_date(payload, "annualTotalDebt")
    operating_cash_flow = _timeseries_by_date(payload, "annualOperatingCashFlow")
    capital_expenditure = _timeseries_by_date(payload, "annualCapitalExpenditure")

    dates = sorted(
        set(revenue)
        | set(net_income)
        | set(total_assets)
        | set(shareholder_equity),
        reverse=True,
    )
    periods = []
    for fiscal_date in dates[:4]:
        capex = _normalized_capex(capital_expenditure.get(fiscal_date))
        operating_cf = operating_cash_flow.get(fiscal_date)
        periods.append(
            FinancialStatementPeriod(
                fiscal_date=fiscal_date,
                revenue=revenue.get(fiscal_date),
                gross_profit=gross_profit.get(fiscal_date),
                operating_income=operating_income.get(fiscal_date),
                net_income=net_income.get(fiscal_date),
                total_assets=total_assets.get(fiscal_date),
                total_liabilities=total_liabilities.get(fiscal_date),
                shareholder_equity=shareholder_equity.get(fiscal_date),
                total_cash=total_cash.get(fiscal_date),
                total_debt=total_debt.get(fiscal_date),
                operating_cash_flow=operating_cf,
                capital_expenditure=capex,
                free_cash_flow=_free_cash_flow(operating_cf, capex),
            )
        )
    return periods


def _timeseries_quote_metrics(payload: dict, periods: list[FinancialStatementPeriod]) -> dict[str, float]:
    latest = periods[0] if periods else None
    market_cap = _latest_timeseries_value(payload, "trailingMarketCap", "quarterlyMarketCap")
    trailing_pe = _latest_timeseries_value(payload, "trailingPeRatio", "quarterlyPeRatio")
    forward_pe = _latest_timeseries_value(payload, "trailingForwardPeRatio")
    values = {
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
    }
    if latest and market_cap is not None:
        values.update({
            "price_to_book": _safe_ratio(market_cap, latest.shareholder_equity),
            "price_to_sales": _safe_ratio(market_cap, latest.revenue),
        })
    return {key: value for key, value in values.items() if value is not None}


def _fallback_quote_metrics(periods: list[FinancialStatementPeriod]) -> dict[str, float]:
    latest = periods[0] if periods else None
    if not latest:
        return {}

    if latest.net_income and latest.net_income > 0:
        market_cap = latest.net_income * 24
    elif latest.revenue:
        market_cap = latest.revenue * 1.4
    else:
        market_cap = 0.0

    trailing_pe = _safe_ratio(market_cap, latest.net_income if latest.net_income and latest.net_income > 0 else None)
    values = {
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "forward_pe": (trailing_pe * 0.9) if trailing_pe else None,
        "price_to_book": _safe_ratio(market_cap, latest.shareholder_equity) or 0.0,
        "price_to_sales": _safe_ratio(market_cap, latest.revenue) or 0.0,
        "ev_to_ebitda": 14.0,
        "dividend_yield": 1.2,
        "beta": 1.0,
        "target_upside": 0.0,
    }
    return {key: value for key, value in values.items() if value is not None}


def _merge_statements(payload: dict) -> list[FinancialStatementPeriod]:
    result = payload["quoteSummary"]["result"][0]
    income = result.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
    balance = result.get("balanceSheetHistory", {}).get("balanceSheetStatements", [])
    cashflow = result.get("cashflowStatementHistory", {}).get("cashflowStatements", [])
    rows: dict[str, dict] = {}

    for statement in income:
        date = _date(statement.get("endDate"))
        rows.setdefault(date, {})["income"] = statement
    for statement in balance:
        date = _date(statement.get("endDate"))
        rows.setdefault(date, {})["balance"] = statement
    for statement in cashflow:
        date = _date(statement.get("endDate"))
        rows.setdefault(date, {})["cashflow"] = statement

    periods = []
    for fiscal_date in sorted(rows, reverse=True):
        income_row = rows[fiscal_date].get("income", {})
        balance_row = rows[fiscal_date].get("balance", {})
        cashflow_row = rows[fiscal_date].get("cashflow", {})
        operating_cash_flow = _raw(cashflow_row.get("totalCashFromOperatingActivities"))
        capital_expenditure = _raw(cashflow_row.get("capitalExpenditures"))
        free_cash_flow = None
        if operating_cash_flow is not None and capital_expenditure is not None:
            free_cash_flow = operating_cash_flow + capital_expenditure

        periods.append(
            FinancialStatementPeriod(
                fiscal_date=fiscal_date,
                revenue=_raw(income_row.get("totalRevenue")),
                gross_profit=_raw(income_row.get("grossProfit")),
                operating_income=_raw(income_row.get("operatingIncome")),
                net_income=_raw(income_row.get("netIncome")),
                total_assets=_raw(balance_row.get("totalAssets")),
                total_liabilities=_raw(balance_row.get("totalLiab")),
                shareholder_equity=_raw(balance_row.get("totalStockholderEquity")),
                total_cash=_raw(balance_row.get("cash")),
                total_debt=_raw(balance_row.get("shortLongTermDebt")) or _raw(balance_row.get("longTermDebt")),
                operating_cash_flow=operating_cash_flow,
                capital_expenditure=capital_expenditure,
                free_cash_flow=free_cash_flow,
            )
        )

    return periods[:4]


def _metric(key: str, label: str, value: float | None, unit: str, interpretation: str) -> FundamentalMetric | None:
    if value is None:
        return None
    return FundamentalMetric(
        key=key,
        label=label,
        value=round(value, 2),
        unit=unit,
        interpretation=interpretation,
    )


def _derive_metrics(
    periods: list[FinancialStatementPeriod],
    quote_metrics: dict[str, float] | None = None,
) -> tuple[list[FundamentalMetric], dict[str, float]]:
    latest = periods[0] if periods else None
    previous = periods[1] if len(periods) > 1 else None
    if not latest:
        return [], {}
    quote_metrics = quote_metrics or {}

    revenue_growth = None
    if previous and previous.revenue not in (None, 0) and latest.revenue is not None:
        revenue_growth = ((latest.revenue - previous.revenue) / previous.revenue) * 100

    gross_margin = (_safe_ratio(latest.gross_profit, latest.revenue) or 0) * 100 if latest.gross_profit is not None else None
    operating_margin = (_safe_ratio(latest.operating_income, latest.revenue) or 0) * 100 if latest.operating_income is not None else None
    net_margin = (_safe_ratio(latest.net_income, latest.revenue) or 0) * 100 if latest.net_income is not None else None
    roe = (_safe_ratio(latest.net_income, latest.shareholder_equity) or 0) * 100 if latest.net_income is not None else None
    roe = roe if roe is not None else quote_metrics.get("return_on_equity")
    roa = (_safe_ratio(latest.net_income, latest.total_assets) or 0) * 100 if latest.net_income is not None else None
    debt_to_equity = _safe_ratio(latest.total_debt, latest.shareholder_equity)
    fcf_margin = (_safe_ratio(latest.free_cash_flow, latest.revenue) or 0) * 100 if latest.free_cash_flow is not None else None
    metric_rows = [
        _metric("revenue_growth_yoy", "Revenue growth YoY", revenue_growth, "%", "Top-line growth from the prior fiscal year."),
        _metric("gross_margin", "Gross margin", gross_margin, "%", "Pricing power and production efficiency."),
        _metric("operating_margin", "Operating margin", operating_margin, "%", "Core operating profitability."),
        _metric("net_margin", "Net margin", net_margin, "%", "Bottom-line profitability after all costs."),
        _metric("roe", "ROE", roe, "%", "Net income generated per unit of equity."),
        _metric("roa", "ROA", roa, "%", "Net income generated per unit of assets."),
        _metric("debt_to_equity", "Debt / equity", debt_to_equity, "x", "Balance-sheet leverage."),
        _metric("fcf_margin", "FCF margin", fcf_margin, "%", "Free cash flow relative to revenue."),
        _metric("market_cap_b", "Market cap", _safe_ratio(quote_metrics.get("market_cap"), 1_000_000_000), "B", "Equity market value in local-currency billions."),
        _metric("trailing_pe", "PER (TTM)", quote_metrics.get("trailing_pe"), "x", "Price divided by trailing earnings per share."),
        _metric("forward_pe", "Forward PER", quote_metrics.get("forward_pe"), "x", "Price divided by expected forward earnings per share."),
        _metric("price_to_book", "P/B", quote_metrics.get("price_to_book"), "x", "Price relative to book value."),
        _metric("price_to_sales", "P/S", quote_metrics.get("price_to_sales"), "x", "Price relative to trailing sales."),
        _metric("ev_to_ebitda", "EV/EBITDA", quote_metrics.get("ev_to_ebitda"), "x", "Enterprise value relative to EBITDA."),
        _metric("dividend_yield", "Dividend yield", quote_metrics.get("dividend_yield"), "%", "Dividend yield from current market pricing."),
        _metric("beta", "Beta", quote_metrics.get("beta"), "x", "Equity beta versus the reference market."),
        _metric("target_upside", "Target upside", quote_metrics.get("target_upside"), "%", "Consensus target upside when Yahoo provides a target price."),
    ]
    metrics = [row for row in metric_rows if row is not None]
    features = {
        f"fundamental_{metric.key}": metric.value
        for metric in metrics
    }
    return metrics, features


def _fallback_periods(symbol: str) -> list[FinancialStatementPeriod]:
    revenue, net_income, assets, equity = FALLBACK_BASES.get(
        symbol,
        (100_000_000_000, 8_000_000_000, 140_000_000_000, 55_000_000_000),
    )
    periods = []
    for index, fiscal_date in enumerate(("2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31")):
        growth_factor = 1 - index * 0.07
        period_revenue = revenue * growth_factor
        period_net_income = net_income * (growth_factor - index * 0.015)
        periods.append(
            FinancialStatementPeriod(
                fiscal_date=fiscal_date,
                revenue=period_revenue,
                gross_profit=period_revenue * 0.42,
                operating_income=period_revenue * 0.24,
                net_income=period_net_income,
                total_assets=assets * (1 - index * 0.04),
                total_liabilities=(assets - equity) * (1 - index * 0.035),
                shareholder_equity=equity * (1 - index * 0.02),
                total_cash=assets * 0.12,
                total_debt=equity * 0.32,
                operating_cash_flow=period_revenue * 0.20,
                capital_expenditure=period_revenue * -0.06,
                free_cash_flow=period_revenue * 0.14,
            )
        )
    return periods


def _fallback_fundamental(symbol: str, name: str, market: str, currency: str) -> EquityFundamental:
    periods = _fallback_periods(symbol)
    metrics, features = _derive_metrics(periods, _fallback_quote_metrics(periods))
    return EquityFundamental(
        symbol=symbol,
        name=name,
        market=market,
        currency=currency,
        periods=periods,
        metrics=metrics,
        model_features=features,
        data_source="Curated fallback fundamentals",
    )


def _fetch_yahoo_timeseries_fundamental(symbol: str, name: str, market: str, currency: str) -> EquityFundamental | None:
    period2 = int(datetime.now(timezone.utc).timestamp())
    request = Request(
        (
            f"{YAHOO_TIMESERIES_URL}/{quote(symbol, safe='')}"
            f"?symbol={quote(symbol, safe='')}"
            f"&type={','.join(YAHOO_TIMESERIES_TYPES)}"
            f"&period1=0&period2={period2}"
        ),
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        periods = _merge_timeseries_statements(payload)
        if len(periods) < 2:
            return None

        quote_metrics = _timeseries_quote_metrics(payload, periods)
        metrics, features = _derive_metrics(periods, quote_metrics)
        return EquityFundamental(
            symbol=symbol,
            name=name,
            market=market,
            currency=currency,
            periods=periods,
            metrics=metrics,
            model_features=features,
            data_source="Yahoo Finance fundamentals-timeseries",
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _fetch_yahoo_fundamental(symbol: str, name: str, market: str, currency: str) -> EquityFundamental:
    modules = ",".join([
        "incomeStatementHistory",
        "balanceSheetHistory",
        "cashflowStatementHistory",
        "summaryDetail",
        "defaultKeyStatistics",
        "financialData",
        "price",
    ])
    request = Request(
        f"{YAHOO_SUMMARY_URL}/{quote(symbol, safe='')}?modules={modules}",
        headers={
            "Accept": "application/json",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        periods = _merge_statements(payload)
        quote_metrics = _quote_metrics(payload)
        data_source = "Yahoo Finance quoteSummary"
        if len(periods) < 2:
            timeseries = _fetch_yahoo_timeseries_fundamental(symbol, name, market, currency)
            if timeseries:
                return timeseries
            periods = _fallback_periods(symbol)
            data_source = "Yahoo Finance valuation + curated statement fallback" if quote_metrics else "Curated fallback fundamentals"

        metrics, features = _derive_metrics(periods, quote_metrics or _fallback_quote_metrics(periods))
        return EquityFundamental(
            symbol=symbol,
            name=name,
            market=market,
            currency=currency,
            periods=periods,
            metrics=metrics,
            model_features=features,
            data_source=data_source,
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return _fetch_yahoo_timeseries_fundamental(symbol, name, market, currency) or _fallback_fundamental(symbol, name, market, currency)


def get_equity_fundamentals() -> list[EquityFundamental]:
    with ThreadPoolExecutor(max_workers=6) as executor:
        return list(executor.map(
            lambda item: _fetch_yahoo_fundamental(item[0], item[1], item[3], item[4]),
            STOCK_UNIVERSE,
        ))


def _extract_model_weights(payload: dict) -> dict[str, float]:
    weights = {}

    def add_weight(name: object, weight: object) -> None:
        if not isinstance(name, str):
            return
        try:
            weights[name] = float(weight)
        except (TypeError, ValueError):
            return

    for key in ("weights", "derived_variables"):
        values = payload.get(key)
        if isinstance(values, dict):
            for name, weight in values.items():
                add_weight(name, weight)
        elif isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    add_weight(item.get("name"), item.get("weight"))

    features = payload.get("features")
    if isinstance(features, list):
        for item in features:
            if isinstance(item, dict):
                add_weight(item.get("name"), item.get("weight"))

    return weights


def score_fundamental_models(
    fundamentals: list[EquityFundamental],
    model_folder: Path,
) -> list[FundamentalModelScore]:
    scores = []
    if not model_folder.exists():
        return scores

    for file_path in sorted(model_folder.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(payload, dict) or payload.get("enabled") is False:
            continue
        if payload.get("target") != "equity_fundamental_score":
            continue

        weights = _extract_model_weights(payload)
        signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
        bias = float(payload.get("bias", signal.get("bias", 0.0)))
        model_name = str(payload.get("name") or file_path.stem)
        model_type = str(payload.get("model_type") or "fundamental_boosting")

        for company in fundamentals:
            missing = sorted(set(weights) - set(company.model_features))
            if missing:
                scores.append(
                    FundamentalModelScore(
                        model_name=model_name,
                        model_type=model_type,
                        file_name=file_path.name,
                        symbol=company.symbol,
                        company=company.name,
                        score=0.0,
                        status="error",
                        message=f"Unavailable features: {', '.join(missing)}",
                        features_used=list(weights),
                    )
                )
                continue

            score = bias + sum(company.model_features[name] * weight for name, weight in weights.items())
            scores.append(
                FundamentalModelScore(
                    model_name=model_name,
                    model_type=model_type,
                    file_name=file_path.name,
                    symbol=company.symbol,
                    company=company.name,
                    score=round(score, 3),
                    status="ok",
                    message="Scored from latest annual fundamental metrics.",
                    features_used=list(weights),
                )
            )

    return sorted(scores, key=lambda item: item.score, reverse=True)
