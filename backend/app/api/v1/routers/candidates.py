from fastapi import APIRouter, HTTPException, status

from app.schemas.candidate import CandidateCreate, CandidateRead, CandidateUpdate, CandidateWithJob
from app.services.candidate_service import CandidateService
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: DbSession, current_user: CurrentUser) -> CandidateRead:
    candidate = CandidateService(db).create(current_user.id, payload)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return candidate


@router.get("", response_model=list[CandidateWithJob])
def list_candidates(db: DbSession, current_user: CurrentUser, job_id: str | None = None) -> list[CandidateWithJob]:
    rows = CandidateService(db).list_for_owner(current_user.id, job_id)
    return [
        CandidateWithJob(
            **CandidateRead.model_validate(row["candidate"]).model_dump(),
            job_title=row["job_title"],
            latest_score=row["latest_score"],
        )
        for row in rows
    ]


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: str, db: DbSession, current_user: CurrentUser) -> CandidateRead:
    candidate = CandidateService(db).get(current_user.id, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(candidate_id: str, payload: CandidateUpdate, db: DbSession, current_user: CurrentUser) -> CandidateRead:
    service = CandidateService(db)
    candidate = service.get(current_user.id, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return service.update(candidate, payload)
