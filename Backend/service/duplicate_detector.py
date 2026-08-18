"""
Duplicate Detector — checks by email, phone, LinkedIn, and file hash.
"""
from sqlalchemy.orm import Session
from models.database import Candidate, CandidateStatus


def find_duplicate(db: Session, candidate: Candidate) -> int | None:
    """
    Returns ID of existing candidate if duplicate found.
    Priority: file_hash → email → phone → linkedin
    Scope: same org only.
    """
    if not candidate.org_id:
        return None

    base = db.query(Candidate).filter(
        Candidate.org_id == candidate.org_id,
        Candidate.id != candidate.id,
        Candidate.duplicate_of == None,
        Candidate.status != CandidateStatus.DUPLICATE,
    )

    # File hash check (exact same file)
    if candidate.file_hash:
        dup = base.filter(Candidate.file_hash == candidate.file_hash).first()
        if dup:
            return dup.id

    # Email check
    if candidate.email:
        dup = base.filter(
            Candidate.email == candidate.email,
            Candidate.email != None,
        ).first()
        if dup:
            return dup.id

    # Phone check
    if candidate.phone:
        dup = base.filter(
            Candidate.phone == candidate.phone,
            Candidate.phone != None,
        ).first()
        if dup:
            return dup.id

    # LinkedIn check
    if candidate.linkedin:
        dup = base.filter(
            Candidate.linkedin == candidate.linkedin,
            Candidate.linkedin != None,
        ).first()
        if dup:
            return dup.id

    return None
