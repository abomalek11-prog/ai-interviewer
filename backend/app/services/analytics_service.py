from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SessionStatus
from app.models.interview import InterviewSession
from app.models.job import Job
from app.schemas.analytics import AnalyticsSummary, DifficultyBreakdownItem, TrendPoint


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes (stored as UTC), Postgres aware ones; compare as aware UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, owner_id: str) -> AnalyticsSummary:
        sessions_query = select(InterviewSession).join(Job, Job.id == InterviewSession.job_id).where(
            Job.owner_id == owner_id
        )
        sessions = self.db.scalars(sessions_query).all()

        total_interviews = len(sessions)
        completed = [s for s in sessions if s.status == SessionStatus.COMPLETED]
        completed_interviews = len(completed)
        scored = [s.overall_score for s in completed if s.overall_score is not None]
        success_rate = round(len([s for s in scored if s >= 70]) / len(scored) * 100, 1) if scored else 0.0
        avg_ai_score = round(sum(scored) / len(scored), 1) if scored else 0.0

        since = datetime.now(UTC) - timedelta(days=30)
        trend_counts: dict[str, int] = {}
        for session in completed:
            completed_at = _as_utc(session.completed_at)
            if completed_at and completed_at >= since:
                day = completed_at.date().isoformat()
                trend_counts[day] = trend_counts.get(day, 0) + 1
        trend_30d = [TrendPoint(date=day, completed=count) for day, count in sorted(trend_counts.items())]

        jobs = self.db.scalars(select(Job).where(Job.owner_id == owner_id)).all()
        total_jobs = len(jobs)
        breakdown_counts: dict[str, int] = {}
        for job in jobs:
            breakdown_counts[job.seniority.value] = breakdown_counts.get(job.seniority.value, 0) + 1
        difficulty_breakdown = [
            DifficultyBreakdownItem(
                seniority=seniority,
                count=count,
                percentage=round(count / total_jobs * 100, 1) if total_jobs else 0.0,
            )
            for seniority, count in breakdown_counts.items()
        ]

        return AnalyticsSummary(
            total_interviews=total_interviews,
            completed_interviews=completed_interviews,
            success_rate=success_rate,
            avg_ai_score=avg_ai_score,
            trend_30d=trend_30d,
            difficulty_breakdown=difficulty_breakdown,
            total_jobs=total_jobs,
        )
