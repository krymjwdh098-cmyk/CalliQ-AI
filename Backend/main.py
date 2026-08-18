"""
TalentAI — FastAPI Application Entrypoint
Multi-tenant, multi-recruiter ATS with AI CV processing.
"""
import sys
import os
import logging
import secrets
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from core.config import get_settings
from models.database import init_db, SessionLocal, User, Organization
from core.security import hash_password
from api import auth, users, jobs, candidates, apply, dashboard, webhooks
from api import webhook_mgmt
from api.auth_extended import router as auth_extended_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    init_db()
    _seed_demo()
    logger.info(f"TalentAI started — {settings.ENVIRONMENT}")
    yield


def _seed_demo():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@company.com").first():
            return
        org = Organization(
            name="Demo Company",
            slug="demo-" + secrets.token_hex(3),
        )
        db.add(org)
        db.flush()
        user = User(
            org_id=org.id,
            email="demo@company.com",
            name="Demo Recruiter",
            hashed_password=hash_password("demo1234"),
            role="owner",
        )
        db.add(user)
        db.commit()
        logger.info("Demo user created: demo@company.com / demo1234")
    except Exception as e:
        db.rollback()
        logger.warning(f"Seed skipped: {e}")
    finally:
        db.close()


app = FastAPI(
    title="TalentAI",
    description="AI-powered Multi-Recruiter ATS Platform",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
prefix = "/api/v1"
app.include_router(auth.router,              prefix=prefix)
app.include_router(auth_extended_router,     prefix=prefix)
app.include_router(users.router,             prefix=prefix)
app.include_router(jobs.router,              prefix=prefix)
app.include_router(candidates.router,        prefix=prefix)
app.include_router(dashboard.router,         prefix=prefix)
app.include_router(webhooks.router,          prefix=prefix)
app.include_router(webhook_mgmt.router,      prefix=prefix)
app.include_router(apply.router)       # /apply/{token} — public, no prefix


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "3.0.0"}


@app.get("/")
def root():
    return HTMLResponse(
        '<html><head><meta http-equiv="refresh" content="0; url=/api/docs"></head><body></body></html>'
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
