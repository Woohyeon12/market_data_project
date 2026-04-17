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
    "us10y": "^TNX",
    "us30y": "^TYX",
    "us5y": "^FVX",
}
TRAIN_END_OFFSET = 504
HIGH_VOLUME_QUANTILE = 0.70
BATCH_SIZE = 2
MAX_MODELS = 10


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


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def drawdown(series: pd.Series, window: int = 60) -> pd.Series:
    rolling_high = series.rolling(window).max()
    return (series - rolling_high) / rolling_high * 100


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
        chart = fetch_yahoo_chart(symbol)[["date", "close"]].rename(columns={"close": f"{prefix}_close"})
        data = data.merge(chart, on="date", how="left")

    data = data.sort_values("date").ffill()
    data["target_return_1d"] = data["btc_close"].pct_change().shift(-1) * 100
    data["target_up"] = (data["target_return_1d"] > 0).astype(int)
    data["btc_return_1d"] = data["btc_close"].pct_change() * 100
    data["btc_return_3d"] = data["btc_close"].pct_change(3) * 100
    data["btc_return_5d"] = data["btc_close"].pct_change(5) * 100
    data["btc_return_10d"] = data["btc_close"].pct_change(10) * 100
    data["btc_range_pct"] = (data["btc_high"] - data["btc_low"]) / data["btc_close"] * 100
    data["btc_body_pct"] = (data["btc_close"] - data["btc_open"]) / data["btc_open"] * 100
    data["btc_rsi_14"] = rsi(data["btc_close"])
    data["btc_volatility_20d"] = data["btc_return_1d"].rolling(20).std()
    data["btc_drawdown_60d"] = drawdown(data["btc_close"])
    data["btc_volume_ratio_20d"] = data["btc_volume"] / data["btc_volume"].rolling(20).mean()
    data["btc_volume_z_60d"] = (
        (data["btc_volume"] - data["btc_volume"].rolling(60).mean())
        / data["btc_volume"].rolling(60).std()
    )
    data["high_volume_candle"] = data["btc_volume"] >= data["btc_volume"].rolling(252).quantile(HIGH_VOLUME_QUANTILE)

    for prefix in ["sp500", "nasdaq", "gold"]:
        data[f"{prefix}_return_1d"] = data[f"{prefix}_close"].pct_change() * 100
        data[f"{prefix}_return_5d"] = data[f"{prefix}_close"].pct_change(5) * 100

    for prefix in ["us10y", "us30y", "us5y"]:
        data[f"{prefix}_bp_chg"] = data[f"{prefix}_close"].diff() * 100

    feature_cols = [
        "btc_return_1d",
        "btc_return_3d",
        "btc_return_5d",
        "btc_return_10d",
        "btc_range_pct",
        "btc_body_pct",
        "btc_rsi_14",
        "btc_volatility_20d",
        "btc_drawdown_60d",
        "btc_volume_ratio_20d",
        "btc_volume_z_60d",
        "sp500_return_1d",
        "sp500_return_5d",
        "nasdaq_return_1d",
        "nasdaq_return_5d",
        "gold_return_1d",
        "gold_return_5d",
        "us10y_bp_chg",
        "us30y_bp_chg",
        "us5y_bp_chg",
    ]
    data = data.dropna(subset=feature_cols + ["target_return_1d"]).reset_index(drop=True)
    return data, feature_cols


