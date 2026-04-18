import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

RUN_ID = "btc_volume_boosting_gpu_latest"
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
    "us30y": "^TYX",
    "us5y": "^FVX",
}

TRAIN_END_OFFSET = 504
VALIDATION_OFFSET = 252
HIGH_VOLUME_QUANTILE = 0.70
INTERACTION_FEATURE_LIMIT = 32
MIN_SELECTED_FEATURES = 120
SOFT_SELECTED_FEATURES = 240
MAX_SELECTED_FEATURES = 360
INTERACTION_PREFILTER_LIMIT = 900
MAX_FEATURE_CORRELATION = 0.68
MIN_SELECTED_BASE_FEATURES = 60
MIN_DYNAMIC_TARGET_CORRELATION = 0.012
SHARPE_TARGET = 2.0
MIN_VALIDATION_TRADES = 18
TRANSACTION_COST_BPS = 5.0
SLIPPAGE_BPS = 5.0
MIN_PACKAGE_ACTIVE_OBSERVATIONS = 40
SCORE_MARGIN_CANDIDATES = [0.0, 0.01, 0.02, 0.035, 0.05, 0.075, 0.1]
CANDIDATES_PER_MODEL = 10
VALIDATION_RETURN_WEIGHT = 0.015
VALIDATION_DRAWDOWN_WEIGHT = 0.015
VALIDATION_COST_PENALTY = 0.08
VALIDATION_TRADE_PENALTY = 0.012
EPSILON = 1e-6


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
        "volume": quote_data.get("volume", [np.nan] * len(result["timestamp"])),
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


def drawdown(series: pd.Series, window: int = 60) -> pd.Series:
    rolling_high = series.rolling(window).max()
    return (series - rolling_high) / rolling_high * 100


def rolling_position(series: pd.Series, window: int) -> pd.Series:
    low = series.rolling(window).min()
    high = series.rolling(window).max()
    return (series - low) / (high - low).replace(0, np.nan)


def add_market_features(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    close = data["btc_close"]
    high = data["btc_high"]
    low = data["btc_low"]
    open_ = data["btc_open"]
    volume = data["btc_volume"]
    features: list[str] = []

    def add(name: str, value: pd.Series) -> None:
        data[name] = value.replace([np.inf, -np.inf], np.nan)
        features.append(name)

    add("btc_return_1d", pct_change(close, 1))
    add("btc_return_3d", pct_change(close, 3))
    add("btc_return_5d", pct_change(close, 5))
    add("btc_return_7d", pct_change(close, 7))
    add("btc_return_14d", pct_change(close, 14))
    add("btc_return_30d", pct_change(close, 30))
    add("btc_return_60d", pct_change(close, 60))
    add("btc_return_lag_1", pct_change(close, 1).shift(1))
    add("btc_return_lag_3", pct_change(close, 1).shift(3))
    add("btc_return_lag_7", pct_change(close, 1).shift(7))
    add("btc_return_lag_14", pct_change(close, 1).shift(14))
    add("btc_return_lag_30", pct_change(close, 1).shift(30))
    add("btc_gap_pct", (open_ / close.shift(1) - 1) * 100)

    candle_range = (high - low).replace(0, np.nan)
    add("btc_candle_range_pct", candle_range / close * 100)
    add("btc_candle_body_pct", (close - open_) / open_.replace(0, np.nan) * 100)
    add("btc_candle_body_abs_pct", (close - open_).abs() / open_.replace(0, np.nan) * 100)
    add("btc_upper_wick_pct", (high - np.maximum(open_, close)) / close * 100)
    add("btc_lower_wick_pct", (np.minimum(open_, close) - low) / close * 100)
    add("btc_close_location", (close - low) / candle_range)
    add("btc_green_candle_flag", (close > open_).astype(float))
    add("btc_body_to_range", (close - open_).abs() / candle_range)
    add("btc_range_expansion_20d", candle_range / candle_range.rolling(20).mean())

    log_volume = np.log1p(volume)
    add("btc_log_volume", log_volume)
    add("btc_volume_diff_1d", volume.diff())
    add("btc_volume_diff_7d", volume.diff(7))
    add("btc_volume_pct_1d", pct_change(volume, 1))
    add("btc_volume_pct_7d", pct_change(volume, 7))
    add("btc_volume_pct_30d", pct_change(volume, 30))
    for window in [7, 20, 30, 60]:
        add(f"btc_volume_ratio_{window}d", volume / volume.rolling(window).mean())
        add(f"btc_volume_z_{window}d", (volume - volume.rolling(window).mean()) / volume.rolling(window).std())

    for window in [7, 14, 20, 30, 60]:
        add(f"btc_rolling_mean_distance_{window}d", (close / close.rolling(window).mean() - 1) * 100)
        add(f"btc_rolling_volatility_{window}d", pct_change(close, 1).rolling(window).std())
        add(f"btc_rolling_position_{window}d", rolling_position(close, window))
        add(f"btc_return_z_{window}d", (pct_change(close, 1) - pct_change(close, 1).rolling(window).mean()) / pct_change(close, 1).rolling(window).std())

    for window in [30, 60, 120]:
        add(f"btc_drawdown_{window}d", drawdown(close, window))
        add(f"btc_drawdown_change_{window}d", drawdown(close, window).diff())

    add("btc_rsi_7", rsi(close, 7))
    add("btc_rsi_14", rsi(close, 14))
    add("btc_rsi_30", rsi(close, 30))

    sma7 = close.rolling(7).mean()
    sma20 = close.rolling(20).mean()
    sma30 = close.rolling(30).mean()
    sma50 = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()
    sma200 = close.rolling(200).mean()
    add("btc_trend_above_sma20", (close > sma20).astype(float))
    add("btc_trend_above_sma50", (close > sma50).astype(float))
    add("btc_trend_sma7_above_sma30", (sma7 > sma30).astype(float))
    add("btc_trend_sma20_above_sma50", (sma20 > sma50).astype(float))
    add("btc_trend_sma50_above_sma200", (sma50 > sma200).astype(float))
    add("btc_trend_strength_20_50", (sma20 / sma50 - 1) * 100)
    add("btc_trend_strength_50_200", (sma50 / sma200 - 1) * 100)
    add("btc_golden_cross_20_50", ((sma20 > sma50) & (sma20.shift(1) <= sma50.shift(1))).astype(float))
    add("btc_golden_cross_50_200", ((sma50 > sma200) & (sma50.shift(1) <= sma200.shift(1))).astype(float))
    add("btc_death_cross_20_50", ((sma20 < sma50) & (sma20.shift(1) >= sma50.shift(1))).astype(float))

    bb_middle = sma20
    bb_std = close.rolling(20).std()
    bb_upper = bb_middle + bb_std * 2
    bb_lower = bb_middle - bb_std * 2
    add("btc_bollinger_width_20d", (bb_upper - bb_lower) / bb_middle * 100)
    add("btc_bollinger_percent_b_20d", (close - bb_lower) / (bb_upper - bb_lower).replace(0, np.nan))
    add("btc_bollinger_upper_distance_20d", (close / bb_upper - 1) * 100)
    add("btc_bollinger_lower_distance_20d", (close / bb_lower - 1) * 100)
    add("btc_bollinger_width_change_20d", ((bb_upper - bb_lower) / bb_middle * 100).diff())

    btc_return_1d = pct_change(close, 1)
    for prefix in ["sp500", "nasdaq", "gold", "silver", "oil", "vix", "dxy"]:
        if f"{prefix}_close" not in data:
            continue
        asset_return_1d = pct_change(data[f"{prefix}_close"], 1)
        add(f"{prefix}_return_1d", pct_change(data[f"{prefix}_close"], 1))
        add(f"{prefix}_return_5d", pct_change(data[f"{prefix}_close"], 5))
        add(f"{prefix}_return_7d", pct_change(data[f"{prefix}_close"], 7))
        add(f"{prefix}_return_20d", pct_change(data[f"{prefix}_close"], 20))
        add(f"{prefix}_return_30d", pct_change(data[f"{prefix}_close"], 30))
        add(f"{prefix}_return_60d", pct_change(data[f"{prefix}_close"], 60))
        add(f"{prefix}_rolling_volatility_20d", asset_return_1d.rolling(20).std())
        add(f"{prefix}_rolling_position_60d", rolling_position(data[f"{prefix}_close"], 60))
        add(f"btc_{prefix}_rolling_corr_30d", btc_return_1d.rolling(30).corr(asset_return_1d))

    for prefix in ["us10y", "us30y", "us5y"]:
        if f"{prefix}_close" not in data:
            continue
        add(f"{prefix}_bp_chg_1d", data[f"{prefix}_close"].diff() * 100)
        add(f"{prefix}_bp_chg_7d", data[f"{prefix}_close"].diff(7) * 100)
        add(f"{prefix}_bp_chg_30d", data[f"{prefix}_close"].diff(30) * 100)
        add(f"{prefix}_level_z_120d", (data[f"{prefix}_close"] - data[f"{prefix}_close"].rolling(120).mean()) / data[f"{prefix}_close"].rolling(120).std())

    if {"us10y_close", "us5y_close"}.issubset(data.columns):
        add("us10y_us5y_spread", data["us10y_close"] - data["us5y_close"])
        add("us10y_us5y_spread_chg_20d", (data["us10y_close"] - data["us5y_close"]).diff(20))
    if {"us30y_close", "us10y_close"}.issubset(data.columns):
        add("us30y_us10y_spread", data["us30y_close"] - data["us10y_close"])
    if {"gold_close", "silver_close"}.issubset(data.columns):
        add("gold_silver_ratio", data["gold_close"] / data["silver_close"])
    if {"nasdaq_close", "sp500_close"}.issubset(data.columns):
        add("nasdaq_sp500_relative_20d", pct_change(data["nasdaq_close"], 20) - pct_change(data["sp500_close"], 20))
    if "vix_close" in data:
        add("vix_term_proxy_20d", data["vix_close"] - data["vix_close"].rolling(20).mean())
    if {"dxy_close", "gold_close"}.issubset(data.columns):
        add("dxy_gold_relative_20d", pct_change(data["dxy_close"], 20) - pct_change(data["gold_close"], 20))

    data["high_volume_candle"] = volume >= volume.rolling(252).quantile(HIGH_VOLUME_QUANTILE)
    data["target_return_1d"] = pct_change(close, 1).shift(-1)
    data["target_up"] = (data["target_return_1d"] > 0).astype(int)
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
            print(f"Optional symbol {prefix} ({symbol}) skipped: {error}")

    data = data.sort_values("date").ffill()
    data, base_features = add_market_features(data)
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=base_features + ["target_return_1d"]).reset_index(drop=True)
    return data, base_features


