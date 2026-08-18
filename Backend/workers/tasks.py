"""
CV Processing Pipeline Tasks.
BUG FIX: matchScore was always 0 because match_cv_to_job was never called
         when job had no description. Fixed: job dict always built properly.
Each candidate's score is strictly isolated — no shared state.
"""
import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── Optional Celery ───────────────────────────────────────────────────────────
try:
    from celery import Celery
    from core.config import get_settings as _gs
    _s = _gs()
    if _s.CELERY_BROKER_URL:
        celery_app = Celery(
            "talentai",
            broker=_s.CELERY_BROKER_URL,
            backend=_s.CELERY_RESULT_BACKEND,
        )
        celery_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )
        _CELERY_AVAILABLE = True
    else:
        celery_app = None
        _CELERY_AVAILABLE = False
except ImportError:
    celery_app = None
    _CELERY_AVAILABLE = False


# ── Core pipeline (sync) ──────────────────────────────────────────────────────

def process_candidate_cv(candidate_id: int) -> dict:
    """
    Full CV processing pipeline — sync, isolated per candidate.
    Returns dict with status and score.
    """
    from models.database import SessionLocal, Candidate, JobDescription, BatchJob, UsageLog
    from service.cv_parser import extract_text_from_file, parse_cv_with_ai, match_cv_to_job
    from service.duplicate_detector import find_duplicate
    from service.scoring import (
        apply_knockout_rules, categorize_candidate,
        save_analysis, rerank_job_candidates
    )
    from core.config import get_settings
    settings = get_settings()

    t_start = time.time()
    logger.info(f"[Pipeline] START candidate={candidate_id}")

    db = SessionLocal()
    try:
        # ── Load candidate ────────────────────────────────────────────────────
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            logger.error(f"Candidate {candidate_id} not found")
            return {"status": "error", "error": "not found"}

        candidate.status = "Processing"
        candidate.processing_attempts = (candidate.processing_attempts or 0) + 1
        db.commit()

        # ── Extract text ──────────────────────────────────────────────────────
        raw_text = extract_text_from_file(candidate.file_path)
        candidate.raw_text = raw_text
        logger.info(f"[Pipeline] text extracted: {len(raw_text)} chars")

        # ── Parse CV with AI ──────────────────────────────────────────────────
        parsed = parse_cv_with_ai(raw_text)
        _apply_parsed(candidate, parsed)
        logger.info(f"[Pipeline] parsed: {parsed.get('full_name')}")
        db.commit()

        # ── Duplicate check ───────────────────────────────────────────────────
        dup_id = find_duplicate(db, candidate)
        if dup_id:
            candidate.duplicate_of = dup_id
            candidate.status = "Duplicate"
            db.commit()
            logger.info(f"[Pipeline] DUPLICATE of {dup_id}")
            return {"status": "duplicate", "duplicate_of": dup_id, "match_score": 0}

        # ── Job matching (FIX: always run if job exists) ──────────────────────
        match_result = {}
        job = None
        if candidate.job_id:
            job = db.query(JobDescription).filter(JobDescription.id == candidate.job_id).first()
            if job:
                job_dict = {
                    "title": job.title,
                    "description": job.description or "",
                    "required_skills": job.required_skills or [],
                    "nice_to_have": job.nice_to_have or [],
                    "min_experience": job.min_experience or 0,
                    "education_req": job.education_req or "",
                    "location_req": job.location_req or "",
                }
                match_result = match_cv_to_job(parsed, job_dict)
                _apply_match(candidate, match_result)
                logger.info(f"[Pipeline] match score: {candidate.match_score}")
                db.commit()

        # ── Knockout rules ────────────────────────────────────────────────────
        if candidate.job_id and job:
            flags = apply_knockout_rules(db, candidate.job_id, candidate, parsed)
            if flags:
                candidate.knockout_flags = flags
                candidate.is_knocked_out = True
                candidate.flagged = True
                candidate.flag_reason = "; ".join(flags)
                candidate.status = "Knockout Failed"
                db.commit()
                logger.info(f"[Pipeline] KNOCKOUT: {flags}")

        # ── Categorize ────────────────────────────────────────────────────────
        candidate.category = categorize_candidate(
            score=candidate.match_score,
            job=job,
            is_knocked_out=candidate.is_knocked_out,
        )

        if candidate.status not in ("Knockout Failed", "Duplicate"):
            candidate.status = "Under Review"

        db.commit()

        # ── Save analysis ─────────────────────────────────────────────────────
        if match_result and job:
            elapsed_ms = int((time.time() - t_start) * 1000)
            save_analysis(
                db=db,
                candidate=candidate,
                match_result=match_result,
                job=job,
                llm_provider=settings.LLM_PROVIDER,
                processing_ms=elapsed_ms,
            )
            # Rerank all candidates for this job
            rerank_job_candidates(db, candidate.job_id, candidate.recruiter_id)

        # ── Email notifications ───────────────────────────────────────────────
        if candidate.email and job:
            try:
                from service.email_service import notify_application_received, notify_recruiter_new_application
                notify_application_received(candidate.email, candidate.full_name, job.title)
                if job.hr_email and candidate.match_score > 0:
                    notify_recruiter_new_application(
                        job.hr_email, "Recruiter", candidate.full_name,
                        job.title, candidate.match_score, candidate.id,
                    )
            except Exception as e:
                logger.warning(f"Email notification failed: {e}")

        # ── Update batch progress ─────────────────────────────────────────────
        if candidate.batch_id:
            batch = db.query(BatchJob).filter(BatchJob.id == candidate.batch_id).first()
            if batch:
                batch.completed += 1
                batch.processing = max(0, batch.processing - 1)
                if batch.completed + batch.failed >= batch.total:
                    batch.status = "completed" if batch.failed == 0 else "partial"
                    batch.completed_at = datetime.utcnow()
                db.commit()

        elapsed = time.time() - t_start
        logger.info(f"[Pipeline] DONE candidate={candidate_id} score={candidate.match_score} status={candidate.status} time={elapsed:.2f}s")
        return {
            "status": candidate.status,
            "match_score": candidate.match_score,
            "category": candidate.category,
            "recommendation": candidate.recommendation,
        }

    except Exception as exc:
        logger.error(f"[Pipeline] FAILED candidate={candidate_id}: {exc}", exc_info=True)
        db.rollback()
        try:
            c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if c:
                c.status = "Error"
                c.last_error = str(exc)[:500]
                db.commit()
        except Exception:
            pass
        # Update batch failed count
        try:
            c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if c and c.batch_id:
                batch = db.query(BatchJob).filter(BatchJob.id == c.batch_id).first()
                if batch:
                    batch.failed += 1
                    batch.processing = max(0, batch.processing - 1)
                    batch.error_log = (batch.error_log or []) + [{"candidate_id": candidate_id, "error": str(exc)[:200]}]
                    db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()


