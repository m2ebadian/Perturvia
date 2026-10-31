from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.models.agent import ToolTrace


def make_trace_payload(**overrides):
    payload = {
        "run_id": str(uuid4()),
        "tool_name": "echo",
        "arguments": {"message": "hello"},
        "result": [{"type": "text", "text": "hello"}],
        "status": "success",
        "duration_ms": 12.5,
        "started_at": "2026-10-31T18:00:00+00:00",
    }
    payload.update(overrides)
    return payload


def count_traces(db_session_factory):
    with db_session_factory() as db:
        return db.scalar(select(func.count()).select_from(ToolTrace))


def test_create_trace_without_agent_returns_created_trace(client):
    payload = make_trace_payload()

    response = client.post("/traces", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"]).version == 7
    assert body["created_at"] is not None
    assert body["run_id"] == payload["run_id"]
    assert body["agent_id"] is None
    assert body["tool_name"] == "echo"
    assert body["arguments"] == {"message": "hello"}
    assert body["result"] == [{"type": "text", "text": "hello"}]
    assert body["status"] == "success"
    assert body["error_message"] is None
    assert body["duration_ms"] == 12.5
    assert datetime.fromisoformat(body["started_at"]) == datetime.fromisoformat(
        payload["started_at"]
    )


def test_create_trace_persists_to_database(client, db_session_factory):
    payload = make_trace_payload(
        tool_name="fail",
        arguments={},
        result=[{"type": "text", "text": "Simulated tool failure"}],
        status="tool_error",
        error_message="Simulated tool failure",
    )

    response = client.post("/traces", json=payload)
    trace_id = UUID(response.json()["id"])

    with db_session_factory() as db:
        trace = db.get(ToolTrace, trace_id)

        assert trace is not None
        assert trace.run_id == UUID(payload["run_id"])
        assert trace.agent_id is None
        assert trace.tool_name == "fail"
        assert trace.arguments == {}
        assert trace.result == [{"type": "text", "text": "Simulated tool failure"}]
        assert trace.status == "tool_error"
        assert trace.error_message == "Simulated tool failure"
        assert trace.duration_ms == 12.5
        assert trace.started_at == datetime.fromisoformat(payload["started_at"])


def test_create_trace_with_existing_agent(client, db_session_factory):
    agent = client.post("/agents", json={"name": "Test Agent"})
    assert agent.status_code == 201
    agent_id = agent.json()["id"]

    response = client.post("/traces", json=make_trace_payload(agent_id=agent_id))

    assert response.status_code == 201
    assert response.json()["agent_id"] == agent_id
    with db_session_factory() as db:
        trace = db.get(ToolTrace, UUID(response.json()["id"]))
        assert trace.agent_id == UUID(agent_id)


def test_create_trace_rejects_nonexistent_agent(client, db_session_factory):
    response = client.post("/traces", json=make_trace_payload(agent_id=str(uuid4())))

    assert response.status_code == 422
    assert response.json() == {"detail": "Agent not found"}
    assert count_traces(db_session_factory) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"duration_ms": -1},
        {"status": "ok"},
        {"started_at": "2026-10-31T18:00:00"},
        {"tool_name": "   "},
        {"tool_name": "a" * 256},
        {"run_id": "not-a-uuid"},
        {"arguments": ["not", "an", "object"]},
    ],
)
def test_create_trace_rejects_invalid_input(client, db_session_factory, overrides):
    response = client.post("/traces", json=make_trace_payload(**overrides))

    assert response.status_code == 422
    assert count_traces(db_session_factory) == 0


@pytest.mark.parametrize(
    "field", ["run_id", "tool_name", "arguments", "status", "duration_ms", "started_at"]
)
def test_create_trace_rejects_missing_required_field(client, db_session_factory, field):
    payload = make_trace_payload()
    del payload[field]

    response = client.post("/traces", json=payload)

    assert response.status_code == 422
    assert count_traces(db_session_factory) == 0
