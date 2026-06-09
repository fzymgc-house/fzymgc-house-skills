"""Tests for dev-flow/scripts/ensure-isolated-workspace."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "ensure-isolated-workspace"
)

JJ_AVAILABLE = shutil.which("jj") is not None


def run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_script_exists_and_executable() -> None:
    assert SCRIPT.is_file(), f"script missing at {SCRIPT}"


def test_check_passes_in_git_repo(git_repo: Path) -> None:
    """git has no shared-default snapshot hazard — check is a no-op pass."""
    result = run(["check"], cwd=git_repo)
    assert result.returncode == 0, result.stderr


def test_ensure_returns_repo_root_in_git_repo(git_repo: Path) -> None:
    result = run(["ensure", "--name", "drain-x"], cwd=git_repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(
        git_repo.resolve()
    ) or result.stdout.strip() == str(git_repo)


@pytest.mark.skipif(not JJ_AVAILABLE, reason="jj is not installed")
class TestJj:
    def test_check_fails_in_default_workspace(self, jj_repo: Path) -> None:
        result = run(["check"], cwd=jj_repo)
        assert result.returncode == 1
        assert "STATUS: FAILED" in result.stderr

    def test_ensure_creates_isolated_workspace_from_default(
        self, jj_repo: Path
    ) -> None:
        worktree_parent = jj_repo.parent / f"{jj_repo.name}_worktrees"
        worktree_path = worktree_parent / "drain-epic-zzz"
        try:
            result = run(["ensure", "--name", "drain-epic-zzz"], cwd=jj_repo)
            assert result.returncode == 0, result.stderr
            assert result.stdout.strip() == str(worktree_path)

            # The created path must be an ADDITIONAL workspace (.jj/repo is a file).
            assert (worktree_path / ".jj" / "repo").is_file()

            wl = subprocess.run(
                ["jj", "--no-pager", "workspace", "list"],
                cwd=str(jj_repo),
                capture_output=True,
                text=True,
                check=True,
            )
            assert "worktree-drain-epic-zzz" in wl.stdout

            bl = subprocess.run(
                ["jj", "--no-pager", "bookmark", "list"],
                cwd=str(jj_repo),
                capture_output=True,
                text=True,
                check=True,
            )
            assert "worktree-drain-epic-zzz" in bl.stdout

            # Idempotent: a second ensure reuses the same path.
            again = run(["ensure", "--name", "drain-epic-zzz"], cwd=jj_repo)
            assert again.returncode == 0, again.stderr
            assert again.stdout.strip() == str(worktree_path)
        finally:
            if worktree_path.exists():
                subprocess.run(
                    [
                        "jj",
                        "--no-pager",
                        "workspace",
                        "forget",
                        "worktree-drain-epic-zzz",
                    ],
                    cwd=str(jj_repo),
                    capture_output=True,
                )
                shutil.rmtree(worktree_path, ignore_errors=True)
            if worktree_parent.is_dir() and not any(worktree_parent.iterdir()):
                worktree_parent.rmdir()

    def test_check_passes_in_additional_workspace(self, jj_repo: Path) -> None:
        ws = jj_repo.parent / f"{jj_repo.name}_worktrees" / "iso"
        ws.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["jj", "--no-pager", "workspace", "add", str(ws), "--name", "worktree-iso"],
            cwd=str(jj_repo),
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            result = run(["check"], cwd=ws)
            assert result.returncode == 0, result.stderr
            ensured = run(["ensure", "--name", "unused"], cwd=ws)
            assert ensured.returncode == 0, ensured.stderr
            assert ensured.stdout.strip() == str(ws)
        finally:
            subprocess.run(
                ["jj", "--no-pager", "workspace", "forget", "worktree-iso"],
                cwd=str(jj_repo),
                capture_output=True,
            )
            shutil.rmtree(ws, ignore_errors=True)
            if ws.parent.is_dir() and not any(ws.parent.iterdir()):
                ws.parent.rmdir()
