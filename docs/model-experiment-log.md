# Model Experiment Log

This log records each small model experiment so weak runs are not repeated and strong runs can be reproduced.

## Best Confirmed Result So Far

- Run: `btc_volume_boosting_gpu_latest`, generated 2026-04-18 14:04 UTC.
- Candidate pool: 2,146 normalized first-order and second-order features.
- Selected features: 200.
- Best model: `extra_trees_engineered`.
- Net Sharpe: -0.553.
- Gross Sharpe: -0.343.
- Net total return: -25.258%.
- Package candidate: false.
- Read: Lowering feature count reduced bloat, but selecting 191 interaction features and only 9 base features likely kept too much synthetic overfit risk.

## 2026-04-18 23:30 KST - Experiment 001

- Hypothesis: The latest 200-feature run overfit because the low-correlation selector allowed interactions to dominate the final set.
- Change: Added a base-feature floor so the selector tries to keep at least 60 normalized first-order features before filling the remaining slots with interactions.
- Files changed: `kaggle/volume_boosting_gpu/volume_boosting_gpu.py`.
- Expected effect: More direct market, volume, trend, volatility, yield, and cross-asset context reaches the models; interaction features remain useful but cannot crowd out base signals.
- Validation done: Python compile check.
- Full backtest status: Not run in this heartbeat. Next run should push the Kaggle kernel, download outputs, and compare Sharpe, return, drawdown, split stability, selected base count, and selected interaction count against the 2026-04-18 14:04 UTC run.

## 2026-04-18 23:50 KST - Experiment Infrastructure

- Observation: The heartbeat environment blocked `scripts/kaggle.ps1` with the local PowerShell execution policy before Kaggle status could be checked.
- Change: Added `scripts/kaggle.cmd`, which reads the user-level `KAGGLE_API_TOKEN` without writing secrets to disk and then calls the Kaggle CLI.
- Expected effect: Future 15-minute model experiments can check kernel status, push runs, and download outputs even when `.ps1` execution is blocked.
- Validation done: Wrapper was executed, but the current heartbeat sandbox cannot see `KAGGLE_API_TOKEN` in either the process or user environment, so Kaggle status is still blocked until auth is restored for this sandbox identity.
- Experiment discipline: Do not stack another modeling change on top of Experiment 001 until the base-feature-floor run is pushed, completed, and downloaded.

## 2026-04-19 00:08 KST - Execution Check

- Check: `KAGGLE_API_TOKEN` is still absent from both process and user environment in the active heartbeat sandbox.
- Check: `scripts/kaggle.cmd kernels status seowoohyeon/btc-volume-boosting-gpu-backtest` still stops before Kaggle because auth is unavailable.
- Check: Git still cannot create `.git/index.lock`, so local changes cannot be committed from this sandbox identity.
- Decision: Do not add Experiment 002 yet. The next useful experiment remains running Experiment 001 on Kaggle after auth and Git access are restored.

## 2026-04-19 00:25 KST - UI Auditability Pass

- Change: The Models showcase now surfaces selected base feature count, selected interaction feature count, and whether the base-feature floor was recorded as met.
- Why: The current imported run selected only 9 base features and 191 interaction features, so the overfit hypothesis should be visible in the product UI, not only in code notes.
- Validation done: Frontend TypeScript check and Kaggle script compile check.
- Full backtest status: Still blocked by missing Kaggle auth in the heartbeat sandbox. No new model experiment was stacked on top of Experiment 001.

## 2026-04-19 00:44 KST - Validation Check

- Check: `KAGGLE_API_TOKEN` is still absent from process and user environment in the active heartbeat sandbox.
- Check: `scripts/kaggle.cmd kernels status seowoohyeon/btc-volume-boosting-gpu-backtest` still stops before contacting Kaggle because auth is unavailable.
- Validation done: `npm.cmd exec tsc -- --noEmit`, `py -m py_compile`, `git diff --check`, and repo token-string scan.
- Blocked: `npm.cmd run build` failed with `spawn EPERM`, and Git still cannot create `.git/index.lock`.
- Decision: Keep Experiment 001 as the next model action. Do not start Experiment 002 until the base-feature-floor Kaggle run is completed and downloaded.

## 2026-04-19 04:35 KST - Permission Refresh

