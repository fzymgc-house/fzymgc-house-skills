"""Validation tests for drain-worker-launch --check."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH = REPO_ROOT / "dev-flow" / "scripts" / "drain-worker-launch"

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
