"""
Audit Log — records every action in the system.
Mandatory for HR systems for legal/compliance reasons.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Session

from models.database import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # What happened
    action       = Column(String(100), nullable=False)   # e.g. "candidate.approved"
    entity_type  = Column(String(50))                    # "candidate" | "job" | "user"
    entity_id    = Column(Integer)                       # ID of the affected record

    # Before/After for changes
    before       = Column(JSON)
    after        = Column(JSON)

    # Context
    ip_address   = Column(String(50))
    user_agent   = Column(String(300))
    notes        = Column(Text)

    created_at   = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_audit_org_action", "org_id", "action"),
        Index("ix_audit_org_entity", "org_id", "entity_type", "entity_id"),
        Index("ix_audit_org_user", "org_id", "user_id"),
    )


def log_action(
    db: Session,
    org_id: int,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    user_id: int = None,
    before: dict = None,
    after: dict = None,
    notes: str = None,
    ip_address: str = None,
):
    """Write an audit log entry. Never raises — logs errors silently."""
    try:
        entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            notes=notes,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass


# ── Common action constants ───────────────────────────────────────────────────

class Actions:
    # Auth
    LOGIN           = "auth.login"
    LOGOUT          = "auth.logout"
    REGISTER        = "auth.register"
    PASSWORD_RESET  = "auth.password_reset"

    # Candidates
    CANDIDATE_UPLOAD    = "candidate.upload"
    CANDIDATE_APPROVED  = "candidate.approved"
    CANDIDATE_REJECTED  = "candidate.rejected"
    CANDIDATE_SHORTLIST = "candidate.shortlisted"
    CANDIDATE_STATUS    = "candidate.status_changed"
    CANDIDATE_DELETED   = "candidate.deleted"
    CANDIDATE_REPROCESS = "candidate.reprocessed"
    CANDIDATE_FLAGGED   = "candidate.flagged"
    CANDIDATE_DECISION  = "candidate.decision_made"

    # Jobs
    JOB_CREATED   = "job.created"
    JOB_UPDATED   = "job.updated"
    JOB_DELETED   = "job.deleted"
    JOB_TOGGLED   = "job.active_toggled"
    RULE_ADDED    = "job.rule_added"
    RULE_DELETED  = "job.rule_deleted"

    # Users
    USER_CREATED  = "user.created"
    USER_UPDATED  = "user.updated"
    USER_DELETED  = "user.deleted"

    # Batch
    BATCH_CREATED   = "batch.created"
    BATCH_COMPLETED = "batch.completed"
