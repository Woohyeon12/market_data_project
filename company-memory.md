# BTC Research AI Company Memory

## Current Goal

Build a Bitcoin and global market research-focused financial intelligence product around this project.

## Product Direction

- Start with a BTC research dashboard and recurring research brief.
- Position the product as market research automation, not personalized investment advice.
- Prioritize explainable market context, scenario analysis, news signals, and risk notes.

## Decisions

- Use the current FastAPI backend and Next.js frontend as the first product shell.
- Use CoinGecko as the first live BTC market data source.
- Use CoinDesk RSS as the first keyless BTC news source.
- Keep a local fallback so the dashboard remains usable when external data is unavailable.
- Show data source information in the dashboard to improve trust.
- Move active Codex work from the original D drive folder to the writable C drive workspace.

## Open Questions

- Should the business become a subscription research service or an internal AI research terminal first?
- Should CoinDesk RSS remain the first news source, or should the product add CryptoPanic/NewsAPI next?
- Should report history use PostgreSQL or Supabase?

## Development Priorities

1. Keep live BTC market data stable and transparent.
2. Add trustworthy news collection.
3. Strengthen risk, disclaimer, and non-advisory language.
4. Add report history and scheduled report generation.
5. Improve dashboard sections for signal explanation.

## Latest Operating Note

