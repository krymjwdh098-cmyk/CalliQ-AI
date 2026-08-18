"""
Jobs API — strict per-recruiter isolation.
Recruiters can only see/modify their own jobs.
Admins/owners can see all jobs in the org.
"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, JobDescription, KnockoutRule, Candidate, User
from api.deps import get_current_user, require_role
from core.config import get_settings
from utils.file_storage import generate_qr_base64

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


# ── Schemas ───────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    company: Optional[str] = None
    description: str
    required_skills: list[str] = []
    nice_to_have: list[str] = []
    min_experience: int = 0
    max_experience: Optional[int] = None
    education_req: Optional[str] = None
    location_req: Optional[str] = None
    hr_email: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    score_strong_match: float = 80.0
    score_potential_match: float = 60.0
    score_weak_match: float = 40.0


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    nice_to_have: Optional[list[str]] = None
    min_experience: Optional[int] = None
    education_req: Optional[str] = None
    location_req: Optional[str] = None
    hr_email: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    is_active: Optional[bool] = None
    score_strong_match: Optional[float] = None
    score_potential_match: Optional[float] = None
    score_weak_match: Optional[float] = None


class KnockoutRuleCreate(BaseModel):
    rule_type: str
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[str] = None
    action: str = "flag"
    description: str
    is_mandatory: bool = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_url(token: str) -> str:
    return f"{settings.BASE_URL}/apply/{token}"


def _job_out(job: JobDescription, db: Session, recruiter_id: Optional[int] = None) -> dict:
    q = db.query(Candidate).filter(Candidate.job_id == job.id)
    return {
        "id": job.id,
        "org_id": job.org_id,
        "recruiter_id": job.recruiter_id,
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "required_skills": job.required_skills or [],
        "nice_to_have": job.nice_to_have or [],
        "min_experience": job.min_experience,
        "max_experience": job.max_experience,
        "education_req": job.education_req,
        "location_req": job.location_req,
        "hr_email": job.hr_email,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "is_active": job.is_active,
        "apply_url": _apply_url(job.apply_url_token or ""),
        "score_strong_match": job.score_strong_match,
        "score_potential_match": job.score_potential_match,
        "score_weak_match": job.score_weak_match,
        "candidate_count": q.count(),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _get_job(job_id: int, current_user: User, db: Session) -> JobDescription:
    """
    Get job with recruiter isolation:
    - Recruiters can only access their own jobs
    - Admins/owners can access all org jobs
    """
    q = db.query(JobDescription).filter(
        JobDescription.id == job_id,
        JobDescription.org_id == current_user.org_id,
    )
    if current_user.role == "recruiter":
        q = q.filter(JobDescription.recruiter_id == current_user.id)
    job = q.first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def list_jobs(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(JobDescription).filter(JobDescription.org_id == current_user.org_id)
    # Recruiter isolation
    if current_user.role == "recruiter":
        q = q.filter(JobDescription.recruiter_id == current_user.id)
    if active_only:
        q = q.filter(JobDescription.is_active == True)
    jobs = q.order_by(JobDescription.created_at.desc()).all()
    return [_job_out(j, db) for j in jobs]


@router.post("/", status_code=201)
def create_job(
    req: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner", "recruiter")),
):
    token = secrets.token_urlsafe(32)
    job_num = db.query(JobDescription).filter(
        JobDescription.org_id == current_user.org_id
    ).count() + 1
    org_slug = current_user.organization.slug if current_user.organization else "org"

    job = JobDescription(
        org_id=current_user.org_id,
        recruiter_id=current_user.id,
        created_by=current_user.id,
        hr_id=current_user.id,
        apply_url_token=token,
        whatsapp_job_id=f"JOB-{current_user.org_id}-{job_num}",
        email_alias=f"job{job_num}@{org_slug}.talentai.io",
        **req.model_dump(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_out(job, db)


@router.get("/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _job_out(_get_job(job_id, current_user, db), db)


@router.patch("/{job_id}")
def update_job(
    job_id: int,
    req: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_job(job_id, current_user, db)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    db.commit()
    return _job_out(job, db)


@router.patch("/{job_id}/toggle-active")
def toggle_active(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_job(job_id, current_user, db)
    job.is_active = not job.is_active
    db.commit()
    return {"is_active": job.is_active}


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    job = _get_job(job_id, current_user, db)
    db.delete(job)
    db.commit()


@router.get("/{job_id}/qr")
def get_qr(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_job(job_id, current_user, db)
    url = _apply_url(job.apply_url_token)
    return {"qr_base64": generate_qr_base64(url), "apply_url": url}


# ── Knockout Rules ────────────────────────────────────────────────────────────

@router.get("/{job_id}/knockout-rules")
def list_rules(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_job(job_id, current_user, db)
    rules = db.query(KnockoutRule).filter(
        KnockoutRule.job_id == job_id,
        KnockoutRule.org_id == current_user.org_id,
    ).all()
    return [
        {
            "id": r.id, "job_id": r.job_id, "rule_type": r.rule_type,
            "field": r.field, "operator": r.operator, "value": r.value,
            "action": r.action, "description": r.description,
            "is_active": r.is_active, "is_mandatory": r.is_mandatory,
        }
        for r in rules
    ]


@router.post("/{job_id}/knockout-rules", status_code=201)
def add_rule(
    job_id: int,
    req: KnockoutRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_job(job_id, current_user, db)
    rule = KnockoutRule(
        job_id=job_id, org_id=current_user.org_id, **req.model_dump()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "description": rule.description, "rule_type": rule.rule_type}


@router.delete("/{job_id}/knockout-rules/{rule_id}", status_code=204)
def delete_rule(
    job_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_job(job_id, current_user, db)
    rule = db.query(KnockoutRule).filter(
        KnockoutRule.id == rule_id,
        KnockoutRule.job_id == job_id,
        KnockoutRule.org_id == current_user.org_id,
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()


# ── Candidates for job ────────────────────────────────────────────────────────

@router.get("/{job_id}/candidates")
def get_job_candidates(
    job_id: int,
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from api.candidates import _candidate_summary
    _get_job(job_id, current_user, db)

    q = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.org_id == current_user.org_id,
    )
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)
    if status:
        q = q.filter(Candidate.status == status)
    if category:
        q = q.filter(Candidate.category == category)
    if min_score:
        q = q.filter(Candidate.match_score >= min_score)

    total = q.count()
    items = (
        q.order_by(Candidate.rank.asc().nullslast(), Candidate.match_score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [_candidate_summary(c) for c in items],
    }


@router.get("/{job_id}/rankings")
def get_rankings(
    job_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get ranked candidates for a job (top N by score)."""
    from api.candidates import _candidate_summary
    _get_job(job_id, current_user, db)

    q = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.org_id == current_user.org_id,
        Candidate.match_score > 0,
    )
    if current_user.role == "recruiter":
        q = q.filter(Candidate.recruiter_id == current_user.id)

    candidates = q.order_by(Candidate.rank.asc().nullslast(), Candidate.match_score.desc()).limit(limit).all()

    return {
        "job_id": job_id,
        "total_ranked": len(candidates),
        "rankings": [
            {
                **_candidate_summary(c),
                "rank": c.rank,
                "percentile": c.analysis.percentile if c.analysis else None,
            }
            for c in candidates
        ],
    }
