import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai import AIModelProfileRead, AnswerEvaluation, GeneratedQuestion

logger = logging.getLogger("app.ai")

# Output ceilings. Gateways that meter credits (OpenRouter) reserve the model's full
# output window when max_tokens is omitted, so an unbounded request fails on a small
# balance even though the actual reply is a few sentences. Reasoning models spend part
# of this budget thinking before they answer (~200-300 tokens per turn at low effort on
# the free Nemotron models), so the ceilings leave room for that on top of the reply.
MAX_REPLY_TOKENS = 1200  # spoken interview turn: 2-4 sentences + reasoning
MAX_JSON_TOKENS = 3000   # evaluation / generated question set + reasoning

# Fail fast so a stalled free model hands over to the next profile instead of hanging
# the live interview for the SDK's 10-minute default.
REQUEST_TIMEOUT_SECONDS = 60
# The end-of-interview evaluation reasons over the whole transcript and regularly needs
# ~60s. At the conversational timeout it was cut off and retried, doubling the wait.
EVAL_TIMEOUT_SECONDS = 150

IMAGE_CAPTION_SCREEN = (
    "[Attached: a screenshot of the candidate's shared screen, taken as they finished speaking. "
    "This reply is spoken aloud: at most 3 short sentences - name the single most important issue "
    "you see, then ask one question. Do not walk through every problem at once.]"
)


def openrouter_reasoning(effort: str) -> dict[str, Any]:
    """OpenRouter's reasoning control, kept out of the reply text. Models without reasoning ignore it."""
    return {"reasoning": {"effort": effort, "exclude": True}}


class EmptyCompletionError(RuntimeError):
    """The model returned no usable content (e.g. a reasoning model spent the whole budget thinking)."""


def completion_text(response: Any, model: str) -> str:
    """The reply text, or EmptyCompletionError so the caller falls through to the next model.

    OpenRouter sometimes answers HTTP 200 with no `choices` at all and the upstream
    provider's failure in an `error` field - that must not crash the turn.
    """
    choices = getattr(response, "choices", None)
    if not choices:
        error = (getattr(response, "model_extra", None) or {}).get("error")
        raise EmptyCompletionError(f"{model} returned no choices: {error}")
    content = choices[0].message.content
    if not content or not content.strip():
        raise EmptyCompletionError(f"{model} returned an empty reply")
    return content.strip()


