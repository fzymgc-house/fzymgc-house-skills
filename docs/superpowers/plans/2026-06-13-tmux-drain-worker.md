# Multiplexer-Parameterized drain-with-worker + tmux Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the autonomous `/drain` worker launcher support tmux as well as cmux, by converting it to a single parameterized skill backed by `uv` scripts, and add a standalone reusable `tmux` plugin.

**Architecture:** A shared stdlib module `_muxdriver.py` is the single seam where cmux and tmux differ (pure argv construction). `drain-watchdog` gains `--multiplexer`; a new `drain-worker-launch` uv script owns bead validation + the pane-launch sequence (logic moved out of markdown). The `drain-with-worker` slash command becomes a skill taking `[worker-type] <drain-id>`. A separate `tmux` plugin documents tmux primitives.

**Tech Stack:** Python 3.11+ stdlib only, PEP 723 `uv run --script`, pytest, bd (beads), Claude Code plugin/skill manifests, release-please.

**Design bead:** fhsk-3qy · **Spec:** `docs/superpowers/specs/2026-06-13-tmux-drain-worker-design.md`

---

## File structure

| File | Responsibility |
|---|---|
| `dev-flow/scripts/_muxdriver.py` (create) | Shared stdlib module: `Multiplexer` ABC, `CmuxDriver`, `TmuxDriver`, `detect()`. Pure argv construction. |
| `tests/test_muxdriver.py` (create) | Unit tests for argv construction, tmux placement branch, `detect()` precedence. |
| `dev-flow/scripts/drain-watchdog` (modify) | Add `--multiplexer`; `read_surface`/`nudge` delegate to `_muxdriver`. |
| `dev-flow/scripts/drain-worker-launch` (create) | Validate the drain bead + launch the worker pane via the driver. `--check` = validate-only. |
| `tests/test_drain_worker_launch.py` (create) | Validation tests with a faked `bd` on PATH. |
| `dev-flow/skills/drain-with-worker/SKILL.md` (create) | The parameterized skill (thin; invokes the scripts). |
| `dev-flow/references/drain-with-worker.md` (modify) | Shared conceptual material; executable steps point at the scripts. |
| `dev-flow/commands/drain-with-worker.md` (delete) | Replaced by the skill. |
| `dev-flow/commands/drain.md` (modify) | Phase D probe widened to cmux-or-tmux; frontmatter gains tmux tools. |
| `tests/test_drain_skill.py` (modify) | Re-point the 4 command-reading tests at the skill/scripts. |
| `tmux/plugin.json` (create) | Source plugin manifest. |
| `tmux/skills/tmux/SKILL.md` (create) | General tmux usage skill. |
| `plugins/tmux/.codex-plugin/plugin.json` (create) | Codex wrapper manifest. |
| `plugins/tmux/skills` (create, symlink) | `-> ../../tmux/skills`. |
| `.claude-plugin/marketplace.json` (modify) | Register `tmux`. |
| `.agents/plugins/marketplace.json` (modify) | Register `tmux`. |
| `release-please-config.json` (modify) | Add `tmux/plugin.json` `$.version` to `extra-files`. |
| `Taskfile.yaml` (modify) | Gate new markdown + `tmux/plugin.json`. |
| `AGENTS.md` (modify) | "three source plugins" → "four"; document the skill arg + tmux plugin. |

**Dependency order:** Task 1 (driver) → Tasks 2 & 3 (scripts use it) → Task 4 (skill uses scripts) → Task 5 (drain.md) → Task 6 (tmux plugin) → Task 7 (docs + full gate).

---

## Task 1: Shared multiplexer driver `_muxdriver.py`

**Files:**

- Create: `dev-flow/scripts/_muxdriver.py`
- Test: `tests/test_muxdriver.py`
- [ ] **Step 1: Write the failing tests**

Create `tests/test_muxdriver.py`:

```python
"""Unit tests for the shared multiplexer driver."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MUXDRIVER = REPO_ROOT / "dev-flow" / "scripts" / "_muxdriver.py"


def _load():
    spec = importlib.util.spec_from_file_location("_muxdriver", MUXDRIVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_cmux_argv_construction() -> None:
    m = _load().CmuxDriver()
    assert m.name == "cmux"
    assert m.spawn_argv("ep-1")[:2] == ["cmux", "new-pane"]
    assert m.send_text_argv("surface:7", "hi") == [
        "cmux", "send", "--surface", "surface:7", "hi"
    ]
    assert m.send_enter_argv("surface:7") == [
        "cmux", "send-key", "--surface", "surface:7", "Enter"
    ]
    assert m.read_screen_argv("surface:7") == [
        "cmux", "read-screen", "--surface", "surface:7"
    ]
    assert m.parse_ref("surface:7\n") == "surface:7"


def test_tmux_argv_construction() -> None:
    m = _load().TmuxDriver(in_tmux=True)
    assert m.name == "tmux"
    assert m.send_text_argv("%7", "hi") == [
        "tmux", "send-keys", "-t", "%7", "-l", "hi"
    ]
    assert m.send_enter_argv("%7") == ["tmux", "send-keys", "-t", "%7", "Enter"]
    assert m.read_screen_argv("%7") == ["tmux", "capture-pane", "-p", "-t", "%7"]
    assert m.parse_ref("%7\n") == "%7"


def test_tmux_spawn_placement_branch() -> None:
    mod = _load()
    inside = mod.TmuxDriver(in_tmux=True).spawn_argv("ep-1")
    assert inside == ["tmux", "new-window", "-P", "-F", "#{pane_id}"]
    outside = mod.TmuxDriver(in_tmux=False).spawn_argv("ep-1")
    assert outside[:5] == ["tmux", "new-session", "-d", "-s", "drain-ep-1"]
    assert "-x" in outside and "-y" in outside
    assert outside[-2:] == ["-F", "#{pane_id}"]


def test_detect_precedence(monkeypatch) -> None:
    mod = _load()
    # explicit always wins
    monkeypatch.delenv("TMUX", raising=False)
    assert mod.detect("cmux").name == "cmux"
    assert mod.detect("tmux").name == "tmux"
    # inside tmux -> tmux
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1,0")
    assert mod.detect("auto").name == "tmux"
    # not inside tmux, cmux present -> cmux
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr(mod.shutil, "which", lambda c: "/usr/bin/cmux" if c == "cmux" else None)
    assert mod.detect("auto").name == "cmux"
    # neither present -> refuse
    monkeypatch.setattr(mod.shutil, "which", lambda c: None)
    import pytest
    with pytest.raises(RuntimeError):
        mod.detect("auto")


def test_detect_rejects_unknown() -> None:
    import pytest
    with pytest.raises(ValueError):
        _load().detect("screen")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Volumes/Code/github.com/fzymgc-house/fzymgc-house-skills_worktrees/tmux-drain-worker && uv run pytest tests/test_muxdriver.py -v`
