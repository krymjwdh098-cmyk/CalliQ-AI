"""
Candidates API — per-recruiter isolation, batch upload, decisions, ranking.
"""
import os
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import (
    get_db, Candidate, JobDescription, User, BatchJob,
    ChatMessage, CandidateStatus, CandidateCategory, RecruiterDecision
)
from api.deps import get_current_user, require_role
from utils.file_storage import save_uploaded_file, allowed_file
from workers.tasks import dispatch_cv, dispatch_batch

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/candidates", tags=["candidates"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class DecisionUpdate(BaseModel):
    decision: str  # NEEDS_REVIEW | APPROVED | REJECTED
    notes: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


class WhatsAppAction(BaseModel):
    action: str
    custom_message: Optional[str] = None


# ── Serializers ───────────────────────────────────────────────────────────────

def _candidate_summary(c: Candidate) -> dict:
    return {
        "id": c.id,
        "full_name": c.full_name,
        "email": c.email,
        "phone": c.phone,
        "current_position": c.current_position,
        "years_experience": c.years_experience,
        "match_score": c.match_score,
        "ats_score": c.ats_score,
        "recommendation": c.recommendation,
        "status": c.status,
        "category": c.category,
        "recruiter_decision": c.recruiter_decision,
        "rank": c.rank,
        "source": c.source,
        "is_knocked_out": c.is_knocked_out,
        "knockout_flags": c.knockout_flags,
        "flagged": c.flagged,
        "flag_reason": c.flag_reason,
        "location": c.location,
        "job_id": c.job_id,
        "recruiter_id": c.recruiter_id,
        "batch_id": c.batch_id,
        "technical_skills": c.technical_skills,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _candidate_full(c: Candidate) -> dict:
    base = _candidate_summary(c)
    base.update({
        "nationality": c.nationality,
        "linkedin": c.linkedin,
        "github": c.github,
        "portfolio": c.portfolio,
        "companies": c.companies,
        "previous_positions": c.previous_positions,
        "education": c.education,
        "certifications": c.certifications,
        "courses": c.courses,
        "soft_skills": c.soft_skills,
        "languages": c.languages,
        "projects": c.projects,
        "achievements": c.achievements,
        "awards": c.awards,
        "skill_match": c.skill_match,
        "experience_match": c.experience_match,
        "education_match": c.education_match,
        "seniority_match": c.seniority_match,
        "location_match": c.location_match,
        "keyword_match": c.keyword_match,
        "ai_confidence": c.ai_confidence,
        "recommendation_reason": c.recommendation_reason,
        "ai_summary": c.ai_summary,
        "strengths": c.strengths,
        "weaknesses": c.weaknesses,
        "missing_skills": c.missing_skills,
        "missing_certs": c.missing_certs,
        "skill_gap_analysis": c.skill_gap_analysis,
        "ats_issues": c.ats_issues,
        "ats_suggestions": c.ats_suggestions,
        "decision_notes": c.decision_notes,
        "decided_at": c.decided_at.isoformat() if c.decided_at else None,
        "interview_notes": c.interview_notes,
        "interview_scheduled": c.interview_scheduled.isoformat() if c.interview_scheduled else None,
        "last_error": c.last_error,
        "processing_attempts": c.processing_attempts,
        "file_name": c.file_name,
        "analysis": _analysis_out(c.analysis) if c.analysis else None,
        "chat_history": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in c.chat_history
        ],
        "whatsapp_history": [
            {"type": m.message_type, "body": m.body, "status": m.status,
             "created_at": m.created_at.isoformat()}
            for m in c.whatsapp_msgs
        ],
    })
    return base


def _analysis_out(a) -> dict:
    if not a:
        return None
    return {
        "overall_score": a.overall_score,
        "skill_match": a.skill_match,
        "experience_match": a.experience_match,
        "education_match": a.education_match,
        "seniority_match": a.seniority_match,
        "location_match": a.location_match,
        "ats_score": a.ats_score,
        "ai_confidence": a.ai_confidence,
        "matched_skills": a.matched_skills,
        "missing_skills": a.missing_skills,
        "matched_requirements": a.matched_requirements,
        "missing_requirements": a.missing_requirements,
        "score_breakdown": a.score_breakdown,
        "recommendation": a.recommendation,
        "recommendation_reason": a.recommendation_reason,
        "ai_summary": a.ai_summary,
        "strengths": a.strengths,
        "weaknesses": a.weaknesses,
        "skill_gap_analysis": a.skill_gap_analysis,
        "ats_issues": a.ats_issues,
        "ats_suggestions": a.ats_suggestions,
        "category": a.category,
        "rank": a.rank,
        "percentile": a.percentile,
        "llm_provider": a.llm_provider,
        "processing_time_ms": a.processing_time_ms,
    }


