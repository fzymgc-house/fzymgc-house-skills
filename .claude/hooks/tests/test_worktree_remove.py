"""Tests for .claude/hooks/worktree-remove Python uv script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HOOK_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOK_DIR / "worktree-remove"


def run_hook(
    data: dict,
    *,
    cwd: Path,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run the worktree-remove hook as a subprocess with JSON on stdin."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(data),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# test_no_path_exits_0 — empty input
# ---------------------------------------------------------------------------


def test_no_path_exits_0(git_repo: Path) -> None:
    """Empty JSON input exits 0 with a warning about missing path field."""
    result = run_hook({}, cwd=git_repo)
    assert result.returncode == 0
    assert "no path field" in result.stderr


# ---------------------------------------------------------------------------
# test_nonexistent_path_exits_0 — path doesn't exist
# ---------------------------------------------------------------------------


def test_nonexistent_path_exits_0(git_repo: Path) -> None:
    """Non-existent path exits 0 with 'already removed' warning."""
    result = run_hook({"path": str(git_repo / "no-such-worktree")}, cwd=git_repo)
    assert result.returncode == 0
    assert "already removed" in result.stderr


# ---------------------------------------------------------------------------
# test_removes_git_worktree — integration: create worktree, remove it
# ---------------------------------------------------------------------------


def test_removes_git_worktree(git_repo: Path) -> None:
    """Create a git worktree in _worktrees sibling, remove it, verify deregistered."""
    repo_name = git_repo.name
    worktrees_dir = git_repo.parent / f"{repo_name}_worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)

    worktree_name = "fix-worker-abc"
    worktree_path = worktrees_dir / worktree_name

    # Create the worktree
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path)],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git worktree add failed: {result.stderr}"
    assert worktree_path.is_dir()

    # Run the remove hook from within the repo (so detect_repo_root works)
    result = run_hook({"path": str(worktree_path)}, cwd=git_repo)
    assert result.returncode == 0, f"hook failed: {result.stderr}"

    # Worktree directory should be gone
    assert not worktree_path.exists()

    # Git should no longer list this worktree
    list_result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
    )
    assert worktree_name not in list_result.stdout


# ---------------------------------------------------------------------------
# test_cleans_up_empty_parent — verify parent rmdir after last worktree removed
# ---------------------------------------------------------------------------


def test_cleans_up_empty_parent(git_repo: Path) -> None:
    """After the last worktree is removed, the _worktrees parent dir is removed."""
    repo_name = git_repo.name
    worktrees_dir = git_repo.parent / f"{repo_name}_worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)

    worktree_name = "fix-worker-xyz"
    worktree_path = worktrees_dir / worktree_name

    # Create the worktree
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path)],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git worktree add failed: {result.stderr}"

    # Run the remove hook
    result = run_hook({"path": str(worktree_path)}, cwd=git_repo)
    assert result.returncode == 0, f"hook failed: {result.stderr}"

    # Both worktree and parent should be gone (parent was the only entry)
    assert not worktree_path.exists()
    assert not worktrees_dir.exists(), (
        f"Expected _worktrees parent to be cleaned up but it still exists: {worktrees_dir}"
    )


# ---------------------------------------------------------------------------
# test_outside_expected_parent_exits_1 — rogue path refused
# ---------------------------------------------------------------------------


def test_outside_expected_parent_exits_1(git_repo: Path, tmp_path: Path) -> None:
    """A path outside the expected _worktrees parent is refused with exit 1."""
    # Create a directory that exists but is NOT inside any _worktrees sibling
    rogue_dir = tmp_path / "rogue-worktree"
    rogue_dir.mkdir()

    # Run hook from within the repo; the rogue_dir is inside tmp_path, not
    # inside <repo>_worktrees/, so it should be refused
    result = run_hook({"path": str(rogue_dir)}, cwd=git_repo)
    assert result.returncode == 1
    assert "refusing removal" in result.stderr or "ERROR" in result.stderr

    # The rogue directory should NOT have been deleted
    assert rogue_dir.exists()
