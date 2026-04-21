# UI Iteration Log

## 2026-04-21 18:25 KST - Iteration 001

### Audit

- `docs/design-system.md` and `docs/ui-iteration-log.md` were missing, so the design protocol did not yet have a persistent baseline.
- The latest completed Exp8 Kaggle artifacts were downloaded into a nested folder under `backend/model_registry/kaggle_runs/btc_volume_boosting_gpu_latest`, which prevented clean freshness tracking.
- Current visual debt remains concentrated in the Models page, especially the dense showcase detail grid.

### Chosen Priority

- Data Synchronization

### Change

- Synced the completed Exp8 Kaggle outputs into the canonical `btc_volume_boosting_gpu_latest` folder so backend import can read the newest files instead of the older Exp7-era summary.
- Updated `docs/model-experiment-log.md` with the completed Exp8 result so the dashboard and the experiment record share the same narrative baseline.
- Initialized the design baseline files so future automation passes can compare against a durable source of truth.

### Result

- Latest completed regime-split experiment is now available for backend/API refresh and UI comparison.
- The next most urgent design pass should simplify the model showcase metadata hierarchy rather than add more cards.

### Verification

- `http://127.0.0.1:8000/research/model-backtests` now returns the synced Exp8 candidate `regime_split_ensemble_c07` with validation score `2.676`, validation worst split Sharpe `1.45`, validation last split Sharpe `2.17`, uncertainty margin `0.0`, and test regime mix `48.61`.
- `http://127.0.0.1:3000` returns HTTP 200 after backend/frontend restart.

### Follow-up Candidate

- Split the model showcase detail area into grouped sections such as Performance, Validation, Regime, and Execution so long technical values stop competing for the same visual weight.

## 2026-04-21 19:10 KST - Iteration 002

### Audit

- The model showcase still read like a flat stat wall even after Exp8 sync, especially on the Models page.
- Risk controls such as turnover rules and stop-loss floors were not clearly visible, which made execution discipline easy to miss.
- Volume and timing backtest scripts could not yet validation-select a close-based stop-loss floor, so downside protection was not part of the candidate search.

### Chosen Priority

- Information hierarchy and downside-control visibility

### Change

- Rebuilt the Models showcase into grouped decision layers: Performance, Validation, Execution & Risk, and Feature & Regime.
- Added a compact metadata strip so selected candidate, strategy side, stop floor, and import freshness sit above the hero instead of hiding in a deep stat grid.
- Extended Kaggle model typing and the backtest schemas so `selected_stop_loss_pct`, `stop_loss_exit_count`, and `stop_loss_trigger_rate_pct` can flow from research output into the dashboard.
- Added validation-selected close-based stop-loss candidates to both `kaggle/volume_boosting_gpu/volume_boosting_gpu.py` and `kaggle/timing_simple_gpu/timing_simple_gpu.py`.

### Result

- The Models page now reads more like an institutional scorecard than a debug dump.
- Stop-loss logic is now part of model selection rather than an afterthought for live trading.
- Existing imported Exp8 artifacts predate the new stop-loss fields, so the UI will show `off` or `n/a` until the next Kaggle run writes fresh summaries.

### Verification

- `python -m py_compile kaggle\\volume_boosting_gpu\\volume_boosting_gpu.py kaggle\\timing_simple_gpu\\timing_simple_gpu.py backend\\app\\schemas\\research.py`
- `npm.cmd exec tsc -- --noEmit`
- `npm.cmd run build`

### Follow-up Candidate

- Re-run the next Kaggle experiment so the new stop-loss fields populate the canonical run summary and compare whether stop floors reduce drawdown without collapsing net Sharpe.
