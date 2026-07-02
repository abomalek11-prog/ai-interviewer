from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CandidateStatus


class CandidateCreate(BaseModel):
    job_id: str
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    resume_url: str | None = Field(default=None, max_length=500)


class CandidateUpdate(BaseModel):
    status: CandidateStatus | None = None
    resume_url: str | None = Field(default=None, max_length=500)


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    full_name: str
    email: EmailStr
    resume_url: str | None
    status: CandidateStatus
    created_at: datetime
    updated_at: datetime


class CandidateWithJob(CandidateRead):
    job_title: str
    latest_score: int | None = None
