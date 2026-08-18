"""
Migration helper — run this to upgrade an existing TalentAI v2 DB to v3.
Adds all new columns safely (ignores if already exists).
"""
from sqlalchemy import text
from models.database import SessionLocal, engine, Base, init_db
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run():
    print("TalentAI v2 → v3 Migration")

    # Create all new tables first
    init_db()
    print("✓ Schema created/verified")

    db = SessionLocal()
    migrations = [
        # candidates new columns
        ("candidates", "recruiter_id", "ALTER TABLE candidates ADD COLUMN recruiter_id INTEGER"),
        ("candidates", "batch_id",     "ALTER TABLE candidates ADD COLUMN batch_id INTEGER"),
        ("candidates", "file_hash",    "ALTER TABLE candidates ADD COLUMN file_hash VARCHAR(64)"),
        ("candidates", "category",     "ALTER TABLE candidates ADD COLUMN category VARCHAR(50) DEFAULT 'NEEDS_REVIEW'"),
        ("candidates", "recruiter_decision", "ALTER TABLE candidates ADD COLUMN recruiter_decision VARCHAR(50) DEFAULT 'NEEDS_REVIEW'"),
        ("candidates", "decision_notes",    "ALTER TABLE candidates ADD COLUMN decision_notes TEXT"),
        ("candidates", "decided_at",        "ALTER TABLE candidates ADD COLUMN decided_at DATETIME"),
        ("candidates", "decided_by",        "ALTER TABLE candidates ADD COLUMN decided_by INTEGER"),
        ("candidates", "rank",              "ALTER TABLE candidates ADD COLUMN rank INTEGER"),
        ("candidates", "processing_attempts", "ALTER TABLE candidates ADD COLUMN processing_attempts INTEGER DEFAULT 0"),
        ("candidates", "last_error",        "ALTER TABLE candidates ADD COLUMN last_error TEXT"),
        ("candidates", "interview_scheduled","ALTER TABLE candidates ADD COLUMN interview_scheduled DATETIME"),
        # job_descriptions new columns
        ("job_descriptions", "recruiter_id",          "ALTER TABLE job_descriptions ADD COLUMN recruiter_id INTEGER"),
        ("job_descriptions", "max_experience",         "ALTER TABLE job_descriptions ADD COLUMN max_experience INTEGER"),
        ("job_descriptions", "score_strong_match",    "ALTER TABLE job_descriptions ADD COLUMN score_strong_match FLOAT DEFAULT 80.0"),
        ("job_descriptions", "score_potential_match", "ALTER TABLE job_descriptions ADD COLUMN score_potential_match FLOAT DEFAULT 60.0"),
        ("job_descriptions", "score_weak_match",      "ALTER TABLE job_descriptions ADD COLUMN score_weak_match FLOAT DEFAULT 40.0"),
        # knockout_rules new columns
        ("knockout_rules", "is_mandatory", "ALTER TABLE knockout_rules ADD COLUMN is_mandatory BOOLEAN DEFAULT 1"),
    ]

    ok, skip = 0, 0
    for table, col, sql in migrations:
        try:
            db.execute(text(sql))
            db.commit()
            print(f"  ✓ {table}.{col}")
            ok += 1
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                skip += 1
            else:
                print(f"  ✗ {table}.{col}: {e}")
            db.rollback()

    # Backfill recruiter_id from hr_id or created_by where missing
    try:
        db.execute(text("""
            UPDATE candidates SET recruiter_id = hr_id
            WHERE recruiter_id IS NULL AND hr_id IS NOT NULL
        """))
        db.execute(text("""
            UPDATE job_descriptions SET recruiter_id = COALESCE(hr_id, created_by)
            WHERE recruiter_id IS NULL
        """))
        db.commit()
        print("✓ Backfilled recruiter_id from hr_id")
    except Exception as e:
        print(f"Backfill warning: {e}")
        db.rollback()

    db.close()
    print(f"\nDone: {ok} applied, {skip} already existed")


if __name__ == "__main__":
    run()
