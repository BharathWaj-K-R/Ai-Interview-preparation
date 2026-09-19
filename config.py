import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parent
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    # Render (and many hosts) provide DATABASE_URL as postgres:// or postgresql://
    # which SQLAlchemy routes to the old psycopg2 driver.
    # We use psycopg3 (psycopg[binary]), so rewrite the scheme here.
    _raw_db_url = os.getenv("DATABASE_URL", "")
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif _raw_db_url.startswith("postgresql://"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    DATABASE_URL = _raw_db_url or None
    SQLALCHEMY_DATABASE_URI = _raw_db_url or f"sqlite:///{(BASE_DIR / 'instance' / 'interview.sqlite3').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    MAX_QUESTIONS = int(os.getenv("MAX_QUESTIONS", "5"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(5 * 1024 * 1024)))
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "0").lower() in {"1", "true", "yes"}
