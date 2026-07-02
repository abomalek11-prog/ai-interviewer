from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobStatus, RoleCategory, Seniority


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    role_category: RoleCategory
    seniority: Seniority
    description: str | None = Field(default=None, max_length=4000)
    duration_minutes: int = Field(default=45, ge=5, le=240)
    task_count: int = Field(default=12, ge=1, le=100)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    status: JobStatus | None = None
    description: str | None = Field(default=None, max_length=4000)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    role_category: RoleCategory
    seniority: Seniority
    status: JobStatus
    description: str | None
    duration_minutes: int
    task_count: int
    created_at: datetime
    updated_at: datetime


class JobWithStats(JobRead):
    candidate_count: int = 0
