"""Tests for the session-end-memory-capture Stop hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "session-end-memory-capture"


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
    )


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    git("remote", "add", "origin", "git@github.com:org/repo.git", cwd=repo)
    git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "--allow-empty",
        "-m",
        "init",
        cwd=repo,
    )
    return repo


def test_loop_guard_allows_stop(git_repo: Path):
    result = run_hook({"cwd": str(git_repo), "stop_hook_active": True})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_blocks_once_with_reason(git_repo: Path):
    result = run_hook({"cwd": str(git_repo), "stop_hook_active": False})
    out = json.loads(result.stdout)
    assert out["decision"] == "block"
    assert "curating-memory" in out["reason"]
    assert "spine repo:github.com/org/repo" in out["reason"]
    assert "overlay" not in out["reason"]  # primary checkout = spine only


def test_non_repo_no_interjection(tmp_path: Path):
    result = run_hook({"cwd": str(tmp_path), "stop_hook_active": False})
    assert result.returncode == 0
    assert result.stdout.strip() == ""
