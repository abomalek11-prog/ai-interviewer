import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai import AIModelProfileRead, AnswerEvaluation, GeneratedQuestion

logger = logging.getLogger("app.ai")


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        raise NotImplementedError

    @abstractmethod
    def converse(self, messages: list[dict[str, Any]], image_data_url: str | None) -> str:
        raise NotImplementedError

    @abstractmethod
    def speak(self, text: str) -> bytes:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.model = model
        self.supports_audio = not base_url or "openai.com" in base_url

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

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        result = self.client.audio.transcriptions.create(model="whisper-1", file=(filename, audio_bytes))
        return result.text

    def converse(self, messages: list[dict[str, Any]], image_data_url: str | None) -> str:
        chat_messages = list(messages)
        if image_data_url and chat_messages and chat_messages[-1]["role"] == "user":
            last = chat_messages[-1]
            chat_messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": last["content"]},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        response = self.client.chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            temperature=0.6,
            messages=chat_messages,
        )
        return response.choices[0].message.content or ""

    def speak(self, text: str) -> bytes:
        response = self.client.audio.speech.create(
            model=settings.OPENAI_TTS_MODEL,
            voice=settings.OPENAI_TTS_VOICE,
            input=text,
        )
        return response.read()


class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider used when OPENAI_API_KEY is not configured.

    Lets the interview flow run end-to-end (question generation, scoring) in local
    / demo environments without requiring API credentials.
    """

    _TECH_MARKERS = frozenset(
        {
            "because", "example", "trade-off", "tradeoff", "trade", "test", "testing", "design", "data",
            "performance", "scale", "scaling", "security", "api", "database", "cache", "caching", "error",
            "complexity", "algorithm", "architecture", "deploy", "monitor", "index", "queue", "async",
            "latency", "throughput", "validate", "measure", "requirement", "edge", "failure", "retry",
        }
    )

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
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

        return self._evaluate_from_content(user_prompt)

    def _evaluate_from_content(self, user_prompt: str) -> dict[str, Any]:
        """Score the actual answer text so demo-mode results track answer quality.

        Deterministic: the same answer always gets the same score, and longer,
        more substantive, more technical answers score higher.
        """
        answer = self._extract_answer_text(user_prompt)
        words = re.findall(r"[\w'-]+", answer.lower())
        word_count = len(words)

        if word_count == 0:
            return {
                "score": 0,
                "correctness": 0,
                "depth": 0,
                "clarity": 0,
                "terminology": 0,
                "feedback": "No substantive answer was provided.",
                "strengths": [],
                "improvements": ["Provide an actual answer to the question"],
            }

        unique_ratio = len(set(words)) / word_count
        marker_hits = len(self._TECH_MARKERS & set(words))
        sentences = max(1, len(re.findall(r"[.!?]+", answer)))

        depth = min(95, 15 + min(50, word_count // 3) + marker_hits * 4)
        terminology = min(95, 20 + marker_hits * 9)
        clarity = min(95, 30 + int(unique_ratio * 40) + min(20, sentences * 4))
        correctness = min(95, round(0.5 * depth + 0.5 * terminology) + 10)
        score = round(0.35 * correctness + 0.25 * depth + 0.2 * clarity + 0.2 * terminology)

        return {
            "score": score,
            "correctness": correctness,
            "depth": depth,
            "clarity": clarity,
            "terminology": terminology,
            "feedback": (
                "Offline demo evaluation (no AI key configured): scored from answer length, structure and "
                "technical vocabulary. Configure an OpenAI API key for a real assessment."
            ),
            "strengths": (["Uses relevant technical vocabulary"] if marker_hits >= 3 else [])
            + (["Substantive, detailed answer"] if word_count >= 80 else []),
            "improvements": (["Go deeper - the answer is quite short"] if word_count < 40 else [])
            + (["Use more precise technical terminology"] if marker_hits < 3 else []),
        }

    @staticmethod
    def _extract_answer_text(user_prompt: str) -> str:
        """Pull only the candidate's own words out of the evaluation prompt."""
        answer_match = re.search(r"Candidate answer:\s*(.*)", user_prompt, re.DOTALL)
        if answer_match:
            return answer_match.group(1).strip()

        transcript_match = re.search(r"Transcript:\s*(.*)", user_prompt, re.DOTALL)
        if transcript_match:
            candidate_lines = [
                line.split(":", 1)[1].strip()
                for line in transcript_match.group(1).splitlines()
                if line.strip().lower().startswith("candidate:")
            ]
            return " ".join(candidate_lines)

        return user_prompt.strip()

    def converse(self, messages: list[dict[str, Any]], image_data_url: str | None) -> str:
        turn_count = sum(1 for m in messages if m["role"] == "assistant")
        if turn_count == 0:
            return "Hi, thanks for joining! To start, could you walk me through your background and what drew you to this role?"
        return (
            f"Thanks for that answer. Here's follow-up question #{turn_count + 1}: "
            "could you go a bit deeper into the trade-offs of the approach you just described?"
        )

    def speak(self, text: str) -> bytes:
        return b""


