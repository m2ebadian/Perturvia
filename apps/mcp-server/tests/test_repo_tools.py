import os
from pathlib import Path

import pytest

import repo_tools
from repo_tools import WorkspaceAccessError


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a small repository inside a temporary directory."""
    root = tmp_path / "repo"
    files = {
        "README.md": "# Demo\n",
        "apps/api/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "apps/web/page.tsx": "export default function Page() {}\n",
        ".env": "SECRET=1\n",
        "apps/api/.env.local": "SECRET=2\n",
        "certs/server.pem": "-----BEGIN-----\n",
        ".git/config": "[core]\n",
        "node_modules/pkg/index.js": "module.exports = {}\n",
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, newline="\n")  # keep LF on Windows too

    (tmp_path / "outside.txt").write_text("outside secret\n")
    return root


def make_symlink(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
    except OSError:
        pytest.skip("symlinks are not supported on this system")


class TestLoadWorkspaceRoot:
    def test_returns_resolved_directory(self, workspace, monkeypatch):
        monkeypatch.setenv(repo_tools.WORKSPACE_ROOT_ENV_VAR, str(workspace))
        assert repo_tools.load_workspace_root() == workspace.resolve()

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_rejects_missing_value(self, monkeypatch, value):
        if value is None:
            monkeypatch.delenv(repo_tools.WORKSPACE_ROOT_ENV_VAR, raising=False)
        else:
            monkeypatch.setenv(repo_tools.WORKSPACE_ROOT_ENV_VAR, value)
        with pytest.raises(RuntimeError, match="not set"):
            repo_tools.load_workspace_root()

    def test_rejects_nonexistent_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv(repo_tools.WORKSPACE_ROOT_ENV_VAR, str(tmp_path / "missing"))
        with pytest.raises(RuntimeError, match="existing directory"):
            repo_tools.load_workspace_root()


class TestResolveInWorkspace:
    def test_resolves_path_inside_workspace(self, workspace):
        resolved = repo_tools.resolve_in_workspace(workspace, "apps/api/main.py")
        assert resolved == (workspace / "apps/api/main.py").resolve()

    @pytest.mark.parametrize("user_path", [".", ""])
    def test_current_directory_resolves_to_root(self, workspace, user_path):
        assert repo_tools.resolve_in_workspace(workspace, user_path) == workspace.resolve()

    def test_rejects_parent_traversal(self, workspace):
        with pytest.raises(WorkspaceAccessError, match="outside the workspace"):
            repo_tools.resolve_in_workspace(workspace, "apps/../../outside.txt")

    def test_rejects_absolute_path_outside_workspace(self, workspace):
        outside = workspace.parent / "outside.txt"
        with pytest.raises(WorkspaceAccessError, match="outside the workspace"):
            repo_tools.resolve_in_workspace(workspace, str(outside))

    @pytest.mark.parametrize(
        "user_path",
        [
            ".env",
            ".ENV",
            "apps/api/.env.local",
            ".git/config",
            "certs/server.pem",
            "certs/SERVER.PEM",
            "node_modules/pkg/index.js",
        ],
    )
    def test_rejects_blocked_paths(self, workspace, user_path):
        with pytest.raises(WorkspaceAccessError, match="blocked"):
            repo_tools.resolve_in_workspace(workspace, user_path)

    def test_rejects_symlink_escaping_workspace(self, workspace):
        make_symlink(workspace / "link.txt", workspace.parent / "outside.txt")
        with pytest.raises(WorkspaceAccessError, match="outside the workspace"):
            repo_tools.resolve_in_workspace(workspace, "link.txt")

    def test_rejects_symlink_into_blocked_directory(self, workspace):
        make_symlink(workspace / "innocent", workspace / ".git")
        with pytest.raises(WorkspaceAccessError, match="blocked"):
            repo_tools.resolve_in_workspace(workspace, "innocent/config")

    def test_error_message_does_not_leak_host_path(self, workspace):
        with pytest.raises(WorkspaceAccessError) as exc_info:
            repo_tools.resolve_in_workspace(workspace, "../outside.txt")
        assert str(workspace.parent) not in str(exc_info.value)


class TestReadFile:
    def test_reads_text_file(self, workspace):
        result = repo_tools.read_file(workspace, "apps/api/main.py")
        assert result == {
            "path": "apps/api/main.py",
            "content": "from fastapi import FastAPI\napp = FastAPI()\n",
            "truncated": False,
        }

    def test_file_at_limit_is_not_truncated(self, workspace):
        (workspace / "exact.txt").write_bytes(b"a" * repo_tools.MAX_READ_BYTES)
        result = repo_tools.read_file(workspace, "exact.txt")
        assert result["truncated"] is False
        assert len(result["content"]) == repo_tools.MAX_READ_BYTES

    def test_file_over_limit_is_truncated(self, workspace):
        (workspace / "big.txt").write_bytes(b"a" * (repo_tools.MAX_READ_BYTES + 1))
        result = repo_tools.read_file(workspace, "big.txt")
        assert result["truncated"] is True
        assert len(result["content"]) == repo_tools.MAX_READ_BYTES

    def test_rejects_binary_file(self, workspace):
        (workspace / "image.png").write_bytes(b"\x89PNG\x00\x00")
        with pytest.raises(ValueError, match="Binary"):
            repo_tools.read_file(workspace, "image.png")

    @pytest.mark.parametrize("path", ["missing.txt", "apps"])
    def test_rejects_missing_file_or_directory(self, workspace, path):
        with pytest.raises(FileNotFoundError):
            repo_tools.read_file(workspace, path)

    def test_rejects_blocked_file(self, workspace):
        with pytest.raises(WorkspaceAccessError):
            repo_tools.read_file(workspace, ".env")


class TestListFiles:
    def test_lists_files_sorted_and_skips_blocked_entries(self, workspace):
        result = repo_tools.list_files(workspace)
        assert result == {
            "directory": ".",
            "files": ["README.md", "apps/api/main.py", "apps/web/page.tsx"],
            "truncated": False,
        }

    def test_lists_subdirectory(self, workspace):
        assert repo_tools.list_files(workspace, "apps/web")["files"] == ["apps/web/page.tsx"]

    def test_skips_symlinks(self, workspace):
        make_symlink(workspace / "link.txt", workspace.parent / "outside.txt")
        make_symlink(workspace / "linkdir", workspace.parent)
        files = repo_tools.list_files(workspace)["files"]
        assert "link.txt" not in files
        assert not any(f.startswith("linkdir") for f in files)

    def test_truncates_at_limit(self, workspace, monkeypatch):
        monkeypatch.setattr(repo_tools, "MAX_LIST_ENTRIES", 2)
        result = repo_tools.list_files(workspace)
        assert result["files"] == ["README.md", "apps/api/main.py"]
        assert result["truncated"] is True

    def test_exactly_at_limit_is_not_truncated(self, workspace, monkeypatch):
        monkeypatch.setattr(repo_tools, "MAX_LIST_ENTRIES", 3)
        assert repo_tools.list_files(workspace)["truncated"] is False

    def test_rejects_file_as_directory(self, workspace):
        with pytest.raises(NotADirectoryError):
            repo_tools.list_files(workspace, "README.md")


class TestSearchText:
    def test_returns_matches_with_line_numbers(self, workspace):
        result = repo_tools.search_text(workspace, "FastAPI")
        assert result["matches"] == [
            {"path": "apps/api/main.py", "line": 1, "text": "from fastapi import FastAPI"},
            {"path": "apps/api/main.py", "line": 2, "text": "app = FastAPI()"},
        ]
        assert result["truncated"] is False

    def test_does_not_search_blocked_files(self, workspace):
        assert repo_tools.search_text(workspace, "SECRET")["matches"] == []

    def test_does_not_read_through_symlinks(self, workspace):
        make_symlink(workspace / "link.txt", workspace.parent / "outside.txt")
        assert repo_tools.search_text(workspace, "outside secret")["matches"] == []

    def test_skips_and_counts_large_and_binary_files(self, workspace):
        (workspace / "big.txt").write_text("FastAPI\n" * repo_tools.MAX_READ_BYTES)
        (workspace / "blob.bin").write_bytes(b"FastAPI\x00")
        result = repo_tools.search_text(workspace, "FastAPI")
        assert result["skipped_files"] == 2
        assert {m["path"] for m in result["matches"]} == {"apps/api/main.py"}

    def test_truncates_long_lines(self, workspace):
        (workspace / "min.js").write_text("FastAPI" + "a" * 1_000 + "\n")
        result = repo_tools.search_text(workspace, "FastAPI")
        match = next(m for m in result["matches"] if m["path"] == "min.js")
        assert len(match["text"]) == repo_tools.MAX_MATCH_LINE_CHARS

    def test_truncates_at_match_limit(self, workspace, monkeypatch):
        monkeypatch.setattr(repo_tools, "MAX_SEARCH_MATCHES", 1)
        result = repo_tools.search_text(workspace, "FastAPI")
        assert len(result["matches"]) == 1
        assert result["truncated"] is True

    def test_rejects_empty_query(self, workspace):
        with pytest.raises(ValueError, match="empty"):
            repo_tools.search_text(workspace, "")