def fit_standardizer(frame: pd.DataFrame, columns: list[str]) -> tuple[pd.Series, pd.Series]:
    means = frame[columns].mean()
    stds = frame[columns].std().replace(0, np.nan).fillna(1.0)
    return means, stds


def apply_standardizer(frame: pd.DataFrame, columns: list[str], means: pd.Series, stds: pd.Series) -> pd.DataFrame:
    normalized = (frame[columns] - means) / stds
    return normalized.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-8, 8)


def select_interaction_sources(train_normalized: pd.DataFrame, target: pd.Series, columns: list[str]) -> list[str]:
    scores = []
    for column in columns:
        corr = train_normalized[column].corr(target)
        scores.append((column, abs(corr) if not np.isnan(corr) else 0.0))
    selected = [name for name, _ in sorted(scores, key=lambda item: item[1], reverse=True)[:INTERACTION_FEATURE_LIMIT]]
    return selected


def safe_divide(left: pd.Series, right: pd.Series) -> pd.Series:
    denominator = right.copy()
    denominator = denominator.mask(denominator.abs() < 0.25, np.sign(denominator).replace(0, 1) * 0.25)
    return (left / denominator).clip(-12, 12)


def build_second_order_features(normalized: pd.DataFrame, source_cols: list[str]) -> pd.DataFrame:
    interactions: dict[str, pd.Series] = {}
    for left_index, left_name in enumerate(source_cols):
        left = normalized[left_name]
        for right_name in source_cols[left_index + 1:]:
            right = normalized[right_name]
            prefix = f"{left_name}__{right_name}"
            interactions[f"{prefix}__mul"] = (left * right).clip(-12, 12)
            interactions[f"{prefix}__add"] = (left + right).clip(-12, 12)
            interactions[f"{prefix}__sub"] = (left - right).clip(-12, 12)
            interactions[f"{prefix}__div"] = safe_divide(left, right)
    return pd.DataFrame(interactions, index=normalized.index).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def select_low_correlation_features(features: pd.DataFrame, target: pd.Series, base_feature_count: int) -> tuple[list[str], dict]:
    target_scores = features.corrwith(target).abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    ranked = target_scores.sort_values(ascending=False)
    base_candidates = [column for column in ranked.index if column.startswith("z_")]
    interaction_candidates = [column for column in ranked.index if column.startswith("z2_")][:INTERACTION_PREFILTER_LIMIT]
    candidate_pool = list(dict.fromkeys(base_candidates + interaction_candidates))
    ranked_pool = [column for column in ranked.index if column in set(candidate_pool)]
    candidate_corr = features[candidate_pool].corr().abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    pool_scores = target_scores[ranked_pool]
    soft_rank_index = min(SOFT_SELECTED_FEATURES - 1, len(pool_scores) - 1) if len(pool_scores) else 0
    dynamic_score_floor = (
        max(MIN_DYNAMIC_TARGET_CORRELATION, float(pool_scores.iloc[soft_rank_index]) * 0.75)
        if len(pool_scores)
        else MIN_DYNAMIC_TARGET_CORRELATION
    )
    selected: list[str] = []
    selected_set: set[str] = set()

    def selected_base_count() -> int:
        return sum(1 for column in selected if column.startswith("z_"))

    def try_add(column: str, max_corr_allowed: float) -> None:
        if column in selected_set or len(selected) >= MAX_SELECTED_FEATURES:
            return
        score = float(target_scores.get(column, 0.0))
        floor_is_active = (
            len(selected) >= MIN_SELECTED_FEATURES
            and not (column.startswith("z_") and selected_base_count() < MIN_SELECTED_BASE_FEATURES)
        )
        if floor_is_active and score < dynamic_score_floor:
            return
        if selected:
            max_corr = float(candidate_corr.loc[column, selected].max())
            if max_corr > max_corr_allowed:
                return
        selected.append(column)
        selected_set.add(column)

    for max_corr_allowed in [MAX_FEATURE_CORRELATION, 0.78, 0.88, 0.96, 1.01]:
        for column in base_candidates:
            if selected_base_count() >= MIN_SELECTED_BASE_FEATURES:
                break
            try_add(column, max_corr_allowed)

        if len(selected) >= MAX_SELECTED_FEATURES:
            break

        for column in ranked_pool:
            try_add(column, max_corr_allowed)
            if len(selected) >= MAX_SELECTED_FEATURES:
                break

        if len(selected) >= MAX_SELECTED_FEATURES:
            break

    selected = selected[:MAX_SELECTED_FEATURES]
    selected_corr = features[selected].corr().abs() if len(selected) > 1 else pd.DataFrame()
    if len(selected) > 1:
        upper = selected_corr.where(np.triu(np.ones(selected_corr.shape), k=1).astype(bool))
        max_pairwise_corr = float(upper.max().max())
    else:
        max_pairwise_corr = 0.0

    summary = {
        "method": "dynamic target-ranked low-correlation selection with full-pool base-feature floor on pre-test training data",
        "candidate_feature_count": int(features.shape[1]),
        "candidate_pool_count": int(len(candidate_pool)),
        "base_candidate_count": int(len(base_candidates)),
        "interaction_prefilter_count": int(len(interaction_candidates)),
        "selected_feature_count": int(len(selected)),
        "base_feature_count": int(base_feature_count),
        "selected_base_feature_count": int(sum(1 for column in selected if column.startswith("z_"))),
        "selected_interaction_feature_count": int(sum(1 for column in selected if column.startswith("z2_"))),
        "min_selected_features": int(MIN_SELECTED_FEATURES),
        "soft_selected_features": int(SOFT_SELECTED_FEATURES),
        "max_selected_features": int(MAX_SELECTED_FEATURES),
        "min_selected_base_features": int(MIN_SELECTED_BASE_FEATURES),
        "selected_base_floor_met": selected_base_count() >= min(MIN_SELECTED_BASE_FEATURES, len(base_candidates)),
        "dynamic_target_score_floor": round(float(dynamic_score_floor), 5),
        "max_allowed_pairwise_correlation": MAX_FEATURE_CORRELATION,
        "observed_max_pairwise_correlation": round(max_pairwise_corr, 4),
        "mean_abs_target_correlation": round(float(target_scores[selected].mean()), 5) if selected else 0.0,
    }
    return selected, summary


