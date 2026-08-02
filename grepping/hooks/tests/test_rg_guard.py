"""Tests for the rg-guard PreToolUse hook."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grepping.hooks.tests.conftest import (
    context,
    deny_reason,
    payload,
    run_hook,
)


@pytest.mark.parametrize(
    ("command", "correction"),
    [
        ("rg -rn ProcessEvent", "rg -n ProcessEvent"),
        ("rg -rln ProcessEvent", "rg -ln ProcessEvent"),
        ("rg -rl ProcessEvent", "rg -l ProcessEvent"),
        ("rg -nr ProcessEvent", "rg -n ProcessEvent"),
        ("cd src && rg -rn ProcessEvent", "rg -n ProcessEvent"),
        ("printf x | rg -rn ProcessEvent", "rg -n ProcessEvent"),
        ("git ls-files | xargs rg -rn ProcessEvent", "xargs rg -n ProcessEvent"),
        ("timeout 5 rg -rn ProcessEvent", "timeout 5 rg -n ProcessEvent"),
        ("rg -ro ProcessEvent", "rg -o ProcessEvent"),
        ("rg -nR ProcessEvent", "rg -n ProcessEvent"),
        ("rg --recursive ProcessEvent", "rg ProcessEvent"),
        ("rg --no-pager ProcessEvent", "rg ProcessEvent"),
        ("rg --include='*.go' ProcessEvent", "rg -g '*.go' ProcessEvent"),
        ("rg --exclude='*_test.go' ProcessEvent", "rg -g '!*_test.go' ProcessEvent"),
        ("rg --exclude-dir=.git ProcessEvent", "rg -g '!.git/**' ProcessEvent"),
        ("rg -E 'A|B'", "rg 'A|B'"),
        (r"rg 'A\|B'", "rg 'A|B'"),
        ("rg 'foo(?=bar)'", "rg -P 'foo(?=bar)'"),
        (r"rg '\1foo'", r"rg -P '\1foo'"),
    ],
)
def test_denies_deterministic_failures(
    command: str, correction: str, isolated_env: dict[str, str]
) -> None:
    reason = deny_reason(run_hook("rg-guard", command, env=isolated_env))
    assert reason is not None
    assert correction in reason
    assert "RG_GUARD_OK=1" in reason


@pytest.mark.parametrize(
    "command",
    [
        "rg -n ProcessEvent",
        "rg -o -r '$1' 'id=(.*)'",
        "rg -or '$1' 'id=(.*)'",
        "rg -E utf-8 ProcessEvent",
        "rg -E x-user-defined ProcessEvent",
        r"rg -F 'A\|B'",
        r"rg -FP 'A\|B'",
        "rg -P 'foo(?=bar)'",
        r"rg '^\| col \|' README.md",
    ],
)
def test_allows_valid_rg(command: str, isolated_env: dict[str, str]) -> None:
    assert payload(run_hook("rg-guard", command, env=isolated_env)) == {}


def test_escape_hatch_bypasses_deny_and_logs(isolated_env: dict[str, str]) -> None:
    result = run_hook("rg-guard", "RG_GUARD_OK=1 rg -rn foo", env=isolated_env)
    assert payload(result) == {}
    log = Path(isolated_env["HOME"]) / ".claude/logs/rg-guard.jsonl"
    record = json.loads(log.read_text().splitlines()[0])
    assert record["decision"] == "bypass"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("rg -h ProcessEvent", "--no-filename"),
        (r"rg 'first\nsecond'", "needs `-U`"),
        ("ssh router 'journalctl | rg error'", "filtering runs locally"),
    ],
)
def test_ambiguous_cases_warn_only(
    command: str, expected: str, isolated_env: dict[str, str]
) -> None:
    result = run_hook("rg-guard", command, env=isolated_env)
    assert deny_reason(result) is None
    assert expected in (context(result) or "")


def test_grep_nudge_remains_available(isolated_env: dict[str, str]) -> None:
    result = run_hook("rg-guard", "cd src && grep -rn needle .", env=isolated_env)
    assert "Prefer rg" in (context(result) or "")


def test_subagent_payload_is_denied_and_identified(
    isolated_env: dict[str, str],
) -> None:
    result = run_hook(
        "rg-guard", "rg -rn needle", env=isolated_env, agent_id="agent-a1"
    )
    assert deny_reason(result) is not None
    log = Path(isolated_env["HOME"]) / ".claude/logs/rg-guard.jsonl"
    record = json.loads(log.read_text().splitlines()[0])
    assert record["agent_id"] == "agent-a1"
    assert record["decision"] == "deny"
