import json
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.ai import AnswerEvaluation, GeneratedQuestion


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None = settings.OPENAI_API_KEY, model: str = settings.OPENAI_MODEL):
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)


class AIService:
    """Provider-neutral AI interface for question generation and answer evaluation."""

    def __init__(self, provider: BaseLLMProvider | None = None):
        self.provider = provider or OpenAIProvider()

    def evaluate_answer(self, question: str, answer: str, difficulty: str, interview_type: str) -> AnswerEvaluation:
        system_prompt = (
            "You are a senior technical interviewer. Return only valid JSON with keys: "
            "score, correctness, depth, clarity, terminology, feedback, strengths, improvements. "
            "All numeric fields must be integers from 0 to 100."
        )
        user_prompt = (
            f"Interview type: {interview_type}\n"
            f"Difficulty: {difficulty}\n"
            f"Question: {question}\n"
            f"Candidate answer: {answer}"
        )
        result = self.provider.complete_json(system_prompt, user_prompt)
        return AnswerEvaluation.model_validate(result)

    def generate_questions(
        self,
        interview_type: str,
        difficulty: str,
        count: int,
        focus_areas: list[str],
    ) -> list[GeneratedQuestion]:
        system_prompt = (
            "You generate technical interview questions. Return valid JSON with a top-level "
            "'questions' array. Each item must include prompt, expected_topics, time_limit_seconds."
        )
        user_prompt = (
            f"Interview type: {interview_type}\n"
            f"Difficulty: {difficulty}\n"
            f"Count: {count}\n"
            f"Focus areas: {', '.join(focus_areas) if focus_areas else 'general'}"
        )
        result = self.provider.complete_json(system_prompt, user_prompt)
        questions = result["questions"] if isinstance(result, dict) else result
        return [GeneratedQuestion.model_validate(item) for item in questions]
