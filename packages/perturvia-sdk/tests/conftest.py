import json
from dataclasses import dataclass, field

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import perturvia
from perturvia import _tracing
from perturvia._processor import SequenceProcessor


@dataclass
class FakeApi:
    """Records every request the SDK sends and answers with a fixed status."""

    status_code: int = 201
    requests: list[httpx.Request] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status_code, json={})

    def calls(self, method: str, path_suffix: str = "") -> list[dict]:
        return [
            json.loads(r.content)
            for r in self.requests
            if r.method == method and r.url.path.endswith(path_suffix)
        ]


@pytest.fixture
def fake_api(monkeypatch) -> FakeApi:
    """Initialize the SDK with every HTTP request routed to an in-memory fake API."""
    api = FakeApi()
    real_client = httpx.Client

    def client_with_fake_transport(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(api.handle), **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_fake_transport)
    perturvia.init("http://perturvia.test")
    yield api
    _tracing._provider.shutdown()
    monkeypatch.setattr(_tracing, "_warned_no_run", False)


@pytest.fixture
def recorded_spans():
    """A tracer whose finished spans are kept in memory, numbered like the real SDK."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SequenceProcessor())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter
