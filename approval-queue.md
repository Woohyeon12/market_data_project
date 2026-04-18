# Approval Queue

## 2026-04-18 04:58 KST

### Current Status

- Done: 2026-04-18 08:20 KST engineered Kaggle model run completed with only LightGBM, XGBoost, and ExtraTrees. The run used 2,325 normalized features after second-order arithmetic interactions. Sharpe 2.0 was not achieved on the full latest two-year window; best full-window Sharpe was 0.269, while one split reached 2.271.
- Done: 2026-04-18 05:17 KST Models page now has a marketplace-style carousel, selected-model score hero, stability score, since-model-start return, split consistency, comparison table, and Docker frontend rebuild.
- Done: Kaggle authentication used the token only as a process environment variable, not as a committed file.
- Done: Kaggle GPU kernel completed the current 3-model BTC high-volume candle run with LightGBM, XGBoost, and ExtraTrees only.
- Done: Downloaded run outputs into `backend/model_registry/kaggle_runs/btc_volume_boosting_gpu_latest`.
- Done: Backend rebuilt and restarted so `/research/model-backtests` now returns one Kaggle run with 3 engineered models and four split metrics for each model.
- Done: Frontend production server restarted on `http://localhost:3000`.
- Done: 2026-04-18 09:15 KST approval cleared the frontend build and Docker refresh. `npm.cmd run build` passed and `docker compose up -d --build frontend` restarted the app with the Models readiness gate.
- Done: 2026-04-18 09:15 KST Git access is available again; readiness UI and regime validation plan were committed and pushed in `5e95856`.
- Done: 2026-04-18 10:50 KST approval cleared the package-gate metrics build and Docker refresh. `npm.cmd run build` passed and `docker compose up -d --build backend frontend` restarted both services.
- Done: 2026-04-18 11:03 KST implemented the lower-overfit 200-feature selection pipeline and rebuilt Docker locally. The running dashboard still shows the previous 2,325-feature Kaggle result until a fresh Kaggle run is launched and downloaded.
- Done: 2026-04-18 23:05 KST Kaggle authentication was restored, kernel version 5 completed, and the fresh roughly 200-feature low-correlation result was downloaded. The dashboard API now reports 200 selected features from 2,146 candidates; best model was `extra_trees_engineered` with Sharpe -0.553, so it is not a package candidate.
- Done: 2026-04-19 04:35 KST permission refresh cleared the local blockers. Git staging succeeded, Kaggle status check authenticated through `scripts/kaggle.cmd`, `npm.cmd run build` passed, and Python compile checks passed.
- Done: 2026-04-19 04:42 KST Kaggle version 6 completed and outputs were downloaded. Experiment 001 slightly improved best Sharpe from -0.553 to -0.536, but the base-feature floor missed with only 30 base features and 170 interaction features, so it is still not a package candidate.
- Done: 2026-04-19 05:51 KST Kaggle version 7 completed and outputs were downloaded. Experiment 002 used dynamic feature count, selected 360 features, met the base floor with 62 base features, and improved the best model to `xgb_gpu_engineered` with net Sharpe -0.132. It is still not a package candidate.
- Done: 2026-04-19 06:03 UTC Kaggle version 8 completed and outputs were downloaded. Experiment 003 selected a 0.075 score margin and slightly improved best net Sharpe to -0.111, but trades and transaction cost did not fall, and positive splits fell to 1/4. It is still not a package candidate.
- Done: 2026-04-19 05:20 KST backend and frontend Docker services were rebuilt and restarted. The `/research/model-backtests` API now exposes the imported Experiment 003 Kaggle run with `selected_score_margin`.
- Done: 2026-04-19 05:38 UTC Kaggle version 9 completed and outputs were downloaded. Experiment 004 ran 10 candidates per model family, but the best candidate worsened to net Sharpe -0.217 with 0/4 positive splits, so it is not a package candidate.
- Done: 2026-04-19 05:54 UTC Kaggle version 10 completed and outputs were downloaded. Experiment 005 added turnover-adjusted validation scoring, but selected the same winners and kept best net Sharpe at -0.217, so it is not a package candidate.

### Pending Approvals

- None.

### User Security Action

- Rotate the exposed Kaggle token in Kaggle settings before using it for long-running automation.

## 2026-04-18 04:10 KST

### Current Status

- Done: `npm.cmd install`, `npm.cmd install next@15.5.15`, `npm.cmd run build`, `npm.cmd audit --audit-level=high`, and Python compile checks.
- Done: Added `.dockerignore` files so Docker builds do not send local `node_modules`, `.next`, data, or venv folders.
- Done: Git commit and push completed through `b14a9b4`.
- Done: Backend Docker rebuild/restart completed after adding Yahoo fundamentals-timeseries; fundamentals now avoid curated fallback for the tracked equities.
- Resolved later: Docker build validation completed successfully on 2026-04-19 05:20 KST with `docker compose up -d --build backend frontend`.

### Pending Approvals

- None. Historical Docker validation blocker is resolved.

### Current Uncommitted Product Changes

- Fundamentals cards show the selected sort metric value next to the currency badge.
- Missing fundamental sort values now fall to the end for both ascending and descending sorts.
- Mobile CSS for the new fundamentals badges wraps instead of overflowing.
- Company memory now describes the product as Bitcoin plus global market research, not BTC-only.
- Tracked stocks now include more large-cap US, Korean, and Japanese equities.
- Fundamentals now include PER, forward PER, P/B, P/S, EV/EBITDA, dividend yield, beta, target upside, and market cap where Yahoo or curated fallback data can provide them.
- Market Snapshot cards use shorter labels and one-line values to avoid messy wrapping.