Expected: FAIL — `_muxdriver.py` does not exist (collection error / ModuleNotFoundError).

- [ ] **Step 3: Write the module**

Create `dev-flow/scripts/_muxdriver.py`:

```python
"""Terminal-multiplexer drivers shared by drain-worker-launch and drain-watchdog.

Plain stdlib module — NO PEP 723 header and NO shebang. It is imported by the
`uv run --script` entrypoints via a resolved-`sys.path` insertion:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _muxdriver

Command construction is pure (argv lists, no subprocess), so it is unit-tested
without spawning a multiplexer. The two surfaces that differ between cmux and
tmux — spawning a worker pane and reading/driving it — live here and nowhere
else.
"""
from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod


class Multiplexer(ABC):
    """A terminal multiplexer the drain worker can run inside."""

    name: str

    @abstractmethod
    def spawn_argv(self, drain_id: str) -> list[str]:
        """Argv that creates the worker surface and prints its ref on stdout."""

    @abstractmethod
    def parse_ref(self, spawn_stdout: str) -> str:
        """Extract the surface ref from `spawn_argv` stdout."""

    @abstractmethod
    def send_text_argv(self, ref: str, text: str) -> list[str]:
        """Argv that types literal text into the surface (no submit)."""

    @abstractmethod
    def send_enter_argv(self, ref: str) -> list[str]:
        """Argv that submits (presses Enter) in the surface."""

    @abstractmethod
    def read_screen_argv(self, ref: str) -> list[str]:
        """Argv that prints the visible surface content to stdout."""


class CmuxDriver(Multiplexer):
    name = "cmux"

    def spawn_argv(self, drain_id: str) -> list[str]:
        return [
            "cmux", "new-pane", "--type", "terminal",
            "--direction", "right", "--focus", "false",
        ]

    def parse_ref(self, spawn_stdout: str) -> str:
        return spawn_stdout.strip().splitlines()[-1].strip()

    def send_text_argv(self, ref: str, text: str) -> list[str]:
        return ["cmux", "send", "--surface", ref, text]

    def send_enter_argv(self, ref: str) -> list[str]:
        return ["cmux", "send-key", "--surface", ref, "Enter"]

    def read_screen_argv(self, ref: str) -> list[str]:
        return ["cmux", "read-screen", "--surface", ref]


class TmuxDriver(Multiplexer):
    name = "tmux"

    def __init__(self, in_tmux: bool | None = None) -> None:
        # When None, decide from the live environment; tests pass it explicitly.
        self._in_tmux = bool(os.environ.get("TMUX")) if in_tmux is None else in_tmux

    def spawn_argv(self, drain_id: str) -> list[str]:
        if self._in_tmux:
            return ["tmux", "new-window", "-P", "-F", "#{pane_id}"]
        return [
            "tmux", "new-session", "-d", "-s", f"drain-{drain_id}",
            "-x", "220", "-y", "50", "-P", "-F", "#{pane_id}",
        ]

    def parse_ref(self, spawn_stdout: str) -> str:
        return spawn_stdout.strip().splitlines()[-1].strip()

    def send_text_argv(self, ref: str, text: str) -> list[str]:
        return ["tmux", "send-keys", "-t", ref, "-l", text]

    def send_enter_argv(self, ref: str) -> list[str]:
        return ["tmux", "send-keys", "-t", ref, "Enter"]

    def read_screen_argv(self, ref: str) -> list[str]:
        return ["tmux", "capture-pane", "-p", "-t", ref]


def detect(explicit: str = "auto") -> Multiplexer:
    """Resolve a multiplexer from an explicit choice or the environment.

    Precedence for ``auto``: inside tmux (``$TMUX``) → tmux; else cmux on PATH →
    cmux; else tmux on PATH → tmux; else refuse. An explicit ``cmux``/``tmux``
    always wins; any other value is an error.
    """
    if explicit == "cmux":
        return CmuxDriver()
    if explicit == "tmux":
        return TmuxDriver()
    if explicit != "auto":
        raise ValueError(f"unknown worker-type: {explicit!r} (want auto|cmux|tmux)")
    if os.environ.get("TMUX"):
        return TmuxDriver(in_tmux=True)
    if shutil.which("cmux"):
        return CmuxDriver()
    if shutil.which("tmux"):
        return TmuxDriver(in_tmux=False)
    raise RuntimeError(
        "no usable multiplexer: not inside tmux and neither cmux nor tmux on PATH"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_muxdriver.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint the new Python**

Run: `uv run ruff check dev-flow/scripts/_muxdriver.py tests/test_muxdriver.py && uv run ruff format --check dev-flow/scripts/_muxdriver.py tests/test_muxdriver.py`
Expected: no errors (run `uv run ruff format` first if format check fails).

- [ ] **Step 6: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md` (jj repo):
`jj commit -m "feat(drain): add shared _muxdriver for cmux/tmux argv construction (fhsk-3qy)"`

---

## Task 2: Parameterize `drain-watchdog` with `--multiplexer`

**Files:**

- Modify: `dev-flow/scripts/drain-watchdog` (imports ~37-44; `read_surface` 118-122; `nudge` 125-130; `main` arg block 147-161; loop usage 170/185)
- Test: `tests/test_drain_skill.py` (add tmux-path tests; keep `classify` tests green)
- [ ] **Step 1: Write the failing tests**

