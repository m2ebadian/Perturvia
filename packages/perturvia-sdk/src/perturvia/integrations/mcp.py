"""Wrap MCP server tools as traced LangChain tools, with optional fault injection.

Requires the ``mcp`` extra: ``pip install "perturvia[mcp]"``.
"""

import asyncio
import json
import random
from typing import Any

try:
    from langchain_core.tools import StructuredTool
    from mcp import Client
    from mcp.types import CallToolResult, Tool
except ImportError as exc:
    raise ImportError(
        "perturvia.integrations.mcp needs extra packages. Install them with: "
        'pip install "perturvia[mcp]"'
    ) from exc

from opentelemetry.trace import Span

import perturvia
from perturvia.faults import (
    TIMEOUT_MESSAGE,
    UNAVAILABLE_MESSAGE,
    FaultPolicy,
    FaultType,
    corrupt,
    inject,
)

__all__ = ["traced_tools"]

TOOL_ERROR_TYPE = "tool_error"


def _result_text(result: CallToolResult) -> str:
    return "\n".join(block.text for block in result.content if block.type == "text")


def _fault_record(fault: FaultType, policy: FaultPolicy) -> str:
    """The perturvia.fault span attribute: the fault type plus the delay it used."""
    record: dict[str, Any] = {"type": fault}
    if fault == "latency":
        record["latency_ms"] = policy.latency_ms
    elif fault == "timeout":
        record["timeout_ms"] = policy.timeout_ms
    return json.dumps(record)


async def _real_call(
    client: Client, span: Span, name: str, arguments: dict[str, Any]
) -> tuple[str, bool]:
    """Call the MCP tool and return (text for the model, whether it succeeded).

    Failures become "Error: ..." text so the model can recover.
    """
    try:
        result = await client.call_tool(name, arguments)
    except Exception as exc:
        # The MCP call itself failed. Report it to the model instead of crashing the agent.
        perturvia.mark_error(span, type(exc).__name__, str(exc))
        return f"Error: {type(exc).__name__}: {exc}", False

    text = _result_text(result)
    if result.is_error:
        # Tool errors go back to the model so it can recover; raising would crash
        # the agent and leave nothing to measure.
        perturvia.mark_error(span, TOOL_ERROR_TYPE, text)
        return f"Error: {text}", False
    return text, True


def _wrap(
    client: Client, tool: Tool, faults: FaultPolicy | None, rng: random.Random
) -> StructuredTool:
    async def call(**arguments: Any) -> str:
        with perturvia.span(tool.name, kind="tool") as span:
            span.set_attribute("tool.arguments", json.dumps(arguments, default=str))

            # decide() runs on every call, even ones that get no fault, so each call
            # consumes exactly one draw and a seed always gives the same schedule.
            fault = faults.decide(rng) if faults is not None else None
            if fault is None:
                text, _ = await _real_call(client, span, tool.name, arguments)
                return text

            assert faults is not None
            span.set_attribute("perturvia.fault", _fault_record(fault, faults))

            if fault == "error":
                perturvia.mark_error(span, "unavailable")
                return "Error: " + UNAVAILABLE_MESSAGE

            if fault == "timeout":
                # asyncio.sleep, never time.sleep: blocking would freeze the event loop.
                await asyncio.sleep(faults.timeout_ms / 1000)
                perturvia.mark_error(span, "timeout")
                return "Error: " + TIMEOUT_MESSAGE.format(seconds=faults.timeout_ms / 1000)

            if fault == "latency":
                await asyncio.sleep(faults.latency_ms / 1000)
                text, _ = await _real_call(client, span, tool.name, arguments)
                return text

            # malformed / injection: damage only a successful result.
            text, ok = await _real_call(client, span, tool.name, arguments)
            if not ok:
                return text
            return corrupt(text) if fault == "malformed" else inject(text)

    return StructuredTool.from_function(
        coroutine=call,
        name=tool.name,
        description=tool.description or "",
        args_schema=tool.input_schema,
    )


async def traced_tools(
    client: Client, *, faults: FaultPolicy | None = None, seed: int | None = None
) -> list[StructuredTool]:
    """List every tool the MCP server offers and wrap each as a traced LangChain tool.

    With ``faults``, each call may get one injected fault, recorded on its span as
    ``perturvia.fault``. All tools share one random generator seeded with ``seed``,
    so the same seed and the same sequence of calls give the same faults.
    """
    tools: list[Tool] = []
    cursor: str | None = None
    while True:
        page = await client.list_tools(cursor=cursor)
        tools.extend(page.tools)
        cursor = page.next_cursor
        if not cursor:
            break

    rng = random.Random(seed)
    return [_wrap(client, tool, faults, rng) for tool in tools]