- 2026-04-18 04:54 KST: Added a Kaggle GPU volume-model pipeline for BTC. It requests a Kaggle GPU, trains up to 10 boosting/bagging models in batches of two on high-volume candles older than the latest two-year test window, backtests the latest two years in four splits, records Sharpe/win rate/drawdown/exposure, feature importance, split correlations, and predictions, and exposes imported run summaries on the Models page.
- 2026-04-18 04:58 KST: Kaggle run completed with 10 models. The best imported result was `sk_gbc_depth3` with Sharpe 0.696, win rate 52.69%, total return 25.246%, and 93 active high-volume candles over 2024-11-29 to 2026-04-16. LightGBM reported a Tesla P100 GPU trainer, and XGBoost ran on cuda:0 with device-transfer warnings.
- 2026-04-18 05:17 KST: Improved the Models page for a trading-model product presentation. Added a model marketplace-style carousel, selected-model hero card, stability score, since-model-start return, split consistency, side-by-side comparison table, and a non-guarantee note for sales copy discipline.
- 2026-04-18 user directive: Model performance is not acceptable yet; new target is Sharpe ratio 2.0 or higher where honestly achieved. Kaggle modeling should use only LightGBM, XGBoost, and ExtraTrees with normalized first-order variables, arithmetic second-order interactions, and re-normalized interaction features.
- 2026-04-18 08:20 KST: Implemented the requested engineered Kaggle run with 81 base features, 34 interaction sources, 2,325 final normalized features, and only LightGBM/XGBoost/ExtraTrees. GPU run succeeded, but the latest two-year Sharpe target was not met. Best full-window result was `xgb_gpu_engineered` with Sharpe 0.269 and total return 7.317%; split 2 reached Sharpe 2.271, showing regime instability rather than a stable sellable edge.
- 2026-04-18 08:45 KST heartbeat: Development/design meeting decided not to hide the weak full-window model result. Added a model readiness gate to the Models page so Sharpe target miss, validation/backtest decay, split instability, and drawdown risks are summarized before any sales-style comparison.
- 2026-04-18 09:05 KST heartbeat: Build, Docker, and Git are still blocked by local permission errors, so the team documented the next modeling step in `docs/model-regime-validation-plan.md`: regime features, walk-forward rules, package-candidate gates, transaction-cost/slippage requirements, and rejection reasons for unstable Sharpe results.
- 2026-04-18 09:15 KST approval: Frontend production build and Docker refresh succeeded after user approval. The Models readiness gate is now built into the running localhost app, and the approval queue no longer has pending build/Git items.
- 2026-04-18 09:28 KST heartbeat: Added the next package-gate implementation layer to the Kaggle pipeline: net returns after transaction cost/slippage, gross-vs-net metrics, worst split Sharpe, validation/test Sharpe gap, package-candidate boolean, and rejection reasons. Backend/frontend contracts now expose these fields, and the Models detail grid can show gross Sharpe, cost drag, and worst split Sharpe after the next Kaggle result refresh.
- 2026-04-18 09:49 KST heartbeat: Rechecked the package-gate layer. Python compile and frontend TypeScript checks still pass, but production build remains blocked by Windows `spawn EPERM` and Git commit remains blocked by `.git/index.lock` creation permission denied.
- 2026-04-18 10:50 KST approval: Package-gate metrics were production-built and Docker refreshed after user approval. Both backend and frontend services restarted successfully, so the app is ready to expose gross/net cost metrics and rejection reasons after the next Kaggle result refresh.
- 2026-04-18 user directive: The 2,325-feature engineered model looked overfit. Update the Kaggle pipeline to add useful cross-asset/regime features while selecting about 200 important low-correlation features for training instead of using the full synthetic feature pool.
- 2026-04-18 development: Implemented the lower-overfit Kaggle pipeline design. It now adds VIX, DXY, oil, silver, yield spread, cross-asset relative momentum, and rolling-correlation features, but greedily selects about 200 target-ranked low-pairwise-correlation features from the broader normalized candidate pool. Local build/Docker validation passed; a fresh Kaggle run still needs authentication because no Kaggle credential is available in this session.
- 2026-04-18 23:05 KST: Kaggle authentication was restored and kernel version 5 completed. The new lower-overfit run selected 200 features from 2,146 candidates, but performance worsened. Best model was `extra_trees_engineered` with net Sharpe -0.553, gross Sharpe -0.343, and net total return -25.258%; no model passed the package-candidate gate. Next model work should focus on target definition, signal threshold/exposure floor, and regime-specific trade gating rather than adding more features.
- 2026-04-18 23:30 KST heartbeat: Started the repeated experiment loop. Experiment 001 targets the latest run's likely interaction overfit by adding a 60-feature floor for normalized first-order/base variables before the selector fills the rest of the 200 slots with second-order interactions. Full Kaggle validation remains the next step.
- 2026-04-18 23:50 KST heartbeat: PowerShell execution policy blocked `scripts/kaggle.ps1` in the heartbeat environment, so a `scripts/kaggle.cmd` wrapper was added to keep Kaggle status/push/output commands usable without storing tokens in files.
- 2026-04-18 23:50 KST heartbeat follow-up: The `.cmd` wrapper executed, but this sandbox identity cannot see `KAGGLE_API_TOKEN` in process or user environment. Kaggle validation for Experiment 001 is blocked until auth is restored for the active heartbeat sandbox. No second modeling change was stacked on top, to keep the next backtest attributable to the base-feature-floor experiment.
- 2026-04-19 00:08 KST heartbeat: Automation prompt was updated to prefer `scripts/kaggle.cmd` for Kaggle operations and to avoid stacking new model changes until Experiment 001 is actually pushed, completed, and downloaded. Kaggle auth and `.git/index.lock` write access are still blocked in the active sandbox.
- 2026-04-19 00:25 KST heartbeat: Added a small Models UI auditability pass. The showcase now displays selected base features, selected interaction features, and base-floor status so the current 9-base/191-interaction overfit concern is visible to users. Frontend TypeScript and Kaggle script compile checks passed; Kaggle auth and Git write access remain blocked.
- 2026-04-19 00:44 KST heartbeat: Rechecked the Experiment 001 queue without adding Experiment 002. TypeScript, Python compile, diff check, and token-string scan passed. Production build is blocked by `spawn EPERM`, Kaggle auth is still absent in this sandbox, and Git still cannot create `.git/index.lock`.
- 2026-04-19 04:35 KST permission refresh: Local blockers cleared. Kaggle status authenticated through `scripts/kaggle.cmd`, Git staging succeeded, frontend production build passed, and Python compile checks passed. The next action is to commit/push Experiment 001 and run the Kaggle base-feature-floor backtest.
- 2026-04-19 04:42 KST Experiment 001 result: Kaggle version 6 completed. The selector chose 200 features from 2,146 candidates, but the base floor missed with only 30 base features and 170 interaction features. Best model was `extra_trees_engineered` with net Sharpe -0.536, gross Sharpe -0.365, net total return -22.474%, max drawdown -34.733%, and package_candidate false. Next experiment should make the base-floor pass draw from the full normalized base-feature pool instead of the top-900 prefilter.
- 2026-04-18 04:54 KST: Updated the recurring development/design heartbeat prompt to reduce repetition of implemented work, increase freedom for new useful product features, and prioritize Kaggle result recovery, model registry upgrades, data fallback reduction, news refreshes, chart UX, and report persistence.
- 2026-04-18 development: Reduced fundamentals fallback by adding Yahoo Finance fundamentals-timeseries as a second source after quoteSummary. After backend rebuild, all 28 tracked equities returned Yahoo Finance fundamentals-timeseries instead of curated fallback data.
- 2026-04-18 user directive: Updated the recurring meeting prompt to stop repeating already implemented items, give developers/designers more freedom to add useful market-data product features, allow alternate public data sources when Yahoo/fallbacks fail, and prioritize cleaning messy market snapshot layouts.
- 2026-04-18 development: Expanded the tracked large-cap stock universe across the US, Korea, and Japan; added valuation metrics such as PER, forward PER, P/B, P/S, EV/EBITDA, dividend yield, beta, target upside, and market cap; added curated fallback valuation metrics; and tightened the Market Snapshot card text to one-line values.
- 2026-04-18 heartbeat: Added approval-queue.md so blocked build, Docker, and Git actions are preserved for morning approval instead of disappearing into chat history.
- 2026-04-18 heartbeat: Development/design pass added visible sort-value badges to each fundamentals card and made missing fundamental sort values fall to the end, so stock comparisons are easier to audit.
- 2026-04-18 heartbeat: Design/development check added Fundamentals page sorting by ROE, revenue growth, FCF margin, and low leverage so statement-derived metrics are easier to compare.
- 2026-04-17: Added user priority for historical stock financial statements, derived fundamental indicators, and financial-statement-based boosting/bagging model support.
- 2026-04-17 heartbeat: Development/design meeting checked the new page-switching dashboard and added per-page count badges so each list communicates its current contents before the user clicks.
- 2026-04-17 23:45 KST: Added a design/development request for click-based page switching so the dashboard becomes multiple focused lists instead of one long page. Implementation priority is section navigation, next/previous controls, and cleaner page grouping.
- 2026-04-17 23:25 KST: Added a model backtesting product requirement. User wants JSON files with trained model weights and derived variables placed in a dedicated folder, then recent two-year BTC backtests displayed on the web with Sharpe ratio and win rate by model.
- 2026-04-17 23:10 KST: Shifted near-term meetings to development and design only. Development will keep adding useful variables, indicators, research products, and interactions; design will directly inspect the dashboard and tighten layout/readability. Current implementation started with an interactive feature-correlation workbench.
- 2026-04-17 22:28 KST: Added lead-lag feature correlation planning and AI-style research commentary requirements after the user requested both.
- 2026-04-17 22:12 KST: Heartbeat operations check confirmed a clean git tree, running Docker services, and a live 12-feature/144-cell engineered correlation heatmap on the dashboard.
- 2026-04-17 21:58 KST: Updated correlation display from target-only bars to a multivariate engineered-feature heatmap while keeping BTC return as a key variable.
- 2026-04-17 21:55 KST: Corrected correlation direction from asset-to-asset heatmap toward BTC target feature correlations, and prioritized chart axis labels plus text overflow fixes.
- 2026-04-17 21:25 KST: Added user priority for major government bond yield monitoring and cross-asset correlation analysis across BTC, equities, gold, and yields.
- 2026-04-17 21:05 KST: Added user priority for major BTC news summaries with a three-hour refresh cadence and a more polished research dashboard presentation.
- 2026-04-17 20:45 KST: Added user priority for BTC charting, Bollinger Bands, RSI, chart range/size controls, and proactive small feature additions during recurring operating meetings.
- 2026-04-17 20:20 KST: Added SQLite-backed 10-year OHLC storage for major index candles and made news cards interactive with sentiment filters and expandable source links.
- 2026-04-17 20:02 KST: Changed major index SVG plots from line charts to candlestick charts using OHLC data from Yahoo Finance with fallback candles.
- 2026-04-17 19:45 KST: Added one-month SVG line plots for S&P 500, Nasdaq Composite, KOSPI, and Nikkei 225 using Yahoo Finance chart data with local fallback.
- 2026-04-17 19:31 KST: Added visual market summary bars and per-instrument move bars to make global market moves easier to scan.
- 2026-04-17 19:20 KST: Added a global market watch API and dashboard section for selected US, Korean, Japanese equities, major indices, and gold spot using Yahoo Finance with local fallback.
- 2026-04-17 19:12 KST: Added scenario probability bars to the dashboard so scenario odds are visible as a small bar chart, not only numeric percentages.
- 2026-04-17 19:03 KST: Switched the frontend API base URL from localhost to 127.0.0.1 to avoid Windows localhost resolving to an older WSL relay on IPv6.
- 2026-04-17 18:39 KST: Added a keyless CoinDesk RSS news collector with local fallback. Research summaries now state the active news data source.
- 2026-04-17 18:23 KST: Added news data-source transparency to the API contract and dashboard. News is still placeholder content, but the UI now labels it as local fallback data.
- 2026-04-17 18:05 KST: Created the company memory in the writable C drive workspace. The product now has CoinGecko market data with local fallback, but news data and report persistence are still placeholders.
