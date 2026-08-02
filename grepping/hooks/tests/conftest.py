"""Helpers shared by the grepping hook tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent


@pytest.fixture()
def isolated_env(tmp_path: Path) -> dict[str, str]:
    home = tmp_path / "home"
    home.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    return {"HOME": str(home), "XDG_CACHE_HOME": str(cache)}


def run_hook(
    hook: str,
    command: str,
    *,
    env: dict[str, str],
    response: object | None = None,
    cwd: Path | None = None,
    session_id: str = "session-1",
    agent_id: str = "",
) -> subprocess.CompletedProcess[str]:
    data: dict[str, object] = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": session_id,
    }
    if response is not None:
        data["tool_response"] = response
    if cwd is not None:
        data["cwd"] = str(cwd)
    if agent_id:
        data["agent_id"] = agent_id
    full_env = dict(os.environ)
    full_env.update(env)
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=10,
        env=full_env,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else {}


def context(result: subprocess.CompletedProcess[str]) -> str | None:
    value = payload(result)
    output = value.get("hookSpecificOutput", {})
    assert isinstance(output, dict)
    additional = output.get("additionalContext")
    return str(additional) if additional is not None else None


def deny_reason(result: subprocess.CompletedProcess[str]) -> str | None:
    value = payload(result)
    output = value.get("hookSpecificOutput", {})
    assert isinstance(output, dict)
    if output.get("permissionDecision") != "deny":
        return None
    return str(output.get("permissionDecisionReason", ""))
