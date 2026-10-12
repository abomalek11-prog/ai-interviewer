from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MessageRole, SessionMode, SessionStatus


class SessionCreate(BaseModel):
    job_id: str
    candidate_id: str
    ai_model_profile_id: str | None = Field(default=None, max_length=80)
    mode: SessionMode = SessionMode.STRUCTURED


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_index: int
    prompt: str
    expected_topics: list[str]
    time_limit_seconds: int


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    score: int
    correctness: int
    depth: int
    clarity: int
    terminology: int
    feedback: str
    strengths: list[str]
    improvements: list[str]


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    transcript: str
    video_url: str | None
    submitted_at: datetime
    evaluation: EvaluationRead | None = None


class AnswerSubmit(BaseModel):
    question_id: str
    transcript: str = Field(min_length=1)
    video_url: str | None = None


class QuestionWithAnswer(QuestionRead):
    answer: AnswerRead | None = None


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: MessageRole
    content: str
    created_at: datetime


class QuestionInsight(BaseModel):
    topic: str
    score: int
    comment: str


class PresenceAnalysis(BaseModel):
    summary: str
    observations: list[str]
    flags: list[str]
    frames_analyzed: int


class SessionEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score: int
    correctness: int
    depth: int
    clarity: int
    terminology: int
    feedback: str
    strengths: list[str]
    improvements: list[str]
    question_breakdown: list[QuestionInsight]
    presence: PresenceAnalysis | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    candidate_id: str
    status: SessionStatus
    mode: SessionMode
    interview_type: str
    difficulty: str
    ai_model_profile_id: str | None
    overall_score: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    questions: list[QuestionWithAnswer] = Field(default_factory=list)
    conversation_messages: list[ConversationMessageRead] = Field(default_factory=list)
    evaluation: SessionEvaluationRead | None = None


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    candidate_name: str
    job_title: str
    status: SessionStatus
    overall_score: int | None
    started_at: datetime | None
    created_at: datetime
