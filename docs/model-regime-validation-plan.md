# Model Regime Validation Plan

This plan keeps the Sharpe 2.0 target honest. A model should not be presented as a package candidate unless it survives both a full recent backtest and regime-specific checks.

## Current Finding

- Latest engineered Kaggle run used LightGBM, XGBoost, and ExtraTrees only.
- Feature set used normalized first-order variables and re-normalized second-order arithmetic interactions.
- Full latest two-year Sharpe target was not met.
- Best full-window model was `xgb_gpu_engineered` with Sharpe 0.269 and total return 7.317%.
- One split reached Sharpe 2.271, but later splits decayed, pointing to regime instability.

## Regime Features To Add

Use only information available before each prediction date.

- Trend regime: BTC above/below SMA20, SMA50, SMA200, and slope of SMA50/SMA200.
- Volatility regime: rolling 20D/60D BTC volatility percentile.
- Volume regime: rolling 252D volume percentile and volume shock flags.
- Drawdown regime: rolling 30D/60D/120D drawdown bucket.
- Liquidity/risk regime: US 10Y and 5Y yield bp-change buckets, Nasdaq 20D trend, gold 20D trend.
- Momentum regime: RSI bucket, Bollinger percent-b bucket, 7D/30D return bucket.
- Cross-asset regime: VIX, DXY, oil, silver, gold/silver ratio, Nasdaq/S&P 500 relative momentum, and BTC rolling correlations to risk assets.
- Feature selection regime: build a broad candidate pool, but train only on about 200 target-relevant features selected with a low pairwise-correlation gate.

## Walk-Forward Rules

- Train only on data older than the validation and test windows.
- Use a validation window only to choose thresholds, side, and regime gates.
- Test on four chronological recent splits.
- Record per-split Sharpe, win rate, return, drawdown, exposure, and trade count.
- Reject any configuration if it has a strong validation score but weak full test score without a documented regime reason.

## Package Candidate Gate

A model can be labeled `Package candidate` only when all checks pass:

- Latest two-year Sharpe is at least 2.0 after costs.
- At least 3 of 4 recent splits have positive returns.
- No split Sharpe is below 0.0.
- Max drawdown is controlled relative to total return.
- Validation Sharpe and test Sharpe do not diverge by more than 1.0 without a regime explanation.
- Exposure is high enough to avoid a tiny-sample result.

## Next Implementation Steps

1. Add regime labels to Kaggle predictions and split metrics.
2. Done in script: add transaction cost and slippage columns before Sharpe calculation.
3. Done in script: add a model kill-switch metric, `worst_split_sharpe`.
4. Done in script: add a rejection reason list into `run_summary.json`.
5. Done in script: reduce the broad normalized and second-order feature pool to about 200 low-correlation selected features before fitting.
6. Partly done in UI contract: surface package readiness, cost drag, gross Sharpe, worst split Sharpe, selected feature count, candidate pool size, and rejection reasons on the Models page after the next Kaggle run includes those fields.
7. Current experiment: enforce a base-feature floor during low-correlation feature selection so second-order synthetic variables cannot dominate the final 200-feature set.
