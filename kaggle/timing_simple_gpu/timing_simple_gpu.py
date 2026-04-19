import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

RUN_ID = "btc_timing_simple_latest"
OUTPUT_DIR = Path("/kaggle/working") / RUN_ID if Path("/kaggle/working").exists() else Path("backend/model_registry/kaggle_runs") / RUN_ID
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = {
    "btc": "BTC-USD",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "gold": "GC=F",
    "silver": "SI=F",
    "oil": "CL=F",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
}

TRAIN_END_OFFSET = 504
VALIDATION_OFFSET = 252
HIGH_VOLUME_QUANTILE = 0.60
MAX_SELECTED_FEATURES = 48
MAX_FEATURE_CORRELATION = 0.72
FORWARD_HOLD_DAYS = 3
MIN_VALIDATION_ACTIVE_DAYS = 18
TRANSACTION_COST_BPS = 5.0
SLIPPAGE_BPS = 5.0
SHARPE_TARGET = 2.0
LONG_QUANTILES = np.linspace(0.62, 0.96, 15)
SHORT_QUANTILES = np.linspace(0.62, 0.96, 15)
EDGE_GAP_CANDIDATES = [0.02, 0.04, 0.065, 0.09, 0.12, 0.16, 0.20]
TURNOVER_RULES = [
    {"min_hold_days": 3, "cooldown_days": 1},
    {"min_hold_days": 3, "cooldown_days": 2},
    {"min_hold_days": 4, "cooldown_days": 1},
    {"min_hold_days": 4, "cooldown_days": 2},
    {"min_hold_days": 5, "cooldown_days": 2},
    {"min_hold_days": 5, "cooldown_days": 3},
]


