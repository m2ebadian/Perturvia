import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.database.dependencies import get_db
from main import app

API_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        # GitHub Actions sets CI; a skip there would leave CI green without testing PostgreSQL.
        if os.environ.get("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI")
        pytest.skip("TEST_DATABASE_URL is not set")

    # Tests truncate tables, so refuse anything that could be a real database.
    test_url = make_url(url)
    if not (test_url.database or "").endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must name a database ending in '_test'")
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app_url = make_url(database_url)
        same_database = (test_url.host, test_url.port or 5432, test_url.database) == (
            app_url.host,
            app_url.port or 5432,
            app_url.database,
        )
        if same_database:
            raise RuntimeError("TEST_DATABASE_URL must not point to the DATABASE_URL database")

    with pytest.MonkeyPatch.context() as monkeypatch:
        # migrations/env.py reads its connection URL from DATABASE_URL.
        monkeypatch.setenv("DATABASE_URL", url)
        command.upgrade(Config(str(API_DIR / "alembic.ini")), "head")

    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    # Clean before each test so leftovers from an aborted run can't leak in.
    with db_engine.begin() as connection:
        connection.execute(text("TRUNCATE tool_traces, agents"))

    return sessionmaker(bind=db_engine)


@pytest.fixture
def client(db_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db():
        db = db_session_factory()

        try:
            yield db
        finally:
            db.close()

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)

    if previous_override is None:
        del app.dependency_overrides[get_db]
    else:
        app.dependency_overrides[get_db] = previous_override
