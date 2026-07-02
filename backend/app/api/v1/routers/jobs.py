from fastapi import APIRouter, HTTPException, status

from app.schemas.job import JobCreate, JobRead, JobUpdate, JobWithStats
from app.services.job_service import JobService
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: DbSession, current_user: CurrentUser) -> JobRead:
    return JobService(db).create(current_user.id, payload)


@router.get("", response_model=list[JobWithStats])
def list_jobs(db: DbSession, current_user: CurrentUser) -> list[JobWithStats]:
    rows = JobService(db).list_for_owner(current_user.id)
    return [JobWithStats(**JobRead.model_validate(job).model_dump(), candidate_count=count) for job, count in rows]


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: DbSession, current_user: CurrentUser) -> JobRead:
    job = JobService(db).get(current_user.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: str, payload: JobUpdate, db: DbSession, current_user: CurrentUser) -> JobRead:
    service = JobService(db)
    job = service.get(current_user.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return service.update(job, payload)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: DbSession, current_user: CurrentUser) -> None:
    service = JobService(db)
    job = service.get(current_user.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    service.delete(job)
