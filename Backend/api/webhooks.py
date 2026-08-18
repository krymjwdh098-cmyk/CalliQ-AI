from fastapi import APIRouter, Request, Depends, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models.database import get_db, JobDescription, Candidate, Organization, CandidateStatus
from core.config import get_settings
from service.whatsapp_service import parse_inbound_webhook, download_whatsapp_media, queue_whatsapp_message
from utils.file_storage import save_uploaded_file
from workers.tasks import dispatch_cv
import logging, re

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get("/whatsapp")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(403, "Verification failed")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    messages = parse_inbound_webhook(payload)
    for msg in messages:
        background_tasks.add_task(_handle_whatsapp_msg, msg, db)
    return {"status": "ok"}


def _handle_whatsapp_msg(msg: dict, db: Session):
    from_phone = msg.get("from_phone", "")
    media_id = msg.get("media_id")
    media_type = msg.get("media_type", "application/pdf")
    body_text = msg.get("body", "")
    file_name = msg.get("file_name", "cv.pdf")

    if not media_id:
        return

    job = None
    m = re.search(r"JOB-\d+-\d+", body_text.upper())
    if m:
        job = db.query(JobDescription).filter(
            JobDescription.whatsapp_job_id == m.group()
        ).first()

    org = None
    if job:
        org = db.query(Organization).filter(Organization.id == job.org_id).first()
    else:
        org = db.query(Organization).filter(Organization.is_active == True).first()

    if not org:
        logger.warning("No org found for WhatsApp message")
        return

    try:
        file_bytes = download_whatsapp_media(media_id)
    except Exception as e:
        logger.error(f"WA media download failed: {e}")
        return

    file_path, file_name, file_hash = save_uploaded_file(file_bytes, file_name, org.id, media_type)

    candidate = Candidate(
        org_id=org.id,
        recruiter_id=job.recruiter_id if job else None,
        job_id=job.id if job else None,
        full_name=f"WhatsApp {from_phone}",
        whatsapp_phone=from_phone,
        source="whatsapp",
        file_path=file_path,
        file_name=file_name,
        file_hash=file_hash,
        status=CandidateStatus.QUEUED,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    dispatch_cv(candidate.id)

    try:
        queue_whatsapp_message(
            db, org.id, candidate, "confirmation",
            job_title=job.title if job else "our open positions",
        )
    except Exception:
        pass