def process_batch(
    candidate_ids: list[int],
    batch_id: int,
    max_concurrent: int = 5,
) -> dict:
    """
    Process 20-50 CVs with controlled concurrency.
    One failed CV does NOT stop the batch.
    Idempotent: skips already-processed candidates.
    """
    from models.database import SessionLocal, Candidate, BatchJob, CandidateStatus

    logger.info(f"[Batch] START batch={batch_id} total={len(candidate_ids)} concurrency={max_concurrent}")

    # Mark batch as processing
    db = SessionLocal()
    try:
        batch = db.query(BatchJob).filter(BatchJob.id == batch_id).first()
        if batch:
            batch.status = "processing"
            batch.started_at = datetime.utcnow()
            batch.processing = min(max_concurrent, len(candidate_ids))
            db.commit()
    finally:
        db.close()

    results = {"total": len(candidate_ids), "completed": 0, "failed": 0, "skipped": 0, "errors": []}
    lock = threading.Lock()

    def process_one(cid: int) -> dict:
        # Skip if already processed (idempotency)
        db2 = SessionLocal()
        try:
            c = db2.query(Candidate).filter(Candidate.id == cid).first()
            if c and c.status not in ("Queued", "Error", "Processing"):
                return {"candidate_id": cid, "status": "skipped"}
        finally:
            db2.close()

        try:
            res = process_candidate_cv(cid)
            return {"candidate_id": cid, **res}
        except Exception as e:
            return {"candidate_id": cid, "status": "error", "error": str(e)[:200]}

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(process_one, cid): cid for cid in candidate_ids}
        for future in as_completed(futures):
            cid = futures[future]
            try:
                res = future.result()
                with lock:
                    if res.get("status") == "error":
                        results["failed"] += 1
                        results["errors"].append(res)
                    elif res.get("status") == "skipped":
                        results["skipped"] += 1
                    else:
                        results["completed"] += 1
            except Exception as e:
                with lock:
                    results["failed"] += 1
                    results["errors"].append({"candidate_id": cid, "error": str(e)[:200]})

    logger.info(f"[Batch] DONE batch={batch_id}: {results}")
    return results


