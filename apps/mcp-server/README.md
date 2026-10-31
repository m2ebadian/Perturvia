# MCP Test Server

A small Model Context Protocol (MCP) server used to test Perturvia's execution tracing.

It exposes two tools:

- `echo` — Returns the provided message.
- `fail` — Intentionally raises an error to test failure handling.

## Running locally

From this directory:

```bash
uv sync
uv run client.py
```

The client calls both tools and sends execution traces to the Perturvia API at `http://localhost:8000`.

Start the API first if you want traces saved to PostgreSQL. Set `PERTURVIA_API_URL` to use a different API address.

## MCP Inspector

To inspect and call the tools manually:

```bash
uv run mcp dev main.py
```

## Tracing

Each tool call records its execution time, arguments, result, status, and error information.

Calls within the same client run share a `run_id`. If the API is unavailable, the client logs a warning without changing the tool's execution result.
