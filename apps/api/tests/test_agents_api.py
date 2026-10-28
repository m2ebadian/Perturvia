from uuid import UUID, uuid4

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


def test_list_agents_returns_empty_list_when_no_agents_exist(client):
    response = client.get("/agents")

    assert response.status_code == 200
    assert response.json() == []


def test_list_agents_returns_newest_first(client):
    first = client.post("/agents", json={"name": "Agent 1"})
    second = client.post("/agents", json={"name": "Agent 2"})
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get("/agents")

    assert response.status_code == 200
    returned_ids = [agent["id"] for agent in response.json()]
    assert returned_ids == [second.json()["id"], first.json()["id"]]


def test_get_agent_returns_agent(client):
    created = client.post("/agents", json={"name": "Test Agent"})
    assert created.status_code == 201

    response = client.get(f"/agents/{created.json()['id']}")

    assert response.status_code == 200
    assert response.json() == created.json()


def test_get_agent_returns_404_when_agent_does_not_exist(client):
    response = client.get(f"/agents/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent not found"}


def test_get_agent_returns_422_for_malformed_id(client):
    response = client.get("/agents/not-a-uuid")

    assert response.status_code == 422
