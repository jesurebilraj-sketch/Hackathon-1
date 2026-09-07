import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database.database import Base, get_db
# Import models to ensure they are registered with Base.metadata
from database.models import User, Course, Module, Lesson  # noqa: F401
from tests.conftest import test_engine, TestingSessionLocal, override_get_db

# Ensure dependency override is active
Base.metadata.create_all(bind=test_engine)
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /health returns standard {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_endpoint():
    """Verify GET /health/db returns database connectivity status."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert data["status"] == "ok"


def test_root_endpoint():
    """Verify GET / returns API metadata and docs URL."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs_url" in data
    assert data["health_endpoint"] == "/health"


def test_courses_endpoint():
    """Verify GET /api/courses/ returns empty list when there are no courses."""
    response = client.get("/api/courses/")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "courses" in data
    assert data["count"] == 0
    assert data["courses"] == []


def test_lessons_endpoint():
    """Verify GET /api/lessons/ returns empty list when there are no lessons."""
    response = client.get("/api/lessons/")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "lessons" in data
    assert data["count"] == 0
    assert data["lessons"] == []
