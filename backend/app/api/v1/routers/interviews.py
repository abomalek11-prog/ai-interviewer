from fastapi import APIRouter, HTTPException, status

from app.schemas.interview import AnswerSubmit, SessionCreate, SessionRead, SessionSummary
from app.services.interview_service import InterviewService
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter()


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, current_user: CurrentUser) -> SessionRead:
    session = InterviewService(db).create_session(current_user.id, payload)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or candidate not found")
    return session


@router.get("", response_model=list[SessionSummary])
def list_sessions(db: DbSession, current_user: CurrentUser, limit: int = 50) -> list[SessionSummary]:
    rows = InterviewService(db).list_sessions(current_user.id, limit)
    return [
        SessionSummary(
            id=row["session"].id,
            candidate_name=row["candidate_name"],
            job_title=row["job_title"],
            status=row["session"].status,
            overall_score=row["session"].overall_score,
            started_at=row["session"].started_at,
            created_at=row["session"].created_at,
        )
        for row in rows
    ]


@router.get("/{session_id}", response_model=SessionRead)
def get_session(session_id: str, db: DbSession, current_user: CurrentUser) -> SessionRead:
    session = InterviewService(db).get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
    return session


@router.post("/{session_id}/answers", response_model=SessionRead)
def submit_answer(session_id: str, payload: AnswerSubmit, db: DbSession, current_user: CurrentUser) -> SessionRead:
    session = InterviewService(db).submit_answer(current_user.id, session_id, payload)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session or question not found")
    return session
