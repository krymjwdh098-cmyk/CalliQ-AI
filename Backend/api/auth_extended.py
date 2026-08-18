"""
Refresh Token + Password Reset flows.
"""
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Session

from models.database import get_db, User, Base
from core.security import create_access_token, decode_token, hash_password
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_EXPIRE_DAYS = 30
RESET_TOKEN_EXPIRE_MINUTES = 30


# ── Models ────────────────────────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_refresh_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(64)
    expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(user_id=user_id, token=token, expires_at=expires)
    db.add(rt)
    db.commit()
    return token


def create_token_pair(db: Session, user_id: int) -> dict:
    access = create_access_token({"sub": str(user_id)})
    refresh = create_refresh_token(db, user_id)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenPair)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange refresh token for new access + refresh token pair."""
    rt = db.query(RefreshToken).filter(
        RefreshToken.token == req.refresh_token,
        RefreshToken.revoked == False,
    ).first()

    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if rt.expires_at < datetime.utcnow():
        rt.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: revoke old, issue new
    rt.revoked = True
    db.commit()

    return create_token_pair(db, user.id)


@router.post("/logout")
def logout(req: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke refresh token on logout."""
    rt = db.query(RefreshToken).filter(RefreshToken.token == req.refresh_token).first()
    if rt:
        rt.revoked = True
        db.commit()
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send password reset email.
    Always returns 200 even if email not found (prevents user enumeration).
    """
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        token = secrets.token_urlsafe(48)
        expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

        # Invalidate previous tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
        ).update({"used": True})

        prt = PasswordResetToken(user_id=user.id, token=token, expires_at=expires)
        db.add(prt)
        db.commit()

        reset_url = f"{settings.BASE_URL}/reset-password?token={token}"
        background_tasks.add_task(_send_reset_email, user.email, user.name, reset_url)
        logger.info(f"Password reset requested for {user.email} — token: {token}")

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Apply new password using reset token."""
    prt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False,
    ).first()

    if not prt:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if prt.expires_at < datetime.utcnow():
        prt.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = db.query(User).filter(User.id == prt.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(req.new_password)
    prt.used = True

    # Revoke all refresh tokens for security
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).update({"revoked": True})

    db.commit()
    logger.info(f"Password reset successful for user {user.id}")
    return {"message": "Password reset successfully. Please log in with your new password."}


def _send_reset_email(to_email: str, name: str, reset_url: str):
    """Send reset email — uses SMTP if configured, else logs."""
    try:
        from core.config import get_settings
        s = get_settings()
        smtp_host = getattr(s, "SMTP_HOST", "")
        if not smtp_host:
            logger.info(f"[MOCK EMAIL] Password reset for {to_email}: {reset_url}")
            return

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset Your TalentAI Password"
        msg["From"] = getattr(s, "SMTP_FROM", "noreply@talentai.io")
        msg["To"] = to_email

        html = f"""
        <html><body>
        <h2>Hello {name},</h2>
        <p>You requested a password reset for your TalentAI account.</p>
        <p><a href="{reset_url}" style="background:#2563eb;color:#fff;padding:12px 24px;
           border-radius:8px;text-decoration:none;display:inline-block;">
           Reset Password
        </a></p>
        <p>This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you didn't request this, please ignore this email.</p>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL(smtp_host, getattr(s, "SMTP_PORT", 465)) as server:
            server.login(getattr(s, "SMTP_USER", ""), getattr(s, "SMTP_PASSWORD", ""))
            server.sendmail(msg["From"], to_email, msg.as_string())

        logger.info(f"Reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Reset email failed for {to_email}: {e}")
        logger.info(f"[FALLBACK] Reset URL for {to_email}: {reset_url}")
