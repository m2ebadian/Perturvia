from uuid import uuid4


def create_trace(client, run_id, tool_name, started_at):
    response = client.post(
        "/traces",
        json={
            "run_id": str(run_id),
            "tool_name": tool_name,
            "arguments": {},
            "status": "success",
            "duration_ms": 10.0,
            "started_at": started_at,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_read_traces_returns_run_traces_oldest_first(client):
    run_id = uuid4()
    # Created out of order to prove the endpoint sorts by started_at.
    second = create_trace(client, run_id, "fail", "2026-10-31T18:00:05+00:00")
    first = create_trace(client, run_id, "echo", "2026-10-31T18:00:00+00:00")

    response = client.get("/traces", params={"run_id": str(run_id)})

    assert response.status_code == 200
    returned_ids = [trace["id"] for trace in response.json()]
    assert returned_ids == [first["id"], second["id"]]


def test_read_traces_returns_only_requested_run(client):
    run_a = uuid4()
    run_b = uuid4()
    trace_a = create_trace(client, run_a, "echo", "2026-10-31T18:00:00+00:00")
    create_trace(client, run_b, "echo", "2026-10-31T18:00:00+00:00")

    response = client.get("/traces", params={"run_id": str(run_a)})

    assert response.status_code == 200
    returned_ids = [trace["id"] for trace in response.json()]
    assert returned_ids == [trace_a["id"]]


def test_read_traces_returns_empty_list_for_unknown_run(client):
    response = client.get("/traces", params={"run_id": str(uuid4())})

    assert response.status_code == 200
    assert response.json() == []


def test_read_traces_rejects_malformed_run_id(client):
    response = client.get("/traces", params={"run_id": "not-a-uuid"})

    assert response.status_code == 422


def test_read_traces_requires_run_id(client):
    response = client.get("/traces")

    assert response.status_code == 422
