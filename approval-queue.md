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
- Done: 2026-04-18 09:15 KST Git access is available again; readiness UI and regime validation plan are ready to commit and push.

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
- Still blocked/slow: `docker compose build` and `docker compose build frontend` repeatedly timed out without useful build logs even after the context cleanup.

### Pending Approvals

1. Docker-based validation after Docker Desktop settles or restarts
   - Why: Docker services are running, but image rebuild commands repeatedly timed out after the local code/build checks passed.
   - Command: `docker compose build frontend && docker compose up -d frontend`
   - Expected result: Rebuild and serve the updated dashboard at `http://localhost:3000`.

### Current Uncommitted Product Changes

- Fundamentals cards show the selected sort metric value next to the currency badge.
- Missing fundamental sort values now fall to the end for both ascending and descending sorts.
- Mobile CSS for the new fundamentals badges wraps instead of overflowing.
- Company memory now describes the product as Bitcoin plus global market research, not BTC-only.
- Tracked stocks now include more large-cap US, Korean, and Japanese equities.
- Fundamentals now include PER, forward PER, P/B, P/S, EV/EBITDA, dividend yield, beta, target upside, and market cap where Yahoo or curated fallback data can provide them.
- Market Snapshot cards use shorter labels and one-line values to avoid messy wrapping.
