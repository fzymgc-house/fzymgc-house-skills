"""Validation tests for drain-worker-launch --check and its direnv gate."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH = REPO_ROOT / "dev-flow" / "scripts" / "drain-worker-launch"


def _load_launch():
    """Import the extensionless `uv run --script` entrypoint as a module.

    `spec_from_file_location` can't infer a loader without a `.py` suffix, so
    drive a `SourceFileLoader` explicitly. The script self-inserts its own dir
    on `sys.path` to resolve `import _muxdriver`; `main()` stays guarded by
    `__name__ == "__main__"`, so import has no side effects.
    """
    loader = SourceFileLoader("drain_worker_launch", str(LAUNCH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


GOOD_BEAD = [
    {
        "id": "ep-9",
        "issue_type": "drain",
        "status": "in_progress",
        "metadata": {
            "drain_mode": "epic",
            "drain_workspace": "/tmp/ws",
            "drain_scope": "ep-9",
            "drain_sentinel": "all children closed",
        },
    }
]


def _run_check(
    tmp_path: Path, bead_json: list, *, worker_type: str = "cmux"
) -> subprocess.CompletedProcess:
    """Run `drain-worker-launch --check` with a fake `bd` and `cmux` on PATH."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "bd").write_text(
        f"#!/usr/bin/env bash\ncat <<'EOF'\n{json.dumps(bead_json)}\nEOF\n"
    )
    (fake_bin / "bd").chmod(0o755)
    # Provide a stub `cmux` so the on-PATH check passes.
    (fake_bin / "cmux").write_text("#!/usr/bin/env bash\nexit 0\n")
    (fake_bin / "cmux").chmod(0o755)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
    env.pop("TMUX", None)
    return subprocess.run(
        [str(LAUNCH), "--check", "--drain-id", "ep-9", "--worker-type", worker_type],
        capture_output=True,
        text=True,
        env=env,
    )


def test_check_happy_path_prints_plan(tmp_path) -> None:
    r = _run_check(tmp_path, GOOD_BEAD)
    assert r.returncode == 0, r.stderr
    assert "multiplexer=cmux" in r.stdout
    assert "workspace=/tmp/ws" in r.stdout
    assert "scope=ep-9" in r.stdout
    assert "sentinel=all children closed" in r.stdout


def test_check_refuses_wrong_type(tmp_path) -> None:
    bad = [dict(GOOD_BEAD[0], issue_type="task")]
    r = _run_check(tmp_path, bad)
    assert r.returncode != 0
    assert "not a drain bead" in r.stderr.lower()


def test_check_refuses_not_in_progress(tmp_path) -> None:
    bad = [dict(GOOD_BEAD[0], status="closed")]
    r = _run_check(tmp_path, bad)
    assert r.returncode != 0
    assert "in_progress" in r.stderr.lower()


def test_check_refuses_non_epic_mode(tmp_path) -> None:
    md = dict(GOOD_BEAD[0]["metadata"], drain_mode="set")
    bad = [dict(GOOD_BEAD[0], metadata=md)]
    r = _run_check(tmp_path, bad)
    assert r.returncode != 0
    assert "epic" in r.stderr.lower()


def test_check_refuses_missing_metadata(tmp_path) -> None:
    md = dict(GOOD_BEAD[0]["metadata"])
    del md["drain_sentinel"]
    bad = [dict(GOOD_BEAD[0], metadata=md)]
    r = _run_check(tmp_path, bad)
    assert r.returncode != 0
    assert "sentinel" in r.stderr.lower()


# --- direnv readiness gate (GitHub #158) ---------------------------------

# A realistic post-allow pane: the stale pre-allow "is blocked" error from the
# first `cd` is still visible, then the echoed probe command, then the resolved
# success line. The old gate did `"blocked" in screen` and false-died on this.
STALE_BLOCKED_THEN_OK = (
    "$ cd /ws/_worktrees/drain-epic-7\n"
    "direnv: error /ws/_worktrees/drain-epic-7/.envrc is blocked. "
    "Run `direnv allow` to approve its content\n"
    "$ direnv allow; echo DRAIN_DIRENV=$?\n"
    "direnv: loading /ws/_worktrees/drain-epic-7/.envrc\n"
    "direnv: export +FOO +BAR\n"
    "DRAIN_DIRENV=0\n"
    "$ \n"
)


def test_probe_is_idempotent_despite_stale_blocked_line() -> None:
    """#158 regression: stale 'is blocked' scrollback must not fail the gate."""
    m = _load_launch()
    # The old absence-of-negative test would have tripped here:
    assert "blocked" in STALE_BLOCKED_THEN_OK.lower()
    # The new positive probe reads the resolved exit code = success:
    match = m._DIRENV_PROBE_RE.search(STALE_BLOCKED_THEN_OK)
    assert match is not None and match.group(1) == "0"


def test_probe_ignores_the_echoed_command_line() -> None:
    """The typed `=$?` command echo must not match before output resolves."""
    m = _load_launch()
    echo_only = "$ direnv allow; echo DRAIN_DIRENV=$?\n"
    assert m._DIRENV_PROBE_RE.search(echo_only) is None


