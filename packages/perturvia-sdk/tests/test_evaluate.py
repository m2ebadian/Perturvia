import json
import logging
from uuid import uuid4

import httpx
import pytest

import perturvia
from perturvia import _tracing

TRACE_ID = str(uuid4())

TRACE = {
    "id": TRACE_ID,
    "status": "completed",
    "final_output": "Done.",
    "spans": [
        {
            "kind": "tool",
            "name": "read_file",
            "status": "error",
            "sequence": 1,
            "fault": {"type": "error"},
            "attributes": {"tool.arguments": '{"path": "a.py"}'},
        },
        {
            "kind": "tool",
            "name": "read_file",
            "status": "ok",
            "sequence": 2,
            "fault": None,
            "attributes": {"tool.arguments": '{"path": "a.py"}'},
        },
    ],
}

BUILT_IN_OUTCOME = {
    "evaluator_version": 1,
    "tool_errors": {"natural": 0, "injected": 1},
    "recovery": {"failed": 1, "recovered": 1, "abandoned": 0, "rate": 1.0},
    "injection_followed": None,
}


@pytest.fixture
def api(fake_api):
    fake_api.status_code = 200
    fake_api.response_json = TRACE
    return fake_api


def test_fetches_the_trace_then_stores_and_returns_the_outcome(api):
    outcome = perturvia.evaluate(TRACE_ID)

    assert outcome == BUILT_IN_OUTCOME
    assert [(r.method, r.url.path) for r in api.requests] == [
        ("GET", f"/v1/traces/{TRACE_ID}"),
        ("PUT", f"/v1/traces/{TRACE_ID}/outcome"),
    ]
    assert json.loads(api.requests[1].content) == BUILT_IN_OUTCOME


def test_merges_custom_checks_in_order(api):
    checks = [
        lambda t: {"benchmark": "repo_analysis@1", "final_status": t["status"]},
        lambda t: {"task_success": True},
    ]

    outcome = perturvia.evaluate(TRACE_ID, checks=checks)

    assert outcome == {
        **BUILT_IN_OUTCOME,
        "benchmark": "repo_analysis@1",
        "final_status": "completed",
        "task_success": True,
    }
    assert api.calls("PUT", "/outcome") == [outcome]


def test_accepts_a_uuid(api):
    perturvia.evaluate(uuid4())

    assert api.requests[0].method == "GET"


def warnings(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name.startswith("perturvia")]


def assert_single_line_warning(caplog) -> logging.LogRecord:
    """Exactly one warning, one line long, with no traceback attached."""
    records = warnings(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.exc_info is None
    assert "\n" not in record.getMessage()
    assert TRACE_ID in record.getMessage()
    return record


def raise_(exc):
    def fail(*args, **kwargs):
        raise exc

    return fail


class TestNetworkFailures:
    def test_unreachable_api_returns_none_and_logs_one_line(self, api, caplog, monkeypatch):
        monkeypatch.setattr(_tracing._client, "get", raise_(httpx.ConnectError("refused")))

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID) is None

        record = assert_single_line_warning(caplog)
        assert "ConnectError: refused" in record.getMessage()

    @pytest.mark.parametrize("status", [404, 500])
    def test_error_status_on_fetch_logs_one_line(self, api, caplog, status):
        api.status_by_method["GET"] = status

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID) is None

        assert [r.method for r in api.requests] == ["GET"]
        # httpx's own message has a second line with a docs link; it is dropped.
        assert str(status) in assert_single_line_warning(caplog).getMessage()

    def test_error_status_on_store_logs_one_line(self, api, caplog):
        api.status_by_method["PUT"] = 500

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID) is None

        assert "500" in assert_single_line_warning(caplog).getMessage()

    def test_timeout_on_store_logs_one_line(self, api, caplog, monkeypatch):
        monkeypatch.setattr(_tracing._client, "put", raise_(httpx.ReadTimeout("")))

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID) is None

        # An empty message still names the error.
        assert assert_single_line_warning(caplog).getMessage().endswith("ReadTimeout")


class TestUnexpectedFailures:
    def test_malformed_trace_logs_a_traceback(self, api, caplog):
        api.response_json = {"id": TRACE_ID}

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID) is None

        [record] = warnings(caplog)
        assert record.exc_info is not None
        assert [r.method for r in api.requests] == ["GET"]

    def test_unserializable_check_result_logs_a_traceback(self, api, caplog):
        with caplog.at_level(logging.WARNING, logger="perturvia"):
            assert perturvia.evaluate(TRACE_ID, checks=[lambda t: {"files": {"a.py"}}]) is None

        [record] = warnings(caplog)
        assert record.exc_info is not None


class TestFailingChecks:
    def test_failing_check_is_recorded_and_the_rest_is_stored(self, api, caplog):
        def ground_truth_check(trace):
            raise KeyError("ground_truth")

        def working_check(trace):
            return {"task_success": True}

        with caplog.at_level(logging.WARNING, logger="perturvia"):
            outcome = perturvia.evaluate(TRACE_ID, checks=[ground_truth_check, working_check])

        assert outcome == {
            **BUILT_IN_OUTCOME,
            "task_success": True,
            "check_errors": ["ground_truth_check: KeyError: 'ground_truth'"],
        }
        assert api.calls("PUT", "/outcome") == [outcome]
        # A check failure is a bug in the check, so its traceback is kept.
        [record] = warnings(caplog)
        assert record.exc_info is not None
        assert "ground_truth_check" in record.getMessage()

    def test_every_failing_check_is_recorded(self, api):
        checks = [lambda t: 1 / 0, lambda t: ["not", "a", "dict"]]

        outcome = perturvia.evaluate(TRACE_ID, checks=checks)

        assert outcome["check_errors"] == [
            "<lambda>: ZeroDivisionError: division by zero",
            "<lambda>: TypeError: returned list, expected dict",
        ]

    def test_falls_back_to_repr_for_checks_without_a_name(self, api):
        class Broken:
            def __call__(self, trace):
                raise ValueError("bad")

            def __repr__(self):
                return "Broken()"

        outcome = perturvia.evaluate(TRACE_ID, checks=[Broken()])

        assert outcome["check_errors"] == ["Broken(): ValueError: bad"]

    def test_no_check_errors_key_when_every_check_succeeds(self, api):
        outcome = perturvia.evaluate(TRACE_ID, checks=[lambda t: {"task_success": True}])

        assert "check_errors" not in outcome


def test_requires_init(monkeypatch):
    monkeypatch.setattr(_tracing, "_client", None)

    with pytest.raises(RuntimeError, match="init"):
        perturvia.evaluate(TRACE_ID)
