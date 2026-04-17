import json
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
FUNDAMENTAL_MODEL_FEATURES = [
    "fundamental_revenue_growth_yoy",
    "fundamental_gross_margin",
    "fundamental_operating_margin",
    "fundamental_net_margin",
    "fundamental_roe",
    "fundamental_roa",
    "fundamental_debt_to_equity",
    "fundamental_fcf_margin",
]

STOCK_UNIVERSE = [
    item for item in TRACKED_INSTRUMENTS
    if item[2] in {"US Stocks", "Korea Stocks", "Japan Stocks"}
]

FALLBACK_BASES = {
    "AAPL": (383_285_000_000, 96_995_000_000, 352_583_000_000, 62_146_000_000),
    "MSFT": (245_122_000_000, 88_136_000_000, 512_163_000_000, 268_477_000_000),
    "NVDA": (60_922_000_000, 29_760_000_000, 65_728_000_000, 43_009_000_000),
    "005930.KS": (258_935_000_000_000, 15_487_000_000_000, 455_906_000_000_000, 363_678_000_000_000),
    "000660.KS": (32_766_000_000_000, -9_137_000_000_000, 100_330_000_000_000, 53_290_000_000_000),
    "005380.KS": (162_664_000_000_000, 12_272_000_000_000, 282_463_000_000_000, 106_478_000_000_000),
    "7203.T": (45_095_000_000_000, 4_945_000_000_000, 90_114_000_000_000, 34_338_000_000_000),
    "6758.T": (13_020_000_000_000, 970_000_000_000, 34_107_000_000_000, 7_999_000_000_000),
    "8306.T": (11_890_000_000_000, 1_491_000_000_000, 403_703_000_000_000, 18_272_000_000_000),
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


def _derive_metrics(periods: list[FinancialStatementPeriod]) -> tuple[list[FundamentalMetric], dict[str, float]]:
    latest = periods[0] if periods else None
    previous = periods[1] if len(periods) > 1 else None
    if not latest:
        return [], {}

    revenue_growth = None
    if previous and previous.revenue not in (None, 0) and latest.revenue is not None:
        revenue_growth = ((latest.revenue - previous.revenue) / previous.revenue) * 100

    gross_margin = (_safe_ratio(latest.gross_profit, latest.revenue) or 0) * 100 if latest.gross_profit is not None else None
    operating_margin = (_safe_ratio(latest.operating_income, latest.revenue) or 0) * 100 if latest.operating_income is not None else None
    net_margin = (_safe_ratio(latest.net_income, latest.revenue) or 0) * 100 if latest.net_income is not None else None
    roe = (_safe_ratio(latest.net_income, latest.shareholder_equity) or 0) * 100 if latest.net_income is not None else None
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
    metrics, features = _derive_metrics(periods)
    return EquityFundamental(
        symbol=symbol,
        name=name,
        market=market,
        currency=currency,
        periods=periods,
        metrics=metrics,
        model_features=features,
        data_source="Local fallback fundamentals",
    )


def _fetch_yahoo_fundamental(symbol: str, name: str, market: str, currency: str) -> EquityFundamental:
    modules = "incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory"
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
        if len(periods) < 2:
            return _fallback_fundamental(symbol, name, market, currency)

        metrics, features = _derive_metrics(periods)
        return EquityFundamental(
            symbol=symbol,
            name=name,
            market=market,
            currency=currency,
            periods=periods,
            metrics=metrics,
            model_features=features,
            data_source="Yahoo Finance quoteSummary",
        )
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return _fallback_fundamental(symbol, name, market, currency)


def get_equity_fundamentals() -> list[EquityFundamental]:
    return [
        _fetch_yahoo_fundamental(symbol, name, market, currency)
        for symbol, name, _, market, currency, _, _ in STOCK_UNIVERSE
    ]


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
