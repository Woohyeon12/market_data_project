from fastapi import APIRouter

from app.schemas.research import MarketsOverview, ResearchReport
from app.services.research_service import build_btc_report, build_markets_overview


router = APIRouter()


@router.get("/btc", response_model=ResearchReport)
def get_btc_research() -> ResearchReport:
    return build_btc_report()


@router.get("/markets", response_model=MarketsOverview)
def get_markets_overview() -> MarketsOverview:
    return build_markets_overview()
