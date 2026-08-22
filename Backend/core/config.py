from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "TalentAI"
    BASE_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-to-random-64-chars-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = "sqlite:///./talentai.db"

    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_CV_SIZE_MB: int = 10

    LLM_PROVIDER: str = "groq"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    GROQ_API_KEY: str = ""
    GROQ_API_KEYS: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "talentai_verify"

    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""

    PARSER_PROVIDER: str = "groq"
    MATCHER_PROVIDER: str = "groq"
    CHAT_PROVIDER: str = "groq"

    # Storage backend: local | s3
    STORAGE_BACKEND: str = "local"
    S3_BUCKET: str = "talentai-cvs"
    S3_ENDPOINT_URL: str = ""          # for Cloudflare R2 or MinIO
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # SMTP Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@talentai.io"
    SCORE_STRONG_MATCH: float = 80.0
    SCORE_POTENTIAL_MATCH: float = 60.0
    SCORE_WEAK_MATCH: float = 40.0

    # Batch processing
    BATCH_MAX_CONCURRENT: int = 10
    BATCH_RETRY_ATTEMPTS: int = 3

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
