"""
Dashboard — aggregated analytics per org + per recruiter.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import get_db, Candidate, JobDescription, BatchJob, User
from api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.org_id
    today = datetime.utcnow().date()

    q = db.query(Candidate).filter(Candidate.org_id == org_id)
    # Recruiters see only their candidates
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)

    total       = q.count()
    today_count = q.filter(func.date(Candidate.created_at) == today).count()
    queued      = q.filter(Candidate.status == "Queued").count()
    processing  = q.filter(Candidate.status == "Processing").count()
    pending     = q.filter(Candidate.status == "Under Review").count()
    shortlisted = q.filter(Candidate.status == "Shortlisted").count()
    interview   = q.filter(Candidate.status == "Interview").count()
    hired       = q.filter(Candidate.status == "Hired").count()
    rejected    = q.filter(Candidate.status == "Rejected").count()
    duplicates  = q.filter(Candidate.status == "Duplicate").count()
    knocked_out = q.filter(Candidate.is_knocked_out == True).count()
    errors      = q.filter(Candidate.status == "Error").count()

    # Category breakdown
    categories = (
        db.query(Candidate.category, func.count(Candidate.id))
        .filter(Candidate.org_id == org_id)
        .group_by(Candidate.category)
        .all()
    )

    # Decision breakdown
    decisions = (
        db.query(Candidate.recruiter_decision, func.count(Candidate.id))
        .filter(Candidate.org_id == org_id)
        .group_by(Candidate.recruiter_decision)
        .all()
    )

    avg_score = db.query(func.avg(Candidate.match_score)).filter(
        Candidate.org_id == org_id, Candidate.match_score > 0
    )
    if current_user.role == "recruiter":
        avg_score = avg_score.filter(Candidate.recruiter_id == current_user.id)
    avg_score = round(float(avg_score.scalar() or 0), 1)

    # Source breakdown
    sources = (
        db.query(Candidate.source, func.count(Candidate.id))
        .filter(Candidate.org_id == org_id)
        .group_by(Candidate.source)
        .all()
    )

    # 7-day trend
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        cnt = q.filter(func.date(Candidate.created_at) == day).count()
        trend.append({"date": day.isoformat(), "count": cnt})

    # Top skills
    skill_freq: dict[str, int] = {}
    all_c = q.filter(Candidate.technical_skills != None).limit(200).all()
    for c in all_c:
        if isinstance(c.technical_skills, dict):
            for skills in c.technical_skills.values():
                for s in (skills or []):
                    skill_freq[s] = skill_freq.get(s, 0) + 1
    top_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # Jobs
    jq = db.query(JobDescription).filter(JobDescription.org_id == org_id)
    if current_user.role == "recruiter":
        jq = jq.filter(JobDescription.recruiter_id == current_user.id)
    active_jobs = jq.filter(JobDescription.is_active == True).count()

    # Batches
    bq = db.query(BatchJob).filter(BatchJob.org_id == org_id)
    if current_user.role == "recruiter":
        bq = bq.filter(BatchJob.recruiter_id == current_user.id)
    active_batches = bq.filter(BatchJob.status.in_(["pending", "processing"])).count()

    return {
        "total_candidates": total,
        "today": today_count,
        "queued": queued,
        "processing": processing,
        "pending": pending,
        "shortlisted": shortlisted,
        "interview": interview,
        "hired": hired,
        "rejected": rejected,
        "duplicates": duplicates,
        "knocked_out": knocked_out,
        "errors": errors,
        "avg_match_score": avg_score,
        "active_jobs": active_jobs,
        "active_batches": active_batches,
        "category_breakdown": {cat: cnt for cat, cnt in categories},
        "decision_breakdown": {dec: cnt for dec, cnt in decisions},
        "source_breakdown": {s: c for s, c in sources},
        "daily_trend": trend,
        "top_skills": [{"skill": k, "count": v} for k, v in top_skills],
        "hiring_funnel": {
            "Applied": total,
            "Under Review": pending,
            "Shortlisted": shortlisted,
            "Interview": interview,
            "Hired": hired,
        },
    }


@router.get("/ai-config")
def get_ai_config(current_user: User = Depends(get_current_user)):
    from service.llm_router import get_active_providers
    from core.config import get_settings
    s = get_settings()
    return {
        "agents": get_active_providers(),
        "models": {
            "groq": s.GROQ_MODEL if s.GROQ_API_KEY else None,
            "openai": s.OPENAI_MODEL if s.OPENAI_API_KEY else None,
            "anthropic": s.ANTHROPIC_MODEL if s.ANTHROPIC_API_KEY else None,
            "gemini": s.GEMINI_MODEL if s.GEMINI_API_KEY else None,
            "ollama": s.OLLAMA_MODEL,
        },
        "keys_configured": {
            "groq": bool(s.GROQ_API_KEY),
            "openai": bool(s.OPENAI_API_KEY),
            "anthropic": bool(s.ANTHROPIC_API_KEY),
            "gemini": bool(s.GEMINI_API_KEY),
            "ollama": True,
        },
    }


@router.get("/audit-log")
def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Audit log — admin/owner only."""
    if current_user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin required")

    from service.audit import AuditLog
    q = db.query(AuditLog).filter(AuditLog.org_id == current_user.org_id)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)

    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "before": e.before,
                "after": e.after,
                "notes": e.notes,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
    }