def fetch_yahoo_chart(symbol: str) -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?range=10y&interval=1d"
    request = Request(url, headers={"User-Agent": "btc-research-ai/0.1", "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload["chart"]["result"][0]
    quote_data = result["indicators"]["quote"][0]
    dates = pd.to_datetime(result["timestamp"], unit="s", utc=True).strftime("%Y-%m-%d")
    frame = pd.DataFrame({
        "date": dates,
        "open": quote_data["open"],
        "high": quote_data["high"],
        "low": quote_data["low"],
        "close": quote_data["close"],
        "volume": quote_data.get("volume", [np.nan] * len(dates)),
    }).dropna(subset=["open", "high", "low", "close"])
    return frame.sort_values("date").reset_index(drop=True)


def pct_change(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods) * 100


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def rolling_position(series: pd.Series, window: int) -> pd.Series:
    low = series.rolling(window).min()
    high = series.rolling(window).max()
    return (series - low) / (high - low).replace(0, np.nan)


def drawdown(series: pd.Series, window: int) -> pd.Series:
    rolling_high = series.rolling(window).max()
    return (series - rolling_high) / rolling_high * 100


def add_features(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    close = data["btc_close"]
    open_ = data["btc_open"]
    high = data["btc_high"]
    low = data["btc_low"]
    volume = data["btc_volume"]
    features: list[str] = []

    def add(name: str, value: pd.Series) -> None:
        data[name] = value.replace([np.inf, -np.inf], np.nan)
        features.append(name)

    btc_return_1d = pct_change(close, 1)
    for window in [1, 3, 5, 7, 14, 21, 30, 60]:
        add(f"btc_return_{window}d", pct_change(close, window))
    for lag in [1, 2, 3, 5, 7, 14, 30]:
        add(f"btc_return_lag_{lag}", btc_return_1d.shift(lag))

    candle_range = (high - low).replace(0, np.nan)
    add("btc_gap_pct", (open_ / close.shift(1) - 1) * 100)
    add("btc_candle_range_pct", candle_range / close * 100)
    add("btc_candle_body_pct", (close - open_) / open_.replace(0, np.nan) * 100)
    add("btc_close_location", (close - low) / candle_range)
    add("btc_body_to_range", (close - open_).abs() / candle_range)

    log_volume = np.log1p(volume)
    add("btc_log_volume", log_volume)
    add("btc_volume_diff_1d", volume.diff())
    add("btc_volume_pct_1d", pct_change(volume, 1))
    add("btc_volume_pct_7d", pct_change(volume, 7))
    for window in [7, 20, 30, 60]:
        volume_mean = volume.rolling(window).mean()
        volume_std = volume.rolling(window).std()
        add(f"btc_volume_ratio_{window}d", volume / volume_mean)
        add(f"btc_volume_z_{window}d", (volume - volume_mean) / volume_std)

    for window in [7, 14, 20, 30, 60, 120]:
        add(f"btc_ma_distance_{window}d", (close / close.rolling(window).mean() - 1) * 100)
        add(f"btc_volatility_{window}d", btc_return_1d.rolling(window).std())
        add(f"btc_position_{window}d", rolling_position(close, window))
        add(f"btc_drawdown_{window}d", drawdown(close, window))

    add("btc_rsi_7", rsi(close, 7))
    add("btc_rsi_14", rsi(close, 14))
    add("btc_rsi_30", rsi(close, 30))

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()
    sma200 = close.rolling(200).mean()
    add("btc_above_sma20", (close > sma20).astype(float))
    add("btc_above_sma50", (close > sma50).astype(float))
    add("btc_sma20_above_sma50", (sma20 > sma50).astype(float))
    add("btc_sma50_above_sma200", (sma50 > sma200).astype(float))
    add("btc_trend_strength_20_50", (sma20 / sma50 - 1) * 100)
    add("btc_trend_strength_50_200", (sma50 / sma200 - 1) * 100)
    add("btc_sma50_slope_10d", pct_change(sma50, 10))
    add("btc_sma100_slope_20d", pct_change(sma100, 20))

    bb_std = close.rolling(20).std()
    bb_upper = sma20 + bb_std * 2
    bb_lower = sma20 - bb_std * 2
    add("btc_bollinger_width_20d", (bb_upper - bb_lower) / sma20 * 100)
    add("btc_bollinger_percent_b_20d", (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan))

    for prefix in ["sp500", "nasdaq", "gold", "silver", "oil", "vix", "dxy"]:
        column = f"{prefix}_close"
        if column not in data:
            continue
        asset_return_1d = pct_change(data[column], 1)
        for window in [1, 5, 20, 60]:
            add(f"{prefix}_return_{window}d", pct_change(data[column], window))
        add(f"{prefix}_volatility_20d", asset_return_1d.rolling(20).std())
        add(f"btc_{prefix}_corr_30d", btc_return_1d.rolling(30).corr(asset_return_1d))

    if "us10y_close" in data:
        add("us10y_bp_chg_1d", data["us10y_close"].diff() * 100)
        add("us10y_bp_chg_20d", data["us10y_close"].diff(20) * 100)
        add("us10y_level_z_120d", (data["us10y_close"] - data["us10y_close"].rolling(120).mean()) / data["us10y_close"].rolling(120).std())

    data["target_return_1d"] = pct_change(close, 1).shift(-1)
    data["forward_return_3d"] = (close.shift(-FORWARD_HOLD_DAYS) / close - 1) * 100
    noise_floor = (btc_return_1d.rolling(30).std() * math.sqrt(FORWARD_HOLD_DAYS) * 0.65).clip(lower=0.80, upper=6.0)
    data["timing_noise_floor_pct"] = noise_floor
    data["target_long_timing"] = (data["forward_return_3d"] > noise_floor).astype(int)
    data["target_short_timing"] = (data["forward_return_3d"] < -noise_floor).astype(int)
    data["high_volume_candle"] = volume >= volume.rolling(252).quantile(HIGH_VOLUME_QUANTILE)
    return data, features


def build_dataset() -> tuple[pd.DataFrame, list[str]]:
    btc = fetch_yahoo_chart(SYMBOLS["btc"]).rename(columns={
        "open": "btc_open",
        "high": "btc_high",
        "low": "btc_low",
        "close": "btc_close",
        "volume": "btc_volume",
    })
    data = btc.copy()
    for prefix, symbol in SYMBOLS.items():
        if prefix == "btc":
            continue
        try:
            chart = fetch_yahoo_chart(symbol)[["date", "close"]].rename(columns={"close": f"{prefix}_close"})
            data = data.merge(chart, on="date", how="left")
        except Exception as error:
            print(f"Optional symbol {prefix} skipped: {error}")

    data = data.sort_values("date").ffill()
    data, features = add_features(data)
    required = features + ["target_return_1d", "forward_return_3d", "target_long_timing", "target_short_timing"]
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=required).reset_index(drop=True)
    return data, features


def fit_standardizer(frame: pd.DataFrame, columns: list[str]) -> tuple[pd.Series, pd.Series]:
    means = frame[columns].mean()
    stds = frame[columns].std().replace(0, np.nan).fillna(1.0)
    return means, stds


def apply_standardizer(frame: pd.DataFrame, columns: list[str], means: pd.Series, stds: pd.Series) -> pd.DataFrame:
    normalized = (frame[columns] - means) / stds
    return normalized.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-8, 8)


def select_features(normalized: pd.DataFrame, train_frame: pd.DataFrame, candidate_columns: list[str]) -> tuple[list[str], dict]:
    target_score = {}
    target_return = train_frame["forward_return_3d"]
    for column in candidate_columns:
        long_corr = normalized[column].corr(train_frame["target_long_timing"])
        short_corr = normalized[column].corr(train_frame["target_short_timing"])
        return_corr = normalized[column].corr(target_return)
        score = max(
            abs(long_corr) if not np.isnan(long_corr) else 0.0,
            abs(short_corr) if not np.isnan(short_corr) else 0.0,
            abs(return_corr) if not np.isnan(return_corr) else 0.0,
        )
        target_score[column] = score

    ranked = sorted(candidate_columns, key=lambda column: target_score[column], reverse=True)
    candidate_corr = normalized[ranked[:120]].corr().abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    selected: list[str] = []
    selected_set: set[str] = set()

    core_substrings = [
        "btc_return_",
        "btc_volume_z_",
        "btc_volatility_",
        "btc_drawdown_",
        "btc_rsi_",
        "btc_bollinger_",
        "btc_trend_strength",
    ]
    core_candidates = [column for column in ranked if any(token in column for token in core_substrings)]
    for pool in [core_candidates, ranked]:
        for column in pool:
            if column in selected_set or len(selected) >= MAX_SELECTED_FEATURES:
                continue
            if selected and column in candidate_corr.index:
                max_corr = float(candidate_corr.loc[column, [item for item in selected if item in candidate_corr.columns]].max())
                if max_corr > MAX_FEATURE_CORRELATION:
                    continue
            selected.append(column)
            selected_set.add(column)
            if len(selected) >= MAX_SELECTED_FEATURES:
                break

    summary = {
        "method": "simple target-timing feature selection without second-order interactions",
        "candidate_feature_count": int(len(candidate_columns)),
        "selected_feature_count": int(len(selected)),
        "max_selected_features": int(MAX_SELECTED_FEATURES),
        "max_allowed_pairwise_correlation": MAX_FEATURE_CORRELATION,
        "mean_abs_timing_score": round(float(np.mean([target_score[column] for column in selected])), 5) if selected else 0.0,
    }
    return selected, summary


def build_model_frame(data: pd.DataFrame, features: list[str], fit_end_index: int) -> tuple[pd.DataFrame, list[str], dict]:
    fit_frame = data.iloc[:fit_end_index].copy()
    means, stds = fit_standardizer(fit_frame, features)
    normalized = apply_standardizer(data, features, means, stds)
    normalized.columns = [f"z_{column}" for column in features]
    normalized_fit = normalized.iloc[:fit_end_index].copy()
    selected_features, feature_selection = select_features(normalized_fit, fit_frame, list(normalized.columns))
    model_frame = pd.concat(
        [
            data[[
                "date",
                "target_return_1d",
                "forward_return_3d",
                "target_long_timing",
                "target_short_timing",
                "high_volume_candle",
                "timing_noise_floor_pct",
            ]].reset_index(drop=True),
            normalized[selected_features].reset_index(drop=True),
        ],
        axis=1,
    )
    return model_frame, selected_features, feature_selection


def fit_model_pair(model_spec: dict, train: pd.DataFrame, feature_cols: list[str]) -> tuple[object, object, str]:
    try:
        long_model = model_spec["factory"]()
        short_model = model_spec["factory"]()
        long_model.fit(train[feature_cols], train["target_long_timing"])
        short_model.fit(train[feature_cols], train["target_short_timing"])
        return long_model, short_model, model_spec["model_type"]
    except Exception as error:
        if model_spec.get("fallback_factory") is None:
            raise
        print(f"{model_spec['model_type']} failed, retrying fallback: {error}")
        long_model = model_spec["fallback_factory"]()
        short_model = model_spec["fallback_factory"]()
        long_model.fit(train[feature_cols], train["target_long_timing"])
        short_model.fit(train[feature_cols], train["target_short_timing"])
        return long_model, short_model, f"{model_spec['model_type']}_cpu_fallback"


def predict_proba(model, frame: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(frame[feature_cols])[:, 1], dtype=float)
    return np.asarray(model.predict(frame[feature_cols]), dtype=float)


def model_specs() -> list[dict]:
    specs = []
    try:
        from xgboost import XGBClassifier
        gpu_params = {
            "n_estimators": 260,
            "max_depth": 2,
            "learning_rate": 0.035,
            "subsample": 0.78,
            "colsample_bytree": 0.66,
            "reg_alpha": 0.35,
            "reg_lambda": 1.20,
            "min_child_weight": 5.0,
            "gamma": 0.16,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "device": "cuda",
            "random_state": 6201,
        }
        cpu_params = dict(gpu_params)
        cpu_params["tree_method"] = "hist"
        cpu_params.pop("device", None)
        specs.append({
            "name": "xgb_simple_timing",
            "model_type": "xgboost_simple_timing_gpu",
            "params": gpu_params,
            "factory": lambda params=gpu_params: XGBClassifier(**params),
            "fallback_factory": lambda params=cpu_params: XGBClassifier(**params),
        })
    except Exception as error:
        print(f"XGBoost unavailable: {error}")

    from sklearn.ensemble import ExtraTreesClassifier
    extra_params = {
        "n_estimators": 360,
        "max_depth": 5,
        "min_samples_leaf": 14,
        "min_samples_split": 28,
        "max_features": 0.45,
        "bootstrap": True,
        "random_state": 7301,
        "n_jobs": -1,
    }
    specs.append({
        "name": "extra_trees_simple_timing",
        "model_type": "extra_trees_simple_timing",
        "params": extra_params,
        "factory": lambda params=extra_params: ExtraTreesClassifier(**params),
        "fallback_factory": None,
    })
    return specs


def backtest_timing(
    frame: pd.DataFrame,
    long_scores: np.ndarray,
    short_scores: np.ndarray,
    long_threshold: float,
    short_threshold: float,
    edge_gap: float,
    min_hold_days: int,
    cooldown_days: int,
) -> pd.DataFrame:
    result = frame[["date", "target_return_1d", "high_volume_candle"]].copy()
    result["long_probability"] = long_scores
    result["short_probability"] = short_scores
    result["timing_edge"] = long_scores - short_scores
    allowed = result["high_volume_candle"].to_numpy(dtype=bool)
    raw_position = np.zeros(len(result), dtype=float)
    raw_position[allowed & (long_scores >= long_threshold) & ((long_scores - short_scores) >= edge_gap)] = 1.0
    raw_position[allowed & (short_scores >= short_threshold) & ((short_scores - long_scores) >= edge_gap)] = -1.0

    positions = np.zeros(len(result), dtype=float)
    current_position = 0.0
    hold_remaining = 0
    cooldown_remaining = 0
    for index, desired_position in enumerate(raw_position):
        if current_position != 0:
            if hold_remaining > 0:
                positions[index] = current_position
                hold_remaining -= 1
                continue
            if desired_position == current_position:
                positions[index] = current_position
                continue
            current_position = 0.0
            cooldown_remaining = cooldown_days
            positions[index] = 0.0
            continue

        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            positions[index] = 0.0
            continue

        if desired_position != 0:
            current_position = desired_position
            hold_remaining = max(1, min_hold_days) - 1
            positions[index] = current_position

    result["position"] = positions
    result["long_threshold"] = long_threshold
    result["short_threshold"] = short_threshold
    result["edge_gap"] = edge_gap
    result["min_hold_days"] = min_hold_days
    result["cooldown_days"] = cooldown_days
    result["gross_strategy_return"] = result["position"] * result["target_return_1d"] / 100
    result["position_change"] = result["position"].diff().abs().fillna(result["position"].abs())
    result["transaction_cost"] = result["position_change"] * ((TRANSACTION_COST_BPS + SLIPPAGE_BPS) / 10000)
    result["strategy_return"] = result["gross_strategy_return"] - result["transaction_cost"]
    result["gross_equity"] = (1 + result["gross_strategy_return"]).cumprod()
    result["equity"] = (1 + result["strategy_return"]).cumprod()
    return result


def metrics_for(result: pd.DataFrame) -> dict:
    returns = result["strategy_return"].fillna(0)
    gross_returns = result["gross_strategy_return"].fillna(0)
    active = result[result["position"] != 0]
    volatility = returns.std()
    gross_volatility = gross_returns.std()
    sharpe = (returns.mean() / volatility) * math.sqrt(252) if volatility and not np.isnan(volatility) else 0.0
    gross_sharpe = (gross_returns.mean() / gross_volatility) * math.sqrt(252) if gross_volatility and not np.isnan(gross_volatility) else 0.0
    equity = result["equity"].iloc[-1] if len(result) else 1.0
    gross_equity = result["gross_equity"].iloc[-1] if len(result) else 1.0
    peak = result["equity"].cummax()
    drawdown_pct = ((result["equity"] - peak) / peak).min() * 100 if len(result) else 0.0
    return {
        "sharpe_ratio": round(float(sharpe), 3),
        "gross_sharpe_ratio": round(float(gross_sharpe), 3),
        "win_rate_pct": round(float((active["strategy_return"] > 0).mean() * 100), 2) if len(active) else 0.0,
        "total_return_pct": round(float((equity - 1) * 100), 3),
        "gross_total_return_pct": round(float((gross_equity - 1) * 100), 3),
        "max_drawdown_pct": round(float(drawdown_pct), 3),
        "exposure_pct": round(float((result["position"] != 0).mean() * 100), 2) if len(result) else 0.0,
        "trades": int(result["position_change"].sum()),
        "total_transaction_cost_pct": round(float(result["transaction_cost"].sum() * 100), 3),
        "observations": int(len(result)),
        "active_observations": int(len(active)),
    }


def split_metrics(result: pd.DataFrame, model_name: str) -> list[dict]:
    rows = []
    for index, values in enumerate(np.array_split(np.arange(len(result)), 4), start=1):
        if len(values) == 0:
            continue
        part = result.iloc[values].copy()
        row = metrics_for(part)
        row.update({
            "model_name": model_name,
            "split": index,
            "start": str(part["date"].iloc[0]),
            "end": str(part["date"].iloc[-1]),
        })
        rows.append(row)
    return rows


def validation_score(metrics: dict, splits: list[dict]) -> float:
    split_sharpes = [float(item.get("sharpe_ratio", 0.0)) for item in splits]
    split_returns = [float(item.get("total_return_pct", 0.0)) for item in splits]
    worst_split = min(split_sharpes) if split_sharpes else 0.0
    last_split = split_sharpes[-1] if split_sharpes else 0.0
    positive_ratio = (sum(1 for value in split_returns if value > 0) / len(split_returns)) if split_returns else 0.0
    split_std = float(np.std(split_sharpes)) if split_sharpes else 0.0
    return (
        float(metrics["sharpe_ratio"])
        + float(metrics["total_return_pct"]) * 0.015
        + float(metrics["max_drawdown_pct"]) * 0.012
        + worst_split * 0.35
        + last_split * 0.20
        + positive_ratio * 0.20
        - float(metrics["total_transaction_cost_pct"]) * 0.08
        - float(metrics["trades"]) * 0.012
        - split_std * 0.10
    )


def select_thresholds(validation: pd.DataFrame, long_scores: np.ndarray, short_scores: np.ndarray) -> tuple[dict, dict]:
    long_candidates = sorted(set(float(np.nanquantile(long_scores[validation["high_volume_candle"].to_numpy(dtype=bool)], q)) for q in LONG_QUANTILES))
    short_candidates = sorted(set(float(np.nanquantile(short_scores[validation["high_volume_candle"].to_numpy(dtype=bool)], q)) for q in SHORT_QUANTILES))
    best = None
    best_result = None

    for long_threshold in long_candidates:
        for short_threshold in short_candidates:
            for edge_gap in EDGE_GAP_CANDIDATES:
                for rule in TURNOVER_RULES:
                    result = backtest_timing(validation, long_scores, short_scores, long_threshold, short_threshold, edge_gap, **rule)
                    metrics = metrics_for(result)
                    if metrics["active_observations"] < MIN_VALIDATION_ACTIVE_DAYS:
                        continue
                    splits = split_metrics(result, "validation")
                    score = validation_score(metrics, splits)
                    candidate = {
                        "selected_threshold": round(float(long_threshold), 6),
                        "selected_short_threshold": round(float(short_threshold), 6),
                        "selected_edge_gap": round(float(edge_gap), 6),
                        "selected_min_hold_days": int(rule["min_hold_days"]),
                        "selected_cooldown_days": int(rule["cooldown_days"]),
                        "validation_selection_score": round(float(score), 3),
                        "validation_worst_split_sharpe": round(float(min(item["sharpe_ratio"] for item in splits)), 3),
                        "validation_last_split_sharpe": round(float(splits[-1]["sharpe_ratio"]), 3),
                        "validation_positive_split_count": sum(1 for item in splits if item["total_return_pct"] > 0),
                        "validation_split_count": len(splits),
                        **{f"validation_{key}": value for key, value in metrics.items()},
                    }
                    if best is None or score > best["validation_selection_score"]:
                        best = candidate
                        best_result = result

    if best is None:
        long_threshold = float(np.nanquantile(long_scores, 0.85))
        short_threshold = float(np.nanquantile(short_scores, 0.85))
        result = backtest_timing(validation, long_scores, short_scores, long_threshold, short_threshold, 0.10, 3, 2)
        metrics = metrics_for(result)
        splits = split_metrics(result, "validation")
        best = {
            "selected_threshold": round(float(long_threshold), 6),
            "selected_short_threshold": round(float(short_threshold), 6),
            "selected_edge_gap": 0.10,
            "selected_min_hold_days": 3,
            "selected_cooldown_days": 2,
            "validation_selection_score": round(float(validation_score(metrics, splits)), 3),
            "validation_worst_split_sharpe": round(float(min(item["sharpe_ratio"] for item in splits)), 3),
            "validation_last_split_sharpe": round(float(splits[-1]["sharpe_ratio"]), 3),
            "validation_positive_split_count": sum(1 for item in splits if item["total_return_pct"] > 0),
            "validation_split_count": len(splits),
            **{f"validation_{key}": value for key, value in metrics.items()},
        }
        best_result = result

    return best, best_result


def feature_importance(long_model, short_model, feature_cols: list[str], train: pd.DataFrame) -> list[dict]:
    totals: dict[str, float] = {}
    for model, target in [(long_model, "target_long_timing"), (short_model, "target_short_timing")]:
        if hasattr(model, "feature_importances_"):
            values = np.asarray(model.feature_importances_, dtype=float)
        else:
            values = np.asarray([abs(train[column].corr(train[target])) if train[column].std() else 0.0 for column in feature_cols], dtype=float)
        for column, value in zip(feature_cols, values):
            totals[column] = totals.get(column, 0.0) + float(value)
    total = sum(totals.values()) or 1.0
    return [
        {"feature": column, "importance": round(float(value / total), 6)}
        for column, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def package_gate(metrics: dict, splits: list[dict], validation_metrics: dict) -> dict:
    split_returns = [float(row.get("total_return_pct", 0.0)) for row in splits]
    split_sharpes = [float(row.get("sharpe_ratio", 0.0)) for row in splits]
    positive_split_count = sum(1 for value in split_returns if value > 0)
    worst_split_sharpe = min(split_sharpes) if split_sharpes else 0.0
    reasons = []
    if metrics["sharpe_ratio"] < SHARPE_TARGET:
        reasons.append(f"Latest two-year net Sharpe {metrics['sharpe_ratio']:.2f} is below {SHARPE_TARGET:.1f}.")
    if worst_split_sharpe < 0:
        reasons.append(f"Worst split Sharpe is {worst_split_sharpe:.2f}.")
    if positive_split_count < min(3, len(splits)):
        reasons.append(f"Only {positive_split_count}/{len(splits)} splits are positive after costs.")
    if metrics["total_transaction_cost_pct"] > max(1.0, abs(metrics["total_return_pct"]) * 0.35):
        reasons.append("Estimated trading cost is large relative to net return.")
    return {
        "package_candidate": len(reasons) == 0,
        "rejection_reasons": reasons,
        "worst_split_sharpe": round(float(worst_split_sharpe), 3),
        "positive_split_count": positive_split_count,
        "split_count": len(splits),
        "validation_test_sharpe_gap": round(float(validation_metrics.get("validation_sharpe_ratio", 0.0) - metrics["sharpe_ratio"]), 3),
        "transaction_cost_bps": TRANSACTION_COST_BPS,
        "slippage_bps": SLIPPAGE_BPS,
    }


def run() -> None:
    data, base_features = build_dataset()
    if len(data) <= TRAIN_END_OFFSET + VALIDATION_OFFSET + 200:
        raise RuntimeError("Not enough history for timing experiment.")

    test_start_index = len(data) - TRAIN_END_OFFSET
    validation_start_index = test_start_index - VALIDATION_OFFSET
    model_frame, feature_cols, feature_selection = build_model_frame(data, base_features, validation_start_index)
    fit = model_frame.iloc[:validation_start_index].copy()
    validation = model_frame.iloc[validation_start_index:test_start_index].copy()
    train_full = model_frame.iloc[:test_start_index].copy()
    test = model_frame.iloc[test_start_index:].copy()

    model_rows = []
    split_rows = []
    feature_rows = []
    prediction_frames = []

    for spec in model_specs():
        try:
            print(f"Running simple timing model: {spec['name']}")
            validation_long_model, validation_short_model, validation_model_type = fit_model_pair(spec, fit, feature_cols)
            validation_long_scores = predict_proba(validation_long_model, validation, feature_cols)
            validation_short_scores = predict_proba(validation_short_model, validation, feature_cols)
            threshold_config, _ = select_thresholds(validation, validation_long_scores, validation_short_scores)

            final_long_model, final_short_model, final_model_type = fit_model_pair(spec, train_full, feature_cols)
            test_long_scores = predict_proba(final_long_model, test, feature_cols)
            test_short_scores = predict_proba(final_short_model, test, feature_cols)
            result = backtest_timing(
                test,
                test_long_scores,
                test_short_scores,
                threshold_config["selected_threshold"],
                threshold_config["selected_short_threshold"],
                threshold_config["selected_edge_gap"],
                threshold_config["selected_min_hold_days"],
                threshold_config["selected_cooldown_days"],
            )
            metrics = metrics_for(result)
            splits = split_metrics(result, spec["name"])
            importances = feature_importance(final_long_model, final_short_model, feature_cols, train_full)
            gate = package_gate(metrics, splits, threshold_config)
            row = {
                "name": spec["name"],
                "model_type": final_model_type,
                "status": "ok",
                "message": (
                    "Simple timing model: shallow two-head long/short classifiers target 3-day moves beyond a rolling noise floor. "
                    "The model uses only selected first-order features, no second-order interaction pool, and trades only when timing edge exceeds validation-selected thresholds."
                ),
                "backtest_start": str(test["date"].iloc[0]),
                "backtest_end": str(test["date"].iloc[-1]),
                "features": feature_cols,
                "feature_engineering": [
                    "simple_first_order_features",
                    "rolling_noise_floor_target",
                    "long_short_timing_heads",
                    "validation_selected_entry_edge",
                    "minimum_hold_and_cooldown",
                ],
                "feature_count": len(feature_cols),
                "feature_candidate_count": len(base_features),
                "selected_feature_count": len(feature_cols),
                "feature_selection": feature_selection,
                "interaction_source_count": 0,
                "selected_threshold": threshold_config["selected_threshold"],
                "selected_short_threshold": threshold_config["selected_short_threshold"],
                "selected_score_margin": threshold_config["selected_edge_gap"],
                "selected_min_hold_days": threshold_config["selected_min_hold_days"],
                "selected_cooldown_days": threshold_config["selected_cooldown_days"],
                "strategy_side": "long_short_timing",
                "selected_candidate": spec["name"],
                "selected_candidate_index": 1,
                "candidate_count": len(model_specs()),
                "selected_validation_score": threshold_config["validation_selection_score"],
                "selected_hyperparameters": spec["params"],
                "candidate_trials": [threshold_config],
                "sharpe_target": SHARPE_TARGET,
                "target_met": metrics["sharpe_ratio"] >= SHARPE_TARGET,
                **gate,
                **threshold_config,
                **metrics,
                "feature_importance": importances[:16],
                "split_metrics": splits,
                "split_correlations": [],
                "equity_curve": [
                    {
                        "date": str(item["date"]),
                        "equity": round(float(item["equity"]), 4),
                        "gross_equity": round(float(item["gross_equity"]), 4),
                        "daily_return_pct": round(float(item["strategy_return"] * 100), 4),
                        "gross_daily_return_pct": round(float(item["gross_strategy_return"] * 100), 4),
                        "position": float(item["position"]),
                    }
                    for _, item in result.iloc[::max(1, len(result) // 120)].iterrows()
                ],
            }
            model_rows.append(row)
            split_rows.extend(splits)
            feature_rows.extend({"model_name": spec["name"], **item} for item in importances)
            prediction_frames.append(result.assign(model_name=spec["name"]))
        except Exception as error:
            model_rows.append({
                "name": spec["name"],
                "model_type": spec["model_type"],
                "status": "error",
                "message": str(error),
                "sharpe_ratio": 0.0,
                "win_rate_pct": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "exposure_pct": 0.0,
                "trades": 0,
                "observations": 0,
                "active_observations": 0,
                "feature_importance": [],
                "split_metrics": [],
                "split_correlations": [],
                "equity_curve": [],
            })

    summary = {
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accelerator": "GPU requested for simple XGBoost timing model; ExtraTrees CPU parallel baseline",
        "high_volume_rule": f"BTC volume >= rolling 252D {int(HIGH_VOLUME_QUANTILE * 100)}th percentile",
        "training_window": f"{data['date'].iloc[0]} to {data['date'].iloc[validation_start_index - 1]}",
        "validation_window": f"{data['date'].iloc[validation_start_index]} to {data['date'].iloc[test_start_index - 1]}",
        "backtest_window": f"{test['date'].iloc[0]} to {test['date'].iloc[-1]}",
        "batch_size": len(model_rows),
        "models_requested": len(model_rows),
        "candidate_count_total": len(model_rows),
        "sharpe_target": SHARPE_TARGET,
        "transaction_cost_bps": TRANSACTION_COST_BPS,
        "slippage_bps": SLIPPAGE_BPS,
        "feature_engineering": "Simple first-order features, no interaction pool, rolling-noise 3-day timing target, and validation-selected entry timing thresholds.",
        "base_feature_count": len(base_features),
        "interaction_source_count": 0,
        "feature_candidate_count": len(base_features),
        "selected_feature_count": len(feature_cols),
        "final_feature_count": len(feature_cols),
        "feature_selection": feature_selection,
        "models": sorted(model_rows, key=lambda row: row.get("sharpe_ratio", -999), reverse=True),
    }

    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(split_rows).to_csv(OUTPUT_DIR / "split_metrics.csv", index=False)
    pd.DataFrame(feature_rows).to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)
    pd.DataFrame([]).to_csv(OUTPUT_DIR / "split_correlations.csv", index=False)
    if prediction_frames:
        pd.concat(prediction_frames, ignore_index=True).to_csv(OUTPUT_DIR / "predictions.csv", index=False)
    print(json.dumps({"output_dir": str(OUTPUT_DIR), "models": len(model_rows)}, indent=2))


if __name__ == "__main__":
    run()
