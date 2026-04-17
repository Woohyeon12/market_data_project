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

## Next Things To Add

- Expand the first CoinGecko market data integration with retries, caching, and monitoring.
- Replace mock news with RSS, CryptoPanic, or NewsAPI.
- Add PostgreSQL or Supabase for report history.
- Add scheduled collection and report generation.
- Add API key protection before public launch.
- Add backtests before presenting predictions as model output.

## Important Disclaimer

This project is for research and education. It should not make guaranteed return claims or personalized investment recommendations.
