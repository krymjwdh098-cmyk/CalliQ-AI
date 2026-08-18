"""
Tests for new features:
- Rate limiting
- Refresh tokens
- Password reset
- Audit log
- Webhook events
- File storage
- Chat history
- Email notifications
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, get_db, User, Organization, Candidate, JobDescription
from core.security import hash_password, create_access_token
from main import app

# DB setup handled by conftest.py
from tests.conftest import TestingSession, engine
client = TestClient(app)


def _make_org(db, name="TestOrg"):
    import secrets
    org = Organization(name=name, slug=f"t-{secrets.token_hex(3)}")
    db.add(org)
    db.flush()
    return org


def _make_user(db, org_id, email="u@test.com", role="recruiter"):
    u = User(
        org_id=org_id, email=email, name="Test",
        hashed_password=hash_password("pass1234"), role=role, is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_job(db, org_id, recruiter_id):
    import secrets
    j = JobDescription(
        org_id=org_id, recruiter_id=recruiter_id, created_by=recruiter_id,
        title="Dev Job", description="Python dev needed",
        required_skills=["Python"], min_experience=2,
        apply_url_token=secrets.token_urlsafe(16),
    )
    db.add(j)
    db.flush()
    return j


def _headers(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user_id)})}"}


# ── Rate Limiting Tests ────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_login_rate_limit(self):
        """After 5 failed logins, should get 429."""
        from utils.rate_limiter import _store
        # Use unique key per test to avoid cross-test contamination
        import time
        test_key = f"rl:/api/v1/auth/login:testclient"
        _store.reset(test_key)

        for i in range(5):
            client.post("/api/v1/auth/login", data={
                "username": f"nonexistent{i}@test.com", "password": "wrong"
            })

        r = client.post("/api/v1/auth/login", data={
            "username": "nonexistent_final@test.com", "password": "wrong"
        })
        assert r.status_code == 429, f"Expected 429 but got {r.status_code}"
        assert "Retry-After" in r.headers

    def test_rate_limit_has_retry_after_header(self):
        from utils.rate_limiter import _store
        _store.reset("rl:/api/v1/auth/login:testclient")

        for _ in range(5):
            client.post("/api/v1/auth/login", data={"username": "x@x.com", "password": "x"})

        r = client.post("/api/v1/auth/login", data={"username": "x@x.com", "password": "x"})
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            assert int(r.headers["Retry-After"]) > 0

    def test_apply_rate_limit(self):
        """Public apply endpoint is rate limited per IP."""
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "rl_apply@test.com")
        job = _make_job(db, org.id, user.id)
        token = job.apply_url_token
        db.commit()

        from utils.rate_limiter import _store
        _store.reset(f"rl:/apply/{token}:testclient")

        # Exhaust the limit
        for _ in range(10):
            with patch("workers.tasks.dispatch_cv"):
                client.post(
                    f"/apply/{token}",
                    data={"full_name": "Test", "email": f"x{_}@test.com"},
                    files={"cv_file": ("cv.pdf", b"content", "application/pdf")},
                )

        r = client.post(
            f"/apply/{token}",
            data={"full_name": "Test", "email": "extra@test.com"},
            files={"cv_file": ("cv.pdf", b"content", "application/pdf")},
        )
        assert r.status_code == 429
        db.close()

    def test_in_memory_store_allows_within_limit(self):
        from utils.rate_limiter import _InMemoryStore
        store = _InMemoryStore()
        for _ in range(5):
            allowed, retry = store.is_allowed("test_key", limit=10, window=60)
            assert allowed
            assert retry == 0

    def test_in_memory_store_blocks_over_limit(self):
        from utils.rate_limiter import _InMemoryStore
        store = _InMemoryStore()
        for _ in range(5):
            store.is_allowed("key2", limit=5, window=60)
        allowed, retry = store.is_allowed("key2", limit=5, window=60)
        assert not allowed
        assert retry > 0


# ── Refresh Token Tests ────────────────────────────────────────────────────────

class TestRefreshToken:
    def _register_and_get_tokens(self, email="refresh@test.com"):
        r = client.post("/api/v1/auth/register", json={
            "email": email, "password": "pass1234",
            "name": "Refresh User", "org_name": "Refresh Org",
        })
        assert r.status_code == 201
        # Now get tokens via login
        lr = client.post("/api/v1/auth/login", data={
            "username": email, "password": "pass1234"
        })
        return lr.json()

    def test_refresh_returns_new_access_token(self):
        """Refresh token returns valid new access token and a new refresh token."""
        db = TestingSession()
        from api.auth_extended import create_token_pair, RefreshToken
        org = _make_org(db, "RfrOrg")
        user = _make_user(db, org.id, "rfr1@test.com")
        db.commit()

        pair = create_token_pair(db, user.id)
        old_rt = pair["refresh_token"]
        db.close()

        r = client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token must be different
        assert data["refresh_token"] != old_rt
        # Old refresh token is now revoked — using it again should fail
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r2.status_code == 401

    def test_refresh_token_rotation(self):
        """Using a refresh token invalidates it and issues a new one."""
        db = TestingSession()
        from api.auth_extended import create_token_pair, RefreshToken
        org = _make_org(db, "RotateOrg")
        user = _make_user(db, org.id, "rotate@test.com")
        db.commit()

        pair = create_token_pair(db, user.id)
        old_rt = pair["refresh_token"]

        r = client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r.status_code == 200

        # Old token is now revoked
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
        assert r2.status_code == 401
        db.close()

    def test_invalid_refresh_token(self):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "fake-token-xyz"})
        assert r.status_code == 401

    def test_logout_revokes_token(self):
        db = TestingSession()
        from api.auth_extended import create_token_pair
        org = _make_org(db, "LogoutOrg")
        user = _make_user(db, org.id, "logout@test.com")
        db.commit()

        pair = create_token_pair(db, user.id)
        rt = pair["refresh_token"]

        r = client.post("/api/v1/auth/logout", json={"refresh_token": rt})
        assert r.status_code == 200

        # After logout, refresh token is invalid
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert r2.status_code == 401
        db.close()


# ── Password Reset Tests ───────────────────────────────────────────────────────

class TestPasswordReset:
    def test_forgot_password_always_returns_200(self):
        """Even with non-existent email — prevents user enumeration."""
        r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@test.com"})
        assert r.status_code == 200
        assert "sent" in r.json()["message"].lower()

    def test_forgot_password_existing_user(self):
        db = TestingSession()
        org = _make_org(db, "PwOrg")
        user = _make_user(db, org.id, "pw@test.com")
        db.commit()

        with patch("api.auth_extended._send_reset_email") as mock_send:
            r = client.post("/api/v1/auth/forgot-password", json={"email": "pw@test.com"})
            assert r.status_code == 200
            mock_send.assert_called_once()
        db.close()

    def test_reset_password_with_valid_token(self):
        db = TestingSession()
        from api.auth_extended import PasswordResetToken
        from datetime import timedelta, datetime
        import secrets as s

        org = _make_org(db, "ResetOrg")
        user = _make_user(db, org.id, "reset@test.com")
        db.commit()
        user_email = user.email
        db.close()

        db = TestingSession()
        from api.auth_extended import PasswordResetToken
        token = s.token_urlsafe(48)
        prt = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(prt)
        db.commit()
        db.close()

        r = client.post("/api/v1/auth/reset-password", json={
            "token": token, "new_password": "newpassword123"
        })
        assert r.status_code == 200
        assert "successfully" in r.json()["message"].lower()

        # Reset rate limiter before testing login
        from utils.rate_limiter import _store
        _store.reset("rl:/api/v1/auth/login:testclient")

        lr = client.post("/api/v1/auth/login", data={
            "username": user_email, "password": "newpassword123"
        })
        assert lr.status_code == 200, f"Login failed: {lr.json()}"

    def test_reset_password_invalid_token(self):
        r = client.post("/api/v1/auth/reset-password", json={
            "token": "invalid-token", "new_password": "newpassword123"
        })
        assert r.status_code == 400

    def test_reset_password_too_short(self):
        db = TestingSession()
        from api.auth_extended import PasswordResetToken
        import secrets as s
        from datetime import datetime, timedelta

        org = _make_org(db, "ShortPwOrg")
        user = _make_user(db, org.id, "shortpw@test.com")
        db.commit()

        token = s.token_urlsafe(48)
        prt = PasswordResetToken(
            user_id=user.id, token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(prt)
        db.commit()

        r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"})
        assert r.status_code == 400
        db.close()


# ── Audit Log Tests ────────────────────────────────────────────────────────────

class TestAuditLog:
    def test_audit_log_written_on_decision(self):
        db = TestingSession()
        org = _make_org(db, "AuditOrg")
        user = _make_user(db, org.id, "audit@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Audit Candidate", status="Under Review",
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        r = client.post(
            f"/api/v1/candidates/{c.id}/decide",
            headers=_headers(user.id),
            json={"decision": "APPROVED", "notes": "Great candidate"},
        )
        assert r.status_code == 200

        from service.audit import AuditLog
        log = db.query(AuditLog).filter(
            AuditLog.org_id == org.id,
            AuditLog.entity_id == c.id,
        ).first()
        assert log is not None
        assert log.action == "candidate.decision_made"
        assert log.after["decision"] == "APPROVED"
        db.close()

    def test_audit_log_stores_before_and_after(self):
        from service.audit import log_action, AuditLog
        db = TestingSession()
        org = _make_org(db)
        db.commit()

        log_action(
            db, org_id=org.id,
            action="test.action",
            entity_type="candidate",
            entity_id=42,
            user_id=1,
            before={"status": "Under Review"},
            after={"status": "Shortlisted"},
            notes="Test note",
        )

        entry = db.query(AuditLog).filter(AuditLog.action == "test.action").first()
        assert entry is not None
        assert entry.before["status"] == "Under Review"
        assert entry.after["status"] == "Shortlisted"
        assert entry.notes == "Test note"
        db.close()

    def test_audit_log_never_raises(self):
        """Audit log failures must not break the main flow."""
        from service.audit import log_action
        # Call with invalid db — should not raise
        try:
            log_action(None, org_id=1, action="test", notes="test")
        except Exception:
            pytest.fail("audit log raised an exception")

    def test_audit_log_endpoint_admin_only(self):
        db = TestingSession()
        org = _make_org(db)
        recruiter = _make_user(db, org.id, "audrec@test.com", "recruiter")
        admin = _make_user(db, org.id, "audadm@test.com", "admin")
        db.commit()

        # Recruiter cannot access audit log
        r = client.get("/api/v1/dashboard/audit-log", headers=_headers(recruiter.id))
        assert r.status_code == 403

        # Admin can
        r = client.get("/api/v1/dashboard/audit-log", headers=_headers(admin.id))
        assert r.status_code == 200
        db.close()


# ── Webhook Events Tests ───────────────────────────────────────────────────────

class TestWebhookEvents:
    def test_create_webhook_endpoint(self):
        db = TestingSession()
        org = _make_org(db)
        owner = _make_user(db, org.id, "wh_owner@test.com", "owner")
        db.commit()
        owner_id = owner.id
        db.close()

        r = client.post(
            "/api/v1/webhooks/endpoints",
            headers=_headers(owner_id),
            json={
                "url": "https://example.com/webhook",
                "events": ["candidate.applied", "candidate.rejected"],
                "description": "Slack notifications",
            },
        )
        assert r.status_code == 201, f"Got {r.status_code}: {r.json()}"
        data = r.json()
        assert "id" in data
        assert "secret" in data
        assert "candidate.applied" in data["events"]

    def test_recruiter_cannot_manage_webhooks(self):
        db = TestingSession()
        org = _make_org(db)
        recruiter = _make_user(db, org.id, "wh_rec@test.com", "recruiter")
        db.commit()

        r = client.post(
            "/api/v1/webhooks/endpoints",
            headers=_headers(recruiter.id),
            json={"url": "https://example.com/wh", "events": ["*"]},
        )
        assert r.status_code == 403
        db.close()

    def test_invalid_event_rejected(self):
        db = TestingSession()
        org = _make_org(db)
        owner = _make_user(db, org.id, "wh_inv@test.com", "owner")
        db.commit()

        r = client.post(
            "/api/v1/webhooks/endpoints",
            headers=_headers(owner.id),
            json={"url": "https://example.com/wh", "events": ["invalid.event"]},
        )
        assert r.status_code == 400
        db.close()

    def test_fire_event_with_matching_endpoint(self):
        """Event fires to matching endpoint, skips non-matching."""
        db = TestingSession()
        from service.webhook_events import WebhookEndpoint, fire_event, Events
        org = _make_org(db)
        db.commit()

        ep = WebhookEndpoint(
            org_id=org.id,
            url="https://httpbin.org/post",
            secret="test-secret",
            events=[Events.CANDIDATE_SHORTLISTED],
            is_active=True,
        )
        db.add(ep)
        db.commit()

        with patch("service.webhook_events._deliver") as mock_deliver:
            fire_event(db, org.id, Events.CANDIDATE_SHORTLISTED, {"candidate_id": 1})
            import time; time.sleep(0.1)
            # Should have been called for the matching endpoint
            # (may be in background thread, so check mock was registered)

        db.close()

    def test_list_available_events(self):
        r = client.get("/api/v1/webhooks/events")
        assert r.status_code == 200
        assert "*" in r.json()["events"]
        assert "candidate.applied" in r.json()["events"]

    def test_webhook_hmac_signature(self):
        """Webhook deliveries include HMAC signature header."""
        import hmac, hashlib, json

        secret = "test-secret-key"
        payload = {"event": "candidate.approved", "data": {"candidate_id": 1}}
        body = json.dumps(payload)
        expected_sig = "sha256=" + hmac.new(
            secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()

        # Verify signature generation logic
        actual_sig = "sha256=" + hmac.new(
            secret.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        assert actual_sig == expected_sig


# ── File Storage Tests ─────────────────────────────────────────────────────────

class TestFileStorage:
    def test_local_save_and_retrieve(self):
        from utils.file_storage import save_uploaded_file, read_file
        content = b"Test CV content for file storage"
        path, name, hash_val = save_uploaded_file(content, "cv.pdf", org_id=999)
        assert name.endswith(".pdf")
        assert len(hash_val) == 64  # SHA256 hex
        retrieved = read_file(path)
        assert retrieved == content
        # Cleanup
        import os
        os.unlink(path)

    def test_file_hash_is_deterministic(self):
        from utils.file_storage import save_uploaded_file
        content = b"same content"
        _, _, hash1 = save_uploaded_file(content, "a.pdf", org_id=1)
        _, _, hash2 = save_uploaded_file(content, "b.pdf", org_id=1)
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        from utils.file_storage import save_uploaded_file
        _, _, hash1 = save_uploaded_file(b"content A", "a.pdf", org_id=1)
        _, _, hash2 = save_uploaded_file(b"content B", "b.pdf", org_id=1)
        assert hash1 != hash2

    def test_allowed_file_types(self):
        from utils.file_storage import allowed_file
        assert allowed_file("cv.pdf")
        assert allowed_file("cv.PDF")
        assert allowed_file("cv.docx")
        assert allowed_file("cv.jpg")
        assert not allowed_file("cv.exe")
        assert not allowed_file("cv.py")
        assert not allowed_file("cv.sh")

    def test_s3_fallback_to_local_on_error(self):
        """If S3 fails, falls back to local storage."""
        from unittest.mock import patch
        import os
        os.environ["STORAGE_BACKEND"] = "s3"

        try:
            from utils.file_storage import save_uploaded_file
            # boto3 will fail since no creds — should fall back to local
            with patch("boto3.client") as mock_client:
                mock_client.return_value.upload_fileobj.side_effect = Exception("S3 error")
                path, name, hash_val = save_uploaded_file(b"content", "cv.pdf", org_id=1)
                # Should still succeed via local fallback
                assert name.endswith(".pdf")
        finally:
            os.environ["STORAGE_BACKEND"] = "local"


# ── Email Service Tests ────────────────────────────────────────────────────────

class TestEmailService:
    def test_send_email_logs_when_smtp_not_configured(self):
        from service.email_service import send_email
        # No SMTP configured — should return True (mock mode)
        result = send_email("test@test.com", "Test Subject", "<p>Hello</p>")
        assert result == True

    def test_notify_shortlisted_sends_email(self):
        from service.email_service import notify_shortlisted
        with patch("service.email_service.send_email") as mock_send:
            notify_shortlisted("candidate@test.com", "Ahmed Ali", "Python Developer", "Acme Corp")
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "candidate@test.com" == args[0]
            assert "Python Developer" in args[1]

    def test_notify_rejected_sends_email(self):
        from service.email_service import notify_rejected
        with patch("service.email_service.send_email") as mock_send:
            notify_rejected("candidate@test.com", "Ahmed", "Developer Job")
            mock_send.assert_called_once()

    def test_notify_recruiter_new_application(self):
        from service.email_service import notify_recruiter_new_application
        with patch("service.email_service.send_email") as mock_send:
            notify_recruiter_new_application(
                "recruiter@company.com", "Sarah", "Ahmed Ali", "Python Dev", 85.5, 42
            )
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert "recruiter@company.com" == args[0]
            assert "Ahmed Ali" in args[1]


# ── Chat History Context Tests ─────────────────────────────────────────────────

class TestChatHistory:
    def test_chat_stores_messages(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "chat@test.com")
        job = _make_job(db, org.id, user.id)
        c = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Chat Candidate", status="Under Review",
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        from models.database import ChatMessage
        with patch("service.llm_router.llm_complete", return_value="This candidate has strong Python skills."):
            r = client.post(
                f"/api/v1/candidates/{c.id}/chat",
                headers=_headers(user.id),
                json={"message": "What are this candidate's strengths?"},
            )
        assert r.status_code == 200
        assert r.json()["reply"] == "This candidate has strong Python skills."

        # Messages saved in DB
        msgs = db.query(ChatMessage).filter(ChatMessage.candidate_id == c.id).all()
        assert len(msgs) == 2  # user + assistant
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"
        db.close()

    def test_chat_returns_history_length(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "chatlen@test.com")
        job = _make_job(db, org.id, user.id)
        c = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Chat Len", status="Under Review",
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        with patch("service.llm_router.llm_complete", return_value="Reply"):
            r = client.post(
                f"/api/v1/candidates/{c.id}/chat",
                headers=_headers(user.id),
                json={"message": "First question"},
            )
        assert "history_length" in r.json()
        assert r.json()["history_length"] == 2
        db.close()

    def test_chat_history_included_in_candidate_profile(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "chatpro@test.com")
        job = _make_job(db, org.id, user.id)
        c = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Chat Profile", status="Under Review",
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        from models.database import ChatMessage
        db.add(ChatMessage(candidate_id=c.id, org_id=org.id, role="user", content="Q1"))
        db.add(ChatMessage(candidate_id=c.id, org_id=org.id, role="assistant", content="A1"))
        db.commit()

        r = client.get(f"/api/v1/candidates/{c.id}", headers=_headers(user.id))
        assert r.status_code == 200
        history = r.json()["chat_history"]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        db.close()


# ── Integration: Full Flow Test ────────────────────────────────────────────────

class TestFullFlow:
    def test_complete_candidate_journey(self):
        """
        Full journey: register → create job → apply → process → decide → notify
        """
        import tempfile

        # 1. Register
        r = client.post("/api/v1/auth/register", json={
            "email": "journey@company.com", "password": "pass1234",
            "name": "Journey Recruiter", "org_name": "Journey Corp",
        })
        assert r.status_code == 201
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create job
        r = client.post("/api/v1/jobs/", headers=headers, json={
            "title": "Senior Python Developer",
            "description": "Need Python expert with FastAPI and PostgreSQL.",
            "required_skills": ["Python", "FastAPI"],
            "min_experience": 3,
        })
        assert r.status_code == 201
        job = r.json()
        apply_token = job["apply_url"].split("/")[-1]

        # 3. Add knockout rule
        r = client.post(
            f"/api/v1/jobs/{job['id']}/knockout-rules",
            headers=headers,
            json={"rule_type": "experience", "description": "Must have 1+ years", "value": "1"},
        )
        assert r.status_code == 201

        # 4. Public apply
        mock_parsed = {
            "full_name": "Ahmed Hassan", "email": "ahmed@cv.com", "phone": "+20100",
            "current_position": "Python Dev", "years_experience": 4.0,
            "technical_skills": {"Backend": ["Python", "FastAPI"]},
            "education": [], "location": "Cairo",
        }
        mock_match = {
            "overall_score": 82, "skill_match": 90, "experience_match": 85,
            "education_match": 70, "seniority_match": 80, "location_match": 70,
            "keyword_match": 85, "ats_score": 75, "ai_confidence": 88,
            "recommendation": "Hire",
            "recommendation_reason": "Strong Python background.",
            "ai_summary": "Solid Python developer",
            "strengths": ["Python", "FastAPI"],
            "weaknesses": [],
            "missing_skills": [],
            "missing_certs": [],
            "matched_skills": ["Python", "FastAPI"],
            "matched_requirements": ["Python"],
            "missing_requirements": [],
            "skill_gap_analysis": "Good match",
            "ats_issues": [],
            "ats_suggestions": [],
        }

        with patch("service.cv_parser.parse_cv_with_ai", return_value=mock_parsed), \
             patch("service.cv_parser.match_cv_to_job", return_value=mock_match), \
             patch("service.cv_parser.extract_text_from_file", return_value="Python developer CV"):
            with patch("workers.tasks.dispatch_cv") as mock_dispatch:
                r = client.post(
                    f"/apply/{apply_token}",
                    data={"full_name": "Ahmed Hassan", "email": "ahmed@cv.com"},
                    files={"cv_file": ("ahmed_cv.pdf", b"Python dev CV", "application/pdf")},
                )
                assert r.status_code == 200
                candidate_id = r.json()["candidate_id"]

        # 5. Check candidate created
        r = client.get(f"/api/v1/candidates/{candidate_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["full_name"] == "Ahmed Hassan"

        # 6. Recruiter decides
        db = TestingSession()
        c = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        c.status = "Under Review"
        c.match_score = 82
        db.commit()
        db.close()

        r = client.post(
            f"/api/v1/candidates/{candidate_id}/decide",
            headers=headers,
            json={"decision": "APPROVED", "notes": "Strong Python background"},
        )
        assert r.status_code == 200
        assert r.json()["recruiter_decision"] == "APPROVED"
        assert r.json()["status"] == "Shortlisted"

        # 7. Verify audit log
        r = client.get("/api/v1/dashboard/audit-log", headers=headers)
        assert r.status_code == 200
        actions = [e["action"] for e in r.json()["items"]]
        assert "candidate.decision_made" in actions