def build_model_matrices(
    data: pd.DataFrame,
    base_features: list[str],
    test_start_index: int,
) -> tuple[pd.DataFrame, list[str], list[str], dict]:
    train_all = data.iloc[:test_start_index].copy()
    base_means, base_stds = fit_standardizer(train_all, base_features)
    base_normalized = apply_standardizer(data, base_features, base_means, base_stds)
    base_normalized.columns = [f"z_{column}" for column in base_normalized.columns]
    normalized_base_features = list(base_normalized.columns)

    train_normalized = base_normalized.iloc[:test_start_index].copy()
    interaction_sources = select_interaction_sources(
        train_normalized,
        train_all["target_return_1d"],
        normalized_base_features,
    )
    raw_interactions = build_second_order_features(base_normalized, interaction_sources)
    interaction_means, interaction_stds = fit_standardizer(raw_interactions.iloc[:test_start_index], list(raw_interactions.columns))
    normalized_interactions = apply_standardizer(raw_interactions, list(raw_interactions.columns), interaction_means, interaction_stds)
    normalized_interactions.columns = [f"z2_{column}" for column in normalized_interactions.columns]

    feature_candidates = pd.concat([base_normalized, normalized_interactions], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    selected_features, feature_selection = select_low_correlation_features(
        feature_candidates.iloc[:test_start_index],
        train_all["target_return_1d"],
        len(base_features),
    )
    features = feature_candidates[selected_features].copy()
    return features, selected_features, interaction_sources, feature_selection


def _make_factory(model_class, params: dict):
    clean_params = dict(params)
    return lambda clean_params=clean_params: model_class(**clean_params)


def _model_group(name: str, model_type: str, model_class, configs: list[dict], cpu_cleaner=None) -> dict:
    candidates = []
    for index, params in enumerate(configs[:CANDIDATES_PER_MODEL], start=1):
        fallback_params = cpu_cleaner(params) if cpu_cleaner else None
        candidates.append({
            "candidate_name": f"{name}_c{index:02d}",
            "candidate_index": index,
            "params": dict(params),
            "factory": _make_factory(model_class, params),
            "fallback_factory": _make_factory(model_class, fallback_params) if fallback_params else None,
        })
    return {"name": name, "model_type": model_type, "candidates": candidates}


def _lgbm_cpu_params(params: dict) -> dict:
    cpu_params = dict(params)
    cpu_params.pop("device", None)
    return cpu_params


def _xgb_cpu_params(params: dict) -> dict:
    cpu_params = dict(params)
    cpu_params.pop("device", None)
    cpu_params["tree_method"] = "hist"
    return cpu_params


def model_specs():
    groups = []

    try:
        from lightgbm import LGBMClassifier
        lgbm_configs = [
            {"n_estimators": 360, "max_depth": 3, "num_leaves": 10, "learning_rate": 0.035, "subsample": 0.72, "colsample_bytree": 0.50, "reg_alpha": 0.25, "reg_lambda": 0.90, "min_child_samples": 22, "objective": "binary", "device": "gpu", "random_state": 4101},
            {"n_estimators": 420, "max_depth": 3, "num_leaves": 12, "learning_rate": 0.030, "subsample": 0.78, "colsample_bytree": 0.56, "reg_alpha": 0.18, "reg_lambda": 0.70, "min_child_samples": 18, "objective": "binary", "device": "gpu", "random_state": 4102},
            {"n_estimators": 480, "max_depth": 4, "num_leaves": 16, "learning_rate": 0.026, "subsample": 0.82, "colsample_bytree": 0.62, "reg_alpha": 0.12, "reg_lambda": 0.55, "min_child_samples": 16, "objective": "binary", "device": "gpu", "random_state": 4103},
            {"n_estimators": 520, "max_depth": 4, "num_leaves": 18, "learning_rate": 0.024, "subsample": 0.86, "colsample_bytree": 0.66, "reg_alpha": 0.08, "reg_lambda": 0.45, "min_child_samples": 14, "objective": "binary", "device": "gpu", "random_state": 4104},
            {"n_estimators": 580, "max_depth": 4, "num_leaves": 22, "learning_rate": 0.021, "subsample": 0.76, "colsample_bytree": 0.70, "reg_alpha": 0.15, "reg_lambda": 0.80, "min_child_samples": 20, "objective": "binary", "device": "gpu", "random_state": 4105},
            {"n_estimators": 640, "max_depth": 5, "num_leaves": 24, "learning_rate": 0.019, "subsample": 0.84, "colsample_bytree": 0.58, "reg_alpha": 0.10, "reg_lambda": 0.60, "min_child_samples": 18, "objective": "binary", "device": "gpu", "random_state": 4106},
            {"n_estimators": 700, "max_depth": 5, "num_leaves": 28, "learning_rate": 0.017, "subsample": 0.88, "colsample_bytree": 0.74, "reg_alpha": 0.06, "reg_lambda": 0.40, "min_child_samples": 12, "objective": "binary", "device": "gpu", "random_state": 4107},
            {"n_estimators": 460, "max_depth": 2, "num_leaves": 8, "learning_rate": 0.040, "subsample": 0.68, "colsample_bytree": 0.44, "reg_alpha": 0.35, "reg_lambda": 1.10, "min_child_samples": 28, "objective": "binary", "device": "gpu", "random_state": 4108},
            {"n_estimators": 760, "max_depth": 3, "num_leaves": 14, "learning_rate": 0.015, "subsample": 0.80, "colsample_bytree": 0.52, "reg_alpha": 0.22, "reg_lambda": 0.95, "min_child_samples": 24, "objective": "binary", "device": "gpu", "random_state": 4109},
            {"n_estimators": 600, "max_depth": 4, "num_leaves": 20, "learning_rate": 0.022, "subsample": 0.92, "colsample_bytree": 0.60, "reg_alpha": 0.04, "reg_lambda": 0.35, "min_child_samples": 10, "objective": "binary", "device": "gpu", "random_state": 4110},
        ]
        groups.append(_model_group("lgbm_gpu_engineered", "lightgbm_gpu_classifier", LGBMClassifier, lgbm_configs, _lgbm_cpu_params))
    except Exception as error:
        groups.append({
            "name": "lgbm_gpu_engineered",
            "model_type": "lightgbm_import_error",
            "candidates": [{"candidate_name": "lgbm_gpu_engineered_c01", "candidate_index": 1, "params": {}, "factory": lambda error=error: (_ for _ in ()).throw(error), "fallback_factory": None}],
        })

    try:
        from xgboost import XGBClassifier
        xgb_configs = [
            {"n_estimators": 360, "max_depth": 2, "learning_rate": 0.040, "subsample": 0.72, "colsample_bytree": 0.50, "reg_alpha": 0.35, "reg_lambda": 1.10, "min_child_weight": 5.0, "gamma": 0.20, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3701},
            {"n_estimators": 420, "max_depth": 2, "learning_rate": 0.034, "subsample": 0.78, "colsample_bytree": 0.56, "reg_alpha": 0.25, "reg_lambda": 0.90, "min_child_weight": 4.0, "gamma": 0.12, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3702},
            {"n_estimators": 480, "max_depth": 3, "learning_rate": 0.028, "subsample": 0.82, "colsample_bytree": 0.62, "reg_alpha": 0.15, "reg_lambda": 0.65, "min_child_weight": 3.0, "gamma": 0.06, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3703},
            {"n_estimators": 520, "max_depth": 3, "learning_rate": 0.024, "subsample": 0.86, "colsample_bytree": 0.66, "reg_alpha": 0.12, "reg_lambda": 0.55, "min_child_weight": 2.5, "gamma": 0.04, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3704},
            {"n_estimators": 580, "max_depth": 3, "learning_rate": 0.021, "subsample": 0.76, "colsample_bytree": 0.70, "reg_alpha": 0.18, "reg_lambda": 0.80, "min_child_weight": 3.5, "gamma": 0.10, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3705},
            {"n_estimators": 640, "max_depth": 4, "learning_rate": 0.018, "subsample": 0.84, "colsample_bytree": 0.58, "reg_alpha": 0.10, "reg_lambda": 0.60, "min_child_weight": 2.0, "gamma": 0.03, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3706},
            {"n_estimators": 700, "max_depth": 4, "learning_rate": 0.016, "subsample": 0.88, "colsample_bytree": 0.74, "reg_alpha": 0.08, "reg_lambda": 0.45, "min_child_weight": 1.5, "gamma": 0.02, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3707},
            {"n_estimators": 460, "max_depth": 2, "learning_rate": 0.032, "subsample": 0.68, "colsample_bytree": 0.44, "reg_alpha": 0.45, "reg_lambda": 1.30, "min_child_weight": 6.0, "gamma": 0.25, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3708},
            {"n_estimators": 760, "max_depth": 3, "learning_rate": 0.014, "subsample": 0.80, "colsample_bytree": 0.52, "reg_alpha": 0.30, "reg_lambda": 1.00, "min_child_weight": 4.5, "gamma": 0.15, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3709},
            {"n_estimators": 600, "max_depth": 4, "learning_rate": 0.020, "subsample": 0.92, "colsample_bytree": 0.60, "reg_alpha": 0.05, "reg_lambda": 0.35, "min_child_weight": 1.2, "gamma": 0.01, "objective": "binary:logistic", "eval_metric": "logloss", "tree_method": "hist", "device": "cuda", "random_state": 3710},
        ]
        groups.append(_model_group("xgb_gpu_engineered", "xgboost_gpu_classifier", XGBClassifier, xgb_configs, _xgb_cpu_params))
    except Exception as error:
        groups.append({
            "name": "xgb_gpu_engineered",
            "model_type": "xgboost_import_error",
            "candidates": [{"candidate_name": "xgb_gpu_engineered_c01", "candidate_index": 1, "params": {}, "factory": lambda error=error: (_ for _ in ()).throw(error), "fallback_factory": None}],
        })

    from sklearn.ensemble import ExtraTreesClassifier
    extra_configs = [
        {"n_estimators": 420, "max_depth": 5, "min_samples_leaf": 12, "min_samples_split": 24, "max_features": 0.32, "bootstrap": False, "random_state": 1901, "n_jobs": -1},
        {"n_estimators": 480, "max_depth": 6, "min_samples_leaf": 10, "min_samples_split": 20, "max_features": 0.38, "bootstrap": False, "random_state": 1902, "n_jobs": -1},
        {"n_estimators": 520, "max_depth": 7, "min_samples_leaf": 8, "min_samples_split": 16, "max_features": 0.45, "bootstrap": False, "random_state": 1903, "n_jobs": -1},
        {"n_estimators": 580, "max_depth": 8, "min_samples_leaf": 6, "min_samples_split": 14, "max_features": 0.52, "bootstrap": False, "random_state": 1904, "n_jobs": -1},
        {"n_estimators": 640, "max_depth": 9, "min_samples_leaf": 5, "min_samples_split": 12, "max_features": 0.60, "bootstrap": False, "random_state": 1905, "n_jobs": -1},
        {"n_estimators": 700, "max_depth": 10, "min_samples_leaf": 4, "min_samples_split": 10, "max_features": 0.68, "bootstrap": False, "random_state": 1906, "n_jobs": -1},
        {"n_estimators": 760, "max_depth": 7, "min_samples_leaf": 7, "min_samples_split": 18, "max_features": 0.42, "bootstrap": True, "random_state": 1907, "n_jobs": -1},
        {"n_estimators": 540, "max_depth": 4, "min_samples_leaf": 16, "min_samples_split": 32, "max_features": 0.28, "bootstrap": True, "random_state": 1908, "n_jobs": -1},
        {"n_estimators": 820, "max_depth": 6, "min_samples_leaf": 9, "min_samples_split": 18, "max_features": 0.50, "bootstrap": True, "random_state": 1909, "n_jobs": -1},
        {"n_estimators": 620, "max_depth": None, "min_samples_leaf": 12, "min_samples_split": 28, "max_features": 0.36, "bootstrap": True, "random_state": 1910, "n_jobs": -1},
    ]
    groups.append(_model_group("extra_trees_engineered", "extra_trees_classifier", ExtraTreesClassifier, extra_configs))
    return groups


def predict_signal(model, x: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(x)[:, 1], dtype=float)
    return np.asarray(model.predict(x), dtype=float)


def backtest_from_scores(
    frame: pd.DataFrame,
    scores: np.ndarray,
    long_threshold: float,
    short_threshold: float | None = None,
    allow_short: bool = False,
    score_margin: float = 0.0,
) -> pd.DataFrame:
    result = frame[["date", "target_return_1d", "high_volume_candle"]].copy()
    result["score"] = scores
    result["probability"] = scores
    high_volume = result["high_volume_candle"].to_numpy(dtype=bool)
    result["position"] = 0.0
    effective_long_threshold = long_threshold + score_margin
    effective_short_threshold = short_threshold - score_margin if short_threshold is not None else None
    result.loc[high_volume & (result["score"] >= effective_long_threshold), "position"] = 1.0
    if allow_short and short_threshold is not None:
        result.loc[high_volume & (result["score"] <= effective_short_threshold), "position"] = -1.0
    result["score_margin"] = score_margin
    result["gross_strategy_return"] = result["position"] * result["target_return_1d"] / 100
    result["position_change"] = result["position"].diff().abs().fillna(result["position"].abs())
    result["transaction_cost"] = result["position_change"] * ((TRANSACTION_COST_BPS + SLIPPAGE_BPS) / 10000)
    result["strategy_return"] = result["gross_strategy_return"] - result["transaction_cost"]
    result["gross_equity"] = (1 + result["gross_strategy_return"]).cumprod()
    result["equity"] = (1 + result["strategy_return"]).cumprod()
    return result


def metrics_for(result: pd.DataFrame) -> dict:
    returns = result["strategy_return"].fillna(0)
    gross_returns = result.get("gross_strategy_return", result["strategy_return"]).fillna(0)
    active = result[result["position"] != 0]
    volatility = returns.std()
    sharpe = (returns.mean() / volatility) * math.sqrt(252) if volatility and not np.isnan(volatility) else 0.0
    gross_volatility = gross_returns.std()
    gross_sharpe = (
        (gross_returns.mean() / gross_volatility) * math.sqrt(252)
        if gross_volatility and not np.isnan(gross_volatility)
        else 0.0
    )
    equity = result["equity"].iloc[-1] if len(result) else 1.0
    gross_equity = result.get("gross_equity", result["equity"]).iloc[-1] if len(result) else 1.0
    peak = result["equity"].cummax()
    drawdown = ((result["equity"] - peak) / peak).min() * 100 if len(result) else 0.0
    return {
        "sharpe_ratio": round(float(sharpe), 3),
        "gross_sharpe_ratio": round(float(gross_sharpe), 3),
        "win_rate_pct": round(float((active["strategy_return"] > 0).mean() * 100), 2) if len(active) else 0.0,
        "total_return_pct": round(float((equity - 1) * 100), 3),
        "gross_total_return_pct": round(float((gross_equity - 1) * 100), 3),
        "max_drawdown_pct": round(float(drawdown), 3),
        "exposure_pct": round(float((result["position"] != 0).mean() * 100), 2) if len(result) else 0.0,
        "trades": int(result.get("position_change", result["position"].diff().abs().fillna(0)).sum()),
        "total_transaction_cost_pct": round(float(result.get("transaction_cost", pd.Series(0, index=result.index)).sum() * 100), 3),
        "observations": int(len(result)),
        "active_observations": int(len(active)),
    }


def package_gate(metrics: dict, split_metrics: list[dict], validation_metrics: dict) -> dict:
    split_sharpes = [float(row.get("sharpe_ratio", 0.0)) for row in split_metrics]
    split_returns = [float(row.get("total_return_pct", 0.0)) for row in split_metrics]
    split_count = len(split_metrics)
    positive_split_count = sum(1 for value in split_returns if value > 0)
    worst_split_sharpe = min(split_sharpes) if split_sharpes else 0.0
    validation_sharpe = float(validation_metrics.get("validation_sharpe_ratio", 0.0))
    validation_test_gap = round(float(validation_sharpe - metrics["sharpe_ratio"]), 3)
    reasons = []

    if metrics["sharpe_ratio"] < SHARPE_TARGET:
        reasons.append(f"Latest two-year net Sharpe {metrics['sharpe_ratio']:.2f} is below {SHARPE_TARGET:.1f}.")
    if worst_split_sharpe < 0:
        reasons.append(f"Worst split Sharpe is {worst_split_sharpe:.2f}, so the model fails the split kill-switch.")
    if positive_split_count < min(3, split_count):
        reasons.append(f"Only {positive_split_count}/{split_count} splits are positive after costs.")
    if validation_sharpe >= SHARPE_TARGET and validation_test_gap > 1.0:
        reasons.append("Validation Sharpe decayed by more than 1.0 versus the latest two-year backtest.")
    if metrics["active_observations"] < MIN_PACKAGE_ACTIVE_OBSERVATIONS:
        reasons.append(f"Only {metrics['active_observations']} active observations, below the package gate sample floor.")
    if metrics["total_transaction_cost_pct"] > max(1.0, abs(metrics["total_return_pct"]) * 0.35):
        reasons.append("Estimated trading cost is large relative to net return.")

    return {
        "package_candidate": len(reasons) == 0,
        "rejection_reasons": reasons,
        "worst_split_sharpe": round(float(worst_split_sharpe), 3),
        "positive_split_count": positive_split_count,
        "split_count": split_count,
        "validation_test_sharpe_gap": validation_test_gap,
        "transaction_cost_bps": TRANSACTION_COST_BPS,
        "slippage_bps": SLIPPAGE_BPS,
    }


def select_thresholds(validation: pd.DataFrame, scores: np.ndarray) -> tuple[float, float | None, bool, float, dict]:
    high_volume_scores = scores[validation["high_volume_candle"].to_numpy(dtype=bool)]
    if len(high_volume_scores) == 0:
        return float(np.nanmean(scores)), None, False, 0.0, {"validation_sharpe_ratio": 0.0}

    long_quantiles = np.linspace(0.52, 0.97, 20)
    short_quantiles = np.linspace(0.03, 0.42, 18)
    long_candidates = sorted(set(float(np.nanquantile(high_volume_scores, quantile)) for quantile in long_quantiles))
    short_candidates = sorted(set(float(np.nanquantile(high_volume_scores, quantile)) for quantile in short_quantiles))
    best_long = long_candidates[0]
    best_short = None
    best_allow_short = False
    best_margin = 0.0
    best_metrics = {"sharpe_ratio": -999.0, "total_return_pct": -999.0, "active_observations": 0}

    for long_threshold in long_candidates:
        for score_margin in SCORE_MARGIN_CANDIDATES:
            result = backtest_from_scores(validation, scores, long_threshold, score_margin=score_margin)
            metrics = metrics_for(result)
            if metrics["active_observations"] < MIN_VALIDATION_TRADES:
                continue
            candidate_rank = (metrics["sharpe_ratio"], metrics["total_return_pct"], -metrics["trades"])
            best_rank = (best_metrics["sharpe_ratio"], best_metrics["total_return_pct"], -best_metrics.get("trades", 0))
            if candidate_rank > best_rank:
                best_long = long_threshold
                best_short = None
                best_allow_short = False
                best_margin = score_margin
                best_metrics = metrics

    for long_threshold in long_candidates:
        for short_threshold in short_candidates:
            if short_threshold >= long_threshold:
                continue
            for score_margin in SCORE_MARGIN_CANDIDATES:
                result = backtest_from_scores(validation, scores, long_threshold, short_threshold, allow_short=True, score_margin=score_margin)
                metrics = metrics_for(result)
                if metrics["active_observations"] < MIN_VALIDATION_TRADES:
                    continue
                candidate_rank = (metrics["sharpe_ratio"], metrics["total_return_pct"], -metrics["trades"])
                best_rank = (best_metrics["sharpe_ratio"], best_metrics["total_return_pct"], -best_metrics.get("trades", 0))
                if candidate_rank > best_rank:
                    best_long = long_threshold
                    best_short = short_threshold
                    best_allow_short = True
                    best_margin = score_margin
                    best_metrics = metrics

    if best_metrics["sharpe_ratio"] == -999.0:
        best_long = float(np.nanquantile(high_volume_scores, 0.80))
        best_metrics = metrics_for(backtest_from_scores(validation, scores, best_long))

    best_metrics = {f"validation_{key}": value for key, value in best_metrics.items()}
    return float(best_long), float(best_short) if best_short is not None else None, best_allow_short, float(best_margin), best_metrics


def feature_importance(model, feature_cols: list[str], train_x: pd.DataFrame, train_y: pd.Series) -> list[dict]:
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    else:
        values = np.asarray([abs(train_x[col].corr(train_y)) if train_x[col].std() else 0 for col in feature_cols], dtype=float)
    total = values.sum() or 1
    return [
        {"feature": feature, "importance": round(float(value / total), 6)}
        for feature, value in sorted(zip(feature_cols, values), key=lambda item: item[1], reverse=True)
    ]


def split_analysis(model_name: str, result: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str], importances: list[dict]) -> tuple[list[dict], list[dict]]:
    split_metrics = []
    correlations = []
    chunks = np.array_split(np.arange(len(result)), 4)
    top_features = [row["feature"] for row in importances[:10]]
    for split_index, index_values in enumerate(chunks, start=1):
        if len(index_values) == 0:
            continue
        result_part = result.iloc[index_values].copy()
        test_part = test.iloc[index_values].copy()
        metric = metrics_for(result_part)
        metric.update({
            "model_name": model_name,
            "split": split_index,
            "start": str(result_part["date"].iloc[0]),
            "end": str(result_part["date"].iloc[-1]),
        })
        split_metrics.append(metric)
        for feature in top_features:
            corr = test_part[feature].corr(test_part["target_return_1d"])
            correlations.append({
                "model_name": model_name,
                "split": split_index,
                "feature": feature,
                "correlation": round(float(corr), 4) if not np.isnan(corr) else 0.0,
            })
    return split_metrics, correlations