Add to `tests/test_drain_skill.py` (the existing `_load_watchdog()` helper at L19 already imports the script as a module):

```python
def test_watchdog_multiplexer_defaults_to_cmux() -> None:
    wd = _load_watchdog()
    mux = wd.resolve_mux(None)  # None = flag absent
    assert mux.name == "cmux"


def test_watchdog_read_surface_uses_tmux_argv(monkeypatch) -> None:
    wd = _load_watchdog()
    calls: list[list[str]] = []
    monkeypatch.setattr(wd, "_run", lambda cmd: calls.append(cmd) or "line\n")
    mux = wd.resolve_mux("tmux")
    wd.read_surface(mux, "%9")
    assert calls[-1] == ["tmux", "capture-pane", "-p", "-t", "%9"]


def test_watchdog_nudge_uses_tmux_argv(monkeypatch) -> None:
    wd = _load_watchdog()
    calls: list[list[str]] = []
    monkeypatch.setattr(wd.subprocess, "run", lambda cmd, check=False: calls.append(cmd))
    monkeypatch.setattr(wd.time, "sleep", lambda _s: None)
    mux = wd.resolve_mux("tmux")
    wd.nudge(mux, "%9")
    assert calls[0] == ["tmux", "send-keys", "-t", "%9", "-l", wd.NUDGE]
    assert calls[1] == ["tmux", "send-keys", "-t", "%9", "Enter"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_drain_skill.py -k watchdog_multiplexer -v`
Expected: FAIL — `resolve_mux` / new `read_surface` signature does not exist yet.

- [ ] **Step 3: Edit the imports to load the shared driver**

In `dev-flow/scripts/drain-watchdog`, replace the import block (currently lines ~37-44, ending with the `from re import ...` line) by inserting, immediately after `from __future__ import annotations`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _muxdriver  # noqa: E402  (sibling stdlib module on the inserted path)
```

Keep the existing `import argparse / json / subprocess / time` and `from re import ...` lines.

This is safe under the test harness: `_load_watchdog()` (tests/test_drain_skill.py:23) loads the script via `SourceFileLoader("drain_watchdog", str(DRAIN_WATCHDOG))` with the real path, so `module.__file__` is set and `Path(__file__).resolve().parent` resolves to `dev-flow/scripts/` — the same dir holding `_muxdriver.py`.

- [ ] **Step 4: Add `resolve_mux` and rewrite `read_surface` / `nudge`**

Replace the existing `read_surface` (L118-122) and `nudge` (L125-130) with:

```python
def resolve_mux(flag: str | None):
    """Map the --multiplexer flag to a driver; None/absent -> cmux (back-compat)."""
    return _muxdriver.detect(flag or "cmux")


def read_surface(mux, surface: str) -> str:
    """Last 40 lines of the worker's surface, via the active multiplexer."""
    return "\n".join(_run(mux.read_screen_argv(surface)).splitlines()[-40:])


def nudge(mux, surface: str) -> None:
    """Send a SHORT single-line nudge, then submit — a 2s gap lets the TUI
    register the text before Enter (long/fast sends race the submit)."""
    subprocess.run(mux.send_text_argv(surface, NUDGE), check=False)
    time.sleep(2)
    subprocess.run(mux.send_enter_argv(surface), check=False)
```

- [ ] **Step 5: Add the `--multiplexer` arg and thread the driver through `main`**

In `main()`, add this argument alongside the existing ones (the existing `--surface` `add_argument` block ends at L151; insert immediately after it):

```python
    ap.add_argument(
        "--multiplexer",
        choices=["cmux", "tmux"],
        default="cmux",
        help="terminal multiplexer driving the worker surface (default cmux)",
    )
```

Then, immediately after `a = ap.parse_args(argv)` (~L161), add:

```python
    mux = resolve_mux(a.multiplexer)
