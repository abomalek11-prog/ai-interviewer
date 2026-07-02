from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SessionStatus


class SessionCreate(BaseModel):
    job_id: str
    candidate_id: str


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


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    candidate_id: str
    status: SessionStatus
    interview_type: str
    difficulty: str
    overall_score: int | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    questions: list[QuestionWithAnswer] = Field(default_factory=list)


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_name: str
    job_title: str
    status: SessionStatus
    overall_score: int | None
    started_at: datetime | None
    created_at: datetime