def recruiter_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-recruiter stats — for admins/owners to see all recruiters."""
    if current_user.role not in ("admin", "owner"):
        raise Exception("Admin required")

    recruiters = db.query(User).filter(
        User.org_id == current_user.org_id,
        User.is_active == True,
    ).all()

    result = []
    for r in recruiters:
        cands = db.query(func.count(Candidate.id)).filter(
            Candidate.recruiter_id == r.id
        ).scalar()
        jobs = db.query(func.count(JobDescription.id)).filter(
            JobDescription.recruiter_id == r.id
        ).scalar()
        shortlisted = db.query(func.count(Candidate.id)).filter(
            Candidate.recruiter_id == r.id,
            Candidate.status == "Shortlisted",
        ).scalar()
        result.append({
            "recruiter_id": r.id,
            "name": r.name,
            "email": r.email,
            "role": r.role,
            "total_candidates": cands,
            "total_jobs": jobs,
            "shortlisted": shortlisted,
        })
    return result


@router.get("/pipeline-analytics")
def pipeline_analytics(
    job_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full pipeline analytics:
    - Funnel conversion per stage
    - Avg days in each stage
    - Time-to-hire per job
    - Source quality (conversion rate per source)
    - Offer acceptance rate
    """
    from models.database import Candidate, PIPELINE_ORDER
    from sqlalchemy import func

    org_id = current_user.org_id
    q = db.query(Candidate).filter(Candidate.org_id == org_id)
    if job_id:
        q = q.filter(Candidate.job_id == job_id)

    all_candidates = q.all()
    total = len(all_candidates)

    # ── Funnel conversion ──────────────────────────────────────
    funnel = {}
    for stage in PIPELINE_ORDER:
        count = sum(1 for c in all_candidates if (c.pipeline_stage or c.status) == stage
                    or _reached_stage(c, stage))
        funnel[stage] = {
            "count": count,
            "pct_of_total": round(count / max(total, 1) * 100, 1),
        }

    hired_count = sum(1 for c in all_candidates if c.status == "Hired")
    funnel["conversion_rate"] = round(hired_count / max(total, 1) * 100, 1)

    # ── Stage duration averages ────────────────────────────────
    stage_durations = {}
    for c in all_candidates:
        for h in (c.pipeline_history or []):
            stage = h.get("stage")
            days = h.get("days")
            if stage and days is not None:
                if stage not in stage_durations:
                    stage_durations[stage] = []
                stage_durations[stage].append(days)

    avg_stage_days = {
        stage: round(sum(vals) / len(vals), 1)
        for stage, vals in stage_durations.items()
        if vals
    }

    # ── Time to hire ───────────────────────────────────────────
    time_to_hire_vals = []
    for c in all_candidates:
        if c.hired_at and c.applied_at:
            days = (c.hired_at - c.applied_at).days
            time_to_hire_vals.append(days)

    avg_time_to_hire = round(sum(time_to_hire_vals) / len(time_to_hire_vals), 1) if time_to_hire_vals else None

    # ── Source quality ─────────────────────────────────────────
    sources = {}
    for c in all_candidates:
        src = c.source or "unknown"
        if src not in sources:
            sources[src] = {"total": 0, "shortlisted": 0, "hired": 0, "rejected": 0}
        sources[src]["total"] += 1
        if c.status in ("Shortlisted", "Offer Sent", "Hired"):
            sources[src]["shortlisted"] += 1
        if c.status == "Hired":
            sources[src]["hired"] += 1
        if c.status == "Rejected":
            sources[src]["rejected"] += 1

    source_quality = {}
    for src, data in sources.items():
        source_quality[src] = {
            **data,
            "shortlist_rate": round(data["shortlisted"] / max(data["total"], 1) * 100, 1),
            "hire_rate": round(data["hired"] / max(data["total"], 1) * 100, 1),
        }

    # ── Offer acceptance rate ──────────────────────────────────
    offers_sent = sum(1 for c in all_candidates if c.offer_sent_at)
    offers_accepted = sum(1 for c in all_candidates if c.offer_accepted is True)
    offer_acceptance_rate = round(offers_accepted / max(offers_sent, 1) * 100, 1)

    # ── Salary match distribution ──────────────────────────────
    salary_match_dist = {"within_range": 0, "above_range": 0, "below_range": 0, "unknown": 0}
    for c in all_candidates:
        key = c.salary_expectation_match or "unknown"
        salary_match_dist[key] = salary_match_dist.get(key, 0) + 1

    return {
        "total_candidates": total,
        "funnel": funnel,
        "avg_stage_days": avg_stage_days,
        "avg_time_to_hire_days": avg_time_to_hire,
        "source_quality": source_quality,
        "offer_stats": {
            "sent": offers_sent,
            "accepted": offers_accepted,
            "acceptance_rate_pct": offer_acceptance_rate,
        },
        "salary_match_distribution": salary_match_dist,
    }


