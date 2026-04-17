import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.collectors.global_markets import (
    _daily_returns,
    _drawdown_feature,
    _level_changes,
    _rolling_volatility,
    _rsi_feature,
    get_bond_charts,
    get_index_charts,
)
from app.schemas.research import (
    IndexChart,
    ModelBacktestOverview,
    ModelBacktestResult,
    ModelEquityPoint,
)

MODEL_FOLDER = Path(os.getenv("MODEL_REGISTRY_PATH", "model_registry"))
BACKTEST_TRADING_DAYS = 504


def _chart_by_name(charts: list[IndexChart], name: str) -> IndexChart | None:
    return next((chart for chart in charts if chart.name == name), None)


def _build_feature_series(charts: list[IndexChart]) -> dict[str, dict[str, float]]:
    bitcoin = _chart_by_name(charts, "Bitcoin")
    if not bitcoin:
        return {}

    lookback = max(len(bitcoin.points), BACKTEST_TRADING_DAYS + 120)
    features = {
        "btc_return_1d": _daily_returns(bitcoin.points, lookback),
        "btc_rsi_14": _rsi_feature(bitcoin.points, lookback),
        "btc_volatility_20d": _rolling_volatility(bitcoin.points, lookback),
        "btc_drawdown_60d": _drawdown_feature(bitcoin.points, lookback),
    }
    return_charts = {
        "sp500_return_1d": "S&P 500",
        "nasdaq_return_1d": "Nasdaq Composite",
        "kospi_return_1d": "KOSPI",
        "nikkei_return_1d": "Nikkei 225",
        "gold_return_1d": "Gold Spot",
        "gold_futures_return_1d": "Gold Futures",
    }
    yield_charts = {
        "us10y_bp_chg": "US 10Y Treasury Yield",
        "us30y_bp_chg": "US 30Y Treasury Yield",
        "us5y_bp_chg": "US 5Y Treasury Yield",
        "japan10y_bp_chg": "Japan 10Y Government Bond Yield",
        "germany10y_bp_chg": "Germany 10Y Bund Yield",
        "uk10y_bp_chg": "UK 10Y Gilt Yield",
    }

    for feature_name, chart_name in return_charts.items():
        chart = _chart_by_name(charts, chart_name)
        if chart:
            features[feature_name] = _daily_returns(chart.points, lookback)

    for feature_name, chart_name in yield_charts.items():
        chart = _chart_by_name(charts, chart_name)
        if chart:
            features[feature_name] = _level_changes(chart.points, lookback, multiplier=100)

    return features


