"""
Email Notification Service — SMTP with HTML templates.
Fallback to logging when SMTP not configured.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _smtp_configured() -> bool:
    return bool(getattr(settings, "SMTP_HOST", ""))


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    """Send email. Returns True on success."""
    if not _smtp_configured():
        logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = getattr(settings, "SMTP_FROM", "noreply@talentai.io")
        msg["To"] = to

        if text:
            msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        smtp_host = getattr(settings, "SMTP_HOST", "")
        smtp_port = getattr(settings, "SMTP_PORT", 587)
        smtp_user = getattr(settings, "SMTP_USER", "")
        smtp_pass = getattr(settings, "SMTP_PASSWORD", "")

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()

        if smtp_user:
            server.login(smtp_user, smtp_pass)

        server.sendmail(msg["From"], to, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Email failed to {to}: {e}")
        return False


# ── Email Templates ───────────────────────────────────────────────────────────

_BASE = """
<html><body style="font-family:-apple-system,sans-serif;background:#f5f7fa;padding:20px">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;
     box-shadow:0 2px 16px rgba(0,0,0,.08);overflow:hidden">
  <div style="background:#1e40af;padding:24px 32px">
    <h1 style="color:#fff;margin:0;font-size:1.4rem">TalentAI</h1>
  </div>
  <div style="padding:32px">{body}</div>
  <div style="padding:16px 32px;background:#f8fafc;color:#94a3b8;font-size:.8rem">
    TalentAI · AI-powered Recruitment Platform
  </div>
</div>
</body></html>
"""


def _wrap(body: str) -> str:
    return _BASE.replace("{body}", body)


def notify_application_received(to: str, candidate_name: str, job_title: str):
    html = _wrap(f"""
    <h2 style="color:#1e293b">Application Received ✅</h2>
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>We have received your application for <strong>{job_title}</strong>.</p>
    <p>Our AI is reviewing your CV and we'll be in touch soon.</p>
    <p style="color:#64748b;font-size:.9rem">Thank you for your interest!</p>
    """)
    send_email(to, f"Application Received — {job_title}", html)


def notify_shortlisted(to: str, candidate_name: str, job_title: str, company: str = ""):
    html = _wrap(f"""
    <h2 style="color:#1e293b">Great News! 🎉</h2>
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>Congratulations! You have been <strong>shortlisted</strong> for
    <strong>{job_title}</strong>{f" at {company}" if company else ""}.</p>
    <p>Our team will contact you shortly to schedule an interview.</p>
    """)
    send_email(to, f"Shortlisted for {job_title}", html)


def notify_rejected(to: str, candidate_name: str, job_title: str):
    html = _wrap(f"""
    <h2 style="color:#1e293b">Application Update</h2>
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>Thank you for applying for <strong>{job_title}</strong>.</p>
    <p>After careful review, we have decided to move forward with other candidates
    at this time. We appreciate your interest and wish you the best in your
    career journey.</p>
    """)
    send_email(to, f"Regarding Your Application for {job_title}", html)


def notify_interview_scheduled(
    to: str, candidate_name: str, job_title: str,
    interview_time: str, notes: str = ""
):
    html = _wrap(f"""
    <h2 style="color:#1e293b">Interview Scheduled 📅</h2>
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>Your interview for <strong>{job_title}</strong> has been scheduled.</p>
    <div style="background:#f0f7ff;border-left:4px solid #2563eb;padding:16px;border-radius:4px;margin:16px 0">
      <strong>📅 {interview_time}</strong>
    </div>
    {f"<p>{notes}</p>" if notes else ""}
    <p>Please confirm your attendance by replying to this email.</p>
    """)
    send_email(to, f"Interview Scheduled — {job_title}", html)


def notify_recruiter_new_application(
    to: str, recruiter_name: str, candidate_name: str,
    job_title: str, match_score: float, candidate_id: int
):
    """Notify recruiter when new candidate applies."""
    from core.config import get_settings
    s = get_settings()
    candidate_url = f"{s.BASE_URL}/candidates/{candidate_id}"

    color = "#16a34a" if match_score >= 75 else "#d97706" if match_score >= 50 else "#dc2626"
    html = _wrap(f"""
    <h2 style="color:#1e293b">New Application Received</h2>
    <p>Hi <strong>{recruiter_name}</strong>,</p>
    <p><strong>{candidate_name}</strong> has applied for <strong>{job_title}</strong>.</p>
    <div style="display:flex;gap:16px;margin:20px 0">
      <div style="background:#f8fafc;border-radius:8px;padding:16px;flex:1;text-align:center">
        <div style="font-size:2rem;font-weight:700;color:{color}">{match_score:.0f}%</div>
        <div style="color:#64748b;font-size:.85rem">Match Score</div>
      </div>
    </div>
    <a href="{candidate_url}" style="background:#2563eb;color:#fff;padding:12px 24px;
       border-radius:8px;text-decoration:none;display:inline-block">
       Review Candidate →
    </a>
    """)
    send_email(to, f"New Application: {candidate_name} for {job_title}", html)
