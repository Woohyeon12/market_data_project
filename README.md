# BTC Research AI

Extensible starter skeleton for a Bitcoin and financial research website.

The first version is intentionally small:

- A FastAPI backend with health and research endpoints.
- Placeholder collectors for market and news data.
- A scenario model that can later be replaced with a trained model.
- A Next.js frontend dashboard that reads from the backend.
- Dockerfiles and docker-compose for local deployment.

## Project Layout

```text
btc-research-ai/
  backend/
    app/
      api/          HTTP routes
      collectors/   external data collection modules
      core/         configuration
      models/       prediction/scenario model adapters
      schemas/      API response/request contracts
      services/     business logic orchestration
    model_registry/ JSON model weight files for local backtests
  frontend/
    app/            Next.js app router pages
    components/     reusable UI components
    lib/            API client helpers
```

## Local Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend URL:

```text
http://localhost:8000
```

## Local Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## Docker

```powershell
docker compose up --build
```

## Model Backtests

Put enabled JSON model files in `backend/model_registry`.

The backend reads weighted boosting, bagging, or ensemble exports from that folder and evaluates each signal on the latest 504 trading observations, roughly two years. Signals from date T are scored against BTC return on date T+1. The dashboard shows Sharpe ratio, win rate, total return, max drawdown, exposure, and a compact equity curve.

For stock models, use `target: "equity_fundamental_score"` with financial statement features such as `fundamental_revenue_growth_yoy`, `fundamental_net_margin`, `fundamental_roe`, `fundamental_debt_to_equity`, and `fundamental_fcf_margin`. These models score tracked equities from the latest annual financial statement metrics.

See `backend/model_registry/README.md` for the supported feature names and JSON format. User JSON files are ignored by Git by default so private model weights are not pushed accidentally.

## Next Things To Add

- Expand the first CoinGecko market data integration with retries, caching, and monitoring.
- Replace mock news with RSS, CryptoPanic, or NewsAPI.
- Add PostgreSQL or Supabase for report history.
- Add scheduled collection and report generation.
- Add API key protection before public launch.
- Expand backtests with transaction costs, walk-forward validation, and model version history.

## Important Disclaimer

This project is for research and education. It should not make guaranteed return claims or personalized investment recommendations.
