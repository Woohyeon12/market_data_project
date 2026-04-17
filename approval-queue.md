# Approval Queue

## 2026-04-18 04:10 KST

### Current Status

- Done: `npm.cmd install`, `npm.cmd install next@15.5.15`, `npm.cmd run build`, `npm.cmd audit --audit-level=high`, and Python compile checks.
- Done: Added `.dockerignore` files so Docker builds do not send local `node_modules`, `.next`, data, or venv folders.
- Still blocked/slow: `docker compose build` and `docker compose build frontend` repeatedly timed out without useful build logs even after the context cleanup.

### Pending Approvals

1. Docker-based validation
   - Why: Docker services are running, but Docker API access returned permission denied for `docker compose exec`.
   - Command: `docker compose build frontend && docker compose up -d frontend`
   - Expected result: Rebuild and serve the updated dashboard at `http://localhost:3000`.

2. Git commit and push
   - Why: Git cannot create `.git/index.lock` because the current sandbox identity is denied write access inside `.git`.
   - Command: `git add . && git commit -m "Expand equity fundamentals and valuation metrics" && git push origin main`
   - Expected result: Upload the latest development/design changes to `origin/main`.

### Current Uncommitted Product Changes

- Fundamentals cards show the selected sort metric value next to the currency badge.
- Missing fundamental sort values now fall to the end for both ascending and descending sorts.
- Mobile CSS for the new fundamentals badges wraps instead of overflowing.
- Company memory now describes the product as Bitcoin plus global market research, not BTC-only.
- Tracked stocks now include more large-cap US, Korean, and Japanese equities.
- Fundamentals now include PER, forward PER, P/B, P/S, EV/EBITDA, dividend yield, beta, target upside, and market cap where Yahoo or curated fallback data can provide them.
- Market Snapshot cards use shorter labels and one-line values to avoid messy wrapping.
