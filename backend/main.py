import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

# Load environment configuration
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from database.database import init_db, check_db_connection, get_db
# Explicitly import models to guarantee registration on Base.metadata
from database.models import User, Course, Module, Lesson  # noqa: F401
from api import (
    courses_router,
    course_generation_router,
    lessons_router,
    quizzes_router,
    tutor_router,
    planner_router,
    analytics_router,
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("lms.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase: Initialize database models
    logger.info("Initializing application and database models...")
    try:
        init_db()
        logger.info("Database models initialized successfully.")
    except Exception as exc:
        logger.warning(
            "Database connection failed during startup: %s. "
            "Please verify DATABASE_URL in .env or start PostgreSQL.",
            exc,
        )
    yield
    # Shutdown phase
    logger.info("Application shutting down.")


app = FastAPI(
    title="AI-Powered LMS & Course Builder API",
    description="Backend REST API for AI-powered course generation, personalized tutoring, and analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend integration
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Predictable error response format for unexpected exceptions."""
    logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "path": request.url.path},
    )


@app.get("/", summary="Root API Index")
def root():
    return {
        "name": "AI-Powered Learning Management System & Course Builder API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_endpoint": "/health",
    }


@app.get("/health", summary="Health check endpoint")
def health_check():
    """Health endpoint returning standard ok response."""
    return {"status": "ok"}


@app.get("/health/db", summary="Database health check")
def health_db_check(db: Session = Depends(get_db)):
    """Detailed database connectivity check."""
    try:
        db.execute(text("SELECT 1"))
        db_name = getattr(getattr(db.bind, "url", None), "database", None) or "sqlite"
        return {
            "status": "ok",
            "database": {"status": "connected", "database": db_name},
        }
    except Exception as exc:
        logger.warning("Database health check failed via session: %s", exc)
        db_status = check_db_connection()
        return {
            "status": "ok" if db_status.get("status") == "connected" else "degraded",
            "database": db_status,
        }


# Register modular API routers
app.include_router(courses_router)
app.include_router(course_generation_router)
app.include_router(lessons_router)
app.include_router(quizzes_router)
app.include_router(tutor_router)
app.include_router(planner_router)
app.include_router(analytics_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