# ── Guard: recruiter isolation ────────────────────────────────────────────────

def _get_candidate(candidate_id: int, current_user: User, db: Session) -> Candidate:
    q = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.org_id == current_user.org_id,
    )
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)
    c = q.first()
    if not c:
        raise HTTPException(404, "Candidate not found")
    return c


# ── Upload single CV ──────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_cv(
    cv_file: UploadFile = File(...),
    job_id: Optional[int] = Form(None),
    full_name: str = Form("Unknown"),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    source: str = Form("manual"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not allowed_file(cv_file.filename):
        raise HTTPException(400, "Only PDF, DOCX, JPG, PNG allowed")

    content = await cv_file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 10MB)")

    # Validate job ownership
    if job_id:
        q = db.query(JobDescription).filter(
            JobDescription.id == job_id,
            JobDescription.org_id == current_user.org_id,
        )
        if current_user.role == "recruiter":
            q = q.filter(JobDescription.recruiter_id == current_user.id)
        if not q.first():
            raise HTTPException(404, "Job not found")

    file_path, file_name, file_hash = save_uploaded_file(
        content, cv_file.filename, current_user.org_id,
        cv_file.content_type or "application/pdf",
    )

    candidate = Candidate(
        org_id=current_user.org_id,
        recruiter_id=current_user.id,
        hr_id=current_user.id,
        job_id=job_id,
        full_name=full_name,
        email=email,
        phone=phone,
        source=source,
        file_path=file_path,
        file_name=file_name,
        file_hash=file_hash,
        status=CandidateStatus.QUEUED,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    dispatch_cv(candidate.id)
    return _candidate_summary(candidate)


# ── Bulk upload 20–50 CVs ─────────────────────────────────────────────────────

@router.post("/bulk-upload", status_code=202)
async def bulk_upload(
    files: List[UploadFile] = File(...),
    job_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload 20–50 CVs. Returns batch_id for tracking.
    Processing happens in background with controlled concurrency.
    """
    from core.config import get_settings
    settings = get_settings()

    if len(files) > 100:
        raise HTTPException(400, "Max 100 files per batch")

    # Validate job
    if job_id:
        q = db.query(JobDescription).filter(
            JobDescription.id == job_id,
            JobDescription.org_id == current_user.org_id,
        )
        if current_user.role == "recruiter":
            q = q.filter(JobDescription.recruiter_id == current_user.id)
        if not q.first():
            raise HTTPException(404, "Job not found")

    # Create batch record
    batch = BatchJob(
        org_id=current_user.org_id,
        recruiter_id=current_user.id,
        job_id=job_id,
        total=len(files),
        status="pending",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    candidate_ids = []
    errors = []

    for f in files:
        try:
            if not allowed_file(f.filename):
                errors.append({"file": f.filename, "error": "Invalid file type"})
                batch.failed += 1
                continue

            content = await f.read()
            if len(content) > 10 * 1024 * 1024:
                errors.append({"file": f.filename, "error": "File too large"})
                batch.failed += 1
                continue

            file_path, file_name, file_hash = save_uploaded_file(
                content, f.filename, current_user.org_id,
                f.content_type or "application/pdf",
            )

            candidate = Candidate(
                org_id=current_user.org_id,
                recruiter_id=current_user.id,
                hr_id=current_user.id,
                job_id=job_id,
                batch_id=batch.id,
                full_name=f.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title(),
                source="bulk_upload",
                file_path=file_path,
                file_name=file_name,
                file_hash=file_hash,
                status=CandidateStatus.QUEUED,
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            candidate_ids.append(candidate.id)

        except Exception as e:
            errors.append({"file": f.filename, "error": str(e)[:100]})
            batch.failed += 1

    batch.total = len(candidate_ids) + batch.failed
    batch.error_log = errors
    db.commit()

    # Dispatch batch processing in background
    if candidate_ids:
        dispatch_batch(candidate_ids, batch.id, settings.BATCH_MAX_CONCURRENT)

    return {
        "batch_id": batch.id,
        "total": batch.total,
        "queued": len(candidate_ids),
        "rejected_files": len(errors),
        "errors": errors,
        "status": "processing",
        "track_url": f"/api/v1/candidates/batches/{batch.id}",
    }


@router.get("/batches/{batch_id}")
def get_batch_status(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Track batch processing progress."""
    batch = db.query(BatchJob).filter(
        BatchJob.id == batch_id,
        BatchJob.org_id == current_user.org_id,
    )
    if current_user.role == "recruiter":
        batch = batch.filter(BatchJob.recruiter_id == current_user.id)
    batch = batch.first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    # Live count from candidates
    from sqlalchemy import func
    counts = (
        db.query(Candidate.status, func.count(Candidate.id))
        .filter(Candidate.batch_id == batch_id)
        .group_by(Candidate.status)
        .all()
    )
    status_map = {s: c for s, c in counts}

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total": batch.total,
        "completed": batch.completed,
        "failed": batch.failed,
        "processing": batch.processing,
        "progress_pct": round(
            (batch.completed + batch.failed) / max(batch.total, 1) * 100, 1
        ),
        "status_breakdown": status_map,
        "error_log": batch.error_log or [],
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


@router.get("/batches/")
def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(BatchJob).filter(BatchJob.org_id == current_user.org_id)
    if current_user.role == "recruiter":
        q = q.filter(BatchJob.recruiter_id == current_user.id)
    total = q.count()
    batches = q.order_by(BatchJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            {
                "batch_id": b.id, "status": b.status, "total": b.total,
                "completed": b.completed, "failed": b.failed,
                "job_id": b.job_id,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in batches
        ],
    }


# ── List / Filter ─────────────────────────────────────────────────────────────

@router.get("/")
def list_candidates(
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    recruiter_decision: Optional[str] = Query(None),
    min_score: float = Query(0),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("match_score"),  # match_score | rank | created_at
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Candidate).filter(Candidate.org_id == current_user.org_id)

    # Recruiter isolation
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)

    if job_id:
        q = q.filter(Candidate.job_id == job_id)
    if status:
        q = q.filter(Candidate.status == status)
    if category:
        q = q.filter(Candidate.category == category)
    if recruiter_decision:
        q = q.filter(Candidate.recruiter_decision == recruiter_decision)
    if min_score:
        q = q.filter(Candidate.match_score >= min_score)
    if source:
        q = q.filter(Candidate.source == source)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Candidate.full_name.ilike(like)) |
            (Candidate.email.ilike(like)) |
            (Candidate.current_position.ilike(like))
        )

    total = q.count()

    if sort_by == "rank":
        q = q.order_by(Candidate.rank.asc().nullslast(), Candidate.match_score.desc())
    elif sort_by == "created_at":
        q = q.order_by(Candidate.created_at.desc())
    else:
        q = q.order_by(Candidate.match_score.desc(), Candidate.created_at.desc())

    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [_candidate_summary(c) for c in items],
    }


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _candidate_full(_get_candidate(candidate_id, current_user, db))