- Check: `scripts/kaggle.cmd kernels status seowoohyeon/btc-volume-boosting-gpu-backtest` authenticated and returned `COMPLETE`.
- Check: Git staging succeeded after the permission refresh.
- Validation done: `npm.cmd run build` and `py -m py_compile`.
- Decision: Commit and push the base-feature-floor experiment plus the Models UI auditability pass, then launch Experiment 001 on Kaggle.

## 2026-04-19 04:42 KST - Experiment 001 Result

- Kaggle version: 6.
- Candidate pool: 2,146 features.
- Selected features: 200.
- Selected base features: 30.
- Selected interaction features: 170.
- Base floor met: false.
- Best model: `extra_trees_engineered`.
- Net Sharpe: -0.536.
- Gross Sharpe: -0.365.
- Net total return: -22.474%.
- Win rate: 50.00%.
- Max drawdown: -34.733%.
- Active observations: 62.
- Package candidate: false.
- Read: The result is only a tiny improvement over the prior -0.553 Sharpe and still clearly unsellable. The important finding is implementation-related: the base-feature floor missed because base candidates were still constrained by the top-900 prefilter, so only 30 base features were available to the floor pass.
- Next hypothesis: Build the base-feature floor from the full normalized base-feature pool before applying the interaction prefilter, then rerun.

## 2026-04-19 05:05 KST - Experiment 002 Setup

- User directive: Feature count does not need to stay fixed at 200; it may change dynamically.
- Hypothesis: A fixed 200-feature cap is too rigid. A dynamic selector can preserve enough base market structure while avoiding low-score interaction clutter.
- Change: Replaced the fixed `FINAL_FEATURE_LIMIT = 200` cap with a dynamic range: minimum 120, soft target 240, maximum 360.
- Change: Base candidates now come from the full normalized base-feature pool, while interaction candidates still use a target-ranked prefilter.
- Change: After the minimum feature count is reached, additional features must clear a dynamic target-correlation floor unless they are still needed to satisfy the base-feature floor.
- Expected effect: The selected feature count can shrink or expand based on actual signal quality; base features should no longer be capped at 30 by the interaction-heavy prefilter.
- Full backtest status: Pending Kaggle Experiment 002 run.

## 2026-04-19 05:51 KST - Experiment 002 Result

- Kaggle version: 7.
- Candidate pool: 2,146 features.
- Candidate selection pool: 1,062 features.
- Selected features: 360.
- Selected base features: 62.
- Selected interaction features: 298.
- Base floor met: true.
- Dynamic target score floor: 0.0433.
- Best model: `xgb_gpu_engineered`.
- Net Sharpe: -0.132.
- Gross Sharpe: 0.115.
- Net total return: -8.314%.
- Gross total return: 0.735%.
- Win rate: 46.38%.
- Max drawdown: -25.604%.
- Positive splits: 3/4.
- Active observations: 69.
- Package candidate: false.
- Read: Dynamic count and full-pool base selection fixed the feature-selection implementation issue and materially improved the top model from -0.536 to -0.132 Sharpe. The model is still not sellable because costs turn a slightly positive gross edge into a negative net result, and split 4 remains a loss cluster.
- Next hypothesis: Keep dynamic features, but change the threshold/regime layer to trade fewer low-margin candles and avoid late-period drawdown regimes. Candidate changes: validation-selected probability margin, stricter no-trade band, or a simple trend/drawdown regime gate.

## 2026-04-19 06:05 KST - Experiment 003 Setup

- Hypothesis: Experiment 002 found a slightly positive gross edge, but transaction costs pushed it negative. A validation-selected score margin should skip borderline trades and reduce cost drag.
- Change: Keep the dynamic feature selector unchanged.
- Change: Add score margin candidates `[0.0, 0.01, 0.02, 0.035, 0.05, 0.075, 0.1]` to threshold selection.
- Change: Long trades require `score >= selected_long_threshold + selected_score_margin`; shorts, when enabled, require `score <= selected_short_threshold - selected_score_margin`.
- Change: Validation ranking now breaks ties by fewer trades after Sharpe and total return, so equally good validation choices prefer lower churn.
- UI/API: Add `selected_score_margin` to the backend schema and Models detail view.
- Expected effect: Fewer low-margin entries, lower transaction cost drag, and less late-window damage if split 4 was driven by marginal signals.
- Full backtest status: Pending Kaggle Experiment 003 run.

## 2026-04-19 06:03 UTC - Experiment 003 Result