def test_probe_detects_nonzero_exit() -> None:
    m = _load_launch()
    match = m._DIRENV_PROBE_RE.search("DRAIN_DIRENV=1\n")
    assert match is not None and match.group(1) == "1"


def test_await_polls_until_predicate_then_returns_screen() -> None:
    m = _load_launch()
    reads = iter(
        [
            "$ direnv allow; echo DRAIN_DIRENV=$?\n",  # echo only — no digit yet
            "direnv: loading .envrc\n",  # mid re-eval
            "DRAIN_DIRENV=0\n",  # resolved
        ]
    )
    clock = iter([0.0, 1.0, 2.0, 3.0, 4.0])
    got = m._await(
        lambda: next(reads),
        m._DIRENV_PROBE_RE.search,
        now=lambda: next(clock),
        sleep=lambda _seconds: None,
    )
    assert got is not None and m._DIRENV_PROBE_RE.search(got).group(1) == "0"


def test_await_returns_none_on_timeout() -> None:
    m = _load_launch()
    clock = iter([0.0, 16.0])  # second tick is past the default 15s deadline
    got = m._await(
        lambda: "still blocked, never resolves\n",
        m._DIRENV_PROBE_RE.search,
        now=lambda: next(clock),
        sleep=lambda _seconds: None,
    )
    assert got is None


# --- shell-agnostic probe (GitHub #162) ----------------------------------


def test_probe_is_wrapped_in_posix_sh() -> None:
    """#162 regression: the probe must exec POSIX `sh`, not lean on the
    surface's login shell, whose `$?` is a parse error under fish."""
    m = _load_launch()
    assert m._DIRENV_PROBE_CMD.startswith("sh -c ")
    # The exit-status syntax stays sandboxed inside the sh subshell.
    assert "$?" in m._DIRENV_PROBE_CMD


def test_probe_echo_line_still_does_not_match() -> None:
    """The echoed `sh -c '... =$?'` command must not match before output
    resolves — `$?` is not a digit, so the idempotency property holds."""
    m = _load_launch()
    echo_only = "$ " + m._DIRENV_PROBE_CMD + "\n"
    assert m._DIRENV_PROBE_RE.search(echo_only) is None


@pytest.mark.skipif(shutil.which("fish") is None, reason="fish not installed")
def test_probe_parses_under_fish() -> None:
    """#162 regression: drive the probe string through a real fish parse.

    The pre-#162 probe `direnv allow; echo DRAIN_DIRENV=$?` is a parse error
    under fish (`$? is not the exit status`); `fish --no-execute` validates
    syntax without running the command.
    """
    m = _load_launch()
    r = subprocess.run(
        ["fish", "--no-execute", "-c", m._DIRENV_PROBE_CMD],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"fish rejected the probe: {r.stderr.strip()}"


# --- non-direnv repos: skip the probe entirely (GitHub #166) -------------


class _FakeMux:
    """Minimal mux double: spawn runs `true`, ref is fixed."""

    name = "cmux"

    def spawn_argv(self, _drain_id):
        return ["true"]

    def parse_ref(self, _stdout):
        return "surface:1"


def _drive_launch(m, monkeypatch, workspace: Path) -> list[str]:
    """Drive `launch()` with all pane I/O faked, returning the texts sent.

    `_send`/`_enter`/`_screen` are stubbed so no real multiplexer is touched;
    `time.sleep` is neutralized so the launch's fixed delays don't run. The
    canned screen carries the workspace path (cd check), a resolved
    `DRAIN_DIRENV=0` (probe gate, when reached), and `Goal set:` (no warning).
    """
    sent: list[str] = []
    screen = f"{workspace}\nDRAIN_DIRENV=0\nGoal set:\n"
    monkeypatch.setattr(m, "_send", lambda _mux, _ref, text: sent.append(text))
    monkeypatch.setattr(m, "_enter", lambda _mux, _ref: None)
    monkeypatch.setattr(m, "_screen", lambda _mux, _ref: screen)
    monkeypatch.setattr(m.time, "sleep", lambda _seconds: None)
    md = {"drain_workspace": str(workspace), "drain_sentinel": "done"}
    ref = m.launch(_FakeMux(), "ep-9", md)
    assert ref == "surface:1"
    return sent


def test_launch_skips_direnv_probe_when_no_envrc(tmp_path, monkeypatch) -> None:
    """#166 regression: a workspace with no .envrc must not run the probe.

    `direnv allow` exits 1 for BOTH a blocked and a missing .envrc, so the
    exit-code gate would misread a non-direnv repo as 'still blocked' and abort
    the launch. The probe must be skipped when there is nothing to allow.
    """
    m = _load_launch()
    assert not (tmp_path / ".envrc").exists()
    sent = _drive_launch(m, monkeypatch, tmp_path)
    assert m._DIRENV_PROBE_CMD not in sent


def test_launch_runs_direnv_probe_when_envrc_present(tmp_path, monkeypatch) -> None:
    """The guard must not over-correct: a real .envrc still gets probed."""
    m = _load_launch()
    (tmp_path / ".envrc").write_text("export FOO=bar\n")
    sent = _drive_launch(m, monkeypatch, tmp_path)
    assert m._DIRENV_PROBE_CMD in sent
