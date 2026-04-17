# Model Registry

Put trained model definition files in this folder as JSON. The backend reads this folder and backtests each enabled file against recent BTC returns.

Use this for models trained only on data older than the latest two-year evaluation window. The backend cannot prove the training window from weights alone, so keep the training cutoff in the file metadata.

Supported feature names:

- `btc_return_1d`
- `btc_rsi_14`
- `btc_volatility_20d`
- `btc_drawdown_60d`
- `sp500_return_1d`
- `nasdaq_return_1d`
- `kospi_return_1d`
- `nikkei_return_1d`
- `gold_return_1d`
- `gold_futures_return_1d`
- `us10y_bp_chg`
- `us30y_bp_chg`
- `us5y_bp_chg`
- `japan10y_bp_chg`
- `germany10y_bp_chg`
- `uk10y_bp_chg`

Model files can use either a simple `weights` object or a `features` list with optional training-set `mean` and `std` values.

```json
{
  "enabled": true,
  "name": "BTC Gradient Boosting Export",
  "model_type": "boosting",
  "training_cutoff": "2024-04-17",
  "signal": {
    "bias": 0.0,
    "long_threshold": 0.15,
    "short_threshold": -0.15,
    "allow_short": false
  },
  "features": [
    { "name": "btc_rsi_14", "weight": -0.02, "mean": 50.0, "std": 12.0 },
    { "name": "btc_volatility_20d", "weight": -0.15 },
    { "name": "sp500_return_1d", "weight": 0.20 },
    { "name": "us10y_bp_chg", "weight": -0.03 }
  ]
}
```

For safety, user JSON model files are ignored by Git by default. Keep private weights in local files and commit only intentionally shared examples.
