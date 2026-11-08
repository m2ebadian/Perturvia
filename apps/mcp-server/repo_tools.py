import os
from collections.abc import Iterator
from pathlib import Path

WORKSPACE_ROOT_ENV_VAR = "PERTURVIA_WORKSPACE_ROOT"

BLOCKED_NAMES = frozenset({".git", ".venv", "node_modules", "__pycache__"})
BLOCKED_PREFIXES = (".env",)
BLOCKED_SUFFIXES = (".pem", ".key")
MAX_READ_BYTES = 100_000
MAX_LIST_ENTRIES = 1_000
MAX_SEARCH_MATCHES = 200
MAX_MATCH_LINE_CHARS = 300


class WorkspaceAccessError(ValueError):
    """Raised when a requested path is outside the workspace or blocked."""


def _is_blocked(name: str) -> bool:
    """Return True if a single path component matches a blocked rule.

    Matching is case-insensitive so ".ENV" or "KEY.PEM" can't bypass the
    rules on case-insensitive filesystems (Windows, default macOS).
    """
    name = name.lower()
    return (
        name in BLOCKED_NAMES
        or name.startswith(BLOCKED_PREFIXES)
        or name.endswith(BLOCKED_SUFFIXES)
    )


def load_workspace_root() -> Path:
    """Return the absolute workspace root configured for the repository tools.

    Raises:
        RuntimeError: If the environment variable is unset, empty, or does not
            point to an existing directory.
    """
    raw_root = os.getenv(WORKSPACE_ROOT_ENV_VAR, "").strip()
    if not raw_root:
        raise RuntimeError(f"{WORKSPACE_ROOT_ENV_VAR} is not set.")

    root = Path(raw_root).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(
            f"{WORKSPACE_ROOT_ENV_VAR} does not point to an existing directory: {root}"
        )

    return root


def resolve_in_workspace(root: Path, user_path: str) -> Path:
    """Resolve ``user_path`` against ``root`` and enforce workspace rules.

    ``..`` segments and symlinks are resolved before any check, so a path
    cannot escape the root or reach a blocked entry through indirection.

    Raises:
        WorkspaceAccessError: If the resolved path is outside ``root`` or any
            component below ``root`` is blocked.
    """
    root = root.resolve()
    resolved_path = (root / user_path).resolve()

    if not resolved_path.is_relative_to(root):
        raise WorkspaceAccessError(f"Path is outside the workspace: {user_path}")

    for part in resolved_path.relative_to(root).parts:
        if _is_blocked(part):
            raise WorkspaceAccessError(f"Path is blocked: {user_path}")

    return resolved_path


def read_file(root: Path, path: str) -> dict:
    """Read a text file from the workspace, capped at MAX_READ_BYTES.

    Raises:
        WorkspaceAccessError: If the path is outside the workspace or blocked.
        FileNotFoundError: If the path is not an existing file.
        ValueError: If the file looks binary.
    """

    root = root.resolve()

    resolved_path = resolve_in_workspace(root, path)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"File does not exist: {path}")

    with open(resolved_path, "rb") as f:
        data = f.read(MAX_READ_BYTES + 1)

    truncated = len(data) > MAX_READ_BYTES
    if truncated:
        data = data[:MAX_READ_BYTES]
    if b"\x00" in data:
        raise ValueError(f"Binary file not allowed: {path}")

    text = data.decode("utf-8", errors="replace")

    return {
        "path": resolved_path.relative_to(root).as_posix(),
        "content": text,
        "truncated": truncated,
    }


def _iter_files(start: Path) -> Iterator[Path]:
    """Yield regular files under ``start`` in sorted order.

    Blocked entries and symlinks are skipped. ``Path.walk`` reports symlinks
    as files, and following one could read data outside the workspace.
    """
    for current_dir, dirnames, filenames in start.walk():
        dirnames[:] = sorted(d for d in dirnames if not _is_blocked(d))
        for name in sorted(filenames):
            path = current_dir / name
            if not _is_blocked(name) and not path.is_symlink():
                yield path


def list_files(root: Path, directory: str = ".") -> dict:
    """List files under a workspace directory, skipping blocked entries.

    Results are sorted and capped at MAX_LIST_ENTRIES.

    Raises:
        WorkspaceAccessError: If the directory is outside the workspace or blocked.
        NotADirectoryError: If the path is not an existing directory.
    """
    root = root.resolve()
    start = resolve_in_workspace(root, directory)
    if not start.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = []
    for file_path in _iter_files(start):
        if len(files) == MAX_LIST_ENTRIES:
            return {"directory": directory, "files": files, "truncated": True}
        files.append(file_path.relative_to(root).as_posix())

    return {"directory": directory, "files": files, "truncated": False}


def search_text(root: Path, query: str, directory: str = ".") -> dict:
    """Find lines containing ``query`` in workspace text files.

    Matching is a plain, case-sensitive substring check. Files that are
    binary, unreadable, or larger than MAX_READ_BYTES are skipped and counted.
    Results are capped at MAX_SEARCH_MATCHES.

    Raises:
        ValueError: If ``query`` is empty.
        WorkspaceAccessError: If the directory is outside the workspace or blocked.
        NotADirectoryError: If the path is not an existing directory.
    """
    if not query:
        raise ValueError("Query must not be empty.")

    root = root.resolve()
    start = resolve_in_workspace(root, directory)
    if not start.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    matches = []
    skipped_files = 0

    def result(truncated: bool) -> dict:
        return {
            "query": query,
            "directory": directory,
            "matches": matches,
            "skipped_files": skipped_files,
            "truncated": truncated,
        }

    for file_path in _iter_files(start):
        try:
            if file_path.stat().st_size > MAX_READ_BYTES:
                skipped_files += 1
                continue
            data = file_path.read_bytes()
        except OSError:
            skipped_files += 1
            continue

        if b"\x00" in data:
            skipped_files += 1
            continue

        relative_path = file_path.relative_to(root).as_posix()
        text = data.decode("utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if query not in line:
                continue
            if len(matches) == MAX_SEARCH_MATCHES:
                return result(truncated=True)
            matches.append(
                {
                    "path": relative_path,
                    "line": line_number,
                    "text": line.strip()[:MAX_MATCH_LINE_CHARS],
                }
            )

    return result(truncated=False)
