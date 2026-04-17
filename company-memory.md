# BTC Research AI Company Memory

## Current Goal

Build a Bitcoin research-focused financial intelligence company around this project.

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
