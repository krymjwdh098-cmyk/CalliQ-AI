"""
TalentAI — Comprehensive Test Suite
Tests: auth, recruiter isolation, job ownership, CV pipeline,
       batch processing, scoring, ranking, knockout, categorization,
       approval workflow, duplicate detection.
"""
import os
import io
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, get_db, User, Organization, Candidate, JobDescription, BatchJob
from core.security import hash_password, create_access_token
from main import app

# DB setup handled by conftest.py
from tests.conftest import TestingSession, engine
client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_org(db, name="TestOrg") -> Organization:
    import secrets
    org = Organization(name=name, slug=f"test-{secrets.token_hex(3)}")
    db.add(org)
    db.flush()
    return org


def _make_user(db, org_id, email="recruiter@test.com", role="recruiter") -> User:
    user = User(
        org_id=org_id,
        email=email,
        name="Test Recruiter",
        hashed_password=hash_password("password123"),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def _make_job(db, org_id, recruiter_id, title="Python Dev") -> JobDescription:
    import secrets
    job = JobDescription(
        org_id=org_id,
        recruiter_id=recruiter_id,
        created_by=recruiter_id,
        hr_id=recruiter_id,
        title=title,
        description="Build FastAPI services. Need Python, PostgreSQL, Docker.",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        min_experience=2,
        apply_url_token=secrets.token_urlsafe(16),
        score_strong_match=80.0,
        score_potential_match=60.0,
        score_weak_match=40.0,
    )
    db.add(job)
    db.flush()
    return job


def _make_candidate(db, org_id, job_id, recruiter_id, name="Ahmed Ali") -> Candidate:
    candidate = Candidate(
        org_id=org_id,
        job_id=job_id,
        recruiter_id=recruiter_id,
        full_name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        status="Under Review",
        match_score=75.0,
    )
    db.add(candidate)
    db.flush()
    return candidate


def _token(user_id: int) -> str:
    return create_access_token({"sub": str(user_id)})


def _headers(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_token(user_id)}"}


# ── AUTH TESTS ─────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register(self):
        r = client.post("/api/v1/auth/register", json={
            "email": "new@company.com",
            "password": "pass1234",
            "name": "New User",
            "org_name": "New Company",
        })
        assert r.status_code == 201
        assert "access_token" in r.json()

    def test_login_success(self):
        # Register first
        client.post("/api/v1/auth/register", json={
            "email": "login@test.com", "password": "pass1234",
            "name": "Login User", "org_name": "Login Org",
        })
        r = client.post("/api/v1/auth/login", data={
            "username": "login@test.com", "password": "pass1234"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self):
        client.post("/api/v1/auth/register", json={
            "email": "wp@test.com", "password": "correct",
            "name": "WP User", "org_name": "WP Org",
        })
        r = client.post("/api/v1/auth/login", data={
            "username": "wp@test.com", "password": "wrong"
        })
        assert r.status_code == 401

    def test_me_endpoint(self):
        r = client.post("/api/v1/auth/register", json={
            "email": "me@test.com", "password": "pass1234",
            "name": "Me User", "org_name": "Me Org",
        })
        token = r.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "me@test.com"

    def test_invalid_token(self):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


# ── RECRUITER ISOLATION TESTS ──────────────────────────────────────────────────

class TestRecruiterIsolation:
    def test_recruiter_cannot_see_other_recruiter_jobs(self):
        db = TestingSession()
        org = _make_org(db, "IsolationOrg")
        r1 = _make_user(db, org.id, "r1@test.com", "recruiter")
        r2 = _make_user(db, org.id, "r2@test.com", "recruiter")
        j1 = _make_job(db, org.id, r1.id, "R1 Job")
        j2 = _make_job(db, org.id, r2.id, "R2 Job")
        db.commit()

        # R1 sees only R1's job
        r = client.get("/api/v1/jobs/", headers=_headers(r1.id))
        assert r.status_code == 200
        titles = [j["title"] for j in r.json()]
        assert "R1 Job" in titles
        assert "R2 Job" not in titles

        # R2 sees only R2's job
        r = client.get("/api/v1/jobs/", headers=_headers(r2.id))
        titles = [j["title"] for j in r.json()]
        assert "R2 Job" in titles
        assert "R1 Job" not in titles
        db.close()

    def test_recruiter_cannot_access_other_job_directly(self):
        db = TestingSession()
        org = _make_org(db)
        r1 = _make_user(db, org.id, "iso1@test.com", "recruiter")
        r2 = _make_user(db, org.id, "iso2@test.com", "recruiter")
        j2 = _make_job(db, org.id, r2.id, "Private Job")
        db.commit()

        # R1 tries to access R2's job directly — should get 404
        r = client.get(f"/api/v1/jobs/{j2.id}", headers=_headers(r1.id))
        assert r.status_code == 404
        db.close()

    def test_recruiter_cannot_see_other_recruiter_candidates(self):
        db = TestingSession()
        org = _make_org(db)
        r1 = _make_user(db, org.id, "cr1@test.com", "recruiter")
        r2 = _make_user(db, org.id, "cr2@test.com", "recruiter")
        j1 = _make_job(db, org.id, r1.id)
        j2 = _make_job(db, org.id, r2.id)
        c1 = _make_candidate(db, org.id, j1.id, r1.id, "R1 Candidate")
        c2 = _make_candidate(db, org.id, j2.id, r2.id, "R2 Candidate")
        db.commit()

        # R1 cannot see R2's candidate
        r = client.get("/api/v1/candidates/", headers=_headers(r1.id))
        names = [c["full_name"] for c in r.json()["items"]]
        assert "R1 Candidate" in names
        assert "R2 Candidate" not in names

        # Direct access also blocked
        r = client.get(f"/api/v1/candidates/{c2.id}", headers=_headers(r1.id))
        assert r.status_code == 404
        db.close()

    def test_admin_sees_all_org_data(self):
        db = TestingSession()
        org = _make_org(db)
        admin = _make_user(db, org.id, "admin@test.com", "admin")
        r1 = _make_user(db, org.id, "ar1@test.com", "recruiter")
        r2 = _make_user(db, org.id, "ar2@test.com", "recruiter")
        j1 = _make_job(db, org.id, r1.id, "Job A")
        j2 = _make_job(db, org.id, r2.id, "Job B")
        db.commit()

        # Admin sees all jobs
        r = client.get("/api/v1/jobs/", headers=_headers(admin.id))
        titles = [j["title"] for j in r.json()]
        assert "Job A" in titles
        assert "Job B" in titles
        db.close()

    def test_cross_org_isolation(self):
        """Users from different orgs cannot see each other's data."""
        db = TestingSession()
        org1 = _make_org(db, "Org1")
        org2 = _make_org(db, "Org2")
        u1 = _make_user(db, org1.id, "u1@org1.com", "owner")
        u2 = _make_user(db, org2.id, "u2@org2.com", "owner")
        j1 = _make_job(db, org1.id, u1.id, "Org1 Job")
        j2 = _make_job(db, org2.id, u2.id, "Org2 Job")
        db.commit()

        r = client.get("/api/v1/jobs/", headers=_headers(u1.id))
        titles = [j["title"] for j in r.json()]
        assert "Org1 Job" in titles
        assert "Org2 Job" not in titles
        db.close()


# ── JOB TESTS ──────────────────────────────────────────────────────────────────

class TestJobs:
    def test_create_job(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "jcreate@test.com", "recruiter")
        db.commit()

        r = client.post("/api/v1/jobs/", headers=_headers(user.id), json={
            "title": "Senior Python Dev",
            "description": "Build scalable APIs with FastAPI and PostgreSQL.",
            "required_skills": ["Python", "FastAPI"],
            "min_experience": 3,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Senior Python Dev"
        assert data["recruiter_id"] == user.id
        assert "apply_url" in data
        db.close()

    def test_job_apply_url_is_unique(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "jurl@test.com", "recruiter")
        db.commit()

        r1 = client.post("/api/v1/jobs/", headers=_headers(user.id), json={
            "title": "Job 1", "description": "Desc", "required_skills": [],
        })
        r2 = client.post("/api/v1/jobs/", headers=_headers(user.id), json={
            "title": "Job 2", "description": "Desc", "required_skills": [],
        })
        assert r1.json()["apply_url"] != r2.json()["apply_url"]
        db.close()

    def test_update_job(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "jupdate@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        r = client.patch(f"/api/v1/jobs/{job.id}", headers=_headers(user.id), json={
            "min_experience": 5
        })
        assert r.status_code == 200
        assert r.json()["min_experience"] == 5
        db.close()

    def test_toggle_active(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "jtoggle@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        r = client.patch(f"/api/v1/jobs/{job.id}/toggle-active", headers=_headers(user.id))
        assert r.status_code == 200
        assert r.json()["is_active"] == False
        db.close()

    def test_knockout_rule_crud(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "jko@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        # Add rule
        r = client.post(f"/api/v1/jobs/{job.id}/knockout-rules", headers=_headers(user.id), json={
            "rule_type": "experience",
            "description": "Must have 3+ years",
            "value": "3",
            "action": "auto_reject",
        })
        assert r.status_code == 201
        rule_id = r.json()["id"]

        # List rules
        r = client.get(f"/api/v1/jobs/{job.id}/knockout-rules", headers=_headers(user.id))
        assert len(r.json()) == 1

        # Delete rule
        r = client.delete(f"/api/v1/jobs/{job.id}/knockout-rules/{rule_id}", headers=_headers(user.id))
        assert r.status_code == 204
        db.close()


# ── CV PIPELINE TESTS ──────────────────────────────────────────────────────────

class TestCVPipeline:
    def _make_cv_file(self, text="Python developer with 5 years FastAPI experience"):
        """Create a minimal test PDF in memory."""
        content = text.encode()
        return ("test_cv.pdf", io.BytesIO(content), "application/pdf")

    def test_upload_cv_returns_queued(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "cvup@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        with patch("workers.tasks.dispatch_cv"):
            r = client.post(
                "/api/v1/candidates/upload",
                headers=_headers(user.id),
                data={"job_id": job.id, "full_name": "Test Candidate"},
                files={"cv_file": ("cv.pdf", b"CV content", "application/pdf")},
            )
        assert r.status_code == 202
        assert r.json()["status"] == "Queued"
        assert r.json()["recruiter_id"] == user.id
        db.close()

    def test_cv_upload_invalid_file_type(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "invfile@test.com", "recruiter")
        db.commit()

        r = client.post(
            "/api/v1/candidates/upload",
            headers=_headers(user.id),
            data={"full_name": "Test"},
            files={"cv_file": ("script.exe", b"bad file", "application/exe")},
        )
        assert r.status_code == 400
        db.close()

    def test_cv_upload_too_large(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "large@test.com", "recruiter")
        db.commit()

        big_content = b"x" * (11 * 1024 * 1024)  # 11MB
        r = client.post(
            "/api/v1/candidates/upload",
            headers=_headers(user.id),
            data={"full_name": "Test"},
            files={"cv_file": ("big.pdf", big_content, "application/pdf")},
        )
        assert r.status_code == 413
        db.close()

    def test_pipeline_match_score_not_zero(self):
        """
        Critical bug fix test: match_score must NOT be 0 after processing.
        Previous bug: match_cv_to_job was never called, always returned 0.
        """
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "score@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        job.description = "Need Python developer with FastAPI and PostgreSQL"
        job.required_skills = ["Python", "FastAPI"]
        db.commit()

        mock_parsed = {
            "full_name": "Ahmed Ali",
            "email": "ahmed@test.com",
            "phone": "+201001234567",
            "current_position": "Senior Python Developer",
            "years_experience": 5.0,
            "technical_skills": {"Backend": ["Python", "FastAPI", "PostgreSQL"]},
            "education": [{"degree": "Bachelor", "field": "CS", "institution": "Cairo Uni", "year": "2018"}],
            "location": "Cairo",
        }
        mock_match = {
            "overall_score": 88.5,
            "skill_match": 90.0,
            "experience_match": 85.0,
            "education_match": 80.0,
            "seniority_match": 88.0,
            "location_match": 70.0,
            "keyword_match": 85.0,
            "ats_score": 82.0,
            "ai_confidence": 90.0,
            "recommendation": "Strong Hire",
            "recommendation_reason": "Excellent Python and FastAPI experience.",
            "ai_summary": "Senior Python developer with strong backend skills.",
            "strengths": ["Python expertise", "FastAPI", "PostgreSQL"],
            "weaknesses": [],
            "missing_skills": [],
            "missing_certs": [],
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "matched_requirements": ["Python", "FastAPI"],
            "missing_requirements": [],
            "skill_gap_analysis": "Excellent match.",
            "ats_issues": [],
            "ats_suggestions": [],
        }

        # Create a real file for the test
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir="/tmp") as f:
            f.write(b"Python FastAPI developer CV content")
            tmp_path = f.name

        try:
            candidate = Candidate(
                org_id=org.id,
                recruiter_id=user.id,
                job_id=job.id,
                full_name="Test Candidate",
                source="manual",
                file_path=tmp_path,
                file_name="test.pdf",
                status="Queued",
            )
            db.add(candidate)
            db.commit()
            db.refresh(candidate)

            with patch("service.cv_parser.parse_cv_with_ai", return_value=mock_parsed), \
                 patch("service.cv_parser.match_cv_to_job", return_value=mock_match), \
                 patch("service.cv_parser.extract_text_from_file", return_value="Python FastAPI developer"):

                from workers.tasks import process_candidate_cv
                result = process_candidate_cv(candidate.id)

            # Reload from DB
            db.expire(candidate)
            db.refresh(candidate)

            # THE CRITICAL ASSERTION: score must not be 0
            assert candidate.match_score == 88.5, f"Expected 88.5 got {candidate.match_score}"
            assert candidate.status == "Under Review"
            assert candidate.recommendation == "Strong Hire"
            assert candidate.category == "STRONG_MATCH"
        finally:
            os.unlink(tmp_path)
            db.close()

    def test_old_cv_data_not_mixed(self):
        """Each candidate gets their own unique analysis — never mixed with previous."""
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "mix@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        parsed_a = {"full_name": "Candidate A", "email": "a@test.com", "phone": "+1",
                    "current_position": "Developer", "years_experience": 3.0,
                    "technical_skills": {"Backend": ["Python"]}, "education": [], "location": "Cairo"}
        parsed_b = {"full_name": "Candidate B", "email": "b@test.com", "phone": "+2",
                    "current_position": "Designer", "years_experience": 1.0,
                    "technical_skills": {"Design": ["Figma"]}, "education": [], "location": "Dubai"}
        match_a = {**{"overall_score": 85, "skill_match": 90, "experience_match": 80,
                      "education_match": 80, "seniority_match": 80, "location_match": 70,
                      "keyword_match": 80, "ats_score": 80, "ai_confidence": 85,
                      "recommendation": "Hire", "recommendation_reason": "Good",
                      "ai_summary": "Good candidate A", "strengths": ["Python"],
                      "weaknesses": [], "missing_skills": [], "missing_certs": [],
                      "matched_skills": ["Python"], "matched_requirements": [],
                      "missing_requirements": [], "skill_gap_analysis": "", "ats_issues": [], "ats_suggestions": []}}
        match_b = {**{**match_a, "overall_score": 30, "recommendation": "Reject", "ai_summary": "Poor match B"}}

        for name, parsed, match in [("A", parsed_a, match_a), ("B", parsed_b, match_b)]:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"CV content")
                tmp = f.name
            try:
                c = Candidate(
                    org_id=org.id, recruiter_id=user.id, job_id=job.id,
                    full_name=name, source="manual", file_path=tmp, file_name=f"{name}.pdf", status="Queued",
                )
                db.add(c)
                db.commit()
                db.refresh(c)

                with patch("service.cv_parser.parse_cv_with_ai", return_value=parsed), \
                     patch("service.cv_parser.match_cv_to_job", return_value=match), \
                     patch("service.cv_parser.extract_text_from_file", return_value="CV"):
                    from workers.tasks import process_candidate_cv
                    process_candidate_cv(c.id)

                db.expire(c)
                db.refresh(c)

                if name == "A":
                    assert c.match_score == 85, f"Candidate A score wrong: {c.match_score}"
                    assert c.full_name == "Candidate A"
                else:
                    assert c.match_score == 30, f"Candidate B score wrong: {c.match_score}"
                    assert c.full_name == "Candidate B"
                    # Candidate B must NOT have Candidate A's data
                    assert c.full_name != "Candidate A"
            finally:
                os.unlink(tmp)
        db.close()


# ── BATCH PROCESSING TESTS ─────────────────────────────────────────────────────

class TestBatchProcessing:
    def test_bulk_upload_creates_batch(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "batch@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        files = [
            ("files", (f"cv_{i}.pdf", f"CV content {i}".encode(), "application/pdf"))
            for i in range(5)
        ]

        with patch("workers.tasks.dispatch_batch"):
            r = client.post(
                "/api/v1/candidates/bulk-upload",
                headers=_headers(user.id),
                data={"job_id": job.id},
                files=files,
            )

        assert r.status_code == 202
        data = r.json()
        assert "batch_id" in data
        assert data["queued"] == 5
        db.close()

    def test_batch_status_tracking(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "btrack@test.com", "recruiter")
        batch = BatchJob(
            org_id=org.id, recruiter_id=user.id,
            total=10, completed=7, failed=1, status="processing",
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        r = client.get(f"/api/v1/candidates/batches/{batch.id}", headers=_headers(user.id))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 10
        assert data["completed"] == 7
        assert data["failed"] == 1
        assert data["progress_pct"] == 80.0
        db.close()

    def test_failed_cv_does_not_stop_batch(self):
        """One failure must not stop processing of other candidates."""
        from workers.tasks import process_batch
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "bfail@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        batch = BatchJob(org_id=org.id, recruiter_id=user.id, total=3, status="pending")
        db.add(batch)
        db.commit()
        batch_id = batch.id

        tmp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(b"content")
                tmp_files.append(f.name)
                c = Candidate(
                    org_id=org.id, recruiter_id=user.id, job_id=job.id,
                    full_name=f"Batch {i}", batch_id=batch_id,
                    file_path=f.name, file_name=f"cv{i}.pdf",
                    status="Queued",  # must be Queued for batch to process
                )
                db.add(c)
        db.commit()

        cands = db.query(Candidate).filter(Candidate.batch_id == batch_id).all()
        candidate_ids = [c.id for c in cands]
        db.close()

        call_count = {"n": 0}

        def mock_process(cid):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("Simulated failure for candidate 2")
            d = TestingSession()
            cc = d.query(Candidate).filter(Candidate.id == cid).first()
            if cc:
                cc.status = "Under Review"
                cc.match_score = 70
                d.commit()
            d.close()
            return {"status": "Under Review", "match_score": 70}

        with patch("workers.tasks.process_candidate_cv", side_effect=mock_process):
            result = process_batch(candidate_ids, batch_id, max_concurrent=1)

        # All 3 attempted — batch continues despite 1 failure
        assert result["total"] == 3, f"Expected 3, got {result}"
        assert result["completed"] + result["failed"] + result["skipped"] == 3
        # Critical: failure count is exactly 1, processing continued for others
        assert result["failed"] == 1
        assert result["completed"] == 2  # 2 succeeded

        for f in tmp_files:
            try:
                os.unlink(f)
            except Exception:
                pass

    def test_idempotency_skips_processed(self):
        """Already-processed candidates are skipped in batch rerun."""
        from workers.tasks import process_batch
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "idemp@test.com", "recruiter")
        batch = BatchJob(org_id=org.id, recruiter_id=user.id, total=1, status="pending")
        db.add(batch)
        db.commit()

        c = Candidate(
            org_id=org.id, recruiter_id=user.id,
            full_name="Already Done", batch_id=batch.id,
            file_path="/tmp/fake.pdf", file_name="fake.pdf",
            status="Under Review",  # Already processed
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        with patch("workers.tasks.process_candidate_cv") as mock_process:
            result = process_batch([c.id], batch.id, max_concurrent=1)
            # Should skip, not reprocess
            mock_process.assert_not_called()
            assert result["skipped"] == 1
        db.close()


# ── SCORING & RANKING TESTS ────────────────────────────────────────────────────

class TestScoringRanking:
    def test_categorize_strong_match(self):
        from service.scoring import categorize_candidate
        cat = categorize_candidate(score=85.0)
        assert cat == "STRONG_MATCH"

    def test_categorize_potential_match(self):
        from service.scoring import categorize_candidate
        cat = categorize_candidate(score=65.0)
        assert cat == "POTENTIAL_MATCH"

    def test_categorize_weak_match(self):
        from service.scoring import categorize_candidate
        cat = categorize_candidate(score=45.0)
        assert cat == "WEAK_MATCH"

    def test_categorize_needs_review(self):
        from service.scoring import categorize_candidate
        cat = categorize_candidate(score=30.0)
        assert cat == "NEEDS_REVIEW"

    def test_categorize_knockout(self):
        from service.scoring import categorize_candidate
        cat = categorize_candidate(score=85.0, is_knocked_out=True)
        assert cat == "KNOCKOUT_FAILED"

    def test_ranking_order(self):
        from service.scoring import rerank_job_candidates
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "rank@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)

        scores = [90, 70, 85, 60, 95]
        for i, score in enumerate(scores):
            c = Candidate(
                org_id=org.id, recruiter_id=user.id, job_id=job.id,
                full_name=f"Candidate {i}", match_score=score, status="Under Review",
            )
            db.add(c)
        db.commit()

        rerank_job_candidates(db, job.id, user.id)

        ranked = db.query(Candidate).filter(
            Candidate.job_id == job.id
        ).order_by(Candidate.rank).all()

        assert ranked[0].match_score == 95  # rank 1
        assert ranked[1].match_score == 90  # rank 2
        assert ranked[2].match_score == 85  # rank 3
        db.close()

    def test_ranking_per_job_not_global(self):
        """Rankings are per-job, not global across all candidates."""
        from service.scoring import rerank_job_candidates
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "perjob@test.com", "recruiter")
        job1 = _make_job(db, org.id, user.id, "Job 1")
        job2 = _make_job(db, org.id, user.id, "Job 2")

        c1 = Candidate(org_id=org.id, recruiter_id=user.id, job_id=job1.id,
                       full_name="J1-High", match_score=90, status="Under Review")
        c2 = Candidate(org_id=org.id, recruiter_id=user.id, job_id=job2.id,
                       full_name="J2-High", match_score=80, status="Under Review")
        db.add_all([c1, c2])
        db.commit()

        rerank_job_candidates(db, job1.id, user.id)
        rerank_job_candidates(db, job2.id, user.id)

        db.refresh(c1)
        db.refresh(c2)

        # Both are rank 1 in their respective jobs
        assert c1.rank == 1
        assert c2.rank == 1
        db.close()

    def test_job_rankings_endpoint(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "rankep@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)

        for i, score in enumerate([80, 90, 70]):
            c = Candidate(
                org_id=org.id, recruiter_id=user.id, job_id=job.id,
                full_name=f"Candidate {i}", match_score=score,
                rank=3 - i, status="Under Review",
            )
            db.add(c)
        db.commit()

        r = client.get(f"/api/v1/jobs/{job.id}/rankings", headers=_headers(user.id))
        assert r.status_code == 200
        data = r.json()
        assert "rankings" in data
        db.close()


# ── KNOCKOUT TESTS ─────────────────────────────────────────────────────────────

class TestKnockoutRules:
    def test_experience_knockout(self):
        from service.scoring import apply_knockout_rules
        from models.database import KnockoutRule as KR

        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "ko1@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        rule = KR(
            job_id=job.id, org_id=org.id,
            rule_type="experience",
            description="Must have 5+ years experience",
            value="5",
            action="auto_reject",
            is_active=True,
        )
        db.add(rule)
        db.commit()

        candidate = _make_candidate(db, org.id, job.id, user.id)
        candidate.years_experience = 2.0
        db.commit()

        flags = apply_knockout_rules(db, job.id, candidate, {"years_experience": 2.0})
        assert len(flags) > 0
        assert "2.0" in flags[0] or "years" in flags[0].lower() or "5" in flags[0]
        db.close()

    def test_experience_passes(self):
        from service.scoring import apply_knockout_rules
        from models.database import KnockoutRule as KR

        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "ko2@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        rule = KR(
            job_id=job.id, org_id=org.id,
            rule_type="experience",
            description="Must have 2+ years",
            value="2", action="flag", is_active=True,
        )
        db.add(rule)
        db.commit()

        candidate = _make_candidate(db, org.id, job.id, user.id)
        candidate.years_experience = 5.0
        db.commit()

        flags = apply_knockout_rules(db, job.id, candidate, {"years_experience": 5.0})
        assert len(flags) == 0
        db.close()

    def test_knockout_candidate_not_deleted(self):
        """Knocked out candidates stay in DB with KNOCKOUT_FAILED status."""
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "kond@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        db.commit()

        from models.database import KnockoutRule as KR
        rule = KR(
            job_id=job.id, org_id=org.id,
            rule_type="experience",
            description="Must have 10+ years",
            value="10", action="auto_reject", is_active=True,
        )
        db.add(rule)
        db.commit()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"Junior developer CV")
            tmp = f.name

        try:
            c = Candidate(
                org_id=org.id, recruiter_id=user.id, job_id=job.id,
                full_name="Junior Dev", file_path=tmp, file_name="junior.pdf", status="Queued",
            )
            db.add(c)
            db.commit()
            db.refresh(c)

            mock_parsed = {
                "full_name": "Junior Dev", "email": "j@test.com", "phone": "+1",
                "current_position": "Junior", "years_experience": 1.0,
                "technical_skills": {}, "education": [], "location": "Cairo",
            }

            with patch("service.cv_parser.parse_cv_with_ai", return_value=mock_parsed), \
                 patch("service.cv_parser.match_cv_to_job", return_value={"overall_score": 30, "skill_match": 20, "experience_match": 10, "education_match": 50, "seniority_match": 10, "location_match": 70, "keyword_match": 30, "ats_score": 40, "ai_confidence": 80, "recommendation": "Reject", "recommendation_reason": "Too junior", "ai_summary": "Junior", "strengths": [], "weaknesses": ["inexperienced"], "missing_skills": [], "missing_certs": [], "matched_skills": [], "matched_requirements": [], "missing_requirements": [], "skill_gap_analysis": "", "ats_issues": [], "ats_suggestions": []}), \
                 patch("service.cv_parser.extract_text_from_file", return_value="Junior developer"):
                from workers.tasks import process_candidate_cv
                process_candidate_cv(c.id)

            db.refresh(c)
            # Candidate still exists
            assert db.query(Candidate).filter(Candidate.id == c.id).first() is not None
            assert c.is_knocked_out == True
            assert c.status == "Knockout Failed"
        finally:
            os.unlink(tmp)
        db.close()


# ── APPROVAL WORKFLOW TESTS ────────────────────────────────────────────────────

class TestApprovalWorkflow:
    def test_needs_review_by_default(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "dec1@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = _make_candidate(db, org.id, job.id, user.id)
        db.commit()

        r = client.get(f"/api/v1/candidates/{c.id}", headers=_headers(user.id))
        assert r.json()["recruiter_decision"] == "NEEDS_REVIEW"
        db.close()

    def test_approve_candidate(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "approve@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = _make_candidate(db, org.id, job.id, user.id)
        db.commit()

        r = client.post(
            f"/api/v1/candidates/{c.id}/decide",
            headers=_headers(user.id),
            json={"decision": "APPROVED", "notes": "Great candidate"},
        )
        assert r.status_code == 200
        assert r.json()["recruiter_decision"] == "APPROVED"
        assert r.json()["status"] == "Shortlisted"
        db.close()

    def test_reject_candidate(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "reject@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = _make_candidate(db, org.id, job.id, user.id)
        db.commit()

        r = client.post(
            f"/api/v1/candidates/{c.id}/decide",
            headers=_headers(user.id),
            json={"decision": "REJECTED", "notes": "Not qualified"},
        )
        assert r.status_code == 200
        assert r.json()["recruiter_decision"] == "REJECTED"
        assert r.json()["status"] == "Rejected"
        db.close()

    def test_ai_recommendation_does_not_override_decision(self):
        """AI says 'Strong Hire' but recruiter rejects — rejection must win."""
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "aivshr@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="AI Mismatch", match_score=95,
            recommendation="Strong Hire",  # AI says hire
            status="Under Review",
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        # Recruiter overrides
        r = client.post(
            f"/api/v1/candidates/{c.id}/decide",
            headers=_headers(user.id),
            json={"decision": "REJECTED", "notes": "Cultural mismatch"},
        )
        assert r.status_code == 200
        assert r.json()["recruiter_decision"] == "REJECTED"
        assert r.json()["status"] == "Rejected"
        # AI recommendation unchanged — it's advisory
        db.refresh(c)
        assert c.recommendation == "Strong Hire"
        db.close()

    def test_invalid_decision_rejected(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "invdec@test.com", "recruiter")
        job = _make_job(db, org.id, user.id)
        c = _make_candidate(db, org.id, job.id, user.id)
        db.commit()

        r = client.post(
            f"/api/v1/candidates/{c.id}/decide",
            headers=_headers(user.id),
            json={"decision": "MAYBE"},
        )
        assert r.status_code == 400
        db.close()


# ── DUPLICATE DETECTION TESTS ──────────────────────────────────────────────────

class TestDuplicateDetection:
    def test_same_email_is_duplicate(self):
        from service.duplicate_detector import find_duplicate
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "dup1@test.com")
        job = _make_job(db, org.id, user.id)

        original = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Original Ahmed", email="ahmed@test.com", status="Under Review",
        )
        db.add(original)
        db.commit()

        duplicate = Candidate(
            org_id=org.id, recruiter_id=user.id, job_id=job.id,
            full_name="Dup Ahmed", email="ahmed@test.com", status="Queued",
        )
        db.add(duplicate)
        db.commit()

        dup_id = find_duplicate(db, duplicate)
        assert dup_id == original.id
        db.close()

    def test_same_file_hash_is_duplicate(self):
        from service.duplicate_detector import find_duplicate
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "dup2@test.com")

        original = Candidate(
            org_id=org.id, recruiter_id=user.id,
            full_name="Hash Original", file_hash="abc123def456", status="Under Review",
        )
        db.add(original)
        db.commit()

        duplicate = Candidate(
            org_id=org.id, recruiter_id=user.id,
            full_name="Hash Duplicate", file_hash="abc123def456", status="Queued",
        )
        db.add(duplicate)
        db.commit()

        dup_id = find_duplicate(db, duplicate)
        assert dup_id == original.id
        db.close()

    def test_different_orgs_not_duplicate(self):
        from service.duplicate_detector import find_duplicate
        db = TestingSession()
        org1 = _make_org(db, "Dup Org 1")
        org2 = _make_org(db, "Dup Org 2")
        u1 = _make_user(db, org1.id, "dup3a@test.com")
        u2 = _make_user(db, org2.id, "dup3b@test.com")

        c1 = Candidate(
            org_id=org1.id, recruiter_id=u1.id,
            full_name="Org1 Cand", email="shared@email.com", status="Under Review",
        )
        db.add(c1)
        db.commit()

        c2 = Candidate(
            org_id=org2.id, recruiter_id=u2.id,
            full_name="Org2 Cand", email="shared@email.com", status="Queued",
        )
        db.add(c2)
        db.commit()

        # c2 should NOT be flagged as dup of c1 (different org)
        dup_id = find_duplicate(db, c2)
        assert dup_id is None
        db.close()


# ── PUBLIC APPLY TESTS ─────────────────────────────────────────────────────────

class TestPublicApply:
    def test_get_job_by_token(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "apply1@test.com")
        job = _make_job(db, org.id, user.id)
        db.commit()

        r = client.get(f"/apply/{job.apply_url_token}")
        assert r.status_code == 200
        assert r.json()["title"] == job.title
        db.close()

    def test_invalid_token_returns_404(self):
        r = client.get("/apply/invalid-token-xyz-999")
        assert r.status_code == 404

    def test_submit_application(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "apply2@test.com")
        job = _make_job(db, org.id, user.id)
        db.commit()

        with patch("workers.tasks.dispatch_cv"):
            r = client.post(
                f"/apply/{job.apply_url_token}",
                data={"full_name": "Public Applicant", "email": "pub@test.com", "phone": "+1234"},
                files={"cv_file": ("cv.pdf", b"My CV content", "application/pdf")},
            )
        assert r.status_code == 200
        assert "candidate_id" in r.json()
        db.close()

    def test_closed_job_rejects_application(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "apply3@test.com")
        job = _make_job(db, org.id, user.id)
        job.is_active = False
        db.commit()

        r = client.post(
            f"/apply/{job.apply_url_token}",
            data={"full_name": "Late Applicant", "email": "late@test.com"},
            files={"cv_file": ("cv.pdf", b"CV", "application/pdf")},
        )
        assert r.status_code == 404
        db.close()


# ── DASHBOARD TESTS ────────────────────────────────────────────────────────────

class TestDashboard:
    def test_stats_endpoint(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "dash@test.com", "owner")
        job = _make_job(db, org.id, user.id)
        _make_candidate(db, org.id, job.id, user.id)
        db.commit()

        r = client.get("/api/v1/dashboard/stats", headers=_headers(user.id))
        assert r.status_code == 200
        data = r.json()
        assert "total_candidates" in data
        assert "hiring_funnel" in data
        assert "category_breakdown" in data
        assert "decision_breakdown" in data
        db.close()

    def test_ai_config_endpoint(self):
        db = TestingSession()
        org = _make_org(db)
        user = _make_user(db, org.id, "aiconf@test.com")
        db.commit()

        r = client.get("/api/v1/dashboard/ai-config", headers=_headers(user.id))
        assert r.status_code == 200
        assert "agents" in r.json()
        db.close()


# ── HEALTH CHECK ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["version"] == "3.0.0"