def fit_model(factory, x: pd.DataFrame, y: pd.Series, model_type: str, fallback_factory=None):
    try:
        model = factory()
        model.fit(x, y)
        return model, model_type
    except Exception as gpu_error:
        print(f"{model_type} fit failed, retrying CPU-compatible fallback: {gpu_error}")
        if fallback_factory is None:
            raise
        model = fallback_factory()
        model.fit(x, y)
        return model, f"{model_type}_cpu_fallback"


def validation_selection_score(validation_metrics: dict) -> float:
    sharpe = float(validation_metrics.get("validation_sharpe_ratio", -999.0))
    total_return = float(validation_metrics.get("validation_total_return_pct", -999.0))
    max_drawdown = float(validation_metrics.get("validation_max_drawdown_pct", -999.0))
    cost = float(validation_metrics.get("validation_total_transaction_cost_pct", 999.0))
    trades = float(validation_metrics.get("validation_trades", 999.0))
    return (
        sharpe
        + total_return * VALIDATION_RETURN_WEIGHT
        + max_drawdown * VALIDATION_DRAWDOWN_WEIGHT
        - cost * VALIDATION_COST_PENALTY
        - trades * VALIDATION_TRADE_PENALTY
    )


def validation_rank(validation_metrics: dict) -> tuple[float, float, float, float, float, int]:
    return (
        float(validation_metrics.get("validation_selection_score", validation_selection_score(validation_metrics))),
        float(validation_metrics.get("validation_sharpe_ratio", -999.0)),
        float(validation_metrics.get("validation_total_return_pct", -999.0)),
        float(validation_metrics.get("validation_max_drawdown_pct", -999.0)),
        -float(validation_metrics.get("validation_total_transaction_cost_pct", 999.0)),
        -int(validation_metrics.get("validation_trades", 999999)),
    )


