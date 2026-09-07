import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database.database import Base, get_db
import database.models  # noqa: F401 - ensures User, Course, Module, Lesson are registered

# Isolated in-memory SQLite database configuration
# StaticPool maintains a single shared connection across all threads
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Dependency override providing a session from the isolated test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize schema immediately upon test module loading
Base.metadata.create_all(bind=test_engine)
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Session-level fixture initializing and tearing down the test database."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_db_per_test():
    """Cleans table rows between tests to ensure complete test isolation."""
    yield
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client():
    """Fixture providing a TestClient for tests requiring explicit dependency injection."""
    with TestClient(app) as test_client:
        yield test_client
