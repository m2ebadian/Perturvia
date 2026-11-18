import asyncio
import importlib
import json
import random
import subprocess
import sys

import pytest
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

import perturvia
from perturvia.faults import (
    INJECTION_CANARY,
    TIMEOUT_MESSAGE,
    UNAVAILABLE_MESSAGE,
    FaultPolicy,
    corrupt,
    inject,
)
from perturvia.integrations import mcp as mcp_integration
from perturvia.integrations.mcp import traced_tools

REAL_TEXT = json.dumps({"path": "README.md", "content": "# Perturvia", "truncated": False})

READ_FILE = Tool(
    name="read_file",
    description="Read a text file.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
LIST_FILES = Tool(
    name="list_files",
    description="List files.",
    input_schema={"type": "object", "properties": {"directory": {"type": "string"}}},
)


def text_result(text: str, *, is_error: bool = False) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=is_error)


class FakeClient:
    """Minimal stand-in for mcp.Client: serves tools in pages and answers calls."""

    def __init__(
        self,
        pages: list[list[Tool]] | None = None,
        result: CallToolResult | Exception | None = None,
    ) -> None:
        self.pages = pages or [[READ_FILE]]
        self.result = result if result is not None else text_result(REAL_TEXT)
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self, cursor: str | None = None) -> ListToolsResult:
        index = int(cursor) if cursor else 0
        has_next = index + 1 < len(self.pages)
        return ListToolsResult(
            tools=self.pages[index], next_cursor=str(index + 1) if has_next else None
        )

    async def call_tool(self, name: str, arguments: dict) -> CallToolResult:
        self.calls.append((name, arguments))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    """Replace asyncio.sleep in the integration so tests record delays instead of waiting."""
    recorded: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(mcp_integration.asyncio, "sleep", fake_sleep)
    return recorded


def call_once(client: FakeClient, faults: FaultPolicy | None = None) -> str:
    """Load the tools and call read_file once, inside a traced run."""

    async def go() -> str:
        (tool,) = await traced_tools(client, faults=faults, seed=0)
        return await tool.ainvoke({"path": "README.md"})

    with perturvia.run("test"):
        return asyncio.run(go())


def tool_spans(fake_api) -> list[dict]:
    return [
        span
        for batch in fake_api.calls("POST", "/spans")
        for span in batch["spans"]
        if span["kind"] == "tool"
    ]


class TestWithoutFaults:
    def test_returns_real_result_and_traces_call(self, fake_api):
        client = FakeClient()

        assert call_once(client) == REAL_TEXT
        assert client.calls == [("read_file", {"path": "README.md"})]
        (span,) = tool_spans(fake_api)
        assert span["name"] == "read_file"
        assert span["status"] == "ok"
        assert span["fault"] is None
        assert json.loads(span["attributes"]["tool.arguments"]) == {"path": "README.md"}

    def test_tool_error_goes_back_to_model(self, fake_api):
        client = FakeClient(result=text_result("File not found: x.py", is_error=True))

        assert call_once(client) == "Error: File not found: x.py"
        (span,) = tool_spans(fake_api)
        assert span["status"] == "error"
        assert span["error_type"] == "tool_error"

    def test_client_exception_goes_back_to_model(self, fake_api):
        client = FakeClient(result=ConnectionError("server gone"))

        assert call_once(client) == "Error: ConnectionError: server gone"
        (span,) = tool_spans(fake_api)
        assert span["error_type"] == "ConnectionError"

    def test_loads_every_page_of_tools(self):
        client = FakeClient(pages=[[READ_FILE], [LIST_FILES]])

        tools = asyncio.run(traced_tools(client))

        assert [tool.name for tool in tools] == ["read_file", "list_files"]


