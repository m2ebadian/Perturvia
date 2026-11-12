import logging
from datetime import datetime

import pytest
from opentelemetry.trace import INVALID_SPAN

import perturvia
from perturvia import _tracing


class Boom(Exception):
    pass


class TestRun:
    def test_requires_init(self, monkeypatch):
        monkeypatch.setattr(_tracing, "_tracer", None)

        with pytest.raises(RuntimeError, match="init"):
            with perturvia.run("task"):
                pass

    def test_creates_and_completes_trace(self, fake_api):
        with perturvia.run("analyze repo", seed=7) as run:
            run.final_output = "Found 9 endpoints."

        (created,) = fake_api.calls("POST", "/v1/traces")
        (finished,) = fake_api.calls("PATCH")
        assert created["id"] == str(run.trace_id)
        assert created["task"] == "analyze repo"
        assert created["seed"] == 7
        assert finished["status"] == "completed"
        assert finished["final_output"] == "Found 9 endpoints."

    def test_reraises_user_exception_and_marks_trace_failed(self, fake_api):
        with pytest.raises(Boom):
            with perturvia.run("analyze repo"):
                raise Boom("agent crashed")

        (finished,) = fake_api.calls("PATCH")
        assert finished["status"] == "failed"

    def test_flushes_spans_before_finishing(self, fake_api):
        with perturvia.run("analyze repo"):
            with perturvia.span("read_file", kind="tool"):
                pass

        methods = [r.method for r in fake_api.requests]
        assert methods.index("PATCH") > max(
            i for i, r in enumerate(fake_api.requests) if r.url.path.endswith("/spans")
        )

    def test_api_failure_does_not_break_agent(self, fake_api, caplog):
        fake_api.status_code = 500
        ran = False

        with caplog.at_level(logging.WARNING):
            with perturvia.run("analyze repo"):
                ran = True

        assert ran
        assert "POST /v1/traces failed" in caplog.text

    def test_unserializable_config_does_not_break_agent(self, fake_api):
        ran = False

        with perturvia.run("analyze repo", config={"started": datetime.now()}):
            ran = True

        assert ran

    def test_non_string_final_output_is_converted(self, fake_api):
        class Report:
            def __str__(self):
                return "Report(9 endpoints)"

        with perturvia.run("analyze repo") as run:
            run.final_output = Report()

        (finished,) = fake_api.calls("PATCH")
        assert finished == {
            **finished,
            "status": "completed",
            "final_output": "Report(9 endpoints)",
        }


class TestSpan:
    def test_records_kind_agent_name_and_retry_link(self, fake_api):
        with perturvia.run("analyze repo"):
            with perturvia.span("researcher", agent_name="researcher"):
                with perturvia.span("read_file", kind="tool") as first:
                    pass
                with perturvia.span("read_file", kind="tool", retry_of=first):
                    pass

        spans = [s for batch in fake_api.calls("POST", "/spans") for s in batch["spans"]]
        by_sequence = {s["sequence"]: s for s in spans}
        assert by_sequence[1]["agent_name"] == "researcher"
        assert by_sequence[2]["kind"] == "tool"
        assert by_sequence[2]["parent_span_id"] == by_sequence[1]["id"]
        assert by_sequence[3]["retry_of_span_id"] == by_sequence[2]["id"]

    def test_records_error_type_and_reraises(self, fake_api):
        with pytest.raises(TimeoutError):
            with perturvia.run("analyze repo"):
                with perturvia.span("read_file", kind="tool"):
                    raise TimeoutError

        spans = [s for batch in fake_api.calls("POST", "/spans") for s in batch["spans"]]
        tool = next(s for s in spans if s["name"] == "read_file")
        assert tool["status"] == "error"
        assert tool["error_type"] == "TimeoutError"

    def test_truncates_long_error_type(self, fake_api):
        long_error = type("E" * 60, (Exception,), {})

        with pytest.raises(long_error):
            with perturvia.run("analyze repo"):
                with perturvia.span("read_file", kind="tool"):
                    raise long_error

        spans = [s for batch in fake_api.calls("POST", "/spans") for s in batch["spans"]]
        tool = next(s for s in spans if s["name"] == "read_file")
        assert tool["error_type"] == "E" * 50

    def test_mark_error_records_failure_without_raising(self, fake_api):
        with perturvia.run("analyze repo"):
            with perturvia.span("read_file", kind="tool") as span:
                perturvia.mark_error(span, "tool_error")

        spans = [s for batch in fake_api.calls("POST", "/spans") for s in batch["spans"]]
        tool = next(s for s in spans if s["name"] == "read_file")
        assert tool["status"] == "error"
        assert tool["error_type"] == "tool_error"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"name": ""},
            {"name": "x" * 256},
            {"name": "ok", "kind": "db"},
            {"name": "ok", "agent_name": "a" * 256},
        ],
    )
    def test_rejects_invalid_arguments(self, fake_api, kwargs):
        with pytest.raises(ValueError):
            with perturvia.span(**kwargs):
                pass

    def test_outside_run_yields_non_recording_span(self, fake_api, caplog):
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                with perturvia.span("read_file", kind="tool") as span:
                    assert span is INVALID_SPAN

        assert len(caplog.records) == 1  # warned once, not on every call
