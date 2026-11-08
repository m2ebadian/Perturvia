# Perturvia Repository Tools (MCP Server)

An MCP server that gives agents read-only access to a code repository. It is the tool layer for Perturvia's reference repository-analysis agents.

## Tools

| Tool | Purpose |
|---|---|
| `list_files(directory=".")` | Recursively list files, sorted, capped at 1,000 |
| `read_file(path)` | Read a text file, capped at 100 KB |
| `search_text(query, directory=".")` | Case-sensitive literal search, capped at 200 matches |

All paths are relative to the workspace root and use forward slashes.

## Workspace boundary

The server only reads inside `PERTURVIA_WORKSPACE_ROOT` and refuses to start if it is unset or invalid.

- Paths are resolved before checking, so `..` and symlinks cannot escape the root.
- `.git`, `.venv`, `node_modules`, `__pycache__`, `.env*`, `*.pem`, and `*.key` are never listed, read, or searched.
- Symlinks are skipped when walking the tree.
- Binary files are rejected, and every result reports whether it was truncated.

## Running locally

```bash
export PERTURVIA_WORKSPACE_ROOT=/path/to/repo   # PowerShell: $env:PERTURVIA_WORKSPACE_ROOT = "A:\path\to\repo"
uv sync
npx @modelcontextprotocol/inspector uv run main.py
```

## Development

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

Symlink tests are skipped on Windows unless Developer Mode is enabled; CI runs them on Linux.

## Legacy tracing client

`client.py` is the original tracing prototype and still targets the removed `echo` tool. It will be replaced by Perturvia's MCP interceptor.
