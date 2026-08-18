"""
TalentAI Database Models — Multi-Tenant, Multi-Recruiter SaaS
Full isolation: org → recruiter → job → application → candidate
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, JSON, Index, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import enum

from core.config import get_settings

settings = get_settings()
Base = declarative_base()
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10 if "sqlite" not in settings.DATABASE_URL else 1,
    max_overflow=20 if "sqlite" not in settings.DATABASE_URL else 0,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models that have tables so Base.metadata knows about them
    from service.audit import AuditLog  # noqa
    from service.webhook_events import WebhookEndpoint, WebhookDelivery  # noqa
    from api.auth_extended import RefreshToken, PasswordResetToken  # noqa
    Base.metadata.create_all(bind=engine)


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    VIEWER = "viewer"


class CandidateStatus(str, enum.Enum):
    # Processing states
    QUEUED          = "Queued"
    PROCESSING      = "Processing"
    ERROR           = "Error"
    DUPLICATE       = "Duplicate"
    KNOCKOUT_FAILED = "Knockout Failed"
    # ATS Pipeline funnel
    UNDER_REVIEW    = "Under Review"
    SCREENING       = "Screening"
    PHONE_INTERVIEW = "Phone Interview"
    TECHNICAL       = "Technical"
    FINAL_INTERVIEW = "Final Interview"
    SHORTLISTED     = "Shortlisted"
    OFFER_SENT      = "Offer Sent"
    HIRED           = "Hired"
    # Terminal
    REJECTED        = "Rejected"
    WITHDREW        = "Withdrew"
    GHOSTED         = "Ghosted"
    # Legacy compat
    INTERVIEW       = "Interview"
    APPROVED        = "Approved"


PIPELINE_ORDER = [
    "Under Review", "Screening", "Phone Interview",
    "Technical", "Final Interview", "Shortlisted",
    "Offer Sent", "Hired",
]


class CandidateCategory(str, enum.Enum):
    STRONG_MATCH = "STRONG_MATCH"
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    KNOCKOUT_FAILED = "KNOCKOUT_FAILED"


class RecruiterDecision(str, enum.Enum):
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class BatchStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ── Organization (Tenant) ─────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(255), nullable=False)
    slug                = Column(String(100), unique=True, index=True)
    plan                = Column(String(50), default="trial")
    is_active           = Column(Boolean, default=True)
    subscription_status = Column(String(50), default="trialing")
    trial_ends_at       = Column(DateTime)
    billing_email       = Column(String(255))
    whatsapp_phone_id   = Column(String(100))
    whatsapp_token      = Column(Text)
    email_inbox         = Column(String(255))
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users       = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    jobs        = relationship("JobDescription", back_populates="organization", cascade="all, delete-orphan")
    candidates  = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")
    batches     = relationship("BatchJob", back_populates="organization", cascade="all, delete-orphan")


# ── User (Recruiter) ──────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    name            = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(50), default=UserRole.RECRUITER)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    organization    = relationship("Organization", back_populates="users")
    jobs            = relationship("JobDescription", back_populates="recruiter",
                                   foreign_keys="JobDescription.recruiter_id")
    candidates      = relationship("Candidate", back_populates="recruiter",
                                   foreign_keys="Candidate.recruiter_id")
    batch_jobs      = relationship("BatchJob", back_populates="recruiter")


# ── JobDescription ────────────────────────────────────────────────────────────

class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    recruiter_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Keep hr_id as alias for backward compat
    hr_id           = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    title           = Column(String(255), nullable=False)
    company         = Column(String(255))
    description     = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)
    nice_to_have    = Column(JSON, default=list)
    min_experience  = Column(Integer, default=0)
    max_experience  = Column(Integer, nullable=True)
    education_req   = Column(String(255))
    location_req    = Column(String(255))
    salary_min      = Column(Integer)
    salary_max      = Column(Integer)
    hr_email        = Column(String(255))
    is_active       = Column(Boolean, default=True)

    # Public link
    apply_url_token = Column(String(100), unique=True, index=True)
    whatsapp_job_id = Column(String(50), index=True)
    email_alias     = Column(String(255))

    # Score thresholds (per-job override)
    score_strong_match    = Column(Float, default=80.0)
    score_potential_match = Column(Float, default=60.0)
    score_weak_match      = Column(Float, default=40.0)

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization    = relationship("Organization", back_populates="jobs")
    recruiter       = relationship("User", foreign_keys=[recruiter_id], back_populates="jobs")
    candidates      = relationship("Candidate", back_populates="job")
    knockout_rules  = relationship("KnockoutRule", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_org_recruiter", "org_id", "recruiter_id"),
        Index("ix_jobs_org_active", "org_id", "is_active"),
    )


# ── KnockoutRule ──────────────────────────────────────────────────────────────

class KnockoutRule(Base):
    __tablename__ = "knockout_rules"

    id          = Column(Integer, primary_key=True, index=True)
    job_id      = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    rule_type   = Column(String(50))   # location|experience|education|language|skill|custom
    field       = Column(String(100))
    operator    = Column(String(20))   # gte|lte|eq|contains|not_contains
    value       = Column(String(500))
    action      = Column(String(20), default="flag")   # flag | auto_reject
    description = Column(String(500))
    is_active   = Column(Boolean, default=True)
    is_mandatory = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobDescription", back_populates="knockout_rules")


# ── Candidate ─────────────────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    recruiter_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    hr_id           = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    job_id          = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True, index=True)
    batch_id        = Column(Integer, ForeignKey("batch_jobs.id"), nullable=True, index=True)

    # Personal Info
    full_name       = Column(String(255), nullable=False)
    email           = Column(String(255), index=True)
    phone           = Column(String(50))
    whatsapp_phone  = Column(String(50))
    location        = Column(String(255))
    nationality     = Column(String(100))
    linkedin        = Column(String(500))
    github          = Column(String(500))
    portfolio       = Column(String(500))

    # Experience
    current_position    = Column(String(255))
    previous_positions  = Column(JSON, default=list)
    companies           = Column(JSON, default=list)
    years_experience    = Column(Float, default=0)

    # Education
    education           = Column(JSON, default=list)
    certifications      = Column(JSON, default=list)
    courses             = Column(JSON, default=list)

    # Skills
    technical_skills    = Column(JSON, default=dict)
    soft_skills         = Column(JSON, default=list)
    languages           = Column(JSON, default=list)
    projects            = Column(JSON, default=list)
    achievements        = Column(JSON, default=list)
    awards              = Column(JSON, default=list)

    # AI Scores — STRICTLY per job/application, never global
    match_score         = Column(Float, default=0)
    ats_score           = Column(Float, default=0)
    skill_match         = Column(Float, default=0)
    experience_match    = Column(Float, default=0)
    education_match     = Column(Float, default=0)
    keyword_match       = Column(Float, default=0)
    seniority_match     = Column(Float, default=0)
    location_match      = Column(Float, default=0)
    salary_match        = Column(Float, default=0)
    ai_confidence       = Column(Float, default=0)

    # AI Analysis
    recommendation          = Column(String(50))
    recommendation_reason   = Column(Text)
    strengths               = Column(JSON, default=list)
    weaknesses              = Column(JSON, default=list)
    missing_skills          = Column(JSON, default=list)
    missing_certs           = Column(JSON, default=list)
    skill_gap_analysis      = Column(Text)
    ats_issues              = Column(JSON, default=list)
    ats_suggestions         = Column(JSON, default=list)
    ai_summary              = Column(Text)

    # Ranking (per job)
    rank                = Column(Integer, nullable=True)

    # Category (auto from score)
    category            = Column(String(50), default=CandidateCategory.NEEDS_REVIEW)

    # Recruiter Decision
    recruiter_decision  = Column(String(50), default=RecruiterDecision.NEEDS_REVIEW)
    decision_notes      = Column(Text)
    decided_at          = Column(DateTime)
    decided_by          = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Status & Flags
    status              = Column(String(50), default=CandidateStatus.QUEUED)
    flagged             = Column(Boolean, default=False)
    flag_reason         = Column(String(500))
    is_knocked_out      = Column(Boolean, default=False)
    knockout_flags      = Column(JSON, default=list)

    # Duplicate detection
    duplicate_of        = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    file_hash           = Column(String(64))  # SHA256 of CV file — indexed via table_args

    # Source tracking
    source              = Column(String(50), default="manual")

    # File
    raw_text            = Column(Text)
    file_path           = Column(String(500))
    file_name           = Column(String(255))
    file_storage_type   = Column(String(20), default="local")

    # Processing
    processing_attempts = Column(Integer, default=0)
    last_error          = Column(Text)

    # Candidate preferences (extracted from CV)
    salary_expectation       = Column(Float, nullable=True)
    salary_currency          = Column(String(10), nullable=True)
    notice_period_days       = Column(Integer, nullable=True)
    availability_date        = Column(String(50), nullable=True)
    remote_preference        = Column(String(50), nullable=True)
    salary_expectation_match = Column(String(30), nullable=True)

    # Pipeline tracking
    pipeline_stage         = Column(String(50), nullable=True)
    pipeline_stage_entered = Column(DateTime, nullable=True)
    pipeline_history       = Column(JSON, default=list)

    # Interview
    interview_notes         = Column(Text)
    interview_scheduled     = Column(DateTime)
    interview_type          = Column(String(50), nullable=True)
    interview_location      = Column(String(255), nullable=True)
    interview_link          = Column(String(500), nullable=True)
    interview_duration_mins = Column(Integer, nullable=True)
    interview_result        = Column(String(50), nullable=True)

    # Offer
    offer_amount    = Column(Float, nullable=True)
    offer_currency  = Column(String(10), nullable=True)
    offer_sent_at   = Column(DateTime, nullable=True)
    offer_deadline  = Column(DateTime, nullable=True)
    offer_accepted  = Column(Boolean, nullable=True)

    # Time tracking
    applied_at        = Column(DateTime, default=datetime.utcnow)
    first_reviewed_at = Column(DateTime, nullable=True)
    shortlisted_at    = Column(DateTime, nullable=True)
    hired_at          = Column(DateTime, nullable=True)
    rejected_at       = Column(DateTime, nullable=True)

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization    = relationship("Organization", back_populates="candidates")
    recruiter       = relationship("User", foreign_keys=[recruiter_id], back_populates="candidates")
    job             = relationship("JobDescription", back_populates="candidates")
    chat_history    = relationship("ChatMessage", back_populates="candidate", cascade="all, delete-orphan")
    whatsapp_msgs   = relationship("WhatsAppMessage", back_populates="candidate", cascade="all, delete-orphan")
    analysis        = relationship("CandidateAnalysis", back_populates="candidate",
                                   uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_candidates_org_status", "org_id", "status"),
        Index("ix_candidates_org_score", "org_id", "match_score"),
        Index("ix_candidates_org_job", "org_id", "job_id"),
        Index("ix_candidates_recruiter_job", "recruiter_id", "job_id"),
        Index("ix_candidates_file_hash", "org_id", "file_hash"),
    )


# ── CandidateAnalysis — Separate table for score breakdown ───────────────────

class CandidateAnalysis(Base):
    """
    Stores detailed analysis result per candidate per job.
    Strictly bound to candidate_id + job_id — never reused across jobs.
    """
    __tablename__ = "candidate_analyses"

    id              = Column(Integer, primary_key=True, index=True)
    candidate_id    = Column(Integer, ForeignKey("candidates.id"), nullable=False, unique=True)
    job_id          = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False, index=True)
    recruiter_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Full score breakdown
    overall_score       = Column(Float, default=0)
    skill_match         = Column(Float, default=0)
    experience_match    = Column(Float, default=0)
    education_match     = Column(Float, default=0)
    seniority_match     = Column(Float, default=0)
    location_match      = Column(Float, default=0)
    keyword_match       = Column(Float, default=0)
    ats_score           = Column(Float, default=0)
    ai_confidence       = Column(Float, default=0)

    # Matched vs Missing
    matched_skills      = Column(JSON, default=list)
    missing_skills      = Column(JSON, default=list)
    matched_requirements = Column(JSON, default=list)
    missing_requirements = Column(JSON, default=list)

    # Score breakdown per dimension
    score_breakdown     = Column(JSON, default=dict)

    # AI outputs
    recommendation      = Column(String(50))
    recommendation_reason = Column(Text)
    ai_summary          = Column(Text)
    strengths           = Column(JSON, default=list)
    weaknesses          = Column(JSON, default=list)
    skill_gap_analysis  = Column(Text)
    ats_issues          = Column(JSON, default=list)
    ats_suggestions     = Column(JSON, default=list)

    # Category
    category            = Column(String(50))

    # Ranking position (computed after all candidates processed)
    rank                = Column(Integer, nullable=True)
    percentile          = Column(Float, nullable=True)

    llm_provider        = Column(String(50))
    processing_time_ms  = Column(Integer)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate   = relationship("Candidate", back_populates="analysis")
    job         = relationship("JobDescription")


# ── BatchJob ──────────────────────────────────────────────────────────────────

class BatchJob(Base):
    """Tracks batch CV processing for 20-50 CVs"""
    __tablename__ = "batch_jobs"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    recruiter_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id          = Column(Integer, ForeignKey("job_descriptions.id"), nullable=True, index=True)

    status          = Column(String(20), default=BatchStatus.PENDING)
    total           = Column(Integer, default=0)
    completed       = Column(Integer, default=0)
    failed          = Column(Integer, default=0)
    processing      = Column(Integer, default=0)

    error_log       = Column(JSON, default=list)

    started_at      = Column(DateTime)
    completed_at    = Column(DateTime)
    created_at      = Column(DateTime, default=datetime.utcnow)

    organization    = relationship("Organization", back_populates="batches")
    recruiter       = relationship("User", back_populates="batch_jobs")
    candidates      = relationship("Candidate", back_populates=None,
                                   foreign_keys="Candidate.batch_id",
                                   primaryjoin="BatchJob.id == Candidate.batch_id")

    __table_args__ = (
        Index("ix_batches_org_recruiter", "org_id", "recruiter_id"),
    )


# ── WhatsAppMessage ───────────────────────────────────────────────────────────

class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    candidate_id    = Column(Integer, ForeignKey("candidates.id"), nullable=True, index=True)
    wa_message_id   = Column(String(255), unique=True, index=True, nullable=True)
    direction       = Column(String(10))
    message_type    = Column(String(20))
    body            = Column(Text)
    to_phone        = Column(String(50))
    status          = Column(String(30), default="pending")
    delivery_status = Column(String(30), default="sent")
    retry_count     = Column(Integer, default=0)
    error_message   = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="whatsapp_msgs")


# ── ChatMessage ───────────────────────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id           = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    role         = Column(String(20), nullable=False)
    content      = Column(Text, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="chat_history")


# ── UsageLog ──────────────────────────────────────────────────────────────────

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id            = Column(Integer, primary_key=True, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    recruiter_id  = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action        = Column(String(50))
    llm_provider  = Column(String(50))
    llm_model     = Column(String(100))
    tokens_used   = Column(Integer, default=0)
    processing_ms = Column(Integer, default=0)
    success       = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow, index=True)
