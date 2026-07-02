from enum import StrEnum


class JobStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class Seniority(StrEnum):
    JUNIOR = "Junior"
    MID = "Mid-level"
    SENIOR = "Senior"


class RoleCategory(StrEnum):
    FRONTEND = "Frontend"
    BACKEND = "Backend"
    FULLSTACK = "Fullstack"
    MOBILE = "Mobile"
    DEVOPS = "DevOps"


class CandidateStatus(StrEnum):
    NEW = "new"
    INTERVIEWING = "interviewing"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class SessionStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
