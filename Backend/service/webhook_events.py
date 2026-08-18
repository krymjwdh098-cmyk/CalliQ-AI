"""
Webhook Events — fire HTTP events to external tools (Slack, Zapier, n8n, etc.)
when candidate status changes, new applications arrive, etc.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import Session

from models.database import Base

logger = logging.getLogger(__name__)


# ── DB Model ──────────────────────────────────────────────────────────────────

class WebhookEndpoint(Base):
    """Stores registered webhook URLs per org."""
    __tablename__ = "webhook_endpoints"

    id          = Column(Integer, primary_key=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    url         = Column(String(500), nullable=False)
    secret      = Column(String(128))               # for HMAC signature
    events      = Column(JSON, default=list)         # ["candidate.approved", "*"]
    is_active   = Column(Boolean, default=True)
    description = Column(String(255))
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_webhooks_org", "org_id", "is_active"),)


class WebhookDelivery(Base):
    """Delivery log per event per endpoint."""
    __tablename__ = "webhook_deliveries"

    id            = Column(Integer, primary_key=True)
    endpoint_id   = Column(Integer, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    event         = Column(String(100))
    payload       = Column(JSON)
    status_code   = Column(Integer)
    response_body = Column(Text)
    attempt       = Column(Integer, default=1)
    success       = Column(Boolean, default=False)
    error         = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)


# ── Event firing ──────────────────────────────────────────────────────────────

def fire_event(
    db: Session,
    org_id: int,
    event: str,
    payload: dict,
):
    """
    Fire event to all matching webhook endpoints for the org.
    Runs in background threads — never blocks the HTTP response.
    """
    endpoints = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.org_id == org_id,
        WebhookEndpoint.is_active == True,
    ).all()

    matching = [
        ep for ep in endpoints
        if "*" in (ep.events or []) or event in (ep.events or [])
    ]

    if not matching:
        return

    # Add metadata to payload
    full_payload = {
        "event": event,
        "org_id": org_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": payload,
    }

    for ep in matching:
        t = threading.Thread(
            target=_deliver,
            args=(ep.id, ep.url, ep.secret, event, full_payload, org_id),
            daemon=True,
        )
        t.start()


def _deliver(
    endpoint_id: int,
    url: str,
    secret: Optional[str],
    event: str,
    payload: dict,
    org_id: int,
    max_retries: int = 3,
):
    """Deliver webhook with retry + HMAC signature."""
    import httpx, json, hmac, hashlib
    from models.database import SessionLocal

    body = json.dumps(payload, ensure_ascii=False, default=str)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TalentAI-Webhooks/1.0",
        "X-TalentAI-Event": event,
        "X-TalentAI-Delivery": f"{endpoint_id}-{int(time.time())}",
    }

    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-TalentAI-Signature"] = f"sha256={sig}"

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = httpx.post(url, content=body, headers=headers, timeout=15)
            success = 200 <= resp.status_code < 300

            db = SessionLocal()
            try:
                delivery = WebhookDelivery(
                    endpoint_id=endpoint_id,
                    org_id=org_id,
                    event=event,
                    payload=payload,
                    status_code=resp.status_code,
                    response_body=resp.text[:500],
                    attempt=attempt,
                    success=success,
                )
                db.add(delivery)
                db.commit()
            finally:
                db.close()

            if success:
                logger.info(f"Webhook delivered: {event} → {url} ({resp.status_code})")
                return

            logger.warning(f"Webhook failed attempt {attempt}: {url} → {resp.status_code}")

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Webhook error attempt {attempt}: {url} → {e}")

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # exponential backoff

    # Log final failure
    db = SessionLocal()
    try:
        delivery = WebhookDelivery(
            endpoint_id=endpoint_id, org_id=org_id,
            event=event, payload=payload,
            attempt=max_retries, success=False,
            error=last_error,
        )
        db.add(delivery)
        db.commit()
    finally:
        db.close()

    logger.error(f"Webhook permanently failed after {max_retries} attempts: {url}")


# ── Event constants ───────────────────────────────────────────────────────────

class Events:
    CANDIDATE_APPLIED    = "candidate.applied"
    CANDIDATE_PROCESSED  = "candidate.processed"
    CANDIDATE_SHORTLISTED = "candidate.shortlisted"
    CANDIDATE_REJECTED   = "candidate.rejected"
    CANDIDATE_HIRED      = "candidate.hired"
    CANDIDATE_KNOCKOUT   = "candidate.knockout_failed"
    JOB_CREATED          = "job.created"
    JOB_CLOSED           = "job.closed"
    BATCH_COMPLETED      = "batch.completed"