def model_specs():
    specs = []
    from sklearn.ensemble import (
        AdaBoostClassifier,
        BaggingClassifier,
        ExtraTreesClassifier,
        GradientBoostingClassifier,
        HistGradientBoostingClassifier,
        RandomForestClassifier,
    )
    from sklearn.tree import DecisionTreeClassifier

    specs.extend([
        ("sk_gbc_depth2", "sklearn_gradient_boosting", lambda: GradientBoostingClassifier(n_estimators=180, max_depth=2, learning_rate=0.04, random_state=7)),
        ("sk_gbc_depth3", "sklearn_gradient_boosting", lambda: GradientBoostingClassifier(n_estimators=140, max_depth=3, learning_rate=0.05, random_state=11)),
        ("sk_hist_gbc", "sklearn_hist_gradient_boosting", lambda: HistGradientBoostingClassifier(max_iter=220, learning_rate=0.035, max_leaf_nodes=15, random_state=13)),
        ("sk_random_forest", "sklearn_bagging", lambda: RandomForestClassifier(n_estimators=320, max_depth=5, min_samples_leaf=12, random_state=17, n_jobs=-1)),
        ("sk_extra_trees", "sklearn_bagging", lambda: ExtraTreesClassifier(n_estimators=360, max_depth=5, min_samples_leaf=12, random_state=19, n_jobs=-1)),
        ("sk_adaboost", "sklearn_boosting", lambda: AdaBoostClassifier(n_estimators=160, learning_rate=0.04, random_state=23)),
        ("sk_bagged_tree", "sklearn_bagging", lambda: BaggingClassifier(estimator=DecisionTreeClassifier(max_depth=4, min_samples_leaf=15), n_estimators=180, random_state=29, n_jobs=-1)),
    ])

    try:
        from xgboost import XGBClassifier
        specs.extend([
            ("xgb_gpu_depth2", "xgboost_gpu", lambda: XGBClassifier(n_estimators=240, max_depth=2, learning_rate=0.035, subsample=0.85, colsample_bytree=0.85, eval_metric="logloss", tree_method="hist", device="cuda", random_state=31)),
            ("xgb_gpu_depth3", "xgboost_gpu", lambda: XGBClassifier(n_estimators=220, max_depth=3, learning_rate=0.035, subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", tree_method="hist", device="cuda", random_state=37)),
        ])
    except Exception:
        pass

    try:
        from lightgbm import LGBMClassifier
        specs.append(("lgbm_gpu", "lightgbm_gpu", lambda: LGBMClassifier(n_estimators=260, max_depth=3, learning_rate=0.03, subsample=0.85, colsample_bytree=0.85, device="gpu", random_state=41)))
    except Exception:
        pass

    try:
        from catboost import CatBoostClassifier
        specs.append(("catboost_gpu", "catboost_gpu", lambda: CatBoostClassifier(iterations=260, depth=3, learning_rate=0.035, loss_function="Logloss", task_type="GPU", random_seed=43, verbose=False)))
    except Exception:
        pass

    return specs[:MAX_MODELS]


def predict_proba_positive(model, x: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x)[:, 1]
    if hasattr(model, "decision_function"):
        scores = model.decision_function(x)
        return 1 / (1 + np.exp(-scores))
    return np.asarray(model.predict(x), dtype=float)


def backtest_from_probabilities(frame: pd.DataFrame, probabilities: np.ndarray) -> pd.DataFrame:
    result = frame[["date", "target_return_1d", "high_volume_candle"]].copy()
    result["probability"] = probabilities
    result["position"] = np.where((result["high_volume_candle"]) & (result["probability"] >= 0.55), 1.0, 0.0)
    result["strategy_return"] = result["position"] * result["target_return_1d"] / 100
    result["equity"] = (1 + result["strategy_return"]).cumprod()
    return result


def metrics_for(result: pd.DataFrame) -> dict:
    returns = result["strategy_return"].fillna(0)
    active = result[result["position"] != 0]
    volatility = returns.std()
    sharpe = (returns.mean() / volatility) * math.sqrt(252) if volatility and not np.isnan(volatility) else 0.0
    equity = result["equity"].iloc[-1] if len(result) else 1.0
    peak = result["equity"].cummax()
    drawdown = ((result["equity"] - peak) / peak).min() * 100 if len(result) else 0.0
    return {
        "sharpe_ratio": round(float(sharpe), 3),
        "win_rate_pct": round(float((active["strategy_return"] > 0).mean() * 100), 2) if len(active) else 0.0,
        "total_return_pct": round(float((equity - 1) * 100), 3),
        "max_drawdown_pct": round(float(drawdown), 3),
        "exposure_pct": round(float((result["position"] != 0).mean() * 100), 2) if len(result) else 0.0,
        "trades": int(result["position"].diff().abs().fillna(0).sum()),
        "observations": int(len(result)),
        "active_observations": int(len(active)),
    }


def feature_importance(model, feature_cols: list[str], train: pd.DataFrame) -> list[dict]:
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    else:
        target = train["target_up"]
        values = np.asarray([abs(train[col].corr(target)) if train[col].std() else 0 for col in feature_cols], dtype=float)
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


def run():
    data, feature_cols = build_dataset()
    if len(data) <= TRAIN_END_OFFSET + 200:
        raise RuntimeError("Not enough data for older-than-two-year training and two-year backtest.")

    test_start_index = len(data) - TRAIN_END_OFFSET
    train = data.iloc[:test_start_index].copy()
    train = train[train["high_volume_candle"]].copy()
    test = data.iloc[test_start_index:].copy()
    x_train = train[feature_cols]
    y_train = train["target_up"]
    x_test = test[feature_cols]
    specs = model_specs()
    model_rows = []
    split_rows = []
    corr_rows = []
    feature_rows = []
    prediction_frames = []

    for batch_start in range(0, len(specs), BATCH_SIZE):
        batch = specs[batch_start:batch_start + BATCH_SIZE]
        print(f"Running model batch {batch_start // BATCH_SIZE + 1}: {[name for name, _, _ in batch]}")
        for name, model_type, factory in batch:
            try:
                model = factory()
                try:
                    model.fit(x_train, y_train)
                except Exception as gpu_error:
                    print(f"{name} GPU/default fit failed, retrying CPU-compatible fallback: {gpu_error}")
                    from sklearn.ensemble import GradientBoostingClassifier
                    model_type = f"{model_type}_cpu_fallback"
                    model = GradientBoostingClassifier(n_estimators=160, max_depth=2, learning_rate=0.04, random_state=101)
                    model.fit(x_train, y_train)

                probabilities = predict_proba_positive(model, x_test)
                result = backtest_from_probabilities(test, probabilities)
                metrics = metrics_for(result)
                importances = feature_importance(model, feature_cols, train)
                split_metrics, correlations = split_analysis(name, result, test, feature_cols, importances)
                row = {
                    "name": name,
                    "model_type": model_type,
                    "status": "ok",
                    "message": "Trained only on high-volume candles older than the latest two-year test window.",
                    "backtest_start": str(test["date"].iloc[0]),
                    "backtest_end": str(test["date"].iloc[-1]),
                    "features": feature_cols,
                    **metrics,
                    "feature_importance": importances[:12],
                    "split_metrics": split_metrics,
                    "split_correlations": correlations[:40],
                    "equity_curve": [
                        {
                            "date": str(row["date"]),
                            "equity": round(float(row["equity"]), 4),
                            "daily_return_pct": round(float(row["strategy_return"] * 100), 4),
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
        "accelerator": "GPU requested, CPU fallback enabled",
        "high_volume_rule": f"BTC volume >= rolling 252D {int(HIGH_VOLUME_QUANTILE * 100)}th percentile",
        "training_window": f"{data['date'].iloc[0]} to {data['date'].iloc[test_start_index - 1]}",
        "backtest_window": f"{test['date'].iloc[0]} to {test['date'].iloc[-1]}",
        "batch_size": BATCH_SIZE,
        "models_requested": MAX_MODELS,
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
