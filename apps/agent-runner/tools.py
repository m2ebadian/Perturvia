"""Start parameters for the repo-tools MCP server the agent uses."""

import os
from pathlib import Path

from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER_DIR = REPO_ROOT / "apps" / "mcp-server"
WORKSPACE_ROOT_ENV_VAR = "PERTURVIA_WORKSPACE_ROOT"


def server_params(workspace_root: str | Path | None = None) -> StdioServerParameters:
    """Parameters for starting the repo-tools MCP server over stdio.

    The workspace is the repository the agent may read: the argument, then
    PERTURVIA_WORKSPACE_ROOT, then this repository. The server refuses to start
    without it.
    """
    root = workspace_root or os.getenv(WORKSPACE_ROOT_ENV_VAR) or REPO_ROOT
    return StdioServerParameters(
        command="uv",
        args=["run", "main.py"],
        cwd=MCP_SERVER_DIR,
        env={WORKSPACE_ROOT_ENV_VAR: str(Path(root).resolve())},
    )