def _extract_weights(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    extracted: dict[str, dict[str, float]] = {}

    def add_weight(name: Any, weight: Any, mean: Any = None, std: Any = None) -> None:
        if not isinstance(name, str):
            return
        try:
            parsed_weight = float(weight)
            parsed_mean = float(mean) if mean is not None else None
            parsed_std = float(std) if std is not None else None
        except (TypeError, ValueError):
            return

        extracted[name] = {
            "weight": parsed_weight,
            "mean": parsed_mean,
            "std": parsed_std,
        }

    for key in ("weights", "derived_variables"):
        values = payload.get(key)
        if isinstance(values, dict):
            for name, weight in values.items():
                add_weight(name, weight)
        elif isinstance(values, list):
            for item in values:
                if isinstance(item, dict):
                    add_weight(item.get("name"), item.get("weight"), item.get("mean"), item.get("std"))

    features = payload.get("features")
    if isinstance(features, list):
        for item in features:
            if isinstance(item, dict):
                add_weight(item.get("name"), item.get("weight"), item.get("mean"), item.get("std"))

    return extracted


def _position_from_score(score: float, payload: dict[str, Any]) -> float:
    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    long_threshold = float(signal.get("long_threshold", payload.get("long_threshold", 0.0)))
    short_threshold = float(signal.get("short_threshold", payload.get("short_threshold", -long_threshold)))
    allow_short = bool(signal.get("allow_short", payload.get("allow_short", False)))

    if score > long_threshold:
        return 1.0
    if allow_short and score < short_threshold:
        return -1.0
    return 0.0


def _score_date(
    date: str,
    weights: dict[str, dict[str, float]],
    feature_series: dict[str, dict[str, float]],
    bias: float,
) -> float | None:
    score = bias

    for feature_name, config in weights.items():
        value = feature_series.get(feature_name, {}).get(date)
        if value is None:
            return None

        mean = config.get("mean")
        std = config.get("std")
        if mean is not None and std not in (None, 0):
            value = (value - mean) / std

        score += config["weight"] * value

    return score


def _max_drawdown(equity_curve: list[ModelEquityPoint]) -> float:
    peak = 1.0
    max_drawdown = 0.0

    for point in equity_curve:
        peak = max(peak, point.equity)
        if peak:
            max_drawdown = min(max_drawdown, (point.equity - peak) / peak)

    return max_drawdown * 100


def _backtest_model(
    file_path: Path,
    payload: dict[str, Any],
    feature_series: dict[str, dict[str, float]],
) -> ModelBacktestResult:
    name = str(payload.get("name") or file_path.stem)
    model_type = str(payload.get("model_type") or "weighted_signal")

    if payload.get("enabled") is False:
        return ModelBacktestResult(
            name=name,
            model_type=model_type,
            file_name=file_path.name,
            status="disabled",
            message="Model file is present but disabled.",
            sharpe_ratio=0.0,
            win_rate_pct=0.0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            trades=0,
            exposure_pct=0.0,
            observations=0,
        )

    weights = _extract_weights(payload)
    missing_features = sorted(set(weights) - set(feature_series))
    if not weights:
        return _error_result(file_path, name, model_type, "No weights or derived variables were found.")
    if missing_features:
        return _error_result(
            file_path,
            name,
            model_type,
            f"Unavailable features: {', '.join(missing_features)}",
            list(weights),
        )

    target_returns = feature_series.get("btc_return_1d", {})
    target_dates = sorted(target_returns)
    window_dates = target_dates[-(BACKTEST_TRADING_DAYS + 1):]
    if len(window_dates) < 60:
        return _error_result(file_path, name, model_type, "Not enough recent BTC history for a two-year backtest.", list(weights))

    signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
    bias = float(signal.get("bias", payload.get("bias", 0.0)))
    daily_returns = []
    equity_curve = []
    equity = 1.0
    previous_position = 0.0
    trades = 0
    active_days = 0
    wins = 0

    for index in range(len(window_dates) - 1):
        signal_date = window_dates[index]
        return_date = window_dates[index + 1]
        score = _score_date(signal_date, weights, feature_series, bias)
        if score is None:
            continue

        position = _position_from_score(score, payload)
        if position != previous_position:
            trades += 1
        previous_position = position

        realized_return = (target_returns[return_date] / 100) * position
        equity *= 1 + realized_return
        daily_returns.append(realized_return)
        if position != 0:
            active_days += 1
            if realized_return > 0:
                wins += 1

        equity_curve.append(
            ModelEquityPoint(
                date=return_date,
                equity=round(equity, 4),
                daily_return_pct=round(realized_return * 100, 3),
                position=position,
            )
        )

    if not daily_returns:
        return _error_result(file_path, name, model_type, "No overlapping feature dates were available.", list(weights))

    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((item - mean_return) ** 2 for item in daily_returns) / len(daily_returns)
    volatility = math.sqrt(variance)
    sharpe = (mean_return / volatility) * math.sqrt(252) if volatility else 0.0
    win_rate = (wins / active_days) * 100 if active_days else 0.0
    exposure = (active_days / len(daily_returns)) * 100

    return ModelBacktestResult(
        name=name,
        model_type=model_type,
        file_name=file_path.name,
        status="ok",
        message="Backtested on the latest 504 trading observations with next-day BTC returns.",
        sharpe_ratio=round(sharpe, 2),
        win_rate_pct=round(win_rate, 1),
        total_return_pct=round((equity - 1) * 100, 2),
        max_drawdown_pct=round(_max_drawdown(equity_curve), 2),
        trades=trades,
        exposure_pct=round(exposure, 1),
        observations=len(daily_returns),
        backtest_start=equity_curve[0].date if equity_curve else None,
        backtest_end=equity_curve[-1].date if equity_curve else None,
        features=list(weights),
        equity_curve=_sample_equity_curve(equity_curve),
    )


def _sample_equity_curve(points: list[ModelEquityPoint], max_points: int = 120) -> list[ModelEquityPoint]:
    if len(points) <= max_points:
        return points

    step = math.ceil(len(points) / max_points)
    sampled = [point for index, point in enumerate(points) if index % step == 0]
    if sampled[-1].date != points[-1].date:
        sampled.append(points[-1])
    return sampled


def _error_result(
    file_path: Path,
    name: str,
    model_type: str,
    message: str,
    features: list[str] | None = None,
) -> ModelBacktestResult:
    return ModelBacktestResult(
        name=name,
        model_type=model_type,
        file_name=file_path.name,
        status="error",
        message=message,
        sharpe_ratio=0.0,
        win_rate_pct=0.0,
        total_return_pct=0.0,
        max_drawdown_pct=0.0,
        trades=0,
        exposure_pct=0.0,
        observations=0,
        features=features or [],
    )


def build_model_backtests() -> ModelBacktestOverview:
    charts = get_index_charts() + get_bond_charts()
    feature_series = _build_feature_series(charts)
    MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
    results = []

    for file_path in sorted(MODEL_FOLDER.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("model file must contain a JSON object")
            if payload.get("enabled") is False:
                continue
            results.append(_backtest_model(file_path, payload, feature_series))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            results.append(
                _error_result(
                    file_path,
                    file_path.stem,
                    "unknown",
                    f"Could not read model file: {error}",
                )
            )

    return ModelBacktestOverview(
        generated_at=datetime.now(timezone.utc),
        model_folder=str(MODEL_FOLDER),
        evaluation_window="latest 504 trading observations, approximately two years",
        available_features=sorted(feature_series),
        results=results,
        instructions=[
            "Place JSON model files in backend/model_registry.",
            "Use weights or derived_variables to map feature names to trained model weights.",
            "The signal from date T is evaluated against BTC return on date T+1 to reduce look-ahead bias.",
        ],
        disclaimer="Backtests are research diagnostics only. They are not live trading recommendations.",
    )
