"""Tests for jj/hooks/guard-jj-mutating PreToolUse hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "guard-jj-mutating"


def run_hook(command: str | None, cwd: str | None) -> subprocess.CompletedProcess:
    """Run the hook with a simulated Bash tool call. Pass None to omit a field."""
    data: dict = {}
    if command is not None:
        data["tool_input"] = {"command": command}
    if cwd is not None:
        data["cwd"] = cwd
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_hook_raw(stdin: str) -> subprocess.CompletedProcess:
    """Run the hook with arbitrary stdin (for malformed-input tests)."""
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture()
def jj_repo(tmp_path: Path) -> Path:
    """Create a directory with .jj/ to simulate a jj repo."""
    (tmp_path / ".jj").mkdir()
    return tmp_path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a directory with only .git/ (no .jj/)."""
    (tmp_path / ".git").mkdir()
    return tmp_path


class TestEdgeCases:
    """Malformed or empty input must exit 0 (silent allow), never crash."""

    def test_empty_stdin(self) -> None:
        result = run_hook_raw("")
        assert result.returncode == 0
        assert result.stdout == ""

    def test_malformed_json(self) -> None:
        result = run_hook_raw("not json")
        assert result.returncode == 0
        assert result.stdout == ""

    def test_null_tool_input(self) -> None:
        """tool_input as null must not crash with AttributeError."""
        result = run_hook_raw('{"tool_input": null, "cwd": "/tmp"}')
        assert result.returncode == 0
        assert result.stdout == ""

    def test_string_tool_input(self) -> None:
        """tool_input as string must not crash with AttributeError."""
        result = run_hook_raw('{"tool_input": "not-a-dict", "cwd": "/tmp"}')
        assert result.returncode == 0
        assert result.stdout == ""

    def test_missing_tool_input(self) -> None:
        result = run_hook_raw('{"cwd": "/tmp"}')
        assert result.returncode == 0
        assert result.stdout == ""

    def test_missing_cwd(self) -> None:
        """No cwd → can't resolve repo, silent allow."""
        result = run_hook("jj op restore", None)
        assert result.returncode == 0
        assert result.stdout == ""

    def test_empty_command(self) -> None:
        result = run_hook("", "/tmp")
        assert result.returncode == 0
        assert result.stdout == ""
