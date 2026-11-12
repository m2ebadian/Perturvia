from collections.abc import Iterator
from contextlib import contextmanager

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import repo_tools

server = MCPServer("perturvia-repo-tools")


WORKSPACE_ROOT = repo_tools.load_workspace_root()


@contextmanager
def _tool_errors() -> Iterator[None]:
    """Report anticipated failures to the model; leave real crashes hidden.

    Only exceptions whose messages repo_tools writes itself (containing just the
    path the agent asked for) are translated. Others, like PermissionError, can
    contain host paths, so MCP keeps them hidden as crashes.
    WorkspaceAccessError is a ValueError subclass, so it is included.
    """
    try:
        yield
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        raise ToolError(str(exc)) from exc


@server.tool()
def list_files(directory: str = ".") -> dict:
    """
    List files in the repository, recursively.

    Use this first to discover which files exist before reading or searching.
    `directory` is relative to the repository root, using forward slashes
    (e.g. "apps/api"). Use "." for the whole repository.

    Returns file paths relative to the repository root. Sensitive and generated
    folders (.git, node_modules, .env files) are never listed. If `truncated`
    is true, the list was cut off at 1,000 files; narrow `directory` to see more.
    """
    with _tool_errors():
        return repo_tools.list_files(root=WORKSPACE_ROOT, directory=directory)


@server.tool()
def read_file(path: str) -> dict:
    """
    Read a text file from the repository.

    `path` is relative to the repository root, using forward slashes
    (e.g. "apps/api/main.py"). Use list_files or search_text first if you
    don't know the exact path.

    Returns the file content as text. Files over 100 KB are cut off; if
    `truncated` is true, you only have the beginning of the file and should
    not make claims about the rest. Binary files and sensitive files (.env,
    keys, .git) cannot be read.
    """
    with _tool_errors():
        return repo_tools.read_file(root=WORKSPACE_ROOT, path=path)


@server.tool()
def search_text(query: str, directory: str = ".") -> dict:
    """
    Search repository text files for lines containing an exact string.

    The match is case-sensitive and literal, not a regex. `directory` limits
    the search to part of the repository (e.g. "apps/api"); use "." for all
    of it.

    Returns each matching line with its file path and line number. Use
    read_file on a result to see the surrounding code. `skipped_files` counts
    files that were too large, binary, or unreadable, so they were not
    searched. If `truncated` is true, results stopped at 200 matches; use a
    more specific query or directory.
    """
    with _tool_errors():
        return repo_tools.search_text(root=WORKSPACE_ROOT, query=query, directory=directory)


if __name__ == "__main__":
    server.run()
