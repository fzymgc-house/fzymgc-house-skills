"""Tests for dev-flow/hooks/nudge-rg-over-grep PreToolUse hook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "nudge-rg-over-grep"

PROBE_MCP = {"mcpServers": {"probe": {"command": "probe", "args": ["mcp"]}}}
NO_PROBE_MCP = {"mcpServers": {"context7": {"command": "context7"}}}


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    """Isolated HOME + cache dir so the hook never reads the real ~/.claude.json."""
    home = tmp_path / "home"
    home.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    return {"HOME": str(home), "XDG_CACHE_HOME": str(cache)}


def run_hook(
    command: str,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook with a simulated Bash tool call."""
    data: dict[str, object] = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd is not None:
        data["cwd"] = str(cwd)
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=10,
        env=full_env,
    )


def nudge_context(result: subprocess.CompletedProcess) -> str | None:
    """Extract the additionalContext nudge from the hook's stdout, if any."""
    out = result.stdout.strip()
    if not out:
        return None
    payload = json.loads(out)
    return payload.get("hookSpecificOutput", {}).get("additionalContext")


def make_repo(tmp_path: Path, name: str, mcp: dict | None) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    (repo / ".git").mkdir()  # repo-root marker
    if mcp is not None:
        (repo / ".mcp.json").write_text(json.dumps(mcp))
    return repo


class TestGrepToRg:
    """grep-family tools leading a (non-symbol) segment are nudged toward rg."""

    @pytest.mark.parametrize(
        "command",
        [
            "grep -rn foo .",
            "egrep bar src/",
            "fgrep literal file.txt",
            "ugrep -r baz",
            "ug --query",
            "cd internal && grep -rn foo",  # segment split
            "/usr/bin/grep foo bar.txt",  # absolute path
            "GREP_COLORS=mc=01 grep foo x",  # leading env assignment
            "ls; grep foo x",  # semicolon segment
        ],
    )
    def test_nudges_to_rg(self, command: str, env: dict[str, str]) -> None:
        result = run_hook(command, env=env)
        assert result.returncode == 0, result.stderr
        ctx = nudge_context(result)
        assert ctx is not None, f"expected a nudge for: {command}"
        assert "Prefer `rg`" in ctx
        assert "ast-grep" in ctx
        assert "mcp__probe" not in ctx


class TestSilent:
    """Non-grep commands and pipe-filter / quoted uses stay silent."""

    @pytest.mark.parametrize(
        "command",
        [
            "rg -n foo",  # already preferred; not symbol-shaped
            "sg -p 'foo($$$)' -l go",  # ast-grep, not symbol-shaped
            "ps aux | grep foo",  # pipe filter, not leading
            'jj describe -m "fix grep handling"',  # grep inside quotes
            "pgrep node",  # not grep
            "git grep foo",  # git subcommand, first word git
            "echo hello",
            "",  # empty command
        ],
    )
    def test_silent(self, command: str, env: dict[str, str]) -> None:
        result = run_hook(command, env=env)
        assert result.returncode == 0, result.stderr
        assert nudge_context(result) is None, f"unexpected nudge for: {command}"

    def test_non_bash_tool_ignored(self, env: dict[str, str]) -> None:
        data = {"tool_name": "Edit", "tool_input": {"file_path": "/repo/x.go"}}
        full_env = dict(os.environ)
        full_env.update(env)
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(data),
            capture_output=True,
            text=True,
            timeout=10,
            env=full_env,
        )
        assert result.returncode == 0, result.stderr
        assert nudge_context(result) is None


class TestProbeGating:
    """Symbol-shaped searches nudge toward probe ONLY when the MCP is configured."""

    def test_grep_symbol_with_probe_nudges_probe(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "withprobe", PROBE_MCP)
        result = run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        ctx = nudge_context(result)
        assert ctx is not None
        assert "mcp__probe__search_code" in ctx

    def test_grep_symbol_without_probe_nudges_rg(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "noprobe", NO_PROBE_MCP)
        result = run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        ctx = nudge_context(result)
        assert ctx is not None
        assert "Prefer `rg`" in ctx
        assert "mcp__probe" not in ctx

    def test_rg_symbol_with_probe_nudges_probe(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "withprobe", PROBE_MCP)
        result = run_hook("rg 'func Foo'", cwd=repo, env=env)
        ctx = nudge_context(result)
        assert ctx is not None
        assert "mcp__probe__search_code" in ctx

    def test_rg_symbol_without_probe_is_silent(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "noprobe", NO_PROBE_MCP)
        result = run_hook("rg 'func Foo'", cwd=repo, env=env)
        assert nudge_context(result) is None

    def test_sg_symbol_with_probe_nudges_probe(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "withprobe", PROBE_MCP)
        result = run_hook("sg -p 'func Foo' -l go", cwd=repo, env=env)
        ctx = nudge_context(result)
        assert ctx is not None
        assert "mcp__probe__search_code" in ctx

    def test_no_mcp_config_at_all_nudges_rg(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "barerepo", None)
        result = run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        ctx = nudge_context(result)
        assert ctx is not None
        assert "Prefer `rg`" in ctx


class TestCache:
    """The probe-availability sentinel is written and invalidated by config changes."""

    def test_cache_file_written(self, tmp_path: Path, env: dict[str, str]) -> None:
        repo = make_repo(tmp_path, "withprobe", PROBE_MCP)
        run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        cache_dir = Path(env["XDG_CACHE_HOME"]) / "dev-flow-grepping"
        sentinels = list(cache_dir.glob("probe-*.json"))
        assert sentinels, "expected a probe sentinel to be cached"
        payload = json.loads(sentinels[0].read_text())
        assert payload["probe"] is True
        assert "sig" in payload

    def test_signature_invalidates_when_config_changes(
        self, tmp_path: Path, env: dict[str, str]
    ) -> None:
        repo = make_repo(tmp_path, "evolving", NO_PROBE_MCP)
        # First call: no probe -> rg nudge, result cached.
        first = run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        assert "Prefer `rg`" in (nudge_context(first) or "")
        # Add probe to the repo config; the stat signature must invalidate the cache.
        (repo / ".mcp.json").write_text(json.dumps(PROBE_MCP))
        second = run_hook("grep -rn 'func Foo' .", cwd=repo, env=env)
        assert "mcp__probe__search_code" in (nudge_context(second) or "")
