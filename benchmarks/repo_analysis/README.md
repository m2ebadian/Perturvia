# repo_analysis benchmark

Tests whether an agent can analyze a small codebase through read-only tools and report accurate, evidence-backed findings.

The agent analyzes `fixture/`, a small fictional FastAPI app ("Bookshelf"). The fixture is test data: it is never installed or run.

## What it checks

`benchmark.json` holds the `task` prompt and the `ground_truth` a correct answer must match:

- **endpoints**: every real route as `METHOD /full/path`. Two traps:
  - The books router declares `prefix="/books"` only in `app/routers/books.py`, so an agent must read that file to get the full paths.
  - `app/main.py` contains a commented-out `/search` route. It is not an endpoint.
- **dependencies**: the 4 runtime packages in `pyproject.toml`. Dev dependencies (`pytest`, `httpx`) do not count.
- **test_framework**: `pytest`.
- **key_files**: the files a correct analysis must read, relative to `fixture/`.

Evaluation logic is not written yet.

## Running it with any agent

1. Start the repo-tools MCP server (`apps/mcp-server`) with its workspace set to the fixture:

   ```bash
   export PERTURVIA_WORKSPACE_ROOT=/path/to/Perturvia/benchmarks/repo_analysis/fixture
   # PowerShell: $env:PERTURVIA_WORKSPACE_ROOT = "A:\path\to\Perturvia\benchmarks\repo_analysis\fixture"
   ```

2. Give the agent the `task` string from `benchmark.json` as its prompt.
3. Compare its answer against `ground_truth`.

The benchmark depends on no agent's code. `benchmark.json` is plain JSON, so agents in any language can load it.

The reference agent in `apps/agent-runner` already does steps 1 and 2: `uv run main.py` reads the task from this file and analyzes the fixture by default.
