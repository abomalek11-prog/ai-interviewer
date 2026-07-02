from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus, RoleCategory, Seniority


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    role_category: Mapped[RoleCategory] = mapped_column(Enum(RoleCategory, native_enum=False, length=20), nullable=False)
    seniority: Mapped[Seniority] = mapped_column(Enum(Seniority, native_enum=False, length=20), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, native_enum=False, length=20), default=JobStatus.DRAFT, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(default=45, nullable=False)
    task_count: Mapped[int] = mapped_column(default=12, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="jobs")  # noqa: F821
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="job", cascade="all, delete-orphan")  # noqa: F821
    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="job", cascade="all, delete-orphan")  # noqa: F821
