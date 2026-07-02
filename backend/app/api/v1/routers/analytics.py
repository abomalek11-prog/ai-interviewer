from fastapi import APIRouter

from app.schemas.analytics import AnalyticsSummary
from app.services.analytics_service import AnalyticsService
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(db: DbSession, current_user: CurrentUser) -> AnalyticsSummary:
    return AnalyticsService(db).summary(current_user.id)
