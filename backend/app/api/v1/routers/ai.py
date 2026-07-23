from fastapi import APIRouter, HTTPException, UploadFile, status

from app.schemas.ai import (
    AIModelProfileRead,
    AnswerEvaluation,
    AnswerEvaluationRequest,
    GeneratedQuestion,
    QuestionGenerationRequest,
    TranscriptionResult,
)
from app.services.ai_service import AIService
from app.utils.dependencies import CurrentUser

router = APIRouter()

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # OpenAI Whisper API limit


@router.get("/model-profiles", response_model=list[AIModelProfileRead])
def list_model_profiles(_: CurrentUser) -> list[AIModelProfileRead]:
    return AIService.list_model_profiles()


@router.post("/evaluate-answer", response_model=AnswerEvaluation)
def evaluate_answer(payload: AnswerEvaluationRequest, _: CurrentUser) -> AnswerEvaluation:
    return AIService(preferred_profile_id=payload.ai_model_profile_id).evaluate_answer(
        question=payload.question,
        answer=payload.answer,
        difficulty=payload.difficulty,
        interview_type=payload.interview_type,
    )


@router.post("/generate-questions", response_model=list[GeneratedQuestion])
def generate_questions(payload: QuestionGenerationRequest, _: CurrentUser) -> list[GeneratedQuestion]:
    return AIService(preferred_profile_id=payload.ai_model_profile_id).generate_questions(
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        count=payload.count,
        focus_areas=payload.focus_areas,
    )


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(audio: UploadFile, _: CurrentUser) -> TranscriptionResult:
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty audio file")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio file too large (max 25MB)")

    try:
        text = AIService().transcribe_audio(content, audio.filename or "answer.webm")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Voice transcription is currently unavailable"
        ) from exc
    return TranscriptionResult(text=text)
