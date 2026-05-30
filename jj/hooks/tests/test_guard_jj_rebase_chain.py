"""Tests for jj/hooks/guard-jj-rebase-chain PreToolUse hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "guard-jj-rebase-chain"


def run_hook(command: str | None, cwd: str | None) -> subprocess.CompletedProcess:
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
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture()
def jj_repo(tmp_path: Path) -> Path:
    (tmp_path / ".jj").mkdir()
    return tmp_path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def _decision(result: subprocess.CompletedProcess) -> str:
    """Extract the permissionDecision (or '' if no JSON output)."""
    if not result.stdout.strip():
        return ""
    payload = json.loads(result.stdout)
    return payload["hookSpecificOutput"]["permissionDecision"]


class TestEdgeCases:
    """Malformed input is silent — never block on parser errors."""

    def test_empty_stdin(self) -> None:
        result = run_hook_raw("")
        assert result.returncode == 0
        assert result.stdout == ""

    def test_malformed_json(self) -> None:
        result = run_hook_raw("not json")
        assert result.returncode == 0
        assert result.stdout == ""

    def test_null_tool_input(self) -> None:
        result = run_hook_raw('{"tool_input": null, "cwd": "/tmp"}')
        assert result.returncode == 0
        assert result.stdout == ""

    def test_no_command(self, jj_repo: Path) -> None:
        result = run_hook(None, str(jj_repo))
        assert result.returncode == 0
        assert result.stdout == ""


class TestBlocked:
    """The chain-truncating pattern must be denied inside jj repos."""

    @pytest.mark.parametrize(
        "command",
        [
            "jj rebase -r @ -o main",
            "jj rebase -r @ -o master",
            "jj rebase -r @ -o trunk",
            "jj rebase -r @ -o main@origin",
            "jj rebase -r @ -o develop@upstream",
            "jj rebase -r @ --onto main",
            "jj rebase -r @ --onto=main@origin",
            "jj rebase --revision @ -o main",
            "jj rebase --revisions=@ -o main",
            "jj rebase -r '@' -o main",
            'jj rebase -r "@" -o main',
            "jj rebase -r @ -o 'trunk()'",
            # Deprecated -d flag still recognized
            "jj rebase -r @ -d main",
            "jj rebase -r @ --destination main@origin",
            # Tolerates leading jj flags
            "jj --repo /tmp/r rebase -r @ -o main",
            # Tolerates compound shell
            "jj git fetch && jj rebase -r @ -o main@origin",
        ],
    )
    def test_blocked_pattern_denied(self, jj_repo: Path, command: str) -> None:
        result = run_hook(command, str(jj_repo))
        assert result.returncode == 0
        assert _decision(result) == "deny"
        payload = json.loads(result.stdout)
        reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
        assert "truncate" in reason.lower() or "single-revision" in reason
        assert "-s" in reason
        assert "roots(trunk()..@)" in reason

    def test_block_includes_system_message(self, jj_repo: Path) -> None:
        result = run_hook("jj rebase -r @ -o main", str(jj_repo))
        payload = json.loads(result.stdout)
        assert "systemMessage" in payload
        assert "jj-exempt" in payload["systemMessage"]


class TestAllowed:
    """Safe rebase shapes and unrelated commands must pass through silently."""

    @pytest.mark.parametrize(
        "command",
        [
            # -s root (the recommended chain-safe form)
            "jj rebase -s xyz -o main@origin --skip-emptied",
            "jj rebase -s 'roots(trunk()..@)' -o main",
            # -r with non-@ revision (extracting a specific commit)
            "jj rebase -r abc123 -o main",
            "jj rebase -r @- -o main",  # parent of @ — not a chain truncate
            # -r @ to a non-trunk destination (intentional move)
            "jj rebase -r @ -o feature-branch",
            "jj rebase -r @ -A some-change",  # insert-after, no -o trunk
            # -b (whole branch) is chain-safe by definition
            "jj rebase -b @ -o main",
            # Unrelated jj commands
            "jj log",
            "jj st",
            "jj git push -b my-feature",
            # Non-jj commands
            "git status",
            "ls -la",
            # The canonical chain-safe recipe must pass even though its $()
            # substitution contains `roots(trunk()..@)` and `-o main@origin`.
            "jj rebase -s \"$(jj --no-pager log -r 'roots(trunk()..@)' "
            "--no-graph -T 'change_id.short(12)')\" -o main@origin --skip-emptied",
            # FALSE-POSITIVE REGRESSION: a chain-safe `-s` rebase sharing a
            # Bash block with an unrelated `jj log -r '@ | @-'` state-display.
            # The `-r @` belongs to the log, not the rebase; the rebase uses
            # `-s`, so this must NOT block. (Cross-command leakage bug.)
            'jj rebase -s "$ROOT" -o main@origin --skip-emptied\n'
            "jj --no-pager log -r '@ | @-' -T x",
            "jj rebase -s xyz -o main ; jj log -r @ -T x",
            "jj log -r @ && jj rebase -s xyz -o main",
        ],
    )
    def test_allowed_command_passes(self, jj_repo: Path, command: str) -> None:
        result = run_hook(command, str(jj_repo))
        assert result.returncode == 0
        assert result.stdout == ""


class TestBypass:
    """`# jj-exempt` escalates to ASK so a human confirms intent."""

    def test_exempt_marker_escalates_to_ask(self, jj_repo: Path) -> None:
        result = run_hook(
            "jj rebase -r @ -o main@origin  # jj-exempt single-commit PR",
            str(jj_repo),
        )
        assert result.returncode == 0
        assert _decision(result) == "ask"
        payload = json.loads(result.stdout)
        assert (
            "truncat"
            in payload["hookSpecificOutput"]["permissionDecisionReason"].lower()
        )


class TestRepoDetection:
    """Outside a jj repo the hook is silent (no false positives in git-only repos)."""

    def test_git_only_repo_passes(self, git_repo: Path) -> None:
        result = run_hook("jj rebase -r @ -o main", str(git_repo))
        assert result.returncode == 0
        assert result.stdout == ""

    def test_no_cwd_passes(self) -> None:
        result = run_hook("jj rebase -r @ -o main", None)
        assert result.returncode == 0
        assert result.stdout == ""

    def test_subdirectory_detection(self, jj_repo: Path) -> None:
        subdir = jj_repo / "src" / "deep"
        subdir.mkdir(parents=True)
        result = run_hook("jj rebase -r @ -o main", str(subdir))
        assert result.returncode == 0
        assert _decision(result) == "deny"