```

Update the two call sites in the loop **by symbol** (line numbers shift after the import + arg edits, so match the call text, not a line): `read_surface(a.surface)` → `read_surface(mux, a.surface)` (currently L170), and `nudge(a.surface)` → `nudge(mux, a.surface)` (currently L192). Also update the `--surface` help text to read `surface ref of the worker pane (e.g. surface:100 for cmux, %12 for tmux)`.

- [ ] **Step 6: Run the watchdog tests (new + existing classify suite)**

Run: `uv run pytest tests/test_drain_skill.py -k "watchdog or classify" -v`
Expected: PASS — the 3 new tmux tests pass and the existing `classify` / completion tests stay green.

- [ ] **Step 7: Lint**

Run: `uv run ruff check dev-flow/scripts/drain-watchdog`
Expected: no errors.

- [ ] **Step 8: Commit**

`jj commit -m "feat(drain): parameterize drain-watchdog with --multiplexer (fhsk-3qy)"`

---

## Task 3: New `drain-worker-launch` uv script

**Files:**

- Create: `dev-flow/scripts/drain-worker-launch`
- Test: `tests/test_drain_worker_launch.py`
- [ ] **Step 1: Write the failing validation tests**

Create `tests/test_drain_worker_launch.py`. The tests put a fake `bd` executable first on `PATH` and run the script in `--check` mode (no multiplexer side effects):

```python
"""Validation tests for drain-worker-launch --check."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH = REPO_ROOT / "dev-flow" / "scripts" / "drain-worker-launch"

GOOD_BEAD = [{
    "id": "ep-9", "issue_type": "drain", "status": "in_progress",
    "metadata": {
        "drain_mode": "epic", "drain_workspace": "/tmp/ws",
        "drain_scope": "ep-9", "drain_sentinel": "all children closed",
    },
}]


def _run_check(tmp_path: Path, bead_json: list, *, worker_type: str = "cmux") -> subprocess.CompletedProcess:
    """Run `drain-worker-launch --check` with a fake `bd` and `cmux` on PATH."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "bd").write_text(
        "#!/usr/bin/env bash\n"
        f"cat <<'EOF'\n{json.dumps(bead_json)}\nEOF\n"
    )
    (fake_bin / "bd").chmod(0o755)
    # Provide a stub `cmux` so the on-PATH check passes.
    (fake_bin / "cmux").write_text("#!/usr/bin/env bash\nexit 0\n")
    (fake_bin / "cmux").chmod(0o755)
    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
    env.pop("TMUX", None)
    return subprocess.run(
        [str(LAUNCH), "--check", "--drain-id", "ep-9", "--worker-type", worker_type],
        capture_output=True, text=True, env=env,
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_drain_worker_launch.py -v`
Expected: FAIL — `drain-worker-launch` does not exist (non-zero rc, FileNotFoundError).

- [ ] **Step 3: Write the script**

Create `dev-flow/scripts/drain-worker-launch` (executable, PEP 723):

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# SPDX-License-Identifier: Apache-2.0
#
# drain-worker-launch — validate a drain bead and launch its /drain worker in a
# detached multiplexer surface (cmux or tmux). The bead-validation and the
# verified pane-launch sequence live here, NOT in markdown.
#
#   drain-worker-launch --check --drain-id <id> [--worker-type auto|cmux|tmux]
#       validate + resolve multiplexer, print the plan, exit (no side effects)
#   drain-worker-launch --drain-id <id> [--worker-type auto|cmux|tmux]
#       the above, then spawn the surface and drive cd/direnv/claude/goal;
#       prints `multiplexer=<name>` and `surface=<ref>` for the watchdog.
"""Validate a drain bead and launch its worker in a cmux/tmux surface."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _muxdriver  # noqa: E402  (sibling stdlib module on the inserted path)

# Byte-identical with dev-flow/commands/drain.md `## Worker condition`.
WORKER_CONDITION = """\
Drain worker for bead {drain_id}. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show {drain_id} --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Also invoke the jj:jujutsu skill before
any commit/rebase/topology surgery. Execute exactly ONE ready bead this turn
following the protocol, then stop. Goal met when: {sentinel}."""


def _run(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=30, check=False
    ).stdout


def _die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def validate(drain_id: str) -> dict:
    """Read + validate the drain bead; return its metadata or exit non-zero.

    `bd show --json` returns a single-element array; the type field is
    `issue_type`, not `type`.
    """
    try:
        data = json.loads(_run(["bd", "show", drain_id, "--json"]))
    except json.JSONDecodeError:
        _die(f"could not read bead {drain_id} (bd show returned no JSON)")
    if not (isinstance(data, list) and data and isinstance(data[0], dict)):
        _die(f"could not read bead {drain_id} (unexpected bd show shape)")
    b = data[0]
    if b.get("issue_type") != "drain":
        _die(f"not a drain bead: {drain_id} (issue_type={b.get('issue_type')!r})")
    if b.get("status") != "in_progress":
        _die(f"drain {drain_id} not in_progress (already closed?)")
    md = b.get("metadata") or {}
    if md.get("drain_mode") != "epic":
        _die(
            "drain-with-worker supports epic-mode drains only "
            f"(got mode={md.get('drain_mode')!r})"
        )
    for key in ("drain_workspace", "drain_scope", "drain_sentinel"):
        if not md.get(key):
            _die(f"drain bead missing {key}")
    return md


def _send(mux, ref: str, text: str) -> None:
    subprocess.run(mux.send_text_argv(ref, text), check=False)


def _enter(mux, ref: str) -> None:
    subprocess.run(mux.send_enter_argv(ref), check=False)


def _screen(mux, ref: str) -> str:
    return _run(mux.read_screen_argv(ref))


def launch(mux, drain_id: str, md: dict) -> str:
    """Spawn the surface and drive the verified launch sequence. Returns ref."""
    spawned = subprocess.run(
        mux.spawn_argv(drain_id), capture_output=True, text=True, check=False
    )
    if spawned.returncode != 0:
        _die(f"failed to spawn {mux.name} surface: {spawned.stderr.strip()}")
    ref = mux.parse_ref(spawned.stdout)
    if not ref:
        _die(f"{mux.name} spawn printed no surface ref")

    workspace = md["drain_workspace"]
    # cd as its own verified step — never chain `cd X && claude`.
    _send(mux, ref, f"cd {workspace}")
    _enter(mux, ref)
    _send(mux, ref, "pwd")
    _enter(mux, ref)
    time.sleep(1)
    if workspace not in _screen(mux, ref):
        _die(f"cwd did not become {workspace} after cd (surface {ref})")

    # direnv allow — a fresh split hits a blocked .envrc.
    _send(mux, ref, "direnv allow")
    _enter(mux, ref)
    time.sleep(1)
    if "blocked" in _screen(mux, ref).lower():
        _die(f".envrc still blocked after direnv allow (surface {ref})")

    # Launch Claude with the bypass guard.
    _send(mux, ref, "claude --dangerously-skip-permissions")
    _enter(mux, ref)
    time.sleep(6)
    # Trust-folder prompt (option 1 pre-highlighted).
    _enter(mux, ref)
    time.sleep(2)

    # Fire the thin /goal (long send races the submit -> sleep 3 before Enter).
    condition = WORKER_CONDITION.format(drain_id=drain_id, sentinel=md["drain_sentinel"])
    goal = f"/goal {condition}"
    _send(mux, ref, goal)
    time.sleep(3)
    _enter(mux, ref)
    time.sleep(2)
    if "Goal set:" not in _screen(mux, ref) and "/goal active" not in _screen(mux, ref):
        print(
            f"warning: did not observe 'Goal set:' on {ref}; verify the worker manually",
            file=sys.stderr,
        )
    return ref


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drain-id", required=True)
    ap.add_argument("--worker-type", choices=["auto", "cmux", "tmux"], default="auto")
    ap.add_argument("--check", action="store_true", help="validate + resolve only")
    a = ap.parse_args(argv)

    md = validate(a.drain_id)
    try:
        mux = _muxdriver.detect(a.worker_type)
    except (RuntimeError, ValueError) as exc:
        _die(str(exc))

    if a.check:
        print(f"multiplexer={mux.name}")
        print(f"workspace={md['drain_workspace']}")
        print(f"scope={md['drain_scope']}")
        print(f"sentinel={md['drain_sentinel']}")
        return 0

    ref = launch(mux, a.drain_id, md)
    print(f"multiplexer={mux.name}")
    print(f"surface={ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Make it executable**

Run: `chmod +x dev-flow/scripts/drain-worker-launch`

- [ ] **Step 5: Run the validation tests**

Run: `uv run pytest tests/test_drain_worker_launch.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Lint**

Run: `uv run ruff check dev-flow/scripts/drain-worker-launch tests/test_drain_worker_launch.py`
Expected: no errors (`uv run ruff format` first if needed).

- [ ] **Step 7: Commit**

`jj commit -m "feat(drain): add drain-worker-launch uv script (validate + launch) (fhsk-3qy)"`

---

## Task 4: Convert `drain-with-worker` command → skill

**Files:**

- Create: `dev-flow/skills/drain-with-worker/SKILL.md`
- Modify: `dev-flow/references/drain-with-worker.md`
- Delete: `dev-flow/commands/drain-with-worker.md`
- Modify: `tests/test_drain_skill.py` (re-point the 4 command-reading tests)
- [ ] **Step 1: Rewrite the breaking tests to target the skill**

In `tests/test_drain_skill.py`, change the path constants (L12-13) to add the skill path and keep the reference:

```python
DRAIN_WITH_WORKER_REF = REPO_ROOT / "dev-flow" / "references" / "drain-with-worker.md"
DRAIN_WITH_WORKER_SKILL = REPO_ROOT / "dev-flow" / "skills" / "drain-with-worker" / "SKILL.md"
```

Remove the `DRAIN_WITH_WORKER_CMD` constant (L13). Then **delete these four existing test functions entirely and add the four replacements below** — they have new names, so deleting the old functions is required or the suite will crash at collection on the removed constant / removed reference strings:

| Delete (existing) | Add (replacement) | Why the old one breaks |
|---|---|---|
| `test_drain_with_worker_command_frontmatter` (L208) | `test_skill_frontmatter_declares_script_tools` | reads deleted `DRAIN_WITH_WORKER_CMD` |
| `test_drain_with_worker_command_body` (L215) | `test_skill_body_invokes_launch_and_watchdog` | reads deleted `DRAIN_WITH_WORKER_CMD` |
| `test_reference_arms_the_watchdog_script` (L132–143, **both clauses**) | `test_skill_arms_the_watchdog_script` | its second clause (L140) reads deleted `DRAIN_WITH_WORKER_CMD` frontmatter |
| `test_reference_prereqs_refuse_early` (L114–121) | `test_reference_delegates_refuse_early_to_launch` | asserts `command -v cmux` in the reference, which Step 4 removes |
| `test_reference_uses_issue_type_not_type` (L106–111) | *(none — intent moves to the launch script)* | asserts the literal jq accessor `.[0].issue_type` in the reference; Step 4 removes the jq block. The `issue_type`-not-`type` guard now lives in `drain-worker-launch.validate()` and is covered behaviorally by `test_check_refuses_wrong_type` (Task 3). Delete this test; do not replace it. |

Replacement functions:

```python
def test_skill_frontmatter_declares_script_tools() -> None:
    fm = _frontmatter(DRAIN_WITH_WORKER_SKILL.read_text())
    assert "Bash(dev-flow/scripts/drain-worker-launch:*)" in fm
    assert "Bash(dev-flow/scripts/drain-watchdog:*)" in fm
    assert "AskUserQuestion" in fm


def test_skill_body_invokes_launch_and_watchdog() -> None:
    text = DRAIN_WITH_WORKER_SKILL.read_text()
    assert "drain-worker-launch" in text, "skill must invoke the launch script"
    assert "drain-watchdog --multiplexer" in text, "skill must arm the parameterized watchdog"


def test_skill_arms_the_watchdog_script() -> None:
    text = DRAIN_WITH_WORKER_SKILL.read_text()
    assert "--drain-id" in text and "--scope" in text and "--surface" in text
    assert "--multiplexer" in text


def test_reference_delegates_refuse_early_to_launch() -> None:
    text = DRAIN_WITH_WORKER_REF.read_text()
    assert "drain-worker-launch" in text, "reference must delegate validation to the script"
    assert "--check" in text, "reference must mention the validate-only mode"
    # Reclaim the reference coverage the deleted prereqs/arms tests had:
    for meta in ("drain_workspace", "drain_scope", "drain_sentinel"):
        assert meta in text, f"reference must still document the {meta} guard"
    assert "drain-watchdog" in text and "--multiplexer" in text, (
        "reference must keep the (now parameterized) watchdog arm command"
    )
```

Two existing tests need **no change** (verified by reading them) — do not touch them by reflex:

- `test_iteration_body_removed_from_command` (L75) reads `DRAIN_CMD` (`drain.md`) and asserts `## Iteration body` is absent there — unrelated to the command→skill conversion, so it is unaffected.
- `test_worker_condition_byte_identical` (L192) stays pointed at `DRAIN_WITH_WORKER_REF`; the reference keeps the canonical `## Worker condition` block byte-identical.

After editing, run `rg -n "DRAIN_WITH_WORKER_CMD" tests/test_drain_skill.py` and confirm **zero** matches (the constant at L13 and its three read sites at L140/L209/L216 are all gone). A non-zero count means an old function was not deleted.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_drain_skill.py -k "skill or reference_delegates" -v`
Expected: FAIL — `SKILL.md` does not exist yet.

- [ ] **Step 3: Create the skill**

Create `dev-flow/skills/drain-with-worker/SKILL.md`:

````markdown
---
name: drain-with-worker
description: Launch an autonomous /drain worker in a detached cmux or tmux surface and arm a surface-aware watchdog (epic-mode drains). Use when the user runs `/drain-with-worker [cmux|tmux] <drain-id>` or accepts the `/drain` worker handoff. Takes an optional worker-type (auto-detected when omitted).
allowed-tools: ["Read", "AskUserQuestion", "PushNotification", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)", "Bash(command -v cmux:*)", "Bash(command -v tmux:*)", "Bash(dev-flow/scripts/drain-worker-launch:*)", "Bash(dev-flow/scripts/drain-watchdog:*)"]
---

# drain-with-worker

Launch an autonomous `/drain` worker for an existing **live** drain bead in a
detached multiplexer surface (cmux or tmux), and arm a surface-aware watchdog so
the drain self-heals — and wakes you on a question or API error — while you walk
away. Mint the bead first with `/drain epic <id>`; pass the bead id here.

**v1 is epic-mode only.** set/cascade drains are refused fail-fast by the launch
script — drain them via the `/goal` condition `/drain` emits.

## Step 1 — Parse the invocation

Parse the argument string as `[worker-type] <drain-id>`:

- If the first token is `cmux` or `tmux`, it is the **worker-type**; the next
  token is the **drain-id**.
- Otherwise the only token is the **drain-id** and worker-type is `auto`.

`auto` resolves at runtime: inside tmux (`$TMUX`) → tmux; else cmux on PATH →
cmux; else tmux on PATH → tmux; else the launch script refuses.

## Step 2 — Validate + show the plan (no side effects)

Run the launch script in check mode:

```bash
dev-flow/scripts/drain-worker-launch --check --drain-id <drain-id> --worker-type <worker-type>
```

It validates the bead (type=drain, in_progress, epic-mode, workspace/scope/
sentinel present) and resolves the multiplexer. On a non-zero exit, surface the
printed reason to the user and stop. On success it prints `multiplexer=`,
`workspace=`, `scope=`, `sentinel=` — capture `multiplexer` and `scope`.

## Step 3 — Confirm gate (AskUserQuestion)

Show the launch plan — new surface → `cd <workspace>` → `direnv allow` →
`claude --dangerously-skip-permissions` → fire `/goal` for `<drain-id>` → arm
the surface-aware watchdog — and ask via **AskUserQuestion**: "Launch the
autonomous worker for `<drain-id>` via `<multiplexer>` now?" with options
**Launch** / **Cancel**. Proceed only on **Launch**. This gate is the single
confirmation; never launch without it.

## Step 4 — Launch

```bash
dev-flow/scripts/drain-worker-launch --drain-id <drain-id> --worker-type <worker-type>
```

It spawns the surface and drives the verified `cd → direnv → claude → trust →
/goal` sequence, then prints `multiplexer=<name>` and `surface=<ref>`. Capture
both. If it exits non-zero, surface the reason and stop.

## Step 5 — Arm the surface-aware watchdog

Arm the watchdog as a **background** task (`run_in_background: true`), passing
the captured multiplexer + surface:

```bash
dev-flow/scripts/drain-watchdog --multiplexer <multiplexer> --drain-id <drain-id> --scope <scope> --surface <surface>
```

When it exits with an `EXIT=<reason>` marker, react per the reaction table in
`dev-flow/references/drain-with-worker.md` and **re-arm** it (relaunch the same
command), except on `EXIT=complete`. Do not improvise the watchdog mechanics —
the reference documents every gotcha.
````

- [ ] **Step 4: Update the reference to delegate executable steps to the scripts**

In `dev-flow/references/drain-with-worker.md`, replace the **Prerequisites
(refuse early)** section (the fenced `bash` block, lines ~13-29) with:

```markdown
## Prerequisites (refuse early)

Validation is owned by `dev-flow/scripts/drain-worker-launch`. Run it in
check mode — it refuses fail-fast on a non-drain bead, a closed/!in_progress
bead, a non-epic mode, a missing multiplexer, or absent
`drain_workspace`/`drain_scope`/`drain_sentinel` metadata (the `issue_type`
field, not `type`, is the bead type):

\`\`\`bash
dev-flow/scripts/drain-worker-launch --check --drain-id <drain-id> --worker-type <auto|cmux|tmux>
\`\`\`

On a non-zero exit, surface the printed reason and stop.
```

Replace the **Launch sequence** section (lines ~31-43) with a pointer to the
script (the cmux/tmux verb mechanics now live in `_muxdriver` and the launch
script; tmux primitives are documented in the `tmux` plugin skill):

```markdown
## Launch sequence

The verified pane-launch sequence (spawn → `cd` + verify `pwd` → `direnv allow`
+ verify → `claude --dangerously-skip-permissions` → trust prompt → fire the
thin `/goal` with a 3s pre-submit pause) is implemented in
`dev-flow/scripts/drain-worker-launch`. It prints `multiplexer=<name>` and
`surface=<ref>` on success. For the tmux primitives it builds on (spawn a
window vs detached session, `send-keys` vs Enter, `capture-pane`), see the
`tmux` skill.
```

Keep the **Worker condition** block (the canonical `/goal` payload, lines
~45-58) byte-identical — it stays the source of truth the byte-identical test
checks. Keep the **Surface-aware watchdog**, reaction table, and **Gotchas**
sections, but update the watchdog arm command to include `--multiplexer
<multiplexer>` and change the `read-screen` mentions to "read the surface" so
they are multiplexer-neutral.

- [ ] **Step 5: Delete the command file**

Run: `jj file untrack dev-flow/commands/drain-with-worker.md` is NOT needed in
jj; simply remove the file: `rm -f dev-flow/commands/drain-with-worker.md`
(jj auto-snapshots the deletion).

- [ ] **Step 6: Run the affected tests**

Run: `uv run pytest tests/test_drain_skill.py -v`
Expected: PASS — all re-pointed tests green, including `test_worker_condition_byte_identical`.

- [ ] **Step 7: Lint the markdown**

Run: `rumdl check --no-exclude dev-flow/skills/drain-with-worker/SKILL.md dev-flow/references/drain-with-worker.md`
Expected: no errors (run `rumdl fmt --no-exclude <files>` to auto-fix first).

- [ ] **Step 8: Commit**

`jj commit -m "feat(drain): convert drain-with-worker command to a parameterized skill (fhsk-3qy)"`

---

## Task 5: Widen `/drain` Phase D to cmux-or-tmux

**Files:**

- Modify: `dev-flow/commands/drain.md` (frontmatter L4; Phase D probe ~L188-201)
- Test: `tests/test_drain_skill.py` (existing Phase D tests must stay green)
- [ ] **Step 1: Add the failing assertion**

Add to `tests/test_drain_skill.py`:

```python
def test_drain_phase_d_probes_tmux_too() -> None:
    text = DRAIN_CMD.read_text()
    assert "command -v cmux || command -v tmux" in text, "Phase D must probe both multiplexers"


def test_drain_frontmatter_allows_tmux() -> None:
    fm = _frontmatter(DRAIN_CMD.read_text())
    assert "Bash(tmux:*)" in fm and "Bash(command -v tmux:*)" in fm
```

(`DRAIN_CMD` is the existing constant pointing at `dev-flow/commands/drain.md`; confirm it exists near the top of the file — it backs `test_drain_epic_phase_d_offers_worker` at L228.)

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_drain_skill.py -k "phase_d_probes_tmux or frontmatter_allows_tmux" -v`
Expected: FAIL — strings not present yet.

- [ ] **Step 3: Edit the frontmatter**

In `dev-flow/commands/drain.md` frontmatter `allowed-tools` (L4), add `"Bash(tmux:*)"` and `"Bash(command -v tmux:*)"` immediately after the existing `"Bash(cmux:*)"` entry. Do not remove the cmux entries.

- [ ] **Step 4: Edit the Phase D probe**

In `dev-flow/commands/drain.md`, change the probe line (~L188) from:

```text
**Then probe for an autonomous launcher:** run `command -v cmux`.
```

to:

```text
**Then probe for an autonomous launcher:** run `command -v cmux || command -v tmux`.
```

In the surrounding offer text (~L194-196), change "in a detached cmux pane" to
"in a detached cmux/tmux surface" and keep the `/drain-with-worker $DRAIN_ID`
handoff (the auto-detect picks the multiplexer). The handoff target is now the
skill, which accepts the same `$DRAIN_ID` argument.

- [ ] **Step 5: Run all drain-skill tests**

Run: `uv run pytest tests/test_drain_skill.py -v`
Expected: PASS — new tests pass; `test_drain_epic_phase_d_offers_worker` (asserts substring `command -v cmux`) and `test_drain_allowed_tools_gained_launch_toolset` (asserts `Bash(cmux:*)`) stay green.

- [ ] **Step 6: Lint + commit**

Run: `rumdl check --no-exclude dev-flow/commands/drain.md`
`jj commit -m "feat(drain): widen /drain Phase D launcher probe to cmux-or-tmux (fhsk-3qy)"`

---

## Task 6: Standalone `tmux` plugin

**Files:**

- Create: `tmux/plugin.json`, `tmux/skills/tmux/SKILL.md`, `plugins/tmux/.codex-plugin/plugin.json`, `plugins/tmux/skills` (symlink)
- Modify: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `release-please-config.json`, `Taskfile.yaml`
- [ ] **Step 1: Write the failing wiring test**

Add to `tests/test_drain_skill.py` (or a new `tests/test_tmux_plugin.py`):

```python
def test_tmux_plugin_registered_and_versioned() -> None:
    import json
    claude_mp = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert any(p["name"] == "tmux" for p in claude_mp["plugins"])
    codex_mp = json.loads((REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text())
    assert any(p["name"] == "tmux" for p in codex_mp["plugins"])
    cfg = json.loads((REPO_ROOT / "release-please-config.json").read_text())
    paths = [f["path"] for f in cfg["packages"]["."]["extra-files"]]
    assert "tmux/plugin.json" in paths
    assert (REPO_ROOT / "tmux" / "skills" / "tmux" / "SKILL.md").exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_drain_skill.py -k tmux_plugin_registered -v` (or the new test file)
Expected: FAIL.

- [ ] **Step 3: Create the source plugin manifest**

Create `tmux/plugin.json` (version matches the current repo-wide line; release-please keeps it synced):

```json
{
  "name": "tmux",
  "version": "1.23.0",
  "description": "tmux terminal-multiplexer usage skill (sessions, windows, panes, scripting)"
}
```

- [ ] **Step 4: Create the tmux usage skill**

Create `tmux/skills/tmux/SKILL.md`:

````markdown
---
name: tmux
description: tmux terminal-multiplexer usage. Use when spawning or driving tmux sessions/windows/panes from a script or agent, capturing pane output, targeting panes by id, or when the user mentions tmux. Covers detection, spawning, send-keys, capture-pane, and lifecycle.
---

# tmux usage

Practical tmux primitives for scripting and agent automation. Examples below are
illustrative; for the drain worker's operational launch sequence see
`dev-flow/scripts/drain-worker-launch`.

## Detect whether you are inside tmux

```bash
[ -n "$TMUX" ] && echo "inside tmux"
```

`$TMUX` is set inside a tmux pane. Use it to decide between `new-window` (you are
inside a session) and a detached `new-session` (you are not).

## Spawn a surface and capture its pane id

Always target panes by their **pane id** (`%N`), never by index — indices
renumber when panes close.

```bash
# Inside an existing session: a new window, print its pane id
pane=$(tmux new-window -P -F '#{pane_id}')      # -> %12

# No session yet: a detached, named session sized for a TUI
pane=$(tmux new-session -d -s mywork -x 220 -y 50 -P -F '#{pane_id}')  # -> %12
```

A detached `new-session` defaults to **80×24**, which cramps a full-screen TUI;
set `-x`/`-y` explicitly.

## Drive a pane

`send-keys` sends literal text *or* a key. Send text and the submit separately —
a fast/long send can race the program's input handling:

```bash
tmux send-keys -t %12 -l 'echo hello'   # -l = literal text, no submit
tmux send-keys -t %12 Enter             # submit (C-m also works)
```

## Read a pane

```bash
tmux capture-pane -p -t %12             # print visible pane to stdout
tmux capture-pane -p -S -200 -t %12     # include 200 lines of scrollback
```

## Lifecycle

```bash
tmux list-sessions -F '#{session_name}'
tmux list-panes -t mywork -F '#{pane_id} #{pane_active}'
tmux kill-pane -t %12
tmux kill-session -t mywork
```

## Windows, layouts, copy-mode (brief)

```bash
tmux new-window -t mywork -n build       # named window in a session
tmux select-layout -t mywork tiled       # even-horizontal | even-vertical | tiled | main-vertical
tmux copy-mode -t %12                     # enter copy/scroll mode
```
````

- [ ] **Step 5: Create the Codex wrapper**

Create `plugins/tmux/.codex-plugin/plugin.json` (mirror the `plugins/jj` wrapper shape):

```json
{
  "name": "tmux",
  "description": "tmux terminal-multiplexer usage skill (sessions, windows, panes, scripting)",
  "author": {
    "name": "Sean Brandt",
    "email": "4678+seanb4t@users.noreply.github.com",
    "url": "https://github.com/seanb4t"
  },
  "homepage": "https://github.com/fzymgc-house/fzymgc-house-skills",
  "repository": "https://github.com/fzymgc-house/fzymgc-house-skills",
  "license": "UNLICENSED",
  "keywords": ["tmux", "terminal", "multiplexer", "panes"],
  "skills": "./skills/",
  "interface": {
    "displayName": "tmux",
    "shortDescription": "tmux usage skill for scripting and agent automation.",
    "longDescription": "Codex wrapper for the tmux plugin. Reuses the tmux usage skill for spawning, driving, and reading tmux sessions, windows, and panes.",
    "developerName": "fzymgc-house",
    "category": "Developer Tools",
    "capabilities": ["Read", "Run"],
    "websiteURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "privacyPolicyURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "termsOfServiceURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "defaultPrompt": [
      "Spawn a detached tmux session and run a command in it.",
      "Capture the output of a tmux pane by its pane id.",
      "Explain how to target tmux panes reliably from a script."
    ],
    "brandColor": "#1BB91F"
  }
}
```

Then create the skills symlink:

```bash
ln -s ../../tmux/skills plugins/tmux/skills
```

The `plugins/jj` template also has `commands` and `hooks` symlinks; the `tmux`
plugin has **neither commands nor hooks** (it is a single usage skill), so create
only the `skills` symlink — do not copy the template's other symlinks.

- [ ] **Step 6: Register in both marketplaces**

In `.claude-plugin/marketplace.json`, append to the `plugins` array:

```json
    {
      "name": "tmux",
      "description": "tmux terminal-multiplexer usage skill (sessions, windows, panes, scripting)",
      "source": "./tmux"
    }
```

In `.agents/plugins/marketplace.json`, append to the `plugins` array:

```json
    {
      "name": "tmux",
      "source": {
        "source": "local",
        "path": "./plugins/tmux"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools"
    }
```

- [ ] **Step 7: Add to release-please extra-files**

In `release-please-config.json`, add to the `extra-files` array:

```json
        { "type": "json", "path": "tmux/plugin.json", "jsonpath": "$.version" }
```

- [ ] **Step 8: Gate the new files in the Taskfile**

In `Taskfile.yaml`: add `tmux/skills/*/SKILL.md`, `dev-flow/skills/drain-with-worker/SKILL.md`, and `dev-flow/references/drain-with-worker.md` to the `MD_FILES` var list; add `tmux/plugin.json` to the `PLUGIN_JSON` var list (the `PLUGIN_JSON` line currently reads `homelab/plugin.json jj/plugin.json dev-flow/plugin.json` + `plugins/*/.codex-plugin/plugin.json`).

- [ ] **Step 9: Run the wiring test + JSON validation**

Run: `uv run pytest tests/test_drain_skill.py -k tmux_plugin_registered -v && jq empty tmux/plugin.json plugins/tmux/.codex-plugin/plugin.json .claude-plugin/marketplace.json .agents/plugins/marketplace.json release-please-config.json`
Expected: PASS + no jq errors.

- [ ] **Step 10: Lint markdown + commit**

Run: `rumdl check --no-exclude tmux/skills/tmux/SKILL.md`
`jj commit -m "feat(tmux): add standalone tmux usage plugin + wiring (fhsk-3qy)"`

---

## Task 7: Docs + full quality gate

**Files:**

- Modify: `AGENTS.md` (plugin count L9; document the skill arg + tmux plugin)

- [ ] **Step 1: Update the plugin count and purpose**

In `AGENTS.md`, change "This repository publishes three source plugins" (L9) to "four source plugins" and add `tmux - terminal-multiplexer usage skill` to the bulleted list of source plugins.

- [ ] **Step 2: Document the parameterized launcher**

In the `AGENTS.md` section that mentions `/drain-with-worker` (the test `test_agents_doc_mentions_drain_with_worker` asserts the string is present — verify it stays), note that it is now a skill taking `[worker-type] <drain-id>` and supports cmux or tmux (auto-detected). Keep the literal `/drain-with-worker` substring so the test passes.

- [ ] **Step 3: Run the full quality gate**

Run: `task fmt && task lint && task test`
Expected: all green. `task fmt` auto-formats markdown + Python; `task lint` runs rumdl + ruff + jq + evals schema + adr-doctor; `task test` runs every pytest suite (including the new `tests/test_muxdriver.py`, `tests/test_drain_worker_launch.py`, and the modified `tests/test_drain_skill.py`).

- [ ] **Step 4: Verify the deletion did not orphan references**

Run: `rg -n "commands/drain-with-worker" --glob '!docs/superpowers/**'`
Expected: no hits outside the design docs (all live references now point at the skill).

- [ ] **Step 5: Commit**

`jj commit -m "docs(drain): document tmux launcher + four-plugin repo in AGENTS.md (fhsk-3qy)"`

---

## Done criteria

- `task lint && task test` green, including the three new/modified test files.
- `/drain-with-worker tmux <id>` and `/drain-with-worker cmux <id>` both reach the confirm gate; bare `/drain-with-worker <id>` auto-detects.
- `drain-watchdog` with no `--multiplexer` flag behaves exactly as before (cmux).
- The `tmux` plugin is installable from both marketplaces and `tmux/plugin.json` `$.version` is in release-please `extra-files`.
- No live (non-doc) references to the deleted `commands/drain-with-worker.md` remain.
<!-- adr-capture: sha256=884ac7941d1a7df2; session=cli; ts=2026-06-13T12:49:03Z; adrs=fhsk-5dj,fhsk-8yz,fhsk-a6v -->
