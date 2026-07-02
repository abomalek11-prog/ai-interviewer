import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.ai import AnswerEvaluation, GeneratedQuestion

logger = logging.getLogger("app.ai")


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = settings.OPENAI_API_KEY, model: str = settings.OPENAI_MODEL):
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


class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider used when OPENAI_API_KEY is not configured.

    Lets the interview flow run end-to-end (question generation, scoring) in local
    / demo environments without requiring API credentials.
    """

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        seed = int(hashlib.sha256(user_prompt.encode()).hexdigest(), 16)

        if "questions" in system_prompt.lower() or "generate" in system_prompt.lower():
            count = 5
            for line in user_prompt.splitlines():
                if line.lower().startswith("count:"):
                    count = int(line.split(":", 1)[1].strip() or count)
            return {
                "questions": [
                    {
                        "prompt": f"Describe how you would approach challenge #{i + 1} for this role, "
                        "covering trade-offs and how you would validate your solution.",
                        "expected_topics": ["problem solving", "trade-offs", "validation"],
                        "time_limit_seconds": 180,
                    }
                    for i in range(count)
                ]
            }

        base = 55 + (seed % 40)
        return {
            "score": base,
            "correctness": min(100, base + (seed % 7)),
            "depth": min(100, base - (seed % 5)),
            "clarity": min(100, base + (seed % 9) - 4),
            "terminology": min(100, base - (seed % 6)),
            "feedback": "Solid response with relevant detail; consider adding a concrete example next time.",
            "strengths": ["Clear structure", "Relevant terminology"],
            "improvements": ["Add a real-world example", "Discuss edge cases"],
        }


class AIService:
    """Provider-neutral AI interface for question generation and answer evaluation."""

    def __init__(self, provider: BaseLLMProvider | None = None):
        if provider is not None:
            self.provider = provider
        elif settings.OPENAI_API_KEY:
            self.provider = OpenAIProvider()
        else:
            logger.warning("OPENAI_API_KEY is not configured; using MockLLMProvider")
            self.provider = MockLLMProvider()

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
