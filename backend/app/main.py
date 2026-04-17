from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.research import router as research_router
from app.core.config import settings


app = FastAPI(
    title="BTC Research AI API",
    version="0.1.0",
    description="Research API for Bitcoin market summaries and scenario analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(research_router, prefix="/research", tags=["research"])
