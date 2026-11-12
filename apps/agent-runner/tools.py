"""Load tools from an MCP server and wrap each one as a traced LangChain tool."""

import json
import os
from pathlib import Path
from typing import Any

import perturvia
from langchain_core.tools import StructuredTool
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_SERVER_DIR = REPO_ROOT / "apps" / "mcp-server"
WORKSPACE_ROOT_ENV_VAR = "PERTURVIA_WORKSPACE_ROOT"

TOOL_ERROR_TYPE = "tool_error"


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


def _result_text(result: CallToolResult) -> str:
    return "\n".join(block.text for block in result.content if block.type == "text")


def _wrap(client: Client, tool: Tool) -> StructuredTool:
    async def call(**arguments: Any) -> str:
        with perturvia.span(tool.name, kind="tool") as span:
            span.set_attribute("tool.arguments", json.dumps(arguments, default=str))
            try:
                result = await client.call_tool(tool.name, arguments)
            except Exception as exc:
                # The MCP call itself failed  Still report
                # it to the model instead of crashing the agent.
                perturvia.mark_error(span, type(exc).__name__, str(exc))
                return f"Error: {type(exc).__name__}: {exc}"

            text = _result_text(result)
            if result.is_error:
                # Tool errors go back to the model so it can recover; raising would
                # crash the agent and leave nothing to measure.
                perturvia.mark_error(span, TOOL_ERROR_TYPE, text)
                return f"Error: {text}"
            return text

    return StructuredTool.from_function(
        coroutine=call,
        name=tool.name,
        description=tool.description or "",
        args_schema=tool.input_schema,
    )


async def load_tools(client: Client) -> list[StructuredTool]:
    """List every tool the MCP server offers and wrap each as a traced LangChain tool."""
    tools: list[Tool] = []
    cursor: str | None = None
    while True:
        page = await client.list_tools(cursor=cursor)
        tools.extend(page.tools)
        cursor = page.next_cursor
        if not cursor:
            break
    return [_wrap(client, tool) for tool in tools]