# ── Task wrappers (Celery or sync fallback) ───────────────────────────────────

if _CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=30, queue="cv_processing")
    def parse_cv_task(self, candidate_id: int):
        try:
            return process_candidate_cv(candidate_id)
        except Exception as exc:
            raise self.retry(exc=exc)

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60, queue="batch")
    def batch_process_task(self, candidate_ids: list, batch_id: int, max_concurrent: int = 5):
        try:
            return process_batch(candidate_ids, batch_id, max_concurrent)
        except Exception as exc:
            raise self.retry(exc=exc)

    @celery_app.task(bind=True, max_retries=5, default_retry_delay=60, queue="notifications")
    def send_whatsapp_task(self, message_id: int):
        try:
            _send_whatsapp(message_id)
        except Exception as exc:
            raise self.retry(exc=exc)
else:
    # Sync fallback — runs immediately in same process
    class _SyncTask:
        def __init__(self, fn):
            self._fn = fn
        def delay(self, *args, **kwargs):
            return self._fn(*args, **kwargs)
        def apply_async(self, args=(), kwargs=None, **opts):
            return self._fn(*args, **(kwargs or {}))
        def __call__(self, *args, **kwargs):
            return self._fn(*args, **kwargs)

    parse_cv_task = _SyncTask(process_candidate_cv)
    batch_process_task = _SyncTask(lambda ids, bid, mc=5: process_batch(ids, bid, mc))
    send_whatsapp_task = _SyncTask(lambda mid: _send_whatsapp(mid))


def dispatch_cv(candidate_id: int):
    """Dispatch CV processing — async if Celery available, else sync."""
    if _CELERY_AVAILABLE and celery_app:
        try:
            parse_cv_task.delay(candidate_id)
            return
        except Exception as e:
            logger.warning(f"Celery unavailable ({e}), running sync")
    process_candidate_cv(candidate_id)


def dispatch_batch(candidate_ids: list, batch_id: int, max_concurrent: int = 5):
    """Dispatch batch processing."""
    if _CELERY_AVAILABLE and celery_app:
        try:
            batch_process_task.delay(candidate_ids, batch_id, max_concurrent)
            return
        except Exception as e:
            logger.warning(f"Celery unavailable ({e}), running sync batch")
    # Run in background thread to not block HTTP response
    t = threading.Thread(
        target=process_batch,
        args=(candidate_ids, batch_id, max_concurrent),
        daemon=True,
    )
    t.start()


