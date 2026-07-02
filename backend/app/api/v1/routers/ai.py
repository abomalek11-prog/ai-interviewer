from fastapi import APIRouter

from app.schemas.ai import AnswerEvaluation, AnswerEvaluationRequest, GeneratedQuestion, QuestionGenerationRequest
from app.services.ai_service import AIService
from app.utils.dependencies import CurrentUser

router = APIRouter()


@router.post("/evaluate-answer", response_model=AnswerEvaluation)
def evaluate_answer(payload: AnswerEvaluationRequest, _: CurrentUser) -> AnswerEvaluation:
    return AIService().evaluate_answer(
        question=payload.question,
        answer=payload.answer,
        difficulty=payload.difficulty,
        interview_type=payload.interview_type,
    )


@router.post("/generate-questions", response_model=list[GeneratedQuestion])
def generate_questions(payload: QuestionGenerationRequest, _: CurrentUser) -> list[GeneratedQuestion]:
    return AIService().generate_questions(
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        count=payload.count,
        focus_areas=payload.focus_areas,
    )
