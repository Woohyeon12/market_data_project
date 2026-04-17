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