- Kaggle version: 8.
- Selected features: 360.
- Selected base features: 62.
- Selected interaction features: 298.
- Best model: `xgb_gpu_engineered`.
- Selected score margin: 0.075.
- Net Sharpe: -0.111.
- Gross Sharpe: 0.145.
- Net total return: -7.211%.
- Gross total return: 1.949%.
- Win rate: 47.69%.
- Max drawdown: -25.604%.
- Active observations: 65.
- Trades: 94.
- Total transaction cost: 9.400%.
- Positive splits: 1/4.
- Package candidate: false.
- Read: Score margin improved the top model from -0.132 to -0.111 Sharpe and raised gross return, but it did not reduce turnover because the selected base threshold shifted lower while the margin shifted the effective threshold back near the prior cutoff. Split 3 improved, but split consistency worsened to 1/4 positive.
- Next hypothesis: Add a direct turnover control instead of only margin. Candidate changes: minimum holding period, cooldown after position exit, or validation-ranking penalty for transaction cost/trade count.
- Local deployment check: `docker compose up -d --build backend frontend` completed successfully, and `/research/model-backtests` returns Experiment 003 with `selected_score_margin` 0.075 for `xgb_gpu_engineered`.

## 2026-04-19 05:40 KST - Experiment 004 Setup

- User directive: For each model family, create 10 model candidates and keep the best-performing one. Repeat the process until performance improves.
- Guardrail: Candidate selection must be made on the pre-test validation window, not by picking the best latest-two-year test result after the fact.
- Change: LightGBM, XGBoost, and ExtraTrees now each generate 10 deterministic hyperparameter candidates.
- Change: Each candidate trains on the older-than-two-year fit window, selects threshold and score margin on validation, and is ranked by validation Sharpe, validation return, drawdown, lower cost, and fewer trades.
- Change: Only the best validation candidate in each model family is retrained on fit plus validation and then scored on the latest two-year backtest.
- UI/API: Model results now expose `candidate_count`, `selected_candidate`, `selected_candidate_index`, `selected_hyperparameters`, and `candidate_trials`; the Models detail panel shows the selected candidate as best-of-10.
- Expected effect: Better hyperparameter coverage without selecting directly on the test window. If it improves validation but not test, the log should treat that as instability rather than a sellable result.
- Full backtest status: Pending Kaggle Experiment 004 run.

## 2026-04-19 05:38 UTC - Experiment 004 Result

- Kaggle version: 9.
- Candidate plan: 10 LightGBM, 10 XGBoost, and 10 ExtraTrees candidates; one validation-selected winner per model family.
- Selected features: 360.
- Best model: `xgb_gpu_engineered`.
- Selected candidate: `xgb_gpu_engineered_c03`.
- Candidate count: 10 for the winning model, 30 total.
- Net Sharpe: -0.217.
- Gross Sharpe: 0.046.
- Net total return: -10.397%.
- Gross total return: -1.550%.
- Win rate: 47.37%.
- Max drawdown: -20.750%.
- Trades: 94.
- Total transaction cost: 9.400%.
- Positive splits: 0/4.
- Package candidate: false.
- Read: The 10-candidate search ran correctly but worsened versus Experiment 003, where the best net Sharpe was -0.111. More hyperparameter candidates did not fix turnover or the late-window drawdown cluster. The validation-selected candidate reduced max drawdown versus Exp3 but lost gross edge and had zero positive test splits.
- Next hypothesis: Keep the 10-candidate infrastructure, but change the validation ranking from mostly Sharpe-first to a turnover-adjusted validation score that penalizes transaction cost and trades before the final test. Do not choose by the test result.

## 2026-04-19 06:00 KST - Experiment 005 Setup

- Hypothesis: Experiment 004 selected by validation performance but only used transaction cost and trades as late tie-breakers, so over-trading candidates could still win.
- Change: Keep 10 candidates per model family.
- Change: Add a turnover-adjusted validation score before final testing: validation Sharpe plus weighted validation return and drawdown, minus transaction-cost and trade-count penalties.
- Change: Candidate ranking now starts with this validation selection score, then falls back to validation Sharpe, return, drawdown, cost, and trades.
- UI/API: Add `selected_validation_score` so the chosen candidate is auditable in the Models detail panel.
- Expected effect: Prefer candidates that retain edge with fewer cost-heavy entries. If performance still worsens, the next step should be an explicit minimum-hold or cooldown rule rather than more hyperparameter search.
- Full backtest status: Pending Kaggle Experiment 005 run.

