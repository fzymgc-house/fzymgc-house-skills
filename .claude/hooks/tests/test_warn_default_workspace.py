"""Tests for the warn-default-workspace SessionStart hook.

The hook warns (stdout) when invoked in the default jj workspace and stays
silent in additional workspaces or outside jj. Detection: `.jj/repo` is a
directory in the main checkout, a file in additional workspaces.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "warn-default-workspace"
WARNING_MARKER = "shared `default` jj workspace"


def _run(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the hook with an empty JSON event on stdin from ``cwd``."""
    return subprocess.run(
        [str(HOOK)],
        cwd=str(cwd),
        input="{}",
        capture_output=True,
        text=True,
    )


def test_warns_in_default_workspace(jj_repo: Path) -> None:
    result = _run(jj_repo)
    assert result.returncode == 0
    assert WARNING_MARKER in result.stdout


def test_warns_in_colocated_default_workspace(colocated_jj_repo: Path) -> None:
    result = _run(colocated_jj_repo)
    assert result.returncode == 0
    assert WARNING_MARKER in result.stdout


def test_silent_in_additional_workspace(jj_repo: Path) -> None:
    workspace = jj_repo.parent / "additional-ws"
    subprocess.run(
        [
            "jj",
            "--no-pager",
            "workspace",
            "add",
            str(workspace),
            "--name",
            "additional-ws",
        ],
        cwd=str(jj_repo),
        check=True,
        capture_output=True,
    )
    result = _run(workspace)
    assert result.returncode == 0
    assert result.stdout == ""


def test_silent_outside_jj(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
