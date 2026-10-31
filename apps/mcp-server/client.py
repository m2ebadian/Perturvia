import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import httpx2
from mcp import Client, StdioServerParameters

logger = logging.getLogger(__name__)

params = StdioServerParameters(command="uv", args=["run", "main.py"])


def tool_error_message(call) -> str | None:
    texts = [block.text for block in call.content if block.type == "text"]
    return "\n".join(texts) or None


async def trace_tool_call(client, http_client, tool_name: str, arguments: dict, run_id: uuid.UUID):
    start = time.perf_counter()
    started_at = datetime.now(timezone.utc)

    trace = {
        "tool_name": tool_name,
        "arguments": arguments,
        "run_id": run_id,
        "started_at": started_at,
    }

    try:
        call = await client.call_tool(tool_name, arguments)

        trace.update(
            {
                "duration_ms": (time.perf_counter() - start) * 1000,
                "status": "tool_error" if call.is_error else "success",
                "result": call.model_dump(mode="json")["content"],
                "error_message": tool_error_message(call) if call.is_error else None,
            }
        )

        print(trace)
        return call

    except Exception as exc:
        trace.update(
            {
                "duration_ms": (time.perf_counter() - start) * 1000,
                "status": "client_exception",
                "result": None,
                "error_message": f"{type(exc).__name__}: {exc}",
            }
        )

        print(trace)
        raise

    finally:
        if "status" in trace:
            await persist_trace(http_client, trace)


async def persist_trace(http_client, trace: dict):
    api_url = os.getenv("PERTURVIA_API_URL", "http://localhost:8000")
    try:
        payload = {
            **trace,
            "run_id": str(trace["run_id"]),
            "started_at": trace["started_at"].isoformat(),
        }
        response = await http_client.post(f"{api_url}/traces", json=payload)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to persist trace: %s", exc)


async def main():
    run_id = uuid.uuid4()

    async with Client(params) as client:
        async with httpx2.AsyncClient(timeout=5.0) as http_client:
            await trace_tool_call(client, http_client, "echo", {"message": "hello"}, run_id)
            await trace_tool_call(client, http_client, "fail", {}, run_id)


if __name__ == "__main__":
    asyncio.run(main())
