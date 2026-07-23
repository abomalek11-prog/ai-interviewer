from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import MessageRole, SessionStatus
from app.models.interview import ConversationMessage, InterviewSession
from app.services.ai_service import AIService


class LiveInterviewService:
    def __init__(self, db: Session, session: InterviewSession):
        self.db = db
        self.session = session
        self.ai_service = AIService(preferred_profile_id=session.ai_model_profile_id)

    def _system_prompt(self) -> str:
        job = self.session.job
        candidate = self.session.candidate
        return (
            "You are a friendly, sharp senior interviewer conducting a live spoken technical interview. "
            f"Candidate: {candidate.full_name}. Role: {job.seniority.value} {job.role_category.value} "
            f'- "{job.title}". Difficulty: {self.session.difficulty}. '
            "You can see periodic webcam snapshots of the candidate when provided - react naturally to what "
            "you see if relevant, but keep the focus on the interview. Ask one question at a time, listen to "
            "the answer, then ask a natural, adaptive follow-up or move to a new topic. Keep responses concise "
            "(2-4 sentences), conversational, and spoken aloud - no markdown, no lists."
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
        ai_text = self.ai_service.converse(messages)
        self._persist(MessageRole.AI, ai_text)
        self.db.commit()
        return ai_text

    def handle_turn(self, audio_bytes: bytes, frame_data_url: str | None) -> dict[str, str | None]:
        try:
            candidate_text = self.ai_service.transcribe_audio(audio_bytes, "turn.webm")
        except RuntimeError:
            # No transcription provider configured. Do NOT fabricate a placeholder answer -
            # that poisons the transcript and the final evaluation. Tell the client instead.
            return {
                "candidate_text": None,
                "ai_text": None,
                "error": "Server-side voice transcription is not configured. "
                "Use a browser that supports speech recognition (Chrome/Edge) or configure an OpenAI API key.",
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
        ai_text = self.ai_service.converse(messages, image_data_url=frame_data_url)
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

        if not candidate_messages:
            # Nothing was actually answered - do not ask the model to invent a score.
            score = 0
        else:
            system_prompt = (
                "You are a strict, consistent senior technical interviewer evaluating a completed live interview. "
                "Evaluate ONLY what the candidate actually said - ignore the interviewer's own statements. "
                "Return only valid JSON with keys: score, correctness, depth, clarity, terminology, feedback, "
                "strengths, improvements. All numeric fields must be integers from 0 to 100.\n"
                "Scoring rubric (apply strictly):\n"
                "- 0-20: no substantive answers, off-topic, or one-word replies\n"
                "- 21-45: superficial answers, vague generalities, little technical content\n"
                "- 46-65: partially correct answers with some detail but notable gaps\n"
                "- 66-85: solid, mostly correct answers with concrete detail and reasoning\n"
                "- 86-100: exceptional depth, precise terminology, examples and trade-offs\n"
                "Base every sub-score on concrete evidence from the transcript. Do not reward answer length alone."
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
            except Exception:
                score = None

        self.session.overall_score = score
        self.session.status = SessionStatus.COMPLETED
        self.session.completed_at = datetime.now(UTC)
        self.db.add(self.session)
        self.db.commit()
        self.db.refresh(self.session)
        return self.session

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
