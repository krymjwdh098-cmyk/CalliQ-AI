"""
Webhook Management API — register/manage webhook endpoints.
"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from models.database import get_db, User
from api.deps import get_current_user, require_role
from service.webhook_events import WebhookEndpoint, WebhookDelivery

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

AVAILABLE_EVENTS = [
    "candidate.applied", "candidate.processed", "candidate.shortlisted",
    "candidate.rejected", "candidate.hired", "candidate.knockout_failed",
    "job.created", "job.closed", "batch.completed", "*",
]


class WebhookCreate(BaseModel):
    url: str
    events: list[str] = ["*"]
    description: Optional[str] = None


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


@router.get("/endpoints")
def list_endpoints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    endpoints = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.org_id == current_user.org_id
    ).all()
    return [
        {
            "id": ep.id,
            "url": ep.url,
            "events": ep.events,
            "is_active": ep.is_active,
            "description": ep.description,
            "created_at": ep.created_at.isoformat() if ep.created_at else None,
        }
        for ep in endpoints
    ]


@router.post("/endpoints", status_code=201)
def create_endpoint(
    req: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    # Validate events
    invalid = [e for e in req.events if e not in AVAILABLE_EVENTS]
    if invalid:
        raise HTTPException(400, f"Invalid events: {invalid}. Available: {AVAILABLE_EVENTS}")

    ep = WebhookEndpoint(
        org_id=current_user.org_id,
        url=req.url,
        secret=secrets.token_urlsafe(32),
        events=req.events,
        description=req.description,
        is_active=True,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return {
        "id": ep.id,
        "url": ep.url,
        "secret": ep.secret,  # Show once on creation
        "events": ep.events,
        "description": ep.description,
        "message": "Save the secret — it won't be shown again.",
    }


@router.patch("/endpoints/{endpoint_id}")
def update_endpoint(
    endpoint_id: int,
    req: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    ep = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    if req.url is not None:
        ep.url = req.url
    if req.events is not None:
        invalid = [e for e in req.events if e not in AVAILABLE_EVENTS]
        if invalid:
            raise HTTPException(400, f"Invalid events: {invalid}")
        ep.events = req.events
    if req.is_active is not None:
        ep.is_active = req.is_active
    if req.description is not None:
        ep.description = req.description

    db.commit()
    return {"id": ep.id, "url": ep.url, "is_active": ep.is_active}


@router.delete("/endpoints/{endpoint_id}", status_code=204)
def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    ep = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    if not ep:
        raise HTTPException(404, "Endpoint not found")
    db.delete(ep)
    db.commit()


@router.post("/endpoints/{endpoint_id}/test")
def test_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    """Send a test ping to the webhook URL."""
    ep = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    from service.webhook_events import fire_event
    fire_event(db, current_user.org_id, "ping", {
        "message": "TalentAI webhook test",
        "endpoint_id": endpoint_id,
    })
    return {"message": "Test ping sent", "url": ep.url}


@router.get("/endpoints/{endpoint_id}/deliveries")
def get_deliveries(
    endpoint_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "owner")),
):
    ep = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == endpoint_id,
        WebhookEndpoint.org_id == current_user.org_id,
    ).first()
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.endpoint_id == endpoint_id
    ).order_by(WebhookDelivery.created_at.desc()).limit(limit).all()

    return [
        {
            "id": d.id,
            "event": d.event,
            "status_code": d.status_code,
            "success": d.success,
            "attempt": d.attempt,
            "error": d.error,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deliveries
    ]


@router.get("/events")
def list_available_events():
    """List all available webhook event types."""
    return {"events": AVAILABLE_EVENTS}
