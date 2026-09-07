import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

# Locate .env file in backend/ directory or root directory
backend_env = Path(__file__).resolve().parent.parent / ".env"
root_env = Path(__file__).resolve().parent.parent.parent / ".env"
if backend_env.exists():
    load_dotenv(dotenv_path=backend_env)
elif root_env.exists():
    load_dotenv(dotenv_path=root_env)
else:
    load_dotenv()

logger = logging.getLogger("lms.database")

# Read DATABASE_URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lms_db")

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine according to database dialect
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema(eng):
    """
    Safely inspects existing tables and performs lightweight column additions
    if columns are missing from existing development or PostgreSQL databases.
    """
    try:
        inspector = inspect(eng)
        table_names = inspector.get_table_names()
        if "lessons" in table_names:
            existing_columns = {col["name"] for col in inspector.get_columns("lessons")}
            with eng.begin() as conn:
                if "estimated_minutes" not in existing_columns:
                    logger.info("Migrating schema: adding 'estimated_minutes' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN estimated_minutes INTEGER DEFAULT 20"))
                if "difficulty" not in existing_columns:
                    logger.info("Migrating schema: adding 'difficulty' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN difficulty VARCHAR(50) DEFAULT 'beginner'"))
                if "source_pages" not in existing_columns:
                    logger.info("Migrating schema: adding 'source_pages' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN source_pages JSON DEFAULT NULL"))
    except Exception as exc:
        logger.warning("Lightweight schema migration check notice: %s", exc)


def init_db(target_engine=None):
    """Initializes all registered database tables and applies lightweight migrations."""
    from . import models  # noqa: F401 - ensures all models are registered on Base.metadata
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    migrate_schema(eng)
    logger.info("Database tables initialized successfully.")


def check_db_connection(target_engine=None) -> dict:
    """Verifies that the database engine can establish an active connection."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "connected", "database": eng.url.database or "sqlite"}
    except Exception as exc:
        logger.warning("Database connection check failed: %s", exc)
        return {"status": "disconnected", "error": str(exc)}
