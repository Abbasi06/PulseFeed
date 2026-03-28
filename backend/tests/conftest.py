from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import routes.feed as _feed_route
import routes.events as _events_route
from database import Base, get_db
from main import app

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

USER_A: dict = {
    "name": "Alice",
    "occupation": "Software Engineer",
    "selected_chips": ["AI", "Python"],
}

USER_B: dict = {
    "name": "Bob",
    "occupation": "Data Scientist",
    "selected_chips": ["ML", "Statistics"],
}


# ---------------------------------------------------------------------------
# Reset module-level cooldown trackers before every test so that tests that
# call POST /feed/{id}/refresh or POST /events/{id}/refresh don't bleed into
# each other via the 60-second in-memory cooldown dict.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_refresh_cooldowns() -> Generator[None, None, None]:
    _feed_route._last_refresh.clear()
    _events_route._last_refresh.clear()
    _feed_route._generating.clear()
    _events_route._generating.clear()
    yield


@pytest.fixture(autouse=True)
def isolate_generator_db() -> Generator[None, None, None]:
    """
    Prevent tests from reading the real generator.db on disk.
    With _open_generator_db returning None, personalize_feed falls back to
    research_agent.generate_feed — the path all tests were written to exercise.
    """
    with patch("agents.feed_personalizer._open_generator_db", return_value=None):
        yield


# ---------------------------------------------------------------------------
# DB fixture — fresh in-memory SQLite per test
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    # StaticPool ensures all connections share the same in-memory database,
    # so tables created here are visible to every subsequent connection.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Client fixture — TestClient with overridden DB dependency
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: (yield db)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
