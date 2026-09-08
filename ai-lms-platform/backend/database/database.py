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
# If not explicitly configured or if postgres connection is not available, default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./lms.db"

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine according to database dialect
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True

try:
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    # Test connection if postgres
    if not DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            pass
except Exception as conn_err:
    logger.warning(
        "Could not connect to PostgreSQL (%s). Falling back to SQLite database.",
        conn_err,
    )
    DATABASE_URL = "sqlite:///./lms.db"
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
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
                if "learning_objectives" not in existing_columns:
                    logger.info("Migrating schema: adding 'learning_objectives' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN learning_objectives JSON DEFAULT NULL"))
                if "key_concepts" not in existing_columns:
                    logger.info("Migrating schema: adding 'key_concepts' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN key_concepts JSON DEFAULT NULL"))
                if "examples" not in existing_columns:
                    logger.info("Migrating schema: adding 'examples' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN examples JSON DEFAULT NULL"))
                if "key_takeaways" not in existing_columns:
                    logger.info("Migrating schema: adding 'key_takeaways' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN key_takeaways JSON DEFAULT NULL"))
                if "misconceptions" not in existing_columns:
                    logger.info("Migrating schema: adding 'misconceptions' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN misconceptions JSON DEFAULT NULL"))
                if "practice_questions" not in existing_columns:
                    logger.info("Migrating schema: adding 'practice_questions' to 'lessons' table.")
                    conn.execute(text("ALTER TABLE lessons ADD COLUMN practice_questions JSON DEFAULT NULL"))

        if "quizzes" in table_names:
            existing_quiz_cols = {col["name"] for col in inspector.get_columns("quizzes")}
            with eng.begin() as conn:
                if "quiz_type" not in existing_quiz_cols:
                    logger.info("Migrating schema: adding 'quiz_type' to 'quizzes' table.")
                    conn.execute(text("ALTER TABLE quizzes ADD COLUMN quiz_type VARCHAR(50) DEFAULT 'lesson_quiz'"))
                if "passing_score_percentage" not in existing_quiz_cols:
                    logger.info("Migrating schema: adding 'passing_score_percentage' to 'quizzes' table.")
                    conn.execute(text("ALTER TABLE quizzes ADD COLUMN passing_score_percentage INTEGER DEFAULT 70"))
                if "time_limit_minutes" not in existing_quiz_cols:
                    logger.info("Migrating schema: adding 'time_limit_minutes' to 'quizzes' table.")
                    conn.execute(text("ALTER TABLE quizzes ADD COLUMN time_limit_minutes INTEGER DEFAULT NULL"))
                if "is_fallback" not in existing_quiz_cols:
                    logger.info("Migrating schema: adding 'is_fallback' to 'quizzes' table.")
                    conn.execute(text("ALTER TABLE quizzes ADD COLUMN is_fallback BOOLEAN DEFAULT 0"))

        if "quiz_questions" in table_names:
            existing_qq_cols = {col["name"] for col in inspector.get_columns("quiz_questions")}
            with eng.begin() as conn:
                if "concept" not in existing_qq_cols:
                    logger.info("Migrating schema: adding 'concept' to 'quiz_questions' table.")
                    conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN concept VARCHAR(255) DEFAULT NULL"))
                if "points" not in existing_qq_cols:
                    logger.info("Migrating schema: adding 'points' to 'quiz_questions' table.")
                    conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN points INTEGER DEFAULT 1"))
                if "difficulty" not in existing_qq_cols:
                    logger.info("Migrating schema: adding 'difficulty' to 'quiz_questions' table.")
                    conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN difficulty VARCHAR(50) DEFAULT 'medium'"))
                if "order_number" not in existing_qq_cols:
                    logger.info("Migrating schema: adding 'order_number' to 'quiz_questions' table.")
                    conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN order_number INTEGER DEFAULT 1"))

        if "quiz_submissions" in table_names:
            existing_qs_cols = {col["name"] for col in inspector.get_columns("quiz_submissions")}
            with eng.begin() as conn:
                if "feedback" not in existing_qs_cols:
                    logger.info("Migrating schema: adding 'feedback' to 'quiz_submissions' table.")
                    conn.execute(text("ALTER TABLE quiz_submissions ADD COLUMN feedback JSON DEFAULT NULL"))

        if "user_mastery" in table_names:
            existing_um_cols = {col["name"] for col in inspector.get_columns("user_mastery")}
            with eng.begin() as conn:
                if "concept" not in existing_um_cols:
                    logger.info("Migrating schema: adding 'concept' to 'user_mastery' table.")
                    conn.execute(text("ALTER TABLE user_mastery ADD COLUMN concept VARCHAR(255) DEFAULT NULL"))
                if "attempts_count" not in existing_um_cols:
                    logger.info("Migrating schema: adding 'attempts_count' to 'user_mastery' table.")
                    conn.execute(text("ALTER TABLE user_mastery ADD COLUMN attempts_count INTEGER DEFAULT 1"))
                if "status" not in existing_um_cols:
                    logger.info("Migrating schema: adding 'status' to 'user_mastery' table.")
                    conn.execute(text("ALTER TABLE user_mastery ADD COLUMN status VARCHAR(50) DEFAULT 'needs_review'"))
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
