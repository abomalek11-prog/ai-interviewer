"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("title", sa.String(120)),
        sa.Column("bio", sa.Text()),
        sa.Column("profile_picture_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "password_reset_otps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_otps_user_id", "password_reset_otps", ["user_id"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column(
            "role_category",
            sa.String(20),
            sa.CheckConstraint(
                "role_category IN ('Frontend','Backend','Fullstack','Mobile','DevOps')",
                name="ck_jobs_role_category",
            ),
            nullable=False,
        ),
        sa.Column(
            "seniority",
            sa.String(20),
            sa.CheckConstraint("seniority IN ('Junior','Mid-level','Senior')", name="ck_jobs_seniority"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint(
                "status IN ('draft','active','paused','closed')", name="ck_jobs_status"
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("description", sa.Text()),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("task_count", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_owner_id", "jobs", ["owner_id"])

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("resume_url", sa.String(500)),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint(
                "status IN ('new','interviewing','shortlisted','rejected','hired')",
                name="ck_candidates_status",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_candidates_job_id", "candidates", ["job_id"])
    op.create_index("ix_candidates_email", "candidates", ["email"])

    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint(
                "status IN ('pending','in_progress','completed','abandoned')",
                name="ck_interview_sessions_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("interview_type", sa.String(40), nullable=False, server_default="technical"),
        sa.Column("difficulty", sa.String(40), nullable=False),
        sa.Column("overall_score", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_interview_sessions_job_id", "interview_sessions", ["job_id"])
    op.create_index("ix_interview_sessions_candidate_id", "interview_sessions", ["candidate_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("expected_topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_questions_session_id", "questions", ["session_id"])

    op.create_table(
        "answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "question_id",
            sa.String(36),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("video_url", sa.String(500)),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"])

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "answer_id", sa.String(36), sa.ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, unique=True
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("correctness", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("clarity", sa.Integer(), nullable=False),
        sa.Column("terminology", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("improvements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evaluations_answer_id", "evaluations", ["answer_id"])


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("interview_sessions")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("password_reset_otps")
    op.drop_table("users")
