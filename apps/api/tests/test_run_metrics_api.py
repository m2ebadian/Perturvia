from uuid import uuid4

import pytest

NOT_INJECTED = {"latency_ms": 0.0, "failure_injected": False}
INJECTED = {"latency_ms": 0.0, "failure_injected": True}


def create_trace(client, run_id, status, fault_injection):
    response = client.post(
        "/traces",
        json={
            "run_id": str(run_id),
            "tool_name": "echo",
            "arguments": {"message": "hello"},
            "status": status,
            "duration_ms": 10.0,
            "started_at": "2026-10-31T18:00:00+00:00",
            "fault_injection": fault_injection,
        },
    )
    assert response.status_code == 201


def test_run_metrics_for_twenty_trial_experiment(client):
    run_id = uuid4()
    for _ in range(15):
        create_trace(client, run_id, "success", NOT_INJECTED)
    for _ in range(5):
        create_trace(client, run_id, "client_exception", INJECTED)

    response = client.get(f"/runs/{run_id}/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": str(run_id),
        "total_calls": 20,
        "successful_calls": 15,
        "tool_errors": 0,
        "client_exceptions": 5,
        "injected_failures": 5,
        "observed_failure_rate": 0.25,
        "natural_failure_rate": 0.0,
    }


def test_run_metrics_separates_natural_from_injected_failures(client):
    run_id = uuid4()
    create_trace(client, run_id, "success", NOT_INJECTED)
    # Traces recorded before fault injection existed have no metadata.
    create_trace(client, run_id, "success", None)
    create_trace(client, run_id, "tool_error", NOT_INJECTED)
    create_trace(client, run_id, "client_exception", None)
    create_trace(client, run_id, "client_exception", INJECTED)
    create_trace(client, run_id, "client_exception", INJECTED)

    body = client.get(f"/runs/{run_id}/metrics").json()

    assert body["total_calls"] == 6
    assert body["successful_calls"] == 2
    assert body["tool_errors"] == 1
    assert body["client_exceptions"] == 3
    assert body["injected_failures"] == 2
    assert body["observed_failure_rate"] == pytest.approx(4 / 6)
    assert body["natural_failure_rate"] == 0.5


def test_run_metrics_natural_rate_is_null_when_every_call_is_injected(client):
    run_id = uuid4()
    for _ in range(3):
        create_trace(client, run_id, "client_exception", INJECTED)

    body = client.get(f"/runs/{run_id}/metrics").json()

    assert body["observed_failure_rate"] == 1.0
    assert body["natural_failure_rate"] is None


def test_run_metrics_counts_only_requested_run(client):
    run_a = uuid4()
    run_b = uuid4()
    create_trace(client, run_a, "success", NOT_INJECTED)
    create_trace(client, run_b, "client_exception", INJECTED)

    body = client.get(f"/runs/{run_a}/metrics").json()

    assert body["total_calls"] == 1
    assert body["injected_failures"] == 0


def test_run_metrics_returns_404_for_unknown_run(client):
    response = client.get(f"/runs/{uuid4()}/metrics")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_run_metrics_rejects_malformed_run_id(client):
    response = client.get("/runs/not-a-uuid/metrics")

    assert response.status_code == 422
