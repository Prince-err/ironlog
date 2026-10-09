"""Shared fixtures for Iron Log tests.

API tests run entirely against an isolated in-memory SQLite database seeded
with the exercise catalog plus a fictional training history (built here via
tests/demo_history.py — the dev database starts clean and is never touched).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.workout import WorkoutSession


def _recompute_prs(db) -> None:
    """Recompute PRs from the seeded history (same as the dev seed used to)."""
    from sqlalchemy import select

    from app.db import seed as seed_module
    from app.services import prs as prs_service

    user = seed_module.ensure_demo_user(db)
    exercise_ids = {
        we.exercise_id
        for s in db.scalars(
            select(WorkoutSession).where(WorkoutSession.user_id == user.id)
        ).all()
        for we in s.exercises
    }
    for exercise_id in exercise_ids:
        prs_service.recompute_user_prs(db, user.id, exercise_id)


class TestClientWithDb(TestClient):
    """TestClient that also exposes the isolated DB's session factory."""

    session_factory: sessionmaker


@pytest.fixture()
def client() -> TestClientWithDb:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    Base.metadata.create_all(engine)

    from app.db import seed as seed_module
    from tests.demo_history import seed_demo_history

    session = TestingSession()
    try:
        seed_module.seed(session)
        seed_demo_history(session, seed_module.ensure_demo_user(session),
                          seed_module.ensure_exercise_catalog(session))
        _recompute_prs(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClientWithDb(app)
    test_client.session_factory = TestingSession
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture()
def headers() -> dict[str, str]:
    """Dev-only identity for the seeded demo user (id 1)."""
    return {"X-Demo-User-ID": "1"}


@pytest.fixture()
def db_session():
    """Raw DB session against an isolated in-memory SQLite DB (model tests)."""
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from app.db import seed as seed_module
    from tests.demo_history import seed_demo_history

    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        seed_module.seed(session)
        seed_demo_history(session, seed_module.ensure_demo_user(session),
                          seed_module.ensure_exercise_catalog(session))
        _recompute_prs(session)
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()
