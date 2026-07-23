from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.candidate import Candidate
from app.models.enums import SessionMode, SessionStatus
from app.models.interview import Answer, Evaluation, InterviewSession, Question
from app.models.job import Job
from app.schemas.interview import AnswerSubmit, SessionCreate
from app.services.ai_service import AIService


class InterviewService:
    def __init__(self, db: Session, ai_service: AIService | None = None):
        self.db = db
        self.ai_service = ai_service

    def _ai(self, profile_id: str | None = None) -> AIService:
        return self.ai_service or AIService(preferred_profile_id=profile_id)

    def create_session(self, owner_id: str, payload: SessionCreate) -> InterviewSession | None:
        job = self.db.scalar(select(Job).where(Job.id == payload.job_id, Job.owner_id == owner_id))
        if job is None:
            return None
        candidate = self.db.scalar(
            select(Candidate).where(Candidate.id == payload.candidate_id, Candidate.job_id == job.id)
        )
        if candidate is None:
            return None

        session = InterviewSession(
            job_id=job.id,
            candidate_id=candidate.id,
            difficulty=job.seniority.value,
            mode=payload.mode,
            ai_model_profile_id=payload.ai_model_profile_id or job.ai_model_profile_id,
            status=SessionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )
        self.db.add(session)
        self.db.flush()

        if payload.mode == SessionMode.STRUCTURED:
            generated = self._ai(session.ai_model_profile_id).generate_questions(
                interview_type=session.interview_type,
                difficulty=session.difficulty,
                count=min(job.task_count, 20),
                focus_areas=[job.role_category.value],
            )
            for index, item in enumerate(generated):
                self.db.add(
                    Question(
                        session_id=session.id,
                        order_index=index,
                        prompt=item.prompt,
                        expected_topics=item.expected_topics,
                        time_limit_seconds=item.time_limit_seconds,
                    )
                )

        self.db.commit()
        return self.get_session(owner_id, session.id)

    def get_session(self, owner_id: str, session_id: str) -> InterviewSession | None:
        return self.db.scalar(
            select(InterviewSession)
            .join(Job, Job.id == InterviewSession.job_id)
            .where(InterviewSession.id == session_id, Job.owner_id == owner_id)
            .options(
                selectinload(InterviewSession.questions).selectinload(Question.answer).selectinload(Answer.evaluation),
                selectinload(InterviewSession.conversation_messages),
            )
        )

    def list_sessions(self, owner_id: str, limit: int = 50, candidate_id: str | None = None) -> list[dict]:
        query = (
            select(InterviewSession, Candidate.full_name, Job.title)
            .join(Job, Job.id == InterviewSession.job_id)
            .join(Candidate, Candidate.id == InterviewSession.candidate_id)
            .where(Job.owner_id == owner_id)
            .order_by(InterviewSession.created_at.desc())
            .limit(limit)
        )
        if candidate_id:
            query = query.where(InterviewSession.candidate_id == candidate_id)
        return [
            {"session": session, "candidate_name": candidate_name, "job_title": job_title}
            for session, candidate_name, job_title in self.db.execute(query).all()
        ]

    def submit_answer(self, owner_id: str, session_id: str, payload: AnswerSubmit) -> InterviewSession | None:
        session = self.get_session(owner_id, session_id)
        if session is None:
            return None

        question = next((q for q in session.questions if q.id == payload.question_id), None)
        if question is None:
            return None

        answer = Answer(question_id=question.id, transcript=payload.transcript, video_url=payload.video_url)
        self.db.add(answer)
        self.db.flush()

        evaluation_result = self._ai(session.ai_model_profile_id).evaluate_answer(
            question=question.prompt,
            answer=payload.transcript,
            difficulty=session.difficulty,
            interview_type=session.interview_type,
        )
        self.db.add(
            Evaluation(
                answer_id=answer.id,
                score=evaluation_result.score,
                correctness=evaluation_result.correctness,
                depth=evaluation_result.depth,
                clarity=evaluation_result.clarity,
                terminology=evaluation_result.terminology,
                feedback=evaluation_result.feedback,
                strengths=evaluation_result.strengths,
                improvements=evaluation_result.improvements,
            )
        )
        self.db.commit()

        return self._maybe_complete_session(owner_id, session_id)

    def _maybe_complete_session(self, owner_id: str, session_id: str) -> InterviewSession:
        session = self.get_session(owner_id, session_id)
        answered = [q for q in session.questions if q.answer is not None]
        if len(answered) == len(session.questions) and session.questions:
            scored = [q.answer.evaluation.score for q in answered if q.answer.evaluation]
            session.overall_score = round(sum(scored) / len(scored)) if scored else None
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.now(UTC)
            self.db.add(session)
            self.db.commit()
            return self.get_session(owner_id, session_id)
        return session