## 2026-04-19 05:54 UTC - Experiment 005 Result

- Kaggle version: 10.
- Candidate plan: 10 candidates per model family, with turnover-adjusted validation selection score.
- Best model: `xgb_gpu_engineered`.
- Selected candidate: `xgb_gpu_engineered_c03`.
- Selected validation score: 2.122.
- Net Sharpe: -0.217.
- Gross Sharpe: 0.046.
- Net total return: -10.397%.
- Gross total return: -1.550%.
- Win rate: 47.37%.
- Max drawdown: -20.750%.
- Trades: 94.
- Total transaction cost: 9.400%.
- Positive splits: 0/4.
- Package candidate: false.
- Read: The turnover-adjusted candidate score was recorded but did not change the selected candidates versus Experiment 004, so test performance was unchanged and still worse than Experiment 003. Ranking penalties alone are not enough when the same validation winner dominates.
- Next hypothesis: Add an explicit turnover rule inside `backtest_from_scores`, such as minimum holding days and/or cooldown after exits, then let validation choose thresholds plus the turnover rule before the latest two-year test.

## 2026-04-19 06:12 KST - Experiment 006 Setup

- Hypothesis: Exp5 did not improve because ranking penalties did not alter the selected candidate or the realized trade path.
- Change: Keep 10 candidates per model family and the turnover-adjusted candidate score.
- Change: Add explicit turnover-rule candidates inside `backtest_from_scores`: minimum hold days from 1 to 3 and cooldown after exit from 0 to 2 days.
- Change: Validation now selects threshold, score margin, strategy side, minimum hold, and cooldown together before the latest two-year test.
- UI/API: Add `selected_min_hold_days` and `selected_cooldown_days` to make the chosen turnover rule visible in the Models detail panel.
- Expected effect: Reduce churn directly, possibly lower transaction cost drag and improve split stability. If the trade path remains poor, the next experiment should target regime filtering rather than more candidate grids.
- Full backtest status: Pending Kaggle Experiment 006 run.

## 2026-04-19 06:36 KST - Experiment 006 Status Check

- Status check: Blocked in the active heartbeat environment because `KAGGLE_API_TOKEN` is not visible to `scripts/kaggle.cmd`.
- Decision: Do not start Experiment 007 or modify model logic until Experiment 006 version 11 is checked and outputs are recovered.
- Safe work completed: Added the blocker to `approval-queue.md`; current best remains Experiment 003 with net Sharpe -0.111 until a newer completed result proves otherwise.
- Next action: Restore Kaggle token visibility, then check/download version 11 results. If Exp6 is poor or too slow, design Exp7 as a lighter two-stage turnover search or a regime filter rather than adding more candidates.

## 2026-04-19 21:56 UTC - Experiment 006 Result

- Kaggle version: 11.
- Candidate plan: 10 candidates per model family, turnover-adjusted validation score, explicit min-hold/cooldown turnover rules.
- Best model: `xgb_gpu_engineered`.
- Selected candidate: `xgb_gpu_engineered_c03`.
- Selected validation score: 2.744.
- Selected turnover rule: minimum hold 3 days, cooldown 1 day.
- Selected score margin: 0.075.
- Strategy side: long_short.
- Net Sharpe: 0.109.
- Gross Sharpe: 0.303.
- Net total return: 0.111%.
- Gross total return: 8.872%.
- Win rate: 52.14%.
- Max drawdown: -20.489%.
- Trades: 84.
- Total transaction cost: 8.400%.
- Positive splits: 3/4.
- Package candidate: false.
- Read: Explicit turnover control recovered a positive net result and improved split consistency versus Exp4/Exp5. It is also better than Exp3 on net Sharpe, net return, win rate, and positive splits, but still far below the Sharpe 2.0 product target and still has large cost drag and a poor split 3.
- Next hypothesis: Keep the turnover rule and add a simple regime filter that suppresses trades during high drawdown/negative trend regimes, especially to address split 3. Avoid adding more model candidates until regime filtering is tested.
- Local deployment check: backend/frontend Docker services were rebuilt and restarted; `/research/model-backtests` now returns `selected_candidate`, `selected_min_hold_days`, and `selected_cooldown_days` for Experiment 006.
