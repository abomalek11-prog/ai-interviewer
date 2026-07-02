from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: str, payload: JobCreate) -> Job:
        job = Job(owner_id=owner_id, **payload.model_dump())
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_for_owner(self, owner_id: str) -> list[tuple[Job, int]]:
        rows = self.db.execute(
            select(Job, func.count(Candidate.id))
            .outerjoin(Candidate, Candidate.job_id == Job.id)
            .where(Job.owner_id == owner_id)
            .group_by(Job.id)
            .order_by(Job.created_at.desc())
        ).all()
        return [(row[0], row[1]) for row in rows]

    def get(self, owner_id: str, job_id: str) -> Job | None:
        return self.db.scalar(select(Job).where(Job.id == job_id, Job.owner_id == owner_id))

    def update(self, job: Job, payload: JobUpdate) -> Job:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(job, field, value)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def delete(self, job: Job) -> None:
        self.db.delete(job)
        self.db.commit()