def parse_json_content(content: str) -> dict[str, Any] | list[Any]:
    """Parse a model's JSON reply, tolerating the wrappers models without strict JSON mode add.

    Free models often ignore response_format and wrap the object in a ```json fence or a
    sentence of preamble; the payload itself is still usable.
    """
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        end = max(text.rfind("}"), text.rfind("]"))
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        raise NotImplementedError

    @abstractmethod
    def converse(
        self, messages: list[dict[str, Any]], image_data_url: str | None, image_caption: str | None = None
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def speak(self, text: str) -> bytes:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    # Models that rejected an image in this process. Remembered so later turns skip the
    # snapshot up front instead of spending a second request (against a 50/day free quota)
    # on the text-only retry every time.
    _text_only_models: set[str] = set()

    def __init__(self, api_key: str, model: str, base_url: str | None = None, vision_model: str | None = None):
        # OpenRouter asks callers to identify the app; it is optional and harmless elsewhere.
        headers = (
            {"HTTP-Referer": settings.FRONTEND_BASE_URL, "X-Title": settings.PROJECT_NAME}
            if base_url and "openrouter.ai" in base_url
            else None
        )
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            default_headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
        )
        self.model = model
        # Comma-separated fallback list: free vision models are often rate-limited, so the
        # next one is tried before giving up on the picture.
        self.vision_models = [m.strip() for m in (vision_model or settings.OPENAI_VISION_MODEL).split(",") if m.strip()]
        self.supports_audio = not base_url or "openai.com" in base_url
        self.is_openrouter = bool(base_url and "openrouter.ai" in base_url)

    @property
    def vision_model(self) -> str:
        return self.vision_models[0]

    def _reasoning(self, effort: str) -> dict[str, Any] | None:
        return openrouter_reasoning(effort) if self.is_openrouter else None

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | list[Any]:
        response = self.client.with_options(timeout=EVAL_TIMEOUT_SECONDS, max_retries=0).chat.completions.create(
            model=self.model,
            temperature=0.2,
            max_tokens=MAX_JSON_TOKENS,
            response_format={"type": "json_object"},
            extra_body=self._reasoning(settings.AI_REASONING_EVAL),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return parse_json_content(completion_text(response, self.model))

    def analyze_images_json(self, system_prompt: str, user_prompt: str, images: list[str]) -> dict[str, Any]:
        """One request over several images (e.g. webcam snapshots), answered as JSON.

        Walks the vision models in order. No response_format: several free vision models
        reject it, and parse_json_content copes with the looser output.
        """
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        content += [{"type": "image_url", "image_url": {"url": image}} for image in images]
        last_error: Exception | None = None
        for model in self.vision_models:
            if model in self._text_only_models:
                continue
            try:
                response = self.client.with_options(timeout=EVAL_TIMEOUT_SECONDS, max_retries=0).chat.completions.create(
                    model=model,
                    temperature=0.2,
                    max_tokens=MAX_JSON_TOKENS,
                    extra_body=self._reasoning(settings.AI_REASONING_VISION),
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
                )
                result = parse_json_content(completion_text(response, model))
                if isinstance(result, dict):
                    return result
                raise ValueError(f"{model} returned {type(result).__name__}, expected an object")
            except (BadRequestError, NotFoundError) as exc:
                self._text_only_models.add(model)
                last_error = exc
            except (APIError, APITimeoutError, APIConnectionError, EmptyCompletionError, ValueError) as exc:
                last_error = exc
            logger.warning("Vision model %s failed image analysis: %s", model, last_error)
        raise EmptyCompletionError("No vision model could analyze the images") from last_error

    def transcribe(self, audio_bytes: bytes, filename: str, language: str | None = None) -> str:
        # Without the hint Whisper guesses the language per utterance and often mis-detects
        # short Arabic answers as English, returning transliterated nonsense.
        extra = {"language": language} if language else {}
        result = self.client.audio.transcriptions.create(
            model="whisper-1", file=(filename, audio_bytes), **extra
        )
        return result.text

    def converse(
        self, messages: list[dict[str, Any]], image_data_url: str | None, image_caption: str | None = None
    ) -> str:
        if image_data_url and messages and messages[-1]["role"] == "user":
            reply = self._converse_with_image(messages, image_data_url, image_caption)
            if reply is not None:
                return reply
            # No vision model could take the picture. Losing it is far better than losing
            # the turn, so answer from the words alone (and say nothing about an image).
            logger.warning("No vision model available for this turn; answering text-only")
        return self._complete_reply(self.model, list(messages), settings.AI_REASONING_CHAT)

    def _converse_with_image(
        self, messages: list[dict[str, Any]], image_data_url: str, image_caption: str | None
    ) -> str | None:
        text = messages[-1]["content"]
        if image_caption:
            text = f"{image_caption}\n{text}"
        with_image = [
            *messages[:-1],
            {
                "role": "user",
                "content": [{"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": image_data_url}}],
            },
        ]
        for model in self.vision_models:
            if model in self._text_only_models:
                continue
            try:
                return self._complete_reply(model, with_image, settings.AI_REASONING_VISION)
            except (BadRequestError, NotFoundError) as exc:
                # Text-only model: remember it so later turns don't pay for the rejection
                # again (the free quota is 50 requests a day).
                self._text_only_models.add(model)
                logger.warning("Model %s rejected the image input: %s", model, exc)
            except (APIError, APITimeoutError, APIConnectionError, EmptyCompletionError) as exc:
                logger.warning("Vision model %s failed this turn: %s", model, exc)
        return None

    def _complete_reply(self, model: str, messages: list[dict[str, Any]], effort: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            temperature=0.6,
            max_tokens=MAX_REPLY_TOKENS,
            extra_body=self._reasoning(effort),
            messages=messages,
        )
        return completion_text(response, model)

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
                "Offline demo evaluation (no AI provider available): scored from answer length, structure and "
                "technical vocabulary. Configure an OpenRouter or OpenAI API key for a real assessment."
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

    # Canned demo dialogue. This provider cannot understand an answer, so it must not
    # pretend to: it says so out loud rather than silently marching through questions.
    _DEMO_SCRIPT = {
        "Arabic": (
            "[وضع تجريبي - لا يوجد مزوّد ذكاء اصطناعي فعّال (مفتاح مفقود أو رصيد منتهٍ)، "
            "لذلك هذا الردّ آلي ولا يفهم إجابتك]",
            "مرحبًا بك، شكرًا لانضمامك! لنبدأ: حدّثني عن خلفيتك المهنية وما الذي جذبك إلى هذا الدور؟",
            "سؤال رقم {n}: اشرح لي تحديًا تقنيًا واجهته، وكيف قايضت بين الحلول المتاحة؟",
        ),
        "English": (
            "[Demo mode - no working AI provider (missing key or exhausted credits), "
            "so this reply is canned and cannot understand your answer]",
            "Hi, thanks for joining! To start, could you walk me through your background and what drew you to this role?",
            "Question #{n}: describe a technical challenge you faced and the trade-offs you weighed.",
        ),
    }

    @staticmethod
    def _demo_language(messages: list[dict[str, Any]]) -> str:
        system = next((str(m.get("content", "")) for m in messages if m.get("role") == "system"), "")
        return "Arabic" if "in Arabic" in system else "English"

    def converse(
        self, messages: list[dict[str, Any]], image_data_url: str | None, image_caption: str | None = None
    ) -> str:
        turn_count = sum(1 for m in messages if m["role"] == "assistant")
        banner, opening, follow_up = self._DEMO_SCRIPT[self._demo_language(messages)]
        if turn_count == 0:
            return f"{banner} {opening}"
        return f"{banner} {follow_up.format(n=turn_count + 1)}"

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
            vision_model=profile.get("vision_model"),
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
            except (
                RateLimitError,
                APITimeoutError,
                APIConnectionError,
                APIError,
                EmptyCompletionError,
                json.JSONDecodeError,
                ValidationError,
            ) as exc:
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

    def transcribe_audio(self, audio_bytes: bytes, filename: str, language: str | None = None) -> str:
        if self.provider is not None:
            if isinstance(self.provider, OpenAIProvider) and self.provider.supports_audio:
                try:
                    return self.provider.transcribe(audio_bytes, filename, language)
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
                return provider.transcribe(audio_bytes, filename, language)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError) as exc:
                last_error = exc
                logger.warning(
                    "AI profile failed transcription; trying fallback if available. profile_id=%s error=%s",
                    profile["id"],
                    exc,
                )

        raise RuntimeError("Voice transcription failed") from last_error

    def converse(
        self, messages: list[dict[str, Any]], image_data_url: str | None = None, image_caption: str | None = None
    ) -> str:
        if self.provider is not None:
            return self.provider.converse(messages, image_data_url, image_caption)

        profiles = self._ordered_profiles()
        if not profiles:
            return MockLLMProvider().converse(messages, image_data_url)

        last_error: Exception | None = None
        for index, profile in enumerate(profiles):
            try:
                provider = self._build_provider(profile)
                # The first profile already walked every vision model; if it still failed,
                # retrying the same (shared, rate-limited) vision models per profile only
                # adds delay - later profiles answer from the words.
                image = image_data_url if index == 0 else None
                return provider.converse(messages, image, image_caption)
            except (RateLimitError, APITimeoutError, APIConnectionError, APIError, EmptyCompletionError) as exc:
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

    def analyze_images_json(self, system_prompt: str, user_prompt: str, images: list[str]) -> dict[str, Any] | None:
        """Vision analysis over several images, or None when no configured model can do it.

        Unlike the other calls there is no offline fallback: inventing observations about
        a person from pictures nobody looked at would be worse than reporting none.
        """
        providers: list[BaseLLMProvider] = (
            [self.provider] if self.provider is not None else [self._build_provider(p) for p in self._ordered_profiles()[:1]]
        )
        for provider in providers:
            if not isinstance(provider, OpenAIProvider):
                continue
            try:
                return provider.analyze_images_json(system_prompt, user_prompt, images)
            except Exception as exc:
                logger.warning("Image analysis failed: %s", exc)
        return None

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
        try:
            return AnswerEvaluation.model_validate(result)
        except ValidationError:
            # Valid JSON in the wrong shape - common with free models that ignore the schema.
            logger.warning("AI evaluation had an unexpected shape; using the offline evaluator")
            return AnswerEvaluation.model_validate(MockLLMProvider().complete_json(system_prompt, user_prompt))

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
        try:
            questions = result["questions"] if isinstance(result, dict) else result
            return [GeneratedQuestion.model_validate(item) for item in questions]
        except (KeyError, TypeError, ValidationError):
            logger.warning("AI question set had an unexpected shape; using the offline question set")
            fallback = MockLLMProvider().complete_json(system_prompt, user_prompt)
            return [GeneratedQuestion.model_validate(item) for item in fallback["questions"]]