# ── Status update ─────────────────────────────────────────────────────────────

@router.patch("/{candidate_id}/status")
def update_status(
    candidate_id: int,
    req: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.status = req.status
    if req.notes:
        c.decision_notes = req.notes
    db.commit()
    return {"id": c.id, "status": c.status}


# ── Recruiter Decision ────────────────────────────────────────────────────────

@router.post("/{candidate_id}/decide")
def make_decision(
    candidate_id: int,
    req: DecisionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recruiter final decision — APPROVED / REJECTED / NEEDS_REVIEW.
    AI recommendations are advisory only; this is the binding decision.
    """
    valid = ("NEEDS_REVIEW", "APPROVED", "REJECTED")
    if req.decision not in valid:
        raise HTTPException(400, f"Decision must be one of {valid}")

    c = _get_candidate(candidate_id, current_user, db)
    old_decision = c.recruiter_decision
    old_status   = c.status

    c.recruiter_decision = req.decision
    c.decision_notes = req.notes
    c.decided_at = datetime.utcnow()
    c.decided_by = current_user.id

    if req.decision == "APPROVED":
        c.status = CandidateStatus.SHORTLISTED
    elif req.decision == "REJECTED":
        c.status = CandidateStatus.REJECTED

    db.commit()

    # Audit log
    try:
        from service.audit import log_action, Actions
        log_action(
            db, org_id=current_user.org_id,
            action=Actions.CANDIDATE_DECISION,
            entity_type="candidate", entity_id=c.id,
            user_id=current_user.id,
            before={"decision": old_decision, "status": old_status},
            after={"decision": c.recruiter_decision, "status": c.status},
            notes=req.notes,
        )
    except Exception:
        pass

    # Webhook event
    try:
        from service.webhook_events import fire_event, Events
        event = Events.CANDIDATE_SHORTLISTED if req.decision == "APPROVED" else (
            Events.CANDIDATE_REJECTED if req.decision == "REJECTED" else None
        )
        if event:
            fire_event(db, current_user.org_id, event, {
                "candidate_id": c.id,
                "candidate_name": c.full_name,
                "job_id": c.job_id,
                "decision": req.decision,
                "decided_by": current_user.name,
            })
    except Exception:
        pass

    return {"id": c.id, "recruiter_decision": c.recruiter_decision, "status": c.status}


@router.post("/{candidate_id}/approve")
def approve(
    candidate_id: int,
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.recruiter_decision = RecruiterDecision.APPROVED
    c.status = CandidateStatus.SHORTLISTED
    c.decided_at = datetime.utcnow()
    c.decided_by = current_user.id
    if notes:
        c.decision_notes = notes
    db.commit()
    return _candidate_summary(c)


@router.post("/{candidate_id}/reject")
def reject(
    candidate_id: int,
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.recruiter_decision = RecruiterDecision.REJECTED
    c.status = CandidateStatus.REJECTED
    c.decided_at = datetime.utcnow()
    c.decided_by = current_user.id
    if notes:
        c.decision_notes = notes
    db.commit()

    # Send WhatsApp notification
    try:
        from service.whatsapp_service import queue_whatsapp_message
        job_title = c.job.title if c.job else "the position"
        queue_whatsapp_message(db, current_user.org_id, c, "reject", job_title)
    except Exception as e:
        logger.warning(f"WA notify failed: {e}")

    return _candidate_summary(c)


@router.post("/{candidate_id}/shortlist")
def shortlist(
    candidate_id: int,
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.recruiter_decision = RecruiterDecision.APPROVED
    c.status = CandidateStatus.SHORTLISTED
    c.decided_at = datetime.utcnow()
    c.decided_by = current_user.id
    if notes:
        c.decision_notes = notes
    db.commit()

    try:
        from service.whatsapp_service import queue_whatsapp_message
        job_title = c.job.title if c.job else "the position"
        queue_whatsapp_message(db, current_user.org_id, c, "shortlist", job_title)
    except Exception as e:
        logger.warning(f"WA notify failed: {e}")

    return _candidate_summary(c)


# ── Reprocess ─────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/reprocess")
def reprocess(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-trigger AI processing. Clears previous scores."""
    c = _get_candidate(candidate_id, current_user, db)
    if not c.file_path or not os.path.exists(c.file_path):
        raise HTTPException(400, "CV file not found on disk")

    # Reset scores for clean reprocessing
    c.status = CandidateStatus.QUEUED
    c.match_score = 0
    c.skill_match = 0
    c.experience_match = 0
    c.education_match = 0
    c.recommendation = None
    c.is_knocked_out = False
    c.knockout_flags = []
    db.commit()

    dispatch_cv(candidate_id)
    return {"id": c.id, "status": "requeued", "message": "Processing restarted"}


@router.get("/{candidate_id}/processing-status")
def processing_status(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    return {
        "candidate_id": c.id,
        "status": c.status,
        "match_score": c.match_score,
        "category": c.category,
        "recommendation": c.recommendation,
        "rank": c.rank,
        "processing_attempts": c.processing_attempts,
        "last_error": c.last_error,
    }


# ── Flags ─────────────────────────────────────────────────────────────────────

@router.patch("/{candidate_id}/flag")
def flag(
    candidate_id: int,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.flagged = True
    c.flag_reason = reason
    db.commit()
    return {"id": c.id, "flagged": True, "flag_reason": reason}


@router.patch("/{candidate_id}/unflag")
def unflag(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    c.flagged = False
    c.flag_reason = None
    db.commit()
    return {"id": c.id, "flagged": False}


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/chat")
def chat(
    candidate_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import json
    from service.llm_router import llm_complete, _resolve_provider, DISPATCH

    c = _get_candidate(candidate_id, current_user, db)

    # Load last 10 messages for context
    history = db.query(ChatMessage).filter(
        ChatMessage.candidate_id == c.id
    ).order_by(ChatMessage.created_at.asc()).limit(20).all()

    db.add(ChatMessage(
        candidate_id=c.id, org_id=current_user.org_id,
        role="user", content=req.message,
    ))
    db.commit()

    system = (
        "You are an expert HR assistant helping a recruiter evaluate candidates.\n"
        "Candidate Profile:\n"
        f"- Name: {c.full_name}\n"
        f"- Position: {c.current_position or 'N/A'}\n"
        f"- Experience: {c.years_experience} years\n"
        f"- Location: {c.location or 'N/A'}\n"
        f"- Skills: {json.dumps(c.technical_skills or {})}\n"
        f"- Match Score: {c.match_score}/100\n"
        f"- Category: {c.category or 'N/A'}\n"
        f"- AI Summary: {c.ai_summary or 'N/A'}\n"
        f"- Strengths: {c.strengths or []}\n"
        f"- Weaknesses: {c.weaknesses or []}\n"
        f"- Missing Skills: {c.missing_skills or []}\n"
        f"- Education: {json.dumps(c.education or [])}\n\n"
        "Answer questions concisely and professionally. "
        "Base answers strictly on the candidate data above."
    )

    # Build multi-turn conversation for providers that support it
    provider = _resolve_provider(agent="chat")
    if provider in ("openai", "anthropic", "groq") and history:
        messages = []
        for msg in history[-10:]:  # last 10 messages
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": req.message})

        try:
            reply = _chat_with_history(provider, system, messages)
        except Exception:
            reply = llm_complete(system=system, user=req.message, max_tokens=800, agent="chat")
    else:
        # For single-turn providers, include recent context in user message
        history_text = ""
        if history:
            recent = history[-6:]
            history_text = "\n\nPrevious conversation:\n" + "\n".join(
                f"{'Recruiter' if m.role == 'user' else 'Assistant'}: {m.content}"
                for m in recent
            ) + "\n\n"
        user_msg = f"{history_text}Recruiter: {req.message}"
        reply = llm_complete(system=system, user=user_msg, max_tokens=800, agent="chat")

    db.add(ChatMessage(
        candidate_id=c.id, org_id=current_user.org_id,
        role="assistant", content=reply,
    ))
    db.commit()
    return {"reply": reply, "history_length": len(history) + 2}


def _chat_with_history(provider: str, system: str, messages: list) -> str:
    """Send multi-turn conversation to provider."""
    from core.config import get_settings
    from service.llm_router import _get_groq_key
    s = get_settings()

    if provider == "groq":
        import importlib
        groq = importlib.import_module("groq")
        client = groq.Groq(api_key=_get_groq_key(), timeout=60.0)
        resp = client.chat.completions.create(
            model=s.GROQ_MODEL,
            messages=[{"role": "system", "content": system}] + messages,
            temperature=0.3,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()

    if provider == "openai":
        import importlib
        openai = importlib.import_module("openai")
        client = openai.OpenAI(api_key=s.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=s.OPENAI_MODEL,
            messages=[{"role": "system", "content": system}] + messages,
            temperature=0.3, max_tokens=800,
        )
        return resp.choices[0].message.content.strip()

    if provider == "anthropic":
        import importlib
        anthropic = importlib.import_module("anthropic")
        client = anthropic.Anthropic(api_key=s.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=s.ANTHROPIC_MODEL, max_tokens=800,
            system=system, messages=messages, temperature=0.3,
        )
        return resp.content[0].text.strip()

    raise ValueError(f"Multi-turn not supported for {provider}")


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@router.post("/{candidate_id}/whatsapp")
def send_whatsapp(
    candidate_id: int,
    req: WhatsAppAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from service.whatsapp_service import queue_whatsapp_message
    c = _get_candidate(candidate_id, current_user, db)
    job_title = c.job.title if c.job else "the position"
    msg = queue_whatsapp_message(
        db, current_user.org_id, c,
        message_type=req.action,
        job_title=job_title,
        custom_body=req.custom_message or "",
    )
    return {"message_id": msg.id, "status": msg.status}


# ── Download CV ───────────────────────────────────────────────────────────────

@router.get("/{candidate_id}/download")
def download_cv(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    if not c.file_path or not os.path.exists(c.file_path):
        raise HTTPException(404, "File not found")
    return FileResponse(c.file_path, filename=c.file_name or "cv.pdf")


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = _get_candidate(candidate_id, current_user, db)
    if c.file_path and os.path.exists(c.file_path):
        try:
            os.remove(c.file_path)
        except Exception:
            pass
    db.delete(c)
    db.commit()


# ── Bulk analyze (retry Queued/Error candidates) ──────────────────────────────

@router.post("/analyze-pending")
def analyze_pending(
    job_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-trigger processing for all Queued/Error candidates.
    Uses batch processing with controlled concurrency.
    """
    from core.config import get_settings
    settings = get_settings()

    q = db.query(Candidate).filter(
        Candidate.org_id == current_user.org_id,
        Candidate.status.in_([CandidateStatus.QUEUED, CandidateStatus.ERROR]),
    )
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)
    if job_id:
        q = q.filter(Candidate.job_id == job_id)

    candidates = q.all()
    if not candidates:
        return {"message": "No candidates to process", "total": 0}

    # Create a batch for tracking
    batch = BatchJob(
        org_id=current_user.org_id,
        recruiter_id=current_user.id,
        job_id=job_id,
        total=len(candidates),
        status="pending",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    ids = [c.id for c in candidates]
    for c in candidates:
        c.batch_id = batch.id
    db.commit()

    dispatch_batch(ids, batch.id, settings.BATCH_MAX_CONCURRENT)

    return {
        "batch_id": batch.id,
        "total": len(ids),
        "status": "processing",
        "track_url": f"/api/v1/candidates/batches/{batch.id}",
    }


# ── Pipeline Movement ─────────────────────────────────────────────────────────

class PipelineMoveRequest(BaseModel):
    stage: str
    notes: Optional[str] = None


class InterviewRequest(BaseModel):
    scheduled_at: str          # ISO datetime
    interview_type: str = "video"   # phone|video|onsite|technical
    location: Optional[str] = None
    link: Optional[str] = None
    duration_mins: int = 60
    notes: Optional[str] = None


class OfferRequest(BaseModel):
    amount: float
    currency: str = "EGP"
    deadline_days: int = 7
    notes: Optional[str] = None


@router.post("/{candidate_id}/pipeline-move")
def move_pipeline_stage(
    candidate_id: int,
    req: PipelineMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move candidate to a different pipeline stage with history tracking."""
    from models.database import PIPELINE_ORDER
    from datetime import datetime

    valid_stages = [
        "Under Review", "Screening", "Phone Interview", "Technical",
        "Final Interview", "Shortlisted", "Offer Sent", "Hired",
        "Rejected", "Withdrew", "Ghosted",
    ]
    if req.stage not in valid_stages:
        raise HTTPException(400, f"Invalid stage. Choose from: {valid_stages}")

    c = _get_candidate(candidate_id, current_user, db)
    now = datetime.utcnow()
    old_stage = c.pipeline_stage or c.status

    # Update pipeline history
    history = list(c.pipeline_history or [])
    if history:
        # Close previous stage
        history[-1]["exited_at"] = now.isoformat()
        entered = history[-1].get("entered_at")
        if entered:
            delta = now - datetime.fromisoformat(entered)
            history[-1]["days"] = round(delta.total_seconds() / 86400, 1)

    history.append({
        "stage": req.stage,
        "entered_at": now.isoformat(),
        "exited_at": None,
        "days": None,
        "notes": req.notes,
        "moved_by": current_user.name,
    })
    c.pipeline_history = history
    c.pipeline_stage = req.stage
    c.pipeline_stage_entered = now
    c.status = req.stage

    # Set timestamp fields
    if req.stage == "Shortlisted" and not c.shortlisted_at:
        c.shortlisted_at = now
    elif req.stage == "Hired" and not c.hired_at:
        c.hired_at = now
    elif req.stage == "Rejected" and not c.rejected_at:
        c.rejected_at = now
    elif req.stage == "Under Review" and not c.first_reviewed_at:
        c.first_reviewed_at = now

    db.commit()

    # Audit
    try:
        from service.audit import log_action, Actions
        log_action(db, org_id=current_user.org_id, action=Actions.CANDIDATE_STATUS,
                   entity_type="candidate", entity_id=c.id, user_id=current_user.id,
                   before={"stage": old_stage}, after={"stage": req.stage}, notes=req.notes)
    except Exception:
        pass

    # Webhook
    try:
        from service.webhook_events import fire_event, Events
        evt_map = {
            "Shortlisted": Events.CANDIDATE_SHORTLISTED,
            "Hired": Events.CANDIDATE_HIRED,
            "Rejected": Events.CANDIDATE_REJECTED,
        }
        if req.stage in evt_map:
            fire_event(db, current_user.org_id, evt_map[req.stage], {
                "candidate_id": c.id, "stage": req.stage, "job_id": c.job_id,
            })
    except Exception:
        pass

    return {
        "id": c.id,
        "stage": c.pipeline_stage,
        "history": c.pipeline_history,
        "message": f"Moved to {req.stage}",
    }


@router.post("/{candidate_id}/schedule-interview")
def schedule_interview(
    candidate_id: int,
    req: InterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schedule an interview and auto-move candidate to the right pipeline stage."""
    from datetime import datetime

    c = _get_candidate(candidate_id, current_user, db)

    try:
        scheduled_dt = datetime.fromisoformat(req.scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "Invalid datetime format. Use ISO 8601.")

    c.interview_scheduled = scheduled_dt
    c.interview_type = req.interview_type
    c.interview_location = req.location
    c.interview_link = req.link
    c.interview_duration_mins = req.duration_mins
    if req.notes:
        c.interview_notes = (c.interview_notes or "") + f"\n[{datetime.utcnow().date()}] {req.notes}"

    # Auto-advance pipeline stage
    stage_map = {
        "phone": "Phone Interview",
        "video": "Phone Interview",
        "technical": "Technical",
        "onsite": "Final Interview",
        "final": "Final Interview",
    }
    new_stage = stage_map.get(req.interview_type.lower(), "Phone Interview")
    c.status = new_stage
    c.pipeline_stage = new_stage
    c.pipeline_stage_entered = datetime.utcnow()

    history = list(c.pipeline_history or [])
    history.append({
        "stage": new_stage,
        "entered_at": datetime.utcnow().isoformat(),
        "exited_at": None,
        "days": None,
        "notes": f"Interview scheduled for {req.scheduled_at}",
        "moved_by": current_user.name,
    })
    c.pipeline_history = history
    db.commit()

    # Send WhatsApp notification to candidate
    try:
        from service.whatsapp_service import queue_whatsapp_message
        job_title = c.job.title if c.job else "the position"
        interview_msg = (
            f"Interview Scheduled!\n"
            f"Position: {job_title}\n"
            f"Date: {scheduled_dt.strftime('%A, %B %d at %I:%M %p')}\n"
            f"Type: {req.interview_type.title()}\n"
        )
        if req.link:
            interview_msg += f"Link: {req.link}\n"
        if req.location:
            interview_msg += f"Location: {req.location}\n"

        queue_whatsapp_message(
            db=db, org_id=current_user.org_id, candidate=c,
            message_type="custom", job_title=job_title, custom_body=interview_msg,
        )
    except Exception:
        pass

    return {
        "id": c.id,
        "interview_scheduled": scheduled_dt.isoformat(),
        "interview_type": req.interview_type,
        "stage": c.pipeline_stage,
        "message": "Interview scheduled and candidate notified",
    }


@router.post("/{candidate_id}/send-offer")
def send_offer(
    candidate_id: int,
    req: OfferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send an offer to a candidate and move to Offer Sent stage."""
    from datetime import datetime, timedelta

    c = _get_candidate(candidate_id, current_user, db)
    now = datetime.utcnow()
    deadline = now + timedelta(days=req.deadline_days)

    c.offer_amount = req.amount
    c.offer_currency = req.currency
    c.offer_sent_at = now
    c.offer_deadline = deadline
    c.offer_accepted = None
    c.status = "Offer Sent"
    c.pipeline_stage = "Offer Sent"
    c.pipeline_stage_entered = now

    history = list(c.pipeline_history or [])
    history.append({
        "stage": "Offer Sent",
        "entered_at": now.isoformat(),
        "exited_at": None,
        "days": None,
        "notes": f"Offer: {req.amount} {req.currency}, deadline {deadline.date()}",
        "moved_by": current_user.name,
    })
    c.pipeline_history = history
    db.commit()

    # Notify candidate via WhatsApp
    try:
        from service.whatsapp_service import queue_whatsapp_message
        job_title = c.job.title if c.job else "the position"
        offer_msg = (
            f"We're pleased to extend you an offer for {job_title}!\n"
            f"Offer Amount: {req.amount:,.0f} {req.currency}/month\n"
            f"Please respond by: {deadline.strftime('%B %d, %Y')}\n"
            f"Reply YES to accept or contact us for details."
        )
        queue_whatsapp_message(
            db=db, org_id=current_user.org_id, candidate=c,
            message_type="custom", job_title=job_title, custom_body=offer_msg,
        )
    except Exception:
        pass

    return {
        "id": c.id,
        "offer_amount": req.amount,
        "offer_currency": req.currency,
        "offer_deadline": deadline.isoformat(),
        "stage": "Offer Sent",
        "message": "Offer sent and candidate notified",
    }


@router.post("/{candidate_id}/offer-response")
def record_offer_response(
    candidate_id: int,
    accepted: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record candidate's offer acceptance/rejection."""
    from datetime import datetime

    c = _get_candidate(candidate_id, current_user, db)
    c.offer_accepted = accepted
    c.status = "Hired" if accepted else "Rejected"
    c.pipeline_stage = c.status
    c.pipeline_stage_entered = datetime.utcnow()
    if accepted:
        c.hired_at = datetime.utcnow()
    else:
        c.rejected_at = datetime.utcnow()
    db.commit()

    return {"id": c.id, "offer_accepted": accepted, "status": c.status}


@router.get("/{candidate_id}/timeline")
def get_candidate_timeline(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full activity timeline for a candidate."""
    from models.database import ChatMessage
    c = _get_candidate(candidate_id, current_user, db)

    events = []

    # Application
    events.append({"type": "applied", "label": "Applied", "at": c.applied_at.isoformat() if c.applied_at else None})

    # Pipeline history
    for h in (c.pipeline_history or []):
        events.append({"type": "stage_change", "label": f"Moved to {h['stage']}", "at": h.get("entered_at"), "by": h.get("moved_by"), "notes": h.get("notes")})

    # Interview
    if c.interview_scheduled:
        events.append({"type": "interview", "label": f"{(c.interview_type or 'Interview').title()} scheduled", "at": c.interview_scheduled.isoformat()})

    # Offer
    if c.offer_sent_at:
        events.append({"type": "offer", "label": f"Offer sent: {c.offer_amount} {c.offer_currency}", "at": c.offer_sent_at.isoformat()})

    # Sort by date
    events = sorted([e for e in events if e.get("at")], key=lambda x: x["at"])

    return {
        "candidate_id": c.id,
        "candidate_name": c.full_name,
        "current_stage": c.pipeline_stage or c.status,
        "days_in_pipeline": _days_since(c.applied_at),
        "timeline": events,
        "pipeline_history": c.pipeline_history or [],
    }


def _days_since(dt) -> Optional[int]:
    if not dt:
        return None
    from datetime import datetime
    return (datetime.utcnow() - dt).days