def _send_whatsapp(message_id: int):
    import httpx
    from models.database import SessionLocal, WhatsAppMessage
    from core.config import get_settings
    s = get_settings()

    db = SessionLocal()
    msg = None
    try:
        msg = db.query(WhatsAppMessage).filter(WhatsAppMessage.id == message_id).first()
        if not msg:
            return
        url = f"https://graph.facebook.com/v19.0/{s.WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": msg.to_phone,
            "type": "text",
            "text": {"body": msg.body},
        }
        headers = {"Authorization": f"Bearer {s.WHATSAPP_TOKEN}"}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        msg.wa_message_id = data.get("messages", [{}])[0].get("id")
        msg.status = "sent"
        db.commit()
    except Exception as exc:
        logger.error(f"WhatsApp send failed: {exc}")
        if msg:
            msg.retry_count = (msg.retry_count or 0) + 1
            msg.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


# ── Apply helpers ─────────────────────────────────────────────────────────────

def _apply_parsed(candidate, parsed: dict):
    candidate.full_name = parsed.get("full_name") or candidate.full_name
    candidate.email = parsed.get("email") or candidate.email

    phone = parsed.get("phone")
    if isinstance(phone, list):
        phone = phone[0] if phone else None
    candidate.phone = phone or candidate.phone

    candidate.location = parsed.get("location")
    candidate.nationality = parsed.get("nationality")
    candidate.linkedin = parsed.get("linkedin")
    candidate.github = parsed.get("github")
    candidate.portfolio = parsed.get("portfolio")
    candidate.current_position = parsed.get("current_position")
    candidate.companies = parsed.get("companies") or []
    candidate.years_experience = float(parsed.get("years_experience") or 0)
    candidate.previous_positions = parsed.get("previous_positions") or []
    candidate.education = parsed.get("education") or []
    candidate.certifications = parsed.get("certifications") or []
    candidate.courses = parsed.get("courses") or []
    candidate.technical_skills = parsed.get("technical_skills") or {}
    candidate.soft_skills = parsed.get("soft_skills") or []
    candidate.languages = parsed.get("languages") or []
    candidate.projects = parsed.get("projects") or []
    candidate.achievements = parsed.get("achievements") or []
    candidate.awards = parsed.get("awards") or []
    candidate.ai_summary = parsed.get("ai_summary")
    candidate.salary_expectation = parsed.get("salary_expectation")
    candidate.salary_currency    = parsed.get("salary_currency")
    candidate.notice_period_days = parsed.get("notice_period_days")
    candidate.availability_date  = parsed.get("availability_date")
    candidate.remote_preference  = parsed.get("remote_preference")


def _apply_match(candidate, match: dict):
    candidate.match_score = float(match.get("overall_score") or match.get("match_score") or 0)
    candidate.skill_match = float(match.get("skill_match") or 0)
    candidate.experience_match = float(match.get("experience_match") or 0)
    candidate.education_match = float(match.get("education_match") or 0)
    candidate.seniority_match = float(match.get("seniority_match") or 0)
    candidate.location_match = float(match.get("location_match") or 0)
    candidate.keyword_match = float(match.get("keyword_match") or 0)
    candidate.ats_score = float(match.get("ats_score") or 0)
    candidate.ai_confidence = float(match.get("ai_confidence") or 0)
    candidate.recommendation = match.get("recommendation")
    candidate.recommendation_reason = match.get("recommendation_reason")
    candidate.ai_summary = match.get("ai_summary") or candidate.ai_summary
    candidate.strengths = match.get("strengths") or []
    candidate.weaknesses = match.get("weaknesses") or []
    candidate.missing_skills = match.get("missing_skills") or []
    candidate.missing_certs = match.get("missing_certs") or []
    candidate.skill_gap_analysis = match.get("skill_gap_analysis")
    candidate.ats_issues = match.get("ats_issues") or []
    candidate.ats_suggestions = match.get("ats_suggestions") or []
    candidate.salary_match = float(match.get("salary_match") or 0)
    candidate.salary_expectation_match = match.get("salary_expectation_match")
