from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

USER_A: dict = {
    "name": "Alice",
    "occupation": "Software Engineer",
    "interests": ["AI", "Python"],
    "hobbies": ["Reading"],
}

USER_B: dict = {
    "name": "Bob",
    "occupation": "Data Scientist",
    "interests": ["ML", "Statistics"],
    "hobbies": [],
}


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
