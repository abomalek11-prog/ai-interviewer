from pydantic import BaseModel, Field


class AnswerEvaluationRequest(BaseModel):
    question: str = Field(min_length=5)
    answer: str = Field(min_length=1)
    difficulty: str = "mid-level"
    interview_type: str = "technical"


class AnswerEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    correctness: int = Field(ge=0, le=100)
    depth: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    terminology: int = Field(ge=0, le=100)
    feedback: str
    strengths: list[str]
    improvements: list[str]


class QuestionGenerationRequest(BaseModel):
    interview_type: str = "technical"
    difficulty: str = "mid-level"
    count: int = Field(default=5, ge=1, le=20)
    focus_areas: list[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    prompt: str
    expected_topics: list[str]
    time_limit_seconds: int = 180