def safe_json_params(params: dict) -> dict:
    clean = {}
    for key, value in params.items():
        if isinstance(value, (np.integer, np.floating)):
            clean[key] = value.item()
        else:
            clean[key] = value
    return clean


def run():
    data, base_features = build_dataset()
    if len(data) <= TRAIN_END_OFFSET + VALIDATION_OFFSET + 200:
        raise RuntimeError("Not enough data for older-than-two-year training, validation, and two-year backtest.")

    test_start_index = len(data) - TRAIN_END_OFFSET
    validation_start_index = test_start_index - VALIDATION_OFFSET
    feature_matrix, feature_cols, interaction_sources, feature_selection = build_model_matrices(data, base_features, test_start_index)
    model_frame = pd.concat(
        [
            data[["date", "target_return_1d", "target_up", "high_volume_candle"]].reset_index(drop=True),
            feature_matrix.reset_index(drop=True),
        ],
        axis=1,
    )

    fit_frame = model_frame.iloc[:validation_start_index].copy()
    validation = model_frame.iloc[validation_start_index:test_start_index].copy()
    train_full = model_frame.iloc[:test_start_index].copy()
    test = model_frame.iloc[test_start_index:].copy()

    fit_high_volume = fit_frame[fit_frame["high_volume_candle"]].copy()
    train_full_high_volume = train_full[train_full["high_volume_candle"]].copy()
    model_groups = model_specs()
    model_rows = []
    split_rows = []
    corr_rows = []
    feature_rows = []
    prediction_frames = []

    print(json.dumps({
        "base_features": len(base_features),
        "interaction_sources": len(interaction_sources),
        "candidate_features": feature_selection["candidate_feature_count"],
        "final_features": len(feature_cols),
        "feature_selection": feature_selection,
        "models": [group["name"] for group in model_groups],
        "candidates_per_model": CANDIDATES_PER_MODEL,
        "candidate_count_total": sum(len(group["candidates"]) for group in model_groups),
    }, indent=2))

    for group in model_groups:
        name = group["name"]
        model_type = group["model_type"]
        candidates = group["candidates"]
        try:
            print(f"Running engineered model group: {name} with {len(candidates)} candidates")
            candidate_trials = []
            best_trial = None

            for candidate in candidates:
                try:
                    print(f"Running candidate: {candidate['candidate_name']}")
                    validation_model, validation_model_type = fit_model(
                        candidate["factory"],
                        fit_high_volume[feature_cols],
                        fit_high_volume["target_up"],
                        model_type,
                        candidate.get("fallback_factory"),
                    )
                    validation_scores = predict_signal(validation_model, validation[feature_cols])
                    long_threshold, short_threshold, allow_short, score_margin, validation_metrics = select_thresholds(validation, validation_scores)
                    validation_metrics["validation_selection_score"] = round(float(validation_selection_score(validation_metrics)), 3)
                    trial = {
                        "candidate_name": candidate["candidate_name"],
                        "candidate_index": candidate["candidate_index"],
                        "status": "ok",
                        "model_type": validation_model_type,
                        "selected_threshold": round(float(long_threshold), 6),
                        "selected_short_threshold": round(float(short_threshold), 6) if short_threshold is not None else None,
                        "selected_score_margin": round(float(score_margin), 6),
                        "strategy_side": "long_short" if allow_short else "long_only",
                        "hyperparameters": safe_json_params(candidate["params"]),
                        **validation_metrics,
                    }
                    candidate_trials.append(trial)
                    if best_trial is None or validation_rank(trial) > validation_rank(best_trial):
                        best_trial = {
                            **trial,
                            "candidate": candidate,
                            "long_threshold": long_threshold,
                            "short_threshold": short_threshold,
                            "allow_short": allow_short,
                            "score_margin": score_margin,
                        }
                except Exception as candidate_error:
                    candidate_trials.append({
                        "candidate_name": candidate["candidate_name"],
                        "candidate_index": candidate["candidate_index"],
                        "status": "error",
                        "message": str(candidate_error),
                        "hyperparameters": safe_json_params(candidate["params"]),
                    })

            if best_trial is None:
                raise RuntimeError(f"No successful validation candidate for {name}")

            selected_candidate = best_trial["candidate"]
            long_threshold = float(best_trial["long_threshold"])
            short_threshold = best_trial["short_threshold"]
            allow_short = bool(best_trial["allow_short"])
            score_margin = float(best_trial["score_margin"])
            validation_metrics = {
                key: value
                for key, value in best_trial.items()
                if key.startswith("validation_")
            }

            final_model, final_model_type = fit_model(
                selected_candidate["factory"],
                train_full_high_volume[feature_cols],
                train_full_high_volume["target_up"],
                best_trial["model_type"],
                selected_candidate.get("fallback_factory"),
            )
            scores = predict_signal(final_model, test[feature_cols])
            result = backtest_from_scores(test, scores, long_threshold, short_threshold, allow_short, score_margin)
            metrics = metrics_for(result)
            importances = feature_importance(final_model, feature_cols, train_full_high_volume[feature_cols], train_full_high_volume["target_up"])
            split_metrics, correlations = split_analysis(name, result, test, feature_cols, importances)
            target_met = metrics["sharpe_ratio"] >= SHARPE_TARGET
            gate = package_gate(metrics, split_metrics, validation_metrics)
            row = {
                "name": name,
                "model_type": final_model_type,
                "status": "ok",
                "message": (
                    f"Engineered features with normalized first-order inputs and re-normalized second-order interactions. "
                    f"Best of {len(candidates)} candidates selected by turnover-adjusted validation score before the latest two-year test; "
                    f"Sharpe target {SHARPE_TARGET:.1f} {'met' if target_met else 'not met'} on the latest two-year test."
                ),
                "backtest_start": str(test["date"].iloc[0]),
                "backtest_end": str(test["date"].iloc[-1]),
                "features": feature_cols,
                "feature_engineering": [
                    "volume",
                    "trend_flags",
                    "volume_differences",
                    "rolling_values",
                    "rsi",
                    "candle_size",
                    "lag_7_30",
                    "bollinger_bands",
                    "golden_cross",
                    "normalized_second_order_arithmetic",
                ],
                "feature_count": len(feature_cols),
                "feature_candidate_count": feature_selection["candidate_feature_count"],
                "selected_feature_count": feature_selection["selected_feature_count"],
                "feature_selection": feature_selection,
                "interaction_source_count": len(interaction_sources),
                "selected_threshold": round(float(long_threshold), 6),
                "selected_short_threshold": round(float(short_threshold), 6) if short_threshold is not None else None,
                "selected_score_margin": round(float(score_margin), 6),
                "strategy_side": "long_short" if allow_short else "long_only",
                "selected_candidate": best_trial["candidate_name"],
                "selected_candidate_index": int(best_trial["candidate_index"]),
                "candidate_count": len(candidates),
                "selected_validation_score": best_trial.get("validation_selection_score"),
                "selected_hyperparameters": safe_json_params(selected_candidate["params"]),
                "candidate_trials": sorted(candidate_trials, key=validation_rank, reverse=True),
                "sharpe_target": SHARPE_TARGET,
                "target_met": target_met,
                **gate,
                **validation_metrics,
                **metrics,
                "feature_importance": importances[:16],
                "split_metrics": split_metrics,
                "split_correlations": correlations[:40],
                "equity_curve": [
                    {
                        "date": str(row["date"]),
                        "equity": round(float(row["equity"]), 4),
                        "gross_equity": round(float(row["gross_equity"]), 4),
                        "daily_return_pct": round(float(row["strategy_return"] * 100), 4),
                        "gross_daily_return_pct": round(float(row["gross_strategy_return"] * 100), 4),
                        "position": float(row["position"]),
                    }
                    for _, row in result.iloc[::max(1, len(result) // 120)].iterrows()
                ],
            }
            model_rows.append(row)
            split_rows.extend(split_metrics)
            corr_rows.extend(correlations)
            feature_rows.extend({"model_name": name, **item} for item in importances)
            prediction_frames.append(result.assign(model_name=name))
        except Exception as error:
            model_rows.append({
                "name": name,
                "model_type": model_type,
                "status": "error",
                "message": str(error),
                "sharpe_ratio": 0,
                "win_rate_pct": 0,
                "total_return_pct": 0,
                "max_drawdown_pct": 0,
                "exposure_pct": 0,
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
        "accelerator": "GPU requested for LightGBM/XGBoost, ExtraTrees CPU parallel",
        "high_volume_rule": f"BTC volume >= rolling 252D {int(HIGH_VOLUME_QUANTILE * 100)}th percentile",
        "training_window": f"{data['date'].iloc[0]} to {data['date'].iloc[validation_start_index - 1]}",
        "validation_window": f"{data['date'].iloc[validation_start_index]} to {data['date'].iloc[test_start_index - 1]}",
        "backtest_window": f"{test['date'].iloc[0]} to {test['date'].iloc[-1]}",
        "batch_size": CANDIDATES_PER_MODEL,
        "models_requested": len(model_groups),
        "candidate_count_total": sum(len(group["candidates"]) for group in model_groups),
        "sharpe_target": SHARPE_TARGET,
        "transaction_cost_bps": TRANSACTION_COST_BPS,
        "slippage_bps": SLIPPAGE_BPS,
        "feature_engineering": "Normalized base features, arithmetic second-order interactions, re-normalized interactions.",
        "base_feature_count": len(base_features),
        "interaction_source_count": len(interaction_sources),
        "feature_candidate_count": feature_selection["candidate_feature_count"],
        "selected_feature_count": feature_selection["selected_feature_count"],
        "final_feature_count": len(feature_cols),
        "feature_selection": feature_selection,
        "models": sorted(model_rows, key=lambda row: row.get("sharpe_ratio", -999), reverse=True),
    }

    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(split_rows).to_csv(OUTPUT_DIR / "split_metrics.csv", index=False)
    pd.DataFrame(corr_rows).to_csv(OUTPUT_DIR / "split_correlations.csv", index=False)
    pd.DataFrame(feature_rows).to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)
    if prediction_frames:
        pd.concat(prediction_frames, ignore_index=True).to_csv(OUTPUT_DIR / "predictions.csv", index=False)
    print(json.dumps({"output_dir": str(OUTPUT_DIR), "models": len(model_rows)}, indent=2))


if __name__ == "__main__":
    run()
