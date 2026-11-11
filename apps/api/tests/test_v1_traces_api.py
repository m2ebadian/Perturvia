from datetime import datetime
from uuid import uuid4

import pytest

STARTED_AT = "2026-11-11T21:00:00+00:00"


def create_trace(client, **fields):
    response = client.post("/v1/traces", json={"task": "analyze the repository", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def make_span(sequence, **fields):
    return {
        "id": str(uuid4()),
        "sequence": sequence,
        "kind": "tool",
        "name": "read_file",
        "status": "ok",
        "started_at": STARTED_AT,
        "duration_ms": 12.5,
        **fields,
    }


def post_spans(client, trace_id, spans):
    return client.post(f"/v1/traces/{trace_id}/spans", json={"spans": spans})


class TestCreateTrace:
    def test_applies_server_defaults(self, client):
        trace = create_trace(client)

        assert trace["status"] == "running"
        assert trace["config"] == {}
        assert trace["started_at"] is not None
        assert trace["ended_at"] is None

    def test_links_registered_agent(self, client):
        agent = client.post("/agents", json={"name": "repo-analyst"}).json()

        trace = create_trace(client, agent_id=agent["id"])

        assert trace["agent_id"] == agent["id"]

    def test_rejects_unknown_agent(self, client):
        response = client.post("/v1/traces", json={"task": "analyze", "agent_id": str(uuid4())})

        assert response.status_code == 422
        assert response.json() == {"detail": "Agent not found"}

    @pytest.mark.parametrize(
        "fields",
        [
            {"task": "   "},
            {"started_at": "2026-11-11T21:00:00"},
            {"seed": 2**63},
            {"trial_number": 0},
        ],
    )
    def test_rejects_invalid_fields(self, client, fields):
        response = client.post("/v1/traces", json={"task": "analyze", **fields})

        assert response.status_code == 422


class TestIngestSpans:
    def test_inserts_batch(self, client):
        trace = create_trace(client)

        response = post_spans(client, trace["id"], [make_span(0), make_span(1)])

        assert response.status_code == 201
        assert response.json() == {"received": 2, "inserted": 2}

    def test_retried_batch_is_not_duplicated(self, client):
        trace = create_trace(client)
        spans = [make_span(0), make_span(1)]
        post_spans(client, trace["id"], spans)

        retry = post_spans(client, trace["id"], spans)

        assert retry.status_code == 201
        assert retry.json() == {"received": 2, "inserted": 0}
        assert len(client.get(f"/v1/traces/{trace['id']}").json()["spans"]) == 2

    def test_partially_duplicated_batch_inserts_only_new_spans(self, client):
        trace = create_trace(client)
        first = make_span(0)
        post_spans(client, trace["id"], [first])

        response = post_spans(client, trace["id"], [first, make_span(1)])

        assert response.json() == {"received": 2, "inserted": 1}

    def test_rejects_unknown_trace(self, client):
        response = post_spans(client, uuid4(), [make_span(0)])

        assert response.status_code == 404
        assert response.json() == {"detail": "Trace not found"}

    def test_rejects_duplicate_sequence_and_keeps_batch_atomic(self, client):
        trace = create_trace(client)
        post_spans(client, trace["id"], [make_span(0)])

        response = post_spans(client, trace["id"], [make_span(1), make_span(0)])

        assert response.status_code == 409
        assert response.json() == {"detail": "Duplicate span sequence"}
        # The new span at sequence 1 must not be stored on its own.
        assert len(client.get(f"/v1/traces/{trace['id']}").json()["spans"]) == 1

    def test_rejects_error_type_on_successful_span(self, client):
        trace = create_trace(client)

        response = post_spans(client, trace["id"], [make_span(0, error_type="timeout")])

        assert response.status_code == 422

    def test_rejects_empty_batch(self, client):
        trace = create_trace(client)

        assert post_spans(client, trace["id"], []).status_code == 422

    def test_accepts_spans_after_trace_finishes(self, client):
        trace = create_trace(client)
        client.patch(f"/v1/traces/{trace['id']}", json={"status": "completed"})

        response = post_spans(client, trace["id"], [make_span(0)])

        assert response.status_code == 201


class TestFinishTrace:
    def test_completes_running_trace(self, client):
        trace = create_trace(client)

        response = client.patch(
            f"/v1/traces/{trace['id']}",
            json={"status": "completed", "final_output": "Found 9 endpoints."},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["final_output"] == "Found 9 endpoints."
        assert body["ended_at"] is not None

    def test_uses_client_ended_at_when_provided(self, client):
        trace = create_trace(client)

        response = client.patch(
            f"/v1/traces/{trace['id']}",
            json={"status": "failed", "ended_at": "2026-11-11T21:05:00+00:00"},
        )

        ended_at = datetime.fromisoformat(response.json()["ended_at"])
        assert ended_at == datetime.fromisoformat("2026-11-11T21:05:00+00:00")

    def test_rejects_finishing_twice(self, client):
        trace = create_trace(client)
        client.patch(f"/v1/traces/{trace['id']}", json={"status": "completed"})

        response = client.patch(f"/v1/traces/{trace['id']}", json={"status": "failed"})

        assert response.status_code == 409
        assert response.json() == {"detail": "Trace is already finished"}

    def test_rejects_unknown_trace(self, client):
        response = client.patch(f"/v1/traces/{uuid4()}", json={"status": "completed"})

        assert response.status_code == 404

    def test_rejects_running_as_target_status(self, client):
        trace = create_trace(client)

        response = client.patch(f"/v1/traces/{trace['id']}", json={"status": "running"})

        assert response.status_code == 422


class TestGetTrace:
    def test_returns_spans_in_sequence_order(self, client):
        trace = create_trace(client)
        post_spans(client, trace["id"], [make_span(2), make_span(0), make_span(1)])

        response = client.get(f"/v1/traces/{trace['id']}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == trace["id"]
        assert [span["sequence"] for span in body["spans"]] == [0, 1, 2]

    def test_returns_parent_links(self, client):
        trace = create_trace(client)
        parent = make_span(0, kind="agent", name="researcher")
        child = make_span(1, parent_span_id=parent["id"], agent_name="researcher")
        # Children usually arrive before their parent.
        post_spans(client, trace["id"], [child])
        post_spans(client, trace["id"], [parent])

        spans = client.get(f"/v1/traces/{trace['id']}").json()["spans"]

        assert spans[1]["parent_span_id"] == parent["id"]

    def test_rejects_unknown_trace(self, client):
        assert client.get(f"/v1/traces/{uuid4()}").status_code == 404


class TestListTraces:
    def test_returns_newest_first(self, client):
        older = create_trace(client, started_at="2026-11-11T20:00:00+00:00")
        newer = create_trace(client, started_at="2026-11-11T21:00:00+00:00")

        response = client.get("/v1/traces")

        assert response.status_code == 200
        assert [t["id"] for t in response.json()] == [newer["id"], older["id"]]

    def test_filters_by_agent(self, client):
        agent = client.post("/agents", json={"name": "repo-analyst"}).json()
        mine = create_trace(client, agent_id=agent["id"])
        create_trace(client)

        response = client.get("/v1/traces", params={"agent_id": agent["id"]})

        assert [t["id"] for t in response.json()] == [mine["id"]]

    def test_filters_by_experiment(self, client):
        experiment_id = str(uuid4())
        trial = create_trace(client, experiment_id=experiment_id, trial_number=1)
        create_trace(client)

        response = client.get("/v1/traces", params={"experiment_id": experiment_id})

        assert [t["id"] for t in response.json()] == [trial["id"]]

    def test_applies_limit(self, client):
        for _ in range(3):
            create_trace(client)

        response = client.get("/v1/traces", params={"limit": 2})

        assert len(response.json()) == 2

    @pytest.mark.parametrize("limit", [0, 201])
    def test_rejects_out_of_range_limit(self, client, limit):
        assert client.get("/v1/traces", params={"limit": limit}).status_code == 422
