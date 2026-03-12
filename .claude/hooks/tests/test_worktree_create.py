"""Tests for .claude/hooks/worktree-create Python uv script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HOOK_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOK_DIR / "worktree-create"


def run_hook(
    data: dict,
    *,
    cwd: Path,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run the worktree-create hook as a subprocess with JSON on stdin."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(data),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Input validation tests — all should exit 1
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_no_name_field(self, git_repo: Path) -> None:
        """Missing name field exits 1 with an error message."""
        result = run_hook({}, cwd=git_repo)
        assert result.returncode == 1
        assert "no worktree name provided" in result.stderr

    def test_empty_name(self, git_repo: Path) -> None:
        """Empty string name exits 1."""
        result = run_hook({"name": ""}, cwd=git_repo)
        assert result.returncode == 1
        assert "no worktree name provided" in result.stderr

    def test_path_traversal_dotdot(self, git_repo: Path) -> None:
        """Name containing '..' exits 1."""
        result = run_hook({"name": "../evil"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_path_traversal_leading_dot(self, git_repo: Path) -> None:
        """Name starting with '.' exits 1."""
        result = run_hook({"name": ".hidden"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_shell_metachar_semicolon(self, git_repo: Path) -> None:
        """Name containing ';' exits 1."""
        result = run_hook({"name": "foo;bar"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_shell_metachar_dollar(self, git_repo: Path) -> None:
        """Name containing '$' exits 1."""
        result = run_hook({"name": "foo$bar"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_shell_metachar_backtick(self, git_repo: Path) -> None:
        """Name containing backtick exits 1."""
        result = run_hook({"name": "foo`bar"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_shell_metachar_space(self, git_repo: Path) -> None:
        """Name containing space exits 1."""
        result = run_hook({"name": "foo bar"}, cwd=git_repo)
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_invalid_json(self, git_repo: Path) -> None:
        """Malformed JSON input exits 1."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json",
            cwd=str(git_repo),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 1
        assert "ERROR" in proc.stderr


# ---------------------------------------------------------------------------
# Git integration test
# ---------------------------------------------------------------------------


class TestGitIntegration:
    def test_creates_worktree_in_git_repo(self, git_repo: Path) -> None:
        """Creates a worktree and prints its path to stdout."""
        worktree_parent = git_repo.parent / f"{git_repo.name}_worktrees"
        worktree_path = worktree_parent / "feature-x"

        try:
            result = run_hook({"name": "feature-x"}, cwd=git_repo)

            assert result.returncode == 0, f"stderr: {result.stderr}"
            output = result.stdout.strip()
            assert output == str(worktree_path), (
                f"Expected {worktree_path}, got {output}"
            )
            assert Path(output).is_dir(), "Worktree directory should exist"

            # Verify it appears in git worktree list
            wt_list = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=str(git_repo),
                capture_output=True,
                text=True,
                check=True,
            )
            assert str(worktree_path) in wt_list.stdout

        finally:
            # Cleanup
            if worktree_path.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=str(git_repo),
                    capture_output=True,
                )
            if worktree_parent.is_dir() and not any(worktree_parent.iterdir()):
                worktree_parent.rmdir()

    def test_creates_branch_in_git_repo(self, git_repo: Path) -> None:
        """Created worktree has branch worktree/<name>."""
        worktree_parent = git_repo.parent / f"{git_repo.name}_worktrees"
        worktree_path = worktree_parent / "my-feature"

        try:
            result = run_hook({"name": "my-feature"}, cwd=git_repo)
            assert result.returncode == 0, f"stderr: {result.stderr}"

            # Verify the branch exists
            branches = subprocess.run(
                ["git", "branch"],
                cwd=str(git_repo),
                capture_output=True,
                text=True,
                check=True,
            )
            assert "worktree/my-feature" in branches.stdout

        finally:
            if worktree_path.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=str(git_repo),
                    capture_output=True,
                )
            if worktree_parent.is_dir() and not any(worktree_parent.iterdir()):
                worktree_parent.rmdir()


# ---------------------------------------------------------------------------
# Sibling directory test
# ---------------------------------------------------------------------------


class TestSiblingDirectory:
    def test_worktree_parent_is_sibling(self, git_repo: Path) -> None:
        """Worktree parent is <repo>_worktrees at the same level as the repo."""
        worktree_parent = git_repo.parent / f"{git_repo.name}_worktrees"
        worktree_path = worktree_parent / "sibling-test"

        try:
            result = run_hook({"name": "sibling-test"}, cwd=git_repo)
            assert result.returncode == 0, f"stderr: {result.stderr}"

            output_path = Path(result.stdout.strip())

            # Verify the parent directory name pattern
            assert output_path.parent.name == f"{git_repo.name}_worktrees", (
                f"Expected parent name '{git_repo.name}_worktrees', "
                f"got '{output_path.parent.name}'"
            )

            # Verify it's a sibling (same parent as the repo)
            assert output_path.parent.parent == git_repo.parent, (
                f"Worktree parent should be sibling of repo, "
                f"not nested inside it. Repo: {git_repo}, "
                f"Worktree: {output_path}"
            )

            # Verify worktree is NOT inside the repo
            assert not str(output_path).startswith(str(git_repo) + "/"), (
                f"Worktree {output_path} must not be inside repo {git_repo}"
            )

        finally:
            if worktree_path.is_dir():
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree_path)],
                    cwd=str(git_repo),
                    capture_output=True,
                )
            if worktree_parent.is_dir() and not any(worktree_parent.iterdir()):
                worktree_parent.rmdir()
