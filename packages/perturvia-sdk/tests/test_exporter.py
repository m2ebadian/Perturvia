import json

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from perturvia._exporter import PerturviaSpanExporter, span_to_payload


def finished(exporter):
    return {s.name: s for s in exporter.get_finished_spans()}


class TestSpanToPayload:
    def test_maps_core_fields_and_parent_link(self, recorded_spans):
        tracer, exporter = recorded_spans
        with tracer.start_as_current_span("planner"):
            with tracer.start_as_current_span("read_file") as child:
                child.set_status(Status(StatusCode.ERROR))
        spans = finished(exporter)

        parent = span_to_payload(spans["planner"])
        child = span_to_payload(spans["read_file"])

        assert child["parent_span_id"] == parent["id"]
        assert parent["parent_span_id"] is None
        assert child["status"] == "error"
        assert parent["status"] == "ok"
        assert child["duration_ms"] >= 0
        assert child["started_at"].endswith("+00:00")

    def test_maps_perturvia_attributes_and_passes_through_others(self, recorded_spans):
        tracer, exporter = recorded_spans
        attributes = {
            "perturvia.kind": "tool",
            "perturvia.agent_name": "researcher",
            "perturvia.fault": json.dumps({"type": "timeout"}),
            "perturvia.input_span_ids": ["a", "b"],
            "tool.path": "apps/api/main.py",
        }
        with tracer.start_as_current_span("read_file", attributes=attributes):
            pass

        payload = span_to_payload(finished(exporter)["read_file"])

        assert payload["kind"] == "tool"
        assert payload["agent_name"] == "researcher"
        assert payload["fault"] == {"type": "timeout"}
        assert payload["input_span_ids"] == ["a", "b"]
        assert payload["attributes"] == {"tool.path": "apps/api/main.py"}

    @pytest.mark.parametrize(
        ("attributes", "field", "expected"),
        [
            ({"perturvia.kind": "db"}, "kind", "agent"),
            ({"perturvia.fault": "{not json"}, "fault", None),
            ({"perturvia.fault": "[1, 2]"}, "fault", None),
            ({"perturvia.error_type": "timeout"}, "error_type", None),
        ],
    )
    def test_invalid_values_fall_back_safely(self, recorded_spans, attributes, field, expected):
        tracer, exporter = recorded_spans
        with tracer.start_as_current_span("span", attributes=attributes):
            pass

        assert span_to_payload(finished(exporter)["span"])[field] == expected

    def test_skips_span_without_sequence(self):
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        with provider.get_tracer("test").start_as_current_span("unnumbered"):
            pass

        assert span_to_payload(exporter.get_finished_spans()[0]) is None


def make_exporter(handler) -> PerturviaSpanExporter:
    exporter = PerturviaSpanExporter("http://perturvia.test/")
    exporter._client = httpx.Client(transport=httpx.MockTransport(handler))
    return exporter


class TestExport:
    def test_groups_by_trace_and_chunks_large_batches(self, recorded_spans):
        tracer, recorded = recorded_spans
        for count in (600, 3):
            with tracer.start_as_current_span("root"):
                for _ in range(count):
                    with tracer.start_as_current_span("tool"):
                        pass
        requests = []

        def handler(request):
            requests.append((request.url.path, len(json.loads(request.content)["spans"])))
            return httpx.Response(201, json={})

        result = make_exporter(handler).export(recorded.get_finished_spans())

        assert result.name == "SUCCESS"
        assert sorted(size for _, size in requests) == [4, 101, 500]
        assert len({path for path, _ in requests}) == 2

    @pytest.mark.parametrize(
        "handler",
        [
            lambda request: httpx.Response(500),
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused")),
        ],
        ids=["server_error", "unreachable"],
    )
    def test_failures_return_failure_without_raising(self, recorded_spans, handler):
        tracer, recorded = recorded_spans
        with tracer.start_as_current_span("root"):
            pass

        result = make_exporter(handler).export(recorded.get_finished_spans())

        assert result.name == "FAILURE"
