from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models.agent import Agent


def test_create_agent_returns_created_agent(client):
    response = client.post("/agents", json={"name": " Test Agent ", "description": "Runs evals"})

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert UUID(body["id"]).version == 7
    assert body["name"] == "Test Agent"
    assert body["description"] == "Runs evals"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_agent_persists_to_database(client, db_session_factory):
    response = client.post("/agents", json={"name": "Test Agent"})
    agent_id = UUID(response.json()["id"])

    with db_session_factory() as db:
        agent = db.get(Agent, agent_id)

        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.description is None


@pytest.mark.parametrize("payload", [{}, {"name": "   "}, {"name": "a" * 256}])
def test_create_agent_rejects_invalid_input(client, db_session_factory, payload):
    response = client.post("/agents", json=payload)

    assert response.status_code == 422
    with db_session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Agent)) == 0
