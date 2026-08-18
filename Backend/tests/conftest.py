"""
Shared pytest configuration — single DB for all test files.
"""
import os
import pytest

# Set test environment BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///./test_talentai_shared.db"
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["LLM_PROVIDER"] = "groq"
os.environ["STORAGE_BACKEND"] = "local"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base, get_db
from main import app

TEST_DB_URL = "sqlite:///./test_talentai_shared.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="function")
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
