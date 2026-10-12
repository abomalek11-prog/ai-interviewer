import logging
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import MessageRole, SessionStatus
from app.models.interview import ConversationMessage, InterviewSession, SessionEvaluation
from app.services.ai_service import AIService

logger = logging.getLogger("app.live_interview")


# BCP-47 tag from the client -> (name for the prompt, ISO-639-1 code for Whisper).
_LANGUAGES: dict[str, tuple[str, str]] = {
    "ar": ("Arabic", "ar"),
    "en": ("English", "en"),
}
_DEFAULT_LANGUAGE = ("English", "en")


def _clamp_score(value: object) -> int:
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return 0


def _as_string_list(value: object) -> list[str]:
    """Accept a proper list, or the single newline/semicolon-separated string some models return."""
    if isinstance(value, list):
        items = [str(item) for item in value]
    elif isinstance(value, str):
        items = re.split(r"\n|;|؛", value)
    else:
        return []
    cleaned = (re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", item).strip() for item in items)
    return [item for item in cleaned if item]


def _as_breakdown(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    breakdown = []
    for item in value:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or item.get("question") or "").strip()
        comment = str(item.get("comment") or item.get("feedback") or "").strip()
        if topic or comment:
            breakdown.append({"topic": topic, "score": _clamp_score(item.get("score")), "comment": comment})
    return breakdown


def to_spoken_text(text: str) -> str:
    """Strip markdown the model adds despite instructions; TTS would read the symbols aloud."""
    text = re.sub(r"(\*\*|__|`)", "", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)  # *emphasis*
    text = re.sub(r"^\s{0,3}(#{1,6}|[-*•]|\d+[.)])\s+", "", text, flags=re.MULTILINE)  # headings, bullets
    return re.sub(r"\s*\n\s*", " ", text).strip()


def resolve_language(tag: str | None) -> tuple[str, str]:
    """Map a BCP-47 tag such as 'ar-SA' to the language name and Whisper code."""
    if not tag:
        return _DEFAULT_LANGUAGE
    return _LANGUAGES.get(tag.split("-", 1)[0].lower(), _DEFAULT_LANGUAGE)


class LiveInterviewService:
    def __init__(self, db: Session, session: InterviewSession, language_tag: str | None = None):
        self.db = db
        self.session = session
        self.ai_service = AIService(preferred_profile_id=session.ai_model_profile_id)
        self.language_name, self.language_code = resolve_language(language_tag)

    def set_language(self, language_tag: str) -> None:
        """Switch the interview language mid-conversation (candidate changed the selector)."""
        self.language_name, self.language_code = resolve_language(language_tag)

    def _system_prompt(self) -> str:
        job = self.session.job
        candidate = self.session.candidate
        return (
            "You are a friendly, sharp senior interviewer conducting a live spoken technical interview. "
            f"Candidate: {candidate.full_name}. Role: {job.seniority.value} {job.role_category.value} "
            f'- "{job.title}". Difficulty: {self.session.difficulty}. '
            f"Conduct the entire interview in {self.language_name}, including your very first greeting. "
            f"Always reply in {self.language_name} even if the candidate uses another language. "
            "A turn may come with a snapshot: either the candidate's webcam, or their shared screen. "
            "If it shows code, a diagram or a whiteboard, read it carefully and treat it as part of their answer - "
            "point out bugs, ask about specific lines or design choices you can see. If it is the webcam, react "
            "naturally only if relevant and keep the focus on the interview. Ask one question at a time, listen to "
            "the answer, then ask a natural, adaptive follow-up or move to a new topic. Keep responses concise "
            "(2-4 sentences), conversational, and spoken aloud - no markdown, no lists.\n"
            "Turn-taking rules - follow them strictly:\n"
            "- Not every utterance is an answer. Greetings, filler, throat-clearing, audio glitches "
            "or a request to repeat are NOT answers.\n"
            "- If the candidate ASKS you something - to clarify or rephrase the question, about the "
            "role, the process, or a genuine technical aside - answer it directly and helpfully FIRST, "
            "then return to the question still pending. Never ignore a real question, and never respond "
            "to one by simply repeating yourself.\n"
            "- If they drift off-topic, react naturally in a sentence, then steer back to the interview.\n"
            "- If the candidate did not actually answer, do NOT advance to a new question: re-ask the "
            "pending one rephrased in your own words rather than repeated verbatim.\n"
            "- If the answer is partial or vague, probe the same topic instead of advancing.\n"
            "- Only move to a new question once the current one has genuinely been answered.\n"
            "Stay warm and human throughout - never robotic, never repetitive."
        )

    def _history_messages(self) -> list[dict]:
        messages = [{"role": "system", "content": self._system_prompt()}]
        for msg in self.session.conversation_messages:
            role = "assistant" if msg.role == MessageRole.AI else "user"
            messages.append({"role": role, "content": msg.content})
        return messages

    def _persist(self, role: MessageRole, content: str) -> ConversationMessage:
        message = ConversationMessage(session_id=self.session.id, role=role, content=content)
        self.db.add(message)
        self.db.flush()
        self.session.conversation_messages.append(message)
        return message

    def opening_message(self) -> str:
        messages = self._history_messages()
        messages.append(
            {
                "role": "user",
                "content": "Greet the candidate warmly, briefly introduce the interview, and ask your first question.",
            }
        )
        ai_text = to_spoken_text(self.ai_service.converse(messages))
        self._persist(MessageRole.AI, ai_text)
        self.db.commit()
        return ai_text

    def handle_turn(self, audio_bytes: bytes, frame_data_url: str | None) -> dict[str, str | None]:
        try:
            candidate_text = self.ai_service.transcribe_audio(audio_bytes, "turn.webm", self.language_code)
        except RuntimeError:
            # No transcription provider configured. Do NOT fabricate a placeholder answer -
            # that poisons the transcript and the final evaluation. Tell the client instead.
            return {
                "candidate_text": None,
                "ai_text": None,
                "error": "Server-side voice transcription is not configured. "
                "Use a browser that supports speech recognition (Chrome/Edge), or configure an OpenAI API key "
                "for server-side transcription (OpenRouter has no speech endpoint).",
            }
        return self._respond_to(candidate_text, frame_data_url)

    def handle_text_turn(self, candidate_text: str, frame_data_url: str | None) -> dict[str, str | None]:
        return self._respond_to(candidate_text, frame_data_url)

    def _respond_to(self, candidate_text: str, frame_data_url: str | None) -> dict[str, str | None]:
        candidate_text = candidate_text.strip()
        if not candidate_text:
            return {"candidate_text": None, "ai_text": None, "error": "Empty answer - please try speaking again."}

        self._persist(MessageRole.CANDIDATE, candidate_text)

        messages = self._history_messages()
        ai_text = to_spoken_text(self.ai_service.converse(messages, image_data_url=frame_data_url))
        self._persist(MessageRole.AI, ai_text)
        self.db.commit()

        return {"candidate_text": candidate_text, "ai_text": ai_text, "error": None}

    def synthesize(self, text: str) -> bytes:
        return self.ai_service.synthesize_speech(text)

    def finish(self) -> InterviewSession:
        candidate_messages = [
            msg for msg in self.session.conversation_messages if msg.role == MessageRole.CANDIDATE
        ]
        transcript_lines = [
            f"{'Interviewer' if msg.role == MessageRole.AI else 'Candidate'}: {msg.content}"
            for msg in self.session.conversation_messages
        ]
        transcript = "\n".join(transcript_lines) or "No conversation took place."

        evaluation: SessionEvaluation | None = None
        if not candidate_messages:
            # Nothing was actually answered - do not ask the model to invent a score.
            score = 0
        else:
            # Keep the words "questions"/"generate" out of this prompt: the offline
            # MockLLMProvider keys on them to decide it is producing a question set.
            system_prompt = (
                "You are a strict, consistent senior technical interviewer evaluating a completed live interview. "
                "Evaluate ONLY what the candidate actually said - ignore the interviewer's own statements. "
                "Return only valid JSON with exactly these keys:\n"
                "- score, correctness, depth, clarity, terminology: integers from 0 to 100\n"
                "- feedback: a 3-5 sentence overall assessment citing specific things the candidate said\n"
                "- strengths: JSON array of short strings, one strength per item\n"
                "- improvements: JSON array of short, actionable strings, one per item\n"
                "- question_breakdown: JSON array with one object per interviewer question the candidate "
                "engaged with, in order: {\"topic\": short name of what was asked, \"score\": 0-100 integer, "
                "\"comment\": 1-2 sentences on how well that specific answer held up}\n"
                "Scoring rubric (apply strictly):\n"
                "- 0-20: no substantive answers, off-topic, or one-word replies\n"
                "- 21-45: superficial answers, vague generalities, little technical content\n"
                "- 46-65: partially correct answers with some detail but notable gaps\n"
                "- 66-85: solid, mostly correct answers with concrete detail and reasoning\n"
                "- 86-100: exceptional depth, precise terminology, examples and trade-offs\n"
                "Base every sub-score on concrete evidence from the transcript. Do not reward answer length alone.\n"
                "Greetings, filler and requests to repeat are not answers - do not score them as content.\n"
                f"The interview was conducted in {self.language_name}. Judge the substance, never the language "
                f"itself, and write every text field (feedback, strengths, improvements, topic, comment) "
                f"in {self.language_name}."
            )
            user_prompt = (
                f"Interview type: live conversation\n"
                f"Difficulty: {self.session.difficulty}\n"
                f"Number of candidate answers: {len(candidate_messages)}\n"
                f"Transcript:\n{transcript}"
            )

            try:
                result = self.ai_service._complete_json_with_fallback(system_prompt, user_prompt)
                score = self._stable_overall_score(result)
                evaluation = self._build_evaluation(result, score)
            except Exception:
                logger.exception("Final evaluation failed for session_id=%s", self.session.id)
                score = None

        if evaluation is not None:
            # Replaces any earlier evaluation (delete-orphan) if the session is finished twice.
            self.session.evaluation = evaluation
        self.session.overall_score = score
        self.session.status = SessionStatus.COMPLETED
        self.session.completed_at = datetime.now(UTC)
        self.db.add(self.session)
        self.db.commit()
        self.db.refresh(self.session)
        return self.session

    @staticmethod
    def _build_evaluation(result: object, score: int | None) -> SessionEvaluation | None:
        """Turn the model's JSON into a SessionEvaluation, tolerating the shapes models drift into.

        Seen in practice from free models: list fields returned as one long string,
        numbers as strings, breakdown items missing keys.
        """
        if not isinstance(result, dict) or score is None:
            return None
        return SessionEvaluation(
            score=score,
            correctness=_clamp_score(result.get("correctness")),
            depth=_clamp_score(result.get("depth")),
            clarity=_clamp_score(result.get("clarity")),
            terminology=_clamp_score(result.get("terminology")),
            feedback=str(result.get("feedback") or "").strip(),
            strengths=_as_string_list(result.get("strengths")),
            improvements=_as_string_list(result.get("improvements")),
            question_breakdown=_as_breakdown(result.get("question_breakdown")),
        )

    @staticmethod
    def _stable_overall_score(result: object) -> int | None:
        """Derive the overall score as a weighted blend of the sub-scores.

        A single model-emitted number varies a lot between runs; anchoring it to the
        four rubric dimensions makes repeated evaluations far more consistent.
        """
        if not isinstance(result, dict):
            return None

        def _num(key: str) -> int | None:
            value = result.get(key)
            try:
                return max(0, min(100, int(value)))
            except (TypeError, ValueError):
                return None

        weights = {"correctness": 0.35, "depth": 0.25, "clarity": 0.2, "terminology": 0.2}
        parts = {key: _num(key) for key in weights}
        if all(v is not None for v in parts.values()):
            weighted = sum(parts[key] * weight for key, weight in weights.items())
            model_score = _num("score")
            if model_score is not None:
                # Blend, but let the rubric dimensions dominate.
                return round(0.7 * weighted + 0.3 * model_score)
            return round(weighted)
        return _num("score")
