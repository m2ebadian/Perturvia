import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.books import BOOKS


@pytest.fixture
def client():
    BOOKS.clear()
    return TestClient(app)
