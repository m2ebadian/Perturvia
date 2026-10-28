import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

API_DIR = Path(__file__).resolve().parent.parent


def test_health_check():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_without_database_url():
    # A fresh interpreter tests import-time behavior without touching this process's modules.
    env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
    script = "\n".join(
        [
            "from fastapi.testclient import TestClient",
            "from app.database.session import get_engine",
            "from main import app",
            "response = TestClient(app).get('/health')",
            "assert response.status_code == 200, response.status_code",
            "assert response.json() == {'status': 'ok'}, response.json()",
            "assert get_engine.cache_info().currsize == 0, 'engine was created'",
        ]
    )

    result = subprocess.run(
        [sys.executable, "-c", script], cwd=API_DIR, env=env, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
