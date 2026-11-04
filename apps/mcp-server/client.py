import asyncio
import logging
import math
import os
import time
import uuid
from datetime import datetime, timezone
import random

import httpx2
from mcp import Client, StdioServerParameters

logger = logging.getLogger(__name__)

params = StdioServerParameters(command="uv", args=["run", "main.py"])


def tool_error_message(call) -> str | None:
    texts = [block.text for block in call.content if block.type == "text"]
    return "\n".join(texts) or None


async def trace_tool_call(client, http_client, tool_name: str, arguments: dict, run_id: uuid.UUID):
    raw_latency = os.getenv("PERTURVIA_INJECT_LATENCY_MS", "0")
    raw_failure = os.getenv("PERTURVIA_INJECT_FAILURE_RATE", "0")
    try:
        delay_ms = float(raw_latency)
    except ValueError:
        logger.warning("PERTURVIA_INJECT_LATENCY_MS is not a number: %r. Defaulting to 0.", raw_latency)
        delay_ms = 0.0

    if not math.isfinite(delay_ms) or delay_ms < 0:
        logger.warning(
            "PERTURVIA_INJECT_LATENCY_MS must be finite and non-negative: %r. Defaulting to 0.",
            raw_latency,
        )
        delay_ms = 0.0

    try:
        failure_rate = float(raw_failure)
    except ValueError:
        logger.warning("PERTURVIA_INJECT_FAILURE_RATE is not a number: %r. Defaulting to 0.", raw_failure)
        failure_rate = 0.0

    if not (0.0 <= failure_rate <= 1.0):
        logger.warning(
            "PERTURVIA_INJECT_FAILURE_RATE must be between 0 and 1: %r. Defaulting to 0.",
            raw_failure,
        )
        failure_rate = 0.0

    start = time.perf_counter()
    started_at = datetime.now(timezone.utc)

    trace = {
        "tool_name": tool_name,
        "arguments": arguments,
        "run_id": run_id,
        "started_at": started_at,
        "fault_injection": {
            "latency_ms": delay_ms,
            "failure_injected": False,
        },
    }



    try:
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)


        inject_failure = random.random() < failure_rate




        if inject_failure:
            trace["fault_injection"]["failure_injected"] = True
            raise RuntimeError("Perturvia injected tool-call failure")

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
            for trial in range(1, 21):
                try:
                    await trace_tool_call(
                        client, http_client, "echo", {"message": "hello"}, run_id
                    )
                except Exception as exc:
                    logger.warning("Trial %d failed: %s", trial, exc)


if __name__ == "__main__":
    asyncio.run(main())
