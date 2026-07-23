import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.models.enums import SessionMode
from app.schemas.interview import AnswerSubmit, SessionCreate, SessionRead, SessionSummary
from app.services.interview_service import InterviewService
from app.services.live_interview_service import LiveInterviewService
from app.utils.dependencies import CurrentUser, CurrentWsUser, DbSession

router = APIRouter()
logger = logging.getLogger("app.live_interview")


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, current_user: CurrentUser) -> SessionRead:
    session = InterviewService(db).create_session(current_user.id, payload)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or candidate not found")
    return session


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    db: DbSession, current_user: CurrentUser, limit: int = 50, candidate_id: str | None = None
) -> list[SessionSummary]:
    rows = InterviewService(db).list_sessions(current_user.id, limit, candidate_id)
    return [
        SessionSummary(
            id=row["session"].id,
            candidate_id=row["session"].candidate_id,
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


async def _send_turn(websocket: WebSocket, live_service: LiveInterviewService, turn: dict) -> None:
    if turn.get("error"):
        await websocket.send_json({"type": "notice", "message": turn["error"]})
        return
    await websocket.send_json({"type": "transcript", "text": turn["candidate_text"]})
    await websocket.send_json({"type": "ai_text", "text": turn["ai_text"]})
    await websocket.send_bytes(live_service.synthesize(turn["ai_text"]))


@router.websocket("/{session_id}/live")
async def live_interview_ws(websocket: WebSocket, session_id: str, db: DbSession, current_user: CurrentWsUser) -> None:
    session = InterviewService(db).get_session(current_user.id, session_id)
    if session is None or session.mode != SessionMode.LIVE:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    live_service = LiveInterviewService(db, session)

    try:
        opening_text = live_service.opening_message()
        await websocket.send_json({"type": "ai_text", "text": opening_text})
        await websocket.send_bytes(live_service.synthesize(opening_text))

        pending_frame: str | None = None
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if "text" in message and message["text"] is not None:
                try:
                    payload = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                if payload.get("type") == "frame":
                    pending_frame = payload.get("image")
                elif payload.get("type") == "user_text":
                    turn = live_service.handle_text_turn(str(payload.get("text") or ""), pending_frame)
                    pending_frame = None
                    await _send_turn(websocket, live_service, turn)
                elif payload.get("type") == "end":
                    session = live_service.finish()
                    await websocket.send_json(
                        {
                            "type": "summary",
                            "overall_score": session.overall_score,
                            "status": session.status.value,
                        }
                    )
                    await websocket.close()
                    return

            elif "bytes" in message and message["bytes"] is not None:
                audio_bytes = message["bytes"]
                if not audio_bytes:
                    continue

                turn = live_service.handle_turn(audio_bytes, pending_frame)
                pending_frame = None
                await _send_turn(websocket, live_service, turn)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Live interview websocket error for session_id=%s", session_id)
        try:
            await websocket.send_json({"type": "error", "message": "The live interview hit an unexpected error."})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
