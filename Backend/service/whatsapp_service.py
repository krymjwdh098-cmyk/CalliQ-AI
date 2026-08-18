"""
WhatsApp Cloud API service — outbound messages + webhook parsing.
"""
import logging
from sqlalchemy.orm import Session
from models.database import WhatsAppMessage, Candidate
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TEMPLATES = {
    "shortlist": "🎉 Congratulations! You have been shortlisted for *{job_title}*. We will contact you shortly to schedule an interview.",
    "reject": "Thank you for applying for *{job_title}*. After careful review, we have decided to move forward with other candidates. We appreciate your interest.",
    "confirmation": "✅ We received your CV for *{job_title}*! Our AI is reviewing it and you'll hear from us soon.",
    "interview": "📅 Great news! You have been selected for an interview for *{job_title}*. Please reply with your available times.",
    "hired": "🎊 Congratulations! We are pleased to offer you the position of *{job_title}*. Our team will be in touch with the details.",
}


def queue_whatsapp_message(
    db: Session,
    org_id: int,
    candidate: Candidate,
    message_type: str,
    job_title: str = "",
    custom_body: str = "",
) -> WhatsAppMessage:
    phone = candidate.whatsapp_phone or candidate.phone
    if not phone:
        raise ValueError(f"Candidate {candidate.id} has no phone number")

    template = TEMPLATES.get(message_type, "{custom}")
    body = template.format(job_title=job_title) if "{job_title}" in template else custom_body

    msg = WhatsAppMessage(
        candidate_id=candidate.id,
        org_id=org_id,
        to_phone=phone,
        message_type=message_type,
        body=body,
        direction="outbound",
        status="pending",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    if settings.WHATSAPP_TOKEN:
        try:
            from workers.tasks import send_whatsapp_task
            send_whatsapp_task.delay(msg.id)
        except Exception as e:
            logger.warning(f"WhatsApp task dispatch failed: {e}")
    else:
        logger.info(f"[MOCK WA] to={phone}: {body}")
        msg.status = "sent_mock"
        db.commit()

    return msg


def parse_inbound_webhook(payload: dict) -> list[dict]:
    messages = []
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    from_phone = msg.get("from")
                    msg_type = msg.get("type")
                    if msg_type == "text":
                        messages.append({
                            "from_phone": from_phone,
                            "body": msg.get("text", {}).get("body", ""),
                            "media_id": None,
                            "media_type": "text",
                        })
                    elif msg_type == "document":
                        doc = msg.get("document", {})
                        messages.append({
                            "from_phone": from_phone,
                            "body": doc.get("caption", ""),
                            "media_id": doc.get("id"),
                            "media_type": doc.get("mime_type", "application/pdf"),
                            "file_name": doc.get("filename", "cv.pdf"),
                        })
    except Exception as e:
        logger.error(f"Webhook parse error: {e}")
    return messages


def download_whatsapp_media(media_id: str) -> bytes:
    import httpx
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    with httpx.Client(timeout=60) as client:
        url_resp = client.get(
            f"https://graph.facebook.com/v19.0/{media_id}", headers=headers
        )
        url_resp.raise_for_status()
        media_url = url_resp.json()["url"]
        file_resp = client.get(media_url, headers=headers)
        file_resp.raise_for_status()
        return file_resp.content
