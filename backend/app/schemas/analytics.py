from pydantic import BaseModel


class TrendPoint(BaseModel):
    date: str
    completed: int


class DifficultyBreakdownItem(BaseModel):
    seniority: str
    count: int
    percentage: float


class AnalyticsSummary(BaseModel):
    total_interviews: int
    completed_interviews: int
    success_rate: float
    avg_ai_score: float
    trend_30d: list[TrendPoint]
    difficulty_breakdown: list[DifficultyBreakdownItem]
    total_jobs: int
