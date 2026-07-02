from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.interview import InterviewSession
from app.models.job import Job
from app.schemas.candidate import CandidateCreate, CandidateUpdate


class CandidateService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: str, payload: CandidateCreate) -> Candidate | None:
        job = self.db.scalar(select(Job).where(Job.id == payload.job_id, Job.owner_id == owner_id))
        if job is None:
            return None

        candidate = Candidate(**payload.model_dump())
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def list_for_owner(self, owner_id: str, job_id: str | None = None) -> list[dict]:
        latest_score = (
            select(InterviewSession.candidate_id, InterviewSession.overall_score)
            .where(InterviewSession.overall_score.is_not(None))
            .order_by(InterviewSession.candidate_id, InterviewSession.created_at.desc())
        )
        scores_by_candidate = {row.candidate_id: row.overall_score for row in self.db.execute(latest_score)}

        query = select(Candidate, Job.title).join(Job, Job.id == Candidate.job_id).where(Job.owner_id == owner_id)
        if job_id:
            query = query.where(Candidate.job_id == job_id)
        query = query.order_by(Candidate.created_at.desc())

        results = []
        for candidate, job_title in self.db.execute(query).all():
            results.append(
                {
                    "candidate": candidate,
                    "job_title": job_title,
                    "latest_score": scores_by_candidate.get(candidate.id),
                }
            )
        return results

    def get(self, owner_id: str, candidate_id: str) -> Candidate | None:
        return self.db.scalar(
            select(Candidate)
            .join(Job, Job.id == Candidate.job_id)
            .where(Candidate.id == candidate_id, Job.owner_id == owner_id)
        )

    def update(self, candidate: Candidate, payload: CandidateUpdate) -> Candidate:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(candidate, field, value)
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        return candidate
