# Perturvia Python SDK

Send traces of your AI agent runs to [Perturvia](https://github.com/m2ebadian/Perturvia), so you can inspect every agent, LLM, and tool step and test how your agents behave under failures.

Built on OpenTelemetry. Perturvia keeps its own tracer provider and never replaces an OpenTelemetry setup an application already has.

## Quickstart

```python
import perturvia

perturvia.init()  # PERTURVIA_API_URL, or http://localhost:8000 by default

with perturvia.run(task="Analyze this repository", seed=42) as run:
    with perturvia.span("researcher", agent_name="researcher"):
        with perturvia.span("read_file", kind="tool"):
            ...
    run.final_output = "Found 9 API endpoints."
```

- `run()` creates a trace, then marks it `completed`, or `failed` if your code raises. Your exception is always re-raised.
- `span()` records one step. `kind` is `"agent"`, `"llm"`, or `"tool"`. Exceptions inside a span are recorded with their class name as the error type.
- Pass an earlier span as `retry_of=` to link a retry to the call it repeats.

## MCP tools and fault injection

Install the extra with `pip install "perturvia[mcp]"`. Then `traced_tools` wraps every tool on an MCP server as a traced LangChain tool. It can also inject faults so you can test how the agent copes:

```python
from perturvia.faults import FaultPolicy
from perturvia.integrations.mcp import traced_tools

policy = FaultPolicy(error_rate=0.1, latency_rate=0.2, injection_rate=0.05)
tools = await traced_tools(client, faults=policy, seed=42)
```

Each call gets at most one fault: `error`, `timeout`, `latency`, `malformed` (the result is cut in half), or `injection` (an instruction is appended to the result). The fault is recorded on the tool span. The same seed and the same sequence of calls give the same faults.

## Guarantees

- **Perturvia never breaks your agent.** If the API is down, slow, or rejects data, the SDK logs a warning and your code keeps running.
- **Bounded waits.** Requests and the end-of-run flush respect the `timeout` passed to `init()` (5 seconds by default).
- **Safe retries.** Span batches are idempotent on the server, so resending a batch never duplicates spans.

## Threads

Tracing context does not follow your code into new threads automatically. When a run starts work in a thread pool, copy the context so spans stay inside the run:

```python
import contextvars

ctx = contextvars.copy_context()
pool.submit(ctx.run, call_tool, args)
```

`span()` called with no active run does not trace and logs a warning once.

## Development

```bash
uv sync
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```
