"""
Scoring, Ranking, and Categorization Service.
All operations are per-job, per-recruiter — never global.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import (
    Candidate, CandidateAnalysis, JobDescription,
    CandidateCategory, CandidateStatus
)
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def categorize_candidate(
    score: float,
    job: JobDescription = None,
    is_knocked_out: bool = False,
) -> str:
    """Determine candidate category from score and knockout status."""
    if is_knocked_out:
        return CandidateCategory.KNOCKOUT_FAILED

    # Use per-job thresholds if available, else global
    strong  = job.score_strong_match    if job else settings.SCORE_STRONG_MATCH
    potential = job.score_potential_match if job else settings.SCORE_POTENTIAL_MATCH
    weak    = job.score_weak_match      if job else settings.SCORE_WEAK_MATCH

    if score >= strong:
        return CandidateCategory.STRONG_MATCH
    if score >= potential:
        return CandidateCategory.POTENTIAL_MATCH
    if score >= weak:
        return CandidateCategory.WEAK_MATCH
    return CandidateCategory.NEEDS_REVIEW


def rerank_job_candidates(db: Session, job_id: int, recruiter_id: int):
    """
    Recompute rank for ALL candidates in a job.
    Called after each new candidate is processed to keep rankings current.
    Only affects candidates belonging to the specific recruiter's job.
    """
    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.job_id == job_id,
            Candidate.recruiter_id == recruiter_id,
            Candidate.status.notin_([
                CandidateStatus.DUPLICATE,
                CandidateStatus.ERROR,
                CandidateStatus.KNOCKOUT_FAILED,
            ]),
            Candidate.match_score > 0,
        )
        .order_by(Candidate.match_score.desc())
        .all()
    )

    total = len(candidates)
    for i, c in enumerate(candidates):
        c.rank = i + 1
        # Also update analysis rank
        if c.analysis:
            c.analysis.rank = i + 1
            c.analysis.percentile = round((1 - i / max(total, 1)) * 100, 1)

    db.commit()
    logger.info(f"Ranked {total} candidates for job {job_id}")


def apply_knockout_rules(db: Session, job_id: int, candidate: Candidate, parsed: dict) -> list[str]:
    """
    Evaluate all knockout rules for a job.
    Returns list of failure reasons (empty = passed).
    """
    from models.database import KnockoutRule
    import re

    rules = db.query(KnockoutRule).filter(
        KnockoutRule.job_id == job_id,
        KnockoutRule.is_active == True,
    ).all()

    flags = []
    for rule in rules:
        rt = rule.rule_type.lower()
        desc = rule.description or rule.rule_type
        val = (rule.value or "").strip()
        failed = False

        if rt == "experience":
            m = re.search(r"(\d+(?:\.\d+)?)", val or desc)
            if m:
                required = float(m.group(1))
                actual = float(candidate.years_experience or parsed.get("years_experience", 0) or 0)
                if actual < required:
                    failed = True
                    flags.append(f"{desc} — candidate has {actual:.1f} yrs (required: {required})")

        elif rt == "location":
            loc = (candidate.location or parsed.get("location", "") or "").lower()
            keyword = val.lower() if val else desc.lower().replace("must live in", "").replace("must be in", "").strip()
            if keyword and keyword not in loc:
                failed = True
                flags.append(f"{desc} — candidate location: {candidate.location or 'Unknown'}")

        elif rt == "education":
            edu_list = candidate.education or parsed.get("education", []) or []
            degrees = [str(e).lower() if isinstance(e, str) else
                       f"{e.get('degree', '')} {e.get('field', '')}".lower()
                       for e in edu_list]
            keyword = val.lower() if val else desc.lower()
            if "bachelor" in keyword and not any("bachelor" in d or "bsc" in d or "b.sc" in d or "b.s." in d for d in degrees):
                failed = True
                flags.append(f"{desc}")
            elif "master" in keyword and not any("master" in d or "msc" in d or "m.sc" in d for d in degrees):
                failed = True
                flags.append(f"{desc}")

        elif rt == "language":
            langs = candidate.languages or parsed.get("languages", []) or []
            lang_names = [
                (l.get("language", "") if isinstance(l, dict) else str(l)).lower()
                for l in langs
            ]
            keyword = val.lower() if val else desc.lower()
            if "english" in keyword and not any("english" in l for l in lang_names):
                failed = True
                flags.append(f"{desc}")

        elif rt == "skill":
            all_skills = []
            ts = candidate.technical_skills or parsed.get("technical_skills", {}) or {}
            if isinstance(ts, dict):
                for skills in ts.values():
                    all_skills.extend([s.lower() for s in (skills or [])])
            keyword = val.lower() if val else desc.lower()
            if keyword and not any(keyword in s for s in all_skills):
                failed = True
                flags.append(f"{desc} — required skill not found")

        elif rt == "custom":
            pass  # Custom rules need manual evaluation

    return flags


def compute_score_breakdown(match_result: dict) -> dict:
    """Build a detailed score breakdown dict from match result."""
    weights = {
        "skill_match": 0.35,
        "experience_match": 0.25,
        "education_match": 0.15,
        "seniority_match": 0.10,
        "location_match": 0.05,
        "keyword_match": 0.10,
    }
    breakdown = {}
    weighted_sum = 0
    for key, weight in weights.items():
        val = float(match_result.get(key, 0))
        breakdown[key] = {"score": val, "weight": weight, "weighted": round(val * weight, 1)}
        weighted_sum += val * weight

    breakdown["weighted_total"] = round(weighted_sum, 1)
    breakdown["ai_reported"] = float(match_result.get("overall_score", 0))
    return breakdown


def save_analysis(
    db: Session,
    candidate: Candidate,
    match_result: dict,
    job: JobDescription,
    llm_provider: str = "groq",
    processing_ms: int = 0,
) -> CandidateAnalysis:
    """Save or update CandidateAnalysis for a candidate."""
    existing = db.query(CandidateAnalysis).filter(
        CandidateAnalysis.candidate_id == candidate.id
    ).first()

    breakdown = compute_score_breakdown(match_result)
    category = categorize_candidate(
        score=float(match_result.get("overall_score", 0)),
        job=job,
        is_knocked_out=candidate.is_knocked_out,
    )

    data = dict(
        job_id=job.id,
        recruiter_id=candidate.recruiter_id,
        overall_score=float(match_result.get("overall_score", 0)),
        skill_match=float(match_result.get("skill_match", 0)),
        experience_match=float(match_result.get("experience_match", 0)),
        education_match=float(match_result.get("education_match", 0)),
        seniority_match=float(match_result.get("seniority_match", 0)),
        location_match=float(match_result.get("location_match", 0)),
        keyword_match=float(match_result.get("keyword_match", 0)),
        ats_score=float(match_result.get("ats_score", 0)),
        ai_confidence=float(match_result.get("ai_confidence", 0)),
        matched_skills=match_result.get("matched_skills", []),
        missing_skills=match_result.get("missing_skills", []),
        matched_requirements=match_result.get("matched_requirements", []),
        missing_requirements=match_result.get("missing_requirements", []),
        score_breakdown=breakdown,
        recommendation=match_result.get("recommendation"),
        recommendation_reason=match_result.get("recommendation_reason"),
        ai_summary=match_result.get("ai_summary"),
        strengths=match_result.get("strengths", []),
        weaknesses=match_result.get("weaknesses", []),
        skill_gap_analysis=match_result.get("skill_gap_analysis"),
        ats_issues=match_result.get("ats_issues", []),
        ats_suggestions=match_result.get("ats_suggestions", []),
        category=category,
        llm_provider=llm_provider,
        processing_time_ms=processing_ms,
        updated_at=datetime.utcnow(),
    )

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        return existing
    else:
        analysis = CandidateAnalysis(candidate_id=candidate.id, **data)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