def _reached_stage(candidate, stage: str) -> bool:
    """Check if candidate ever reached or passed a given pipeline stage."""
    from models.database import PIPELINE_ORDER
    if stage not in PIPELINE_ORDER:
        return False
    stage_idx = PIPELINE_ORDER.index(stage)
    current = candidate.pipeline_stage or candidate.status
    if current in PIPELINE_ORDER:
        current_idx = PIPELINE_ORDER.index(current)
        if current_idx >= stage_idx:
            return True
    # Check history
    for h in (candidate.pipeline_history or []):
        if h.get("stage") == stage:
            return True
    return False


@router.get("/time-to-hire")
def time_to_hire_report(
    days_back: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-job time-to-hire breakdown for the last N days."""
    from models.database import Candidate, JobDescription
    from datetime import datetime, timedelta

    org_id = current_user.org_id
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    hired = db.query(Candidate).filter(
        Candidate.org_id == org_id,
        Candidate.status == "Hired",
        Candidate.hired_at >= cutoff,
    ).all()

    by_job = {}
    for c in hired:
        if not c.applied_at or not c.hired_at:
            continue
        days = (c.hired_at - c.applied_at).days
        jid = c.job_id or "no_job"
        if jid not in by_job:
            job = c.job
            by_job[jid] = {
                "job_id": jid,
                "job_title": job.title if job else "N/A",
                "hired_count": 0,
                "days_list": [],
            }
        by_job[jid]["hired_count"] += 1
        by_job[jid]["days_list"].append(days)

    result = []
    for jid, data in by_job.items():
        dl = data["days_list"]
        result.append({
            "job_id": data["job_id"],
            "job_title": data["job_title"],
            "hired_count": data["hired_count"],
            "avg_days": round(sum(dl) / len(dl), 1),
            "min_days": min(dl),
            "max_days": max(dl),
        })

    result.sort(key=lambda x: x["avg_days"])
    overall = [d for r in result for d in r.get("days_list", [])] if result else []

    return {
        "period_days": days_back,
        "total_hired": sum(r["hired_count"] for r in result),
        "overall_avg_days": round(sum(overall) / len(overall), 1) if overall else None,
        "by_job": [{k: v for k, v in r.items() if k != "days_list"} for r in result],
    }