class TestFaults:
    def test_error_skips_real_call(self, fake_api, sleeps):
        client = FakeClient()

        assert call_once(client, FaultPolicy(error_rate=1.0)) == "Error: " + UNAVAILABLE_MESSAGE
        assert client.calls == []
        assert sleeps == []
        (span,) = tool_spans(fake_api)
        assert span["status"] == "error"
        assert span["error_type"] == "unavailable"
        assert span["fault"] == {"type": "error"}

    def test_timeout_waits_then_skips_real_call(self, fake_api, sleeps):
        client = FakeClient()
        policy = FaultPolicy(timeout_rate=1.0, timeout_ms=1500)

        result = call_once(client, policy)

        assert result == "Error: " + TIMEOUT_MESSAGE.format(seconds=1.5)
        assert result == "Error: Tool call timed out after 1.5s."
        assert client.calls == []
        assert sleeps == [1.5]
        (span,) = tool_spans(fake_api)
        assert span["status"] == "error"
        assert span["error_type"] == "timeout"
        assert span["fault"] == {"type": "timeout", "timeout_ms": 1500}

    def test_latency_waits_then_makes_real_call(self, fake_api, sleeps):
        client = FakeClient()
        policy = FaultPolicy(latency_rate=1.0, latency_ms=250)

        assert call_once(client, policy) == REAL_TEXT
        assert len(client.calls) == 1
        assert sleeps == [0.25]
        (span,) = tool_spans(fake_api)
        assert span["status"] == "ok"
        assert span["fault"] == {"type": "latency", "latency_ms": 250}

    def test_malformed_corrupts_result(self, fake_api):
        client = FakeClient()

        result = call_once(client, FaultPolicy(malformed_rate=1.0))

        assert result == corrupt(REAL_TEXT)
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)
        (span,) = tool_spans(fake_api)
        assert span["status"] == "ok"
        assert span["fault"] == {"type": "malformed"}

    def test_injection_appends_instruction(self, fake_api):
        client = FakeClient()

        result = call_once(client, FaultPolicy(injection_rate=1.0))

        assert result == inject(REAL_TEXT)
        assert result.startswith(REAL_TEXT)
        assert INJECTION_CANARY in result
        (span,) = tool_spans(fake_api)
        assert span["status"] == "ok"
        assert span["fault"] == {"type": "injection"}

    @pytest.mark.parametrize("field", ["malformed_rate", "injection_rate"])
    def test_tool_error_is_not_damaged(self, fake_api, field):
        client = FakeClient(result=text_result("File not found: x.py", is_error=True))

        assert call_once(client, FaultPolicy(**{field: 1.0})) == "Error: File not found: x.py"
        (span,) = tool_spans(fake_api)
        assert span["error_type"] == "tool_error"

    @pytest.mark.parametrize("field", ["malformed_rate", "injection_rate"])
    def test_successful_result_that_looks_like_error_is_still_damaged(self, fake_api, field):
        client = FakeClient(result=text_result("Error: this text is the file's content"))

        result = call_once_untraced(client, FaultPolicy(**{field: 1.0}))

        assert result != "Error: this text is the file's content"

    def test_works_outside_a_run(self, fake_api):
        client = FakeClient()

        assert call_once_untraced(client, FaultPolicy(error_rate=1.0)).startswith("Error:")
        assert tool_spans(fake_api) == []


def call_once_untraced(client: FakeClient, faults: FaultPolicy) -> str:
    async def go() -> str:
        (tool,) = await traced_tools(client, faults=faults, seed=0)
        return await tool.ainvoke({"path": "README.md"})

    return asyncio.run(go())


class TestSeed:
    POLICY = FaultPolicy(error_rate=0.3, malformed_rate=0.3, latency_rate=0.2, latency_ms=0)

    def run_calls(self, seed: int, n: int = 30) -> list[str]:
        """Alternate calls between two tools that share one fault schedule."""

        async def go() -> list[str]:
            tools = await traced_tools(
                FakeClient(pages=[[READ_FILE, LIST_FILES]]), faults=self.POLICY, seed=seed
            )
            return [await tools[i % 2].ainvoke({"path": "README.md"}) for i in range(n)]

        return asyncio.run(go())

    def test_same_seed_gives_same_results(self):
        assert self.run_calls(7) == self.run_calls(7)
        assert self.run_calls(7) != self.run_calls(8)

    def test_tools_share_one_schedule(self):
        rng = random.Random(7)
        expected = [self.POLICY.decide(rng) for _ in range(30)]

        def outcome(text: str) -> str | None:
            if text == "Error: " + UNAVAILABLE_MESSAGE:
                return "error"
            if text == corrupt(REAL_TEXT):
                return "malformed"
            return None  # latency (0 ms) and no fault both return the real text

        actual = [outcome(text) for text in self.run_calls(7)]

        assert actual == [f if f != "latency" else None for f in expected]


class TestPackaging:
    def test_missing_extra_raises_helpful_import_error(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "perturvia.integrations.mcp")
        monkeypatch.setitem(sys.modules, "mcp", None)  # makes `import mcp` fail

        with pytest.raises(ImportError, match=r'pip install "perturvia\[mcp\]"'):
            importlib.import_module("perturvia.integrations.mcp")

    def test_core_import_does_not_load_extra_packages(self):
        code = (
            "import sys, perturvia, perturvia.faults; "
            "assert 'mcp' not in sys.modules; "
            "assert 'langchain_core' not in sys.modules"
        )

        subprocess.run([sys.executable, "-c", code], check=True)
