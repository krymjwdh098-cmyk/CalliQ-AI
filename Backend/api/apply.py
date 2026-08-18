"""
Public Application Endpoint — no auth required.
Candidates apply via unique job link.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional

from models.database import get_db, JobDescription, Candidate, Organization, CandidateStatus
from utils.file_storage import save_uploaded_file, allowed_file
from utils.rate_limiter import apply_limiter
from workers.tasks import dispatch_cv

router = APIRouter(prefix="/apply", tags=["apply (public)"])


@router.get("/{token}")
def get_job_info(token: str, db: Session = Depends(get_db)):
    """Return job info for the public application form."""
    job = db.query(JobDescription).filter(
        JobDescription.apply_url_token == token,
        JobDescription.is_active == True,
    ).first()
    if not job:
        raise HTTPException(404, "Job not found or no longer accepting applications")

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "required_skills": job.required_skills or [],
        "nice_to_have": job.nice_to_have or [],
        "min_experience": job.min_experience,
        "education_req": job.education_req,
        "location_req": job.location_req,
    }


@router.post("/{token}")
async def submit_application(
    token: str,
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _rl: None = Depends(apply_limiter),
):
    """Accept public CV submission and queue AI processing."""
    job = db.query(JobDescription).filter(
        JobDescription.apply_url_token == token,
        JobDescription.is_active == True,
    ).first()
    if not job:
        raise HTTPException(404, "Job not found or closed")

    if not allowed_file(cv_file.filename):
        raise HTTPException(400, "Only PDF, DOCX, JPG, PNG files allowed")

    content = await cv_file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 10MB)")

    file_path, file_name, file_hash = save_uploaded_file(
        content, cv_file.filename, job.org_id,
        cv_file.content_type or "application/pdf",
    )

    candidate = Candidate(
        org_id=job.org_id,
        recruiter_id=job.recruiter_id,
        hr_id=job.recruiter_id,
        job_id=job.id,
        full_name=full_name,
        email=email,
        phone=phone,
        source="link",
        file_path=file_path,
        file_name=file_name,
        file_hash=file_hash,
        status=CandidateStatus.QUEUED,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    dispatch_cv(candidate.id)

    return {
        "candidate_id": candidate.id,
        "message": "Application received! We will review your CV and be in touch.",
        "status": "queued",
    }