class AIService:
    """Provider-neutral AI interface for question generation and answer evaluation."""

    def __init__(self, provider: BaseLLMProvider | None = None, preferred_profile_id: str | None = None):
        self.provider = provider
        self.preferred_profile_id = preferred_profile_id

        if provider is None and not self._available_profiles():
            logger.warning("OPENAI_API_KEY is not configured; using MockLLMProvider")
            self.provider = MockLLMProvider()

    @staticmethod
    def list_model_profiles() -> list[AIModelProfileRead]:
        profiles = []
        for profile in settings.ai_model_profiles:
            profiles.append(
                AIModelProfileRead(
                    id=str(profile["id"]),
                    label=str(profile["label"]),
                    model=str(profile["model"]),
                    is_available=bool(profile.get("api_key")),
                )
            )
        if not profiles:
            profiles.append(AIModelProfileRead(id="mock", label="Mock local AI", model="mock", is_available=True))
        return profiles

    def _available_profiles(self) -> list[dict[str, str | None]]:
        return [profile for profile in settings.ai_model_profiles if profile.get("api_key")]

    def _ordered_profiles(self) -> list[dict[str, str | None]]:
        profiles = self._available_profiles()
        if not self.preferred_profile_id:
            return profiles

        selected = [profile for profile in profiles if profile["id"] == self.preferred_profile_id]
        fallback = [profile for profile in profiles if profile["id"] != self.preferred_profile_id]
        return selected + (fallback if settings.AI_FALLBACK_ENABLED else [])

    @staticmethod
    def _build_provider(profile: dict[str, str | None]) -> "OpenAIProvider":
        return OpenAIProvider(
            api_key=str(profile["api_key"]),
            model=str(profile["model"]),
            base_url=profile.get("base_url"),
        )

    def _complete_json_with_fallback(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        if self.provider is not None:
            return self.provider.complete_json(system_prompt, user_prompt)

        profiles = self._ordered_profiles()
        if not profiles:
            return MockLLMProvider().complete_json(system_prompt, user_prompt)

        last_error: Exception | None = None
        for profile in profiles:
            try:
                provider = self._build_provider(profile)
                return provider.complete_json(system_prompt, user_prompt)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError, json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "AI profile failed; trying fallback if available. profile_id=%s model=%s error=%s",
                    profile["id"],
                    profile["model"],
                    exc,
                )

        # A configured provider can still be unavailable (for example, an
        # expired key or exhausted provider credits). In local/demo mode the
        # application should remain usable instead of failing the whole
        # interview creation request.
        if last_error is not None:
            if settings.AI_FALLBACK_ENABLED:
                logger.warning("All AI profiles failed; using MockLLMProvider for this request")
                return MockLLMProvider().complete_json(system_prompt, user_prompt)
            raise last_error
        return MockLLMProvider().complete_json(system_prompt, user_prompt)

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        if self.provider is not None:
            if isinstance(self.provider, OpenAIProvider) and self.provider.supports_audio:
                try:
                    return self.provider.transcribe(audio_bytes, filename)
                except Exception as exc:
                    raise RuntimeError("Voice transcription failed") from exc
            raise RuntimeError("Voice transcription is unavailable for the configured AI provider")

        profiles = [p for p in self._available_profiles() if not p.get("base_url") or "openai.com" in str(p.get("base_url"))]
        if not profiles:
            raise RuntimeError(
                "Voice transcription is unavailable - configure an OpenAI API key or type your answer manually"
            )

        last_error: Exception | None = None
        for profile in profiles:
            try:
                provider = self._build_provider(profile)
                return provider.transcribe(audio_bytes, filename)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                last_error = exc
                logger.warning(
                    "AI profile failed transcription; trying fallback if available. profile_id=%s error=%s",
                    profile["id"],
                    exc,
                )

        raise RuntimeError("Voice transcription failed") from last_error

    def converse(self, messages: list[dict[str, Any]], image_data_url: str | None = None) -> str:
        if self.provider is not None:
            return self.provider.converse(messages, image_data_url)

        profiles = self._ordered_profiles()
        if not profiles:
            return MockLLMProvider().converse(messages, image_data_url)

        last_error: Exception | None = None
        for profile in profiles:
            try:
                provider = self._build_provider(profile)
                return provider.converse(messages, image_data_url)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                last_error = exc
                logger.warning(
                    "AI profile failed conversation turn; trying fallback if available. profile_id=%s error=%s",
                    profile["id"],
                    exc,
                )

        if last_error is not None:
            if settings.AI_FALLBACK_ENABLED:
                logger.warning("All AI profiles failed; using MockLLMProvider for this conversation turn")
                return MockLLMProvider().converse(messages, image_data_url)
            raise last_error
        return MockLLMProvider().converse(messages, image_data_url)

    def synthesize_speech(self, text: str) -> bytes:
        """Return synthesized audio, or b"" if unavailable.

        Callers (e.g. the live interview websocket) treat an empty response as "no
        server-side TTS - fall back to the browser's speech synthesis" rather than
        failing the whole turn/session.
        """
        if self.provider is not None:
            try:
                return self.provider.speak(text)
            except Exception:
                logger.warning("Configured AI provider failed speech synthesis; falling back to no audio")
                return b""

        profiles = [p for p in self._available_profiles() if not p.get("base_url") or "openai.com" in str(p.get("base_url"))]
        if not profiles:
            return MockLLMProvider().speak(text)

        for profile in profiles:
            try:
                provider = self._build_provider(profile)
                return provider.speak(text)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                logger.warning(
                    "AI profile failed speech synthesis; trying fallback if available. profile_id=%s error=%s",
                    profile["id"],
                    exc,
                )

        return b""

    def evaluate_answer(self, question: str, answer: str, difficulty: str, interview_type: str) -> AnswerEvaluation:
        system_prompt = (
            "You are a strict, consistent senior technical interviewer. Return only valid JSON with keys: "
            "score, correctness, depth, clarity, terminology, feedback, strengths, improvements. "
            "All numeric fields must be integers from 0 to 100.\n"
            "Scoring rubric (apply strictly and consistently):\n"
            "- 0-20: no substantive answer, off-topic, or a one-liner\n"
            "- 21-45: superficial, vague, little technical content\n"
            "- 46-65: partially correct with some detail but notable gaps\n"
            "- 66-85: solid, mostly correct, concrete detail and reasoning\n"
            "- 86-100: exceptional depth, precise terminology, examples and trade-offs\n"
            "Base every sub-score on concrete evidence from the answer. Do not reward length alone."
        )
        user_prompt = (
            f"Interview type: {interview_type}\n"
            f"Difficulty: {difficulty}\n"
            f"Question: {question}\n"
            f"Candidate answer: {answer}"
        )
        result = self._complete_json_with_fallback(system_prompt, user_prompt)
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
        result = self._complete_json_with_fallback(system_prompt, user_prompt)
        questions = result["questions"] if isinstance(result, dict) else result
        return [GeneratedQuestion.model_validate(item) for item in questions]
