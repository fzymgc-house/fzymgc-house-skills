# memory-curator Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `memory-curator` plugin that wires the self-hosted memory MCP layer into Claude Code — automatic session-start recall, disciplined capture, and a correctable, two-tier per-workspace memory scope — registered in both the Claude and Codex marketplaces.

**Architecture:** A new source plugin `memory-curator/` plus a thin Codex wrapper `plugins/memory-curator/`. An OAuth HTTP MCP server (`memory_oauth`, no secret) is declared in `.mcp.json`. Two uv-python hooks share one local-only scope-derivation module (`scope.py`): a `SessionStart` hook computes the spine+overlay scopes and emits an `additionalContext` instruction for Claude to recall via its own authenticated MCP connection; a `Stop` hook block-once nudges capture. Two model-invoked skills (`curating-memory`, `promoting-memory`) carry the discipline.

**Tech Stack:** Python 3.11+ run via `uv run --script` (PEP-723 inline metadata), stdlib only (`json`, `subprocess`, `pathlib`); pytest; jj/git CLIs; Claude Code plugin + hook JSON contracts; Codex wrapper manifest.

**Spec:** `docs/superpowers/specs/2026-06-01-memory-curator-plugin-design.md` (design-reviewer READY, round 3). **Design bead:** fhsk-ga7.

**Grounding note (Rule 7):** No third-party library APIs are used — the implementation is stdlib + the jj/git CLIs + the Claude Code hook/plugin JSON contracts, all verified live during brainstorming (see the spec's References/Grounding traces and bead fhsk-ga7 notes). All new paths live under a new `memory-curator/` tree (created in Task 1) and `plugins/memory-curator/`; the repo root and `.agents/plugins/`, `.claude-plugin/`, `tests/` already exist. `git rev-parse --git-common-dir` returns the **shared** `.git` (so its parent is the main repo root from any worktree) — confirmed live.

---

## File Structure

```text
memory-curator/
  plugin.json                          # Claude plugin manifest (name + description)
  .mcp.json                            # OAuth HTTP server "memory_oauth"
  hooks/
    hooks.json                         # SessionStart + Stop registration
    session-start-memory-recall        # uv script: scope + recall instruction
    session-end-memory-capture         # uv script: Stop block-once nudge
    lib/
      __init__.py
      scope.py                         # two-tier scope derivation (local git/jj only)
    tests/
      __init__.py
      test_scope.py
      test_session_start_memory_recall.py
      test_session_end_memory_capture.py
      test_plugin_config.py            # asserts .mcp.json / hooks.json / plugin.json shape
  skills/
    curating-memory/SKILL.md
    promoting-memory/SKILL.md
  README.md                            # setup (one-time /mcp auth) + scope convention
plugins/memory-curator/                # Codex wrapper
  .codex-plugin/plugin.json            # only wrapper-local real file
  .mcp.json   -> ../../memory-curator/.mcp.json
  hooks       -> ../../memory-curator/hooks
  skills      -> ../../memory-curator/skills
tests/
  test_memory_curator_plugin.py        # both marketplaces + wrapper symlinks
```

Modified files: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `tests/test_codex_marketplace.py`, `Taskfile.yaml`.

---

### Task 1: `scope.py` — repo identity (spine)

**Files:**

- Create: `memory-curator/hooks/lib/__init__.py`
- Create: `memory-curator/hooks/lib/scope.py`
- Create: `memory-curator/hooks/tests/__init__.py`
- Test: `memory-curator/hooks/tests/test_scope.py`
- [ ] **Step 1: Create the package markers**

Create `memory-curator/hooks/lib/__init__.py` (empty) and `memory-curator/hooks/tests/__init__.py` (empty).

- [ ] **Step 2: Write the failing tests for spine derivation**

Create `memory-curator/hooks/tests/test_scope.py`:

```python
"""Tests for memory-curator scope derivation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # hooks/
from lib import scope  # noqa: E402


def make_fake_run(table):
    """table: list of (prefix_list, return_value). First prefix match wins."""
    calls = []

    def fake_run(args, cwd):
        calls.append(args)
        for prefix, value in table:
            if args[: len(prefix)] == prefix:
                return value
        return None

    fake_run.calls = calls
    return fake_run


def test_normalize_remote_scp_and_https():
    assert scope._normalize_remote("git@github.com:org/repo.git") == "github.com/org/repo"
    assert scope._normalize_remote("https://github.com/org/repo.git") == "github.com/org/repo"
    assert scope._normalize_remote("ssh://git@github.com/org/repo") == "github.com/org/repo"


def test_jj_repo_uses_jj_remote_never_git(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], "/repo"),
        (["jj", "--no-pager", "git", "remote", "list"], "origin git@github.com:org/repo.git"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/repo") == "github.com/org/repo"
    assert not any(a and a[0] == "git" for a in fake.calls)


def test_git_repo_uses_origin(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], None),
        (["git", "remote", "get-url", "origin"], "https://github.com/org/repo.git"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/x") == "github.com/org/repo"


def test_remoteless_jj_default_workspace_uses_basename(monkeypatch, tmp_path):
    (tmp_path / ".jj" / "repo").mkdir(parents=True)  # default ws: repo is a dir
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], str(tmp_path)),
        (["jj", "--no-pager", "git", "remote", "list"], ""),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id(str(tmp_path)) == tmp_path.name


def test_remoteless_jj_secondary_workspace_resolves_pointer(monkeypatch, tmp_path):
    primary = tmp_path / "myrepo"
    (primary / ".jj").mkdir(parents=True)
    ws = tmp_path / "myrepo_worktrees" / "feat"
    (ws / ".jj").mkdir(parents=True)
    (ws / ".jj" / "repo").write_text("../../../myrepo/.jj/repo")  # pointer file
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], str(ws)),
        (["jj", "--no-pager", "git", "remote", "list"], ""),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id(str(ws)) == "myrepo"


def test_no_repo_returns_none(monkeypatch):
    fake = make_fake_run([])  # everything returns None
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/nowhere") is None
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_scope.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.scope'` (or `AttributeError` on `scope._repo_id`).

- [ ] **Step 4: Write the minimal implementation**

Create `memory-curator/hooks/lib/scope.py`:

```python
"""Two-tier memory scope derivation (local git/jj only — no network, no auth).

Public API: derive_scopes(cwd) -> (spine, overlay).
  spine   = "repo:<repo-id>"                      (always, when in a repo)
  overlay = "repo:<repo-id>:ws:<workspace>" | None (None for the primary checkout)
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(args: list[str], cwd: str) -> str | None:
    """Run a command; return stripped stdout, or None on any failure."""
    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _normalize_remote(url: str) -> str:
    """git@github.com:org/repo.git -> github.com/org/repo."""
    u = url.strip()
    for scheme in ("https://", "http://", "ssh://", "git://"):
        if u.startswith(scheme):
            u = u[len(scheme):]
            break
    head = u.split("/", 1)[0]
    if "@" in head:
        u = u.split("@", 1)[1]
    u = u.replace(":", "/", 1)  # scp-style host:path separator
    if u.endswith(".git"):
        u = u[:-4]
    return u.strip("/")


def _origin_from_jj(remotes: str | None) -> str | None:
    if not remotes:
        return None
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "origin":
            return parts[1]
    return None


def _jj_primary_root(workspace_root: str | None) -> str | None:
    """Resolve the primary workspace root via the .jj/repo store pointer."""
    if not workspace_root:
        return None
    pointer = Path(workspace_root) / ".jj" / "repo"
    if pointer.is_dir():
        return workspace_root  # default workspace: .jj/repo is the store dir
    if pointer.is_file():
        try:
            target = pointer.read_text().strip()
        except OSError:
            return None
        tp = Path(target)
        if not tp.is_absolute():
            tp = (pointer.parent / target).resolve()
        if tp.name == "repo" and tp.parent.name == ".jj":
            return str(tp.parent.parent)
    return None


def _repo_id(cwd: str) -> str | None:
    # jj-first: a jj workspace is NOT a git repo, so git remote fails there.
    if _run(["jj", "--no-pager", "root"], cwd) is not None:
        origin = _origin_from_jj(_run(["jj", "--no-pager", "git", "remote", "list"], cwd))
        if origin:
            return _normalize_remote(origin)
        primary = _jj_primary_root(_run(["jj", "--no-pager", "root"], cwd))
        return Path(primary).name if primary else None
    # pure git (including linked worktrees, which share origin)
    origin = _run(["git", "remote", "get-url", "origin"], cwd)
    if origin:
        return _normalize_remote(origin)
    common = _run(["git", "rev-parse", "--git-common-dir"], cwd)
    if common:
        p = Path(common)
        if not p.is_absolute():
            p = (Path(cwd) / p).resolve()
        return p.parent.name  # parent of the shared .git == main repo root
    return None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_scope.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md` (e.g. `jj commit -m "feat(memory-curator): scope spine derivation (fhsk-ga7)"`).

---

### Task 2: `scope.py` — workspace overlay + `derive_scopes`

**Files:**

- Modify: `memory-curator/hooks/lib/scope.py`
- Test: `memory-curator/hooks/tests/test_scope.py` (append)
- [ ] **Step 1: Append failing tests**

Append to `memory-curator/hooks/tests/test_scope.py`:

```python
def test_jj_named_workspace_overlay(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], "/repo/_wt/feat"),
        (["jj", "--no-pager", "git", "remote", "list"], "origin git@github.com:org/repo.git"),
        (["jj", "--no-pager", "log", "-r", "@"], "worktree-feat@"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    spine, overlay = scope.derive_scopes("/repo/_wt/feat")
    assert spine == "repo:github.com/org/repo"
    assert overlay == "repo:github.com/org/repo:ws:worktree-feat"


def test_jj_default_workspace_spine_only(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], "/repo"),
        (["jj", "--no-pager", "git", "remote", "list"], "origin git@github.com:org/repo.git"),
        (["jj", "--no-pager", "log", "-r", "@"], "default@"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    spine, overlay = scope.derive_scopes("/repo")
    assert spine == "repo:github.com/org/repo"
    assert overlay is None


def test_spine_identical_across_workspaces(monkeypatch):
    # Same repo, two different workspaces -> same spine, different/None overlay.
    def fake_for(ws_name):
        return make_fake_run([
            (["jj", "--no-pager", "root"], "/repo"),
            (["jj", "--no-pager", "git", "remote", "list"], "origin git@github.com:org/repo.git"),
            (["jj", "--no-pager", "log", "-r", "@"], ws_name),
        ])
    monkeypatch.setattr(scope, "_run", fake_for("default@"))
    spine_default, ov_default = scope.derive_scopes("/repo")
    monkeypatch.setattr(scope, "_run", fake_for("worktree-feat@"))
    spine_feat, ov_feat = scope.derive_scopes("/repo")
    assert spine_default == spine_feat
    assert ov_default is None
    assert ov_feat == "repo:github.com/org/repo:ws:worktree-feat"


def test_non_repo_returns_none_pair(monkeypatch):
    monkeypatch.setattr(scope, "_run", make_fake_run([]))
    assert scope.derive_scopes("/nowhere") == (None, None)


def test_remoteless_git_uses_common_dir_parent(monkeypatch):
    # jj absent, no origin -> fall back to parent of the shared .git.
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], None),
        (["git", "remote", "get-url", "origin"], None),
        (["git", "rev-parse", "--git-common-dir"], ".git"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/home/u/myrepo") == "myrepo"


def test_git_primary_worktree_no_overlay(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], None),
        (["git", "remote", "get-url", "origin"], "git@github.com:org/repo.git"),
        (["git", "rev-parse", "--git-common-dir"], "/repo/.git"),
        (["git", "rev-parse", "--show-toplevel"], "/repo"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    assert scope.derive_scopes("/repo") == ("repo:github.com/org/repo", None)


def test_git_linked_worktree_overlay_basename(monkeypatch):
    fake = make_fake_run([
        (["jj", "--no-pager", "root"], None),
        (["git", "remote", "get-url", "origin"], "git@github.com:org/repo.git"),
        (["git", "rev-parse", "--git-common-dir"], "/repo/.git"),
        (["git", "rev-parse", "--show-toplevel"], "/repo/_wt/feat"),
    ])
    monkeypatch.setattr(scope, "_run", fake)
    spine, overlay = scope.derive_scopes("/repo/_wt/feat")
    assert spine == "repo:github.com/org/repo"
    assert overlay == "repo:github.com/org/repo:ws:feat"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_scope.py -k "workspace or spine_identical or non_repo_returns_none_pair or git_" -v`
Expected: FAIL with `AttributeError: module 'lib.scope' has no attribute 'derive_scopes'` (and `_workspace` not yet defined).

- [ ] **Step 3: Append the implementation**

Append to `memory-curator/hooks/lib/scope.py`:

```python
def _workspace(cwd: str) -> str | None:
    """Per-workspace name for the overlay; None for the primary checkout."""
    if _run(["jj", "--no-pager", "root"], cwd) is not None:
        wc = _run(
            ["jj", "--no-pager", "log", "-r", "@", "--no-graph", "-T", "working_copies"],
            cwd,
        )
        if wc:
            name = wc.split("@")[0].split()[0] if wc.split() else ""
            if name and name != "default":
                return name
        return None
    # git worktree: primary -> None; linked -> toplevel basename
    common = _run(["git", "rev-parse", "--git-common-dir"], cwd)
    toplevel = _run(["git", "rev-parse", "--show-toplevel"], cwd)
    if common and toplevel:
        cp = Path(common)
        if not cp.is_absolute():
            cp = (Path(cwd) / cp).resolve()
        if cp.parent.resolve() == Path(toplevel).resolve():
            return None  # primary worktree
        return Path(toplevel).name
    return None


def derive_scopes(cwd: str) -> tuple[str | None, str | None]:
    rid = _repo_id(cwd)
    if rid is None:
        return (None, None)
    spine = f"repo:{rid}"
    ws = _workspace(cwd)
    overlay = f"{spine}:ws:{ws}" if ws else None
    return (spine, overlay)
```

- [ ] **Step 4: Run the full scope suite to verify it passes**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_scope.py -v`
Expected: PASS (13 tests — 6 spine + 4 overlay/invariant + 3 git-path).

- [ ] **Step 5: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 3: `session-start-memory-recall` hook

**Files:**

- Create: `memory-curator/hooks/session-start-memory-recall`
- Test: `memory-curator/hooks/tests/test_session_start_memory_recall.py`
- [ ] **Step 1: Write the failing test**

Create `memory-curator/hooks/tests/test_session_start_memory_recall.py`:

```python
"""Tests for the session-start-memory-recall hook (subprocess + real git fixtures)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "session-start-memory-recall"


def run_hook(cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": cwd}),
        capture_output=True,
        text=True,
        timeout=15,
    )


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    git("remote", "add", "origin", "git@github.com:org/repo.git", cwd=repo)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit",
        "--allow-empty", "-m", "init", cwd=repo)
    return repo


def test_primary_checkout_spine_only(git_repo: Path):
    result = run_hook(str(git_repo))
    assert result.returncode == 0
    ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Memory spine scope: repo:github.com/org/repo" in ctx
    assert "Memory workspace scope:" not in ctx
    assert "mcp__memory_oauth__list_memory" in ctx
    assert "401" in ctx


def test_linked_worktree_has_overlay(git_repo: Path, tmp_path: Path):
    wt = tmp_path / "wt-feat"
    git("worktree", "add", "-q", str(wt), cwd=git_repo)
    result = run_hook(str(wt))
    ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Memory spine scope: repo:github.com/org/repo" in ctx
    assert "Memory workspace scope: repo:github.com/org/repo:ws:wt-feat" in ctx


def test_non_repo_is_silent(tmp_path: Path):
    result = run_hook(str(tmp_path))
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_malformed_stdin_is_silent():
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input="not json",
        capture_output=True, text=True, timeout=15,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_session_start_memory_recall.py -v`
Expected: FAIL (hook file does not exist → non-zero / FileNotFoundError).

- [ ] **Step 3: Write the hook**

Create `memory-curator/hooks/session-start-memory-recall` (make it executable: `chmod +x`):

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""SessionStart hook: surface memory scopes + a recall instruction.

Computes the two-tier memory scope locally (git/jj) and emits additionalContext
instructing Claude to call list_memory over its own OAuth-authenticated MCP
connection. Hooks cannot hold the OAuth token, so recall is model-mediated.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.scope import derive_scopes  # noqa: E402


def _build_context(spine: str, overlay: str | None) -> str:
    lines = [f"Memory spine scope: {spine}"]
    if overlay:
        lines.append(f"Memory workspace scope: {overlay}")
    which = "spine, and the workspace overlay if present" if overlay else "the spine"
    lines.append("")
    lines.append(
        "To recall durable memories for this session, call "
        f"mcp__memory_oauth__list_memory once per scope above ({which}), merge "
        "results (prefer the spine record on duplicate ids), and surface them "
        'grouped as "Repo-wide memories" and "This workspace\'s memories" — '
        "silently omitting any group that returns nothing. If memory_oauth "
        "returns 401/403 it is not authenticated: say once that memories are "
        "unavailable and the user can authenticate via /mcp (memory_oauth -> "
        "Authenticate), then continue without blocking."
    )
    return "\n".join(lines)


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    cwd = data.get("cwd", os.getcwd())
    try:
        spine, overlay = derive_scopes(cwd)
    except Exception:
        sys.exit(0)

    if spine is None:
        sys.exit(0)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": _build_context(spine, overlay),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

Then: `chmod +x memory-curator/hooks/session-start-memory-recall`

- [ ] **Step 4: Run to verify pass**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_session_start_memory_recall.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 4: `session-end-memory-capture` hook

**Files:**

- Create: `memory-curator/hooks/session-end-memory-capture`
- Test: `memory-curator/hooks/tests/test_session_end_memory_capture.py`
- [ ] **Step 1: Write the failing test**

Create `memory-curator/hooks/tests/test_session_end_memory_capture.py`:

```python
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
        capture_output=True, text=True, timeout=15,
    )


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", "-b", "main", cwd=repo)
    git("remote", "add", "origin", "git@github.com:org/repo.git", cwd=repo)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit",
        "--allow-empty", "-m", "init", cwd=repo)
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_session_end_memory_capture.py -v`
Expected: FAIL (hook file missing).

- [ ] **Step 3: Write the hook**

Create `memory-curator/hooks/session-end-memory-capture`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Stop hook: block-once nudge to capture durable memories.

The only way to make Claude act at stop is decision:block + reason. The
stop_hook_active guard ensures we block at most once (true => already
continuing from our prior block => allow the stop).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.scope import derive_scopes  # noqa: E402


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    if data.get("stop_hook_active"):
        sys.exit(0)  # already continuing from our block; allow the stop

    cwd = data.get("cwd", os.getcwd())
    try:
        spine, overlay = derive_scopes(cwd)
    except Exception:
        sys.exit(0)

    if spine is None:
        sys.exit(0)

    target = f"repo-wide facts to spine {spine}"
    if overlay:
        target += f", work-local facts to overlay {overlay}"
    reason = (
        "Before stopping: evaluate whether anything durable was learned this "
        "session and capture it per the curating-memory skill — "
        f"{target}. If nothing durable was learned, simply stop."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

Then: `chmod +x memory-curator/hooks/session-end-memory-capture`

- [ ] **Step 4: Run to verify pass**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_session_end_memory_capture.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 5: Plugin wiring — `hooks.json`, `plugin.json`, `.mcp.json`

**Files:**

- Create: `memory-curator/hooks/hooks.json`
- Create: `memory-curator/plugin.json`
- Create: `memory-curator/.mcp.json`
- Test: `memory-curator/hooks/tests/test_plugin_config.py`
- [ ] **Step 1: Write the failing test**

Create `memory-curator/hooks/tests/test_plugin_config.py`:

```python
"""Validate memory-curator plugin config files."""

from __future__ import annotations

import json
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]  # memory-curator/
HOOKS_DIR = PLUGIN_ROOT / "hooks"


def load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def test_mcp_declares_oauth_server():
    cfg = load(PLUGIN_ROOT / ".mcp.json")
    server = cfg["mcpServers"]["memory_oauth"]
    assert server["type"] == "http"
    assert server["url"] == "https://litellm.fzymgc.house/mcp/memory_oauth"
    assert "headers" not in server  # OAuth: no static secret
    assert server["oauth"]["callbackPort"] == 8765


def test_plugin_manifest_minimal():
    manifest = load(PLUGIN_ROOT / "plugin.json")
    assert manifest["name"] == "memory-curator"
    assert manifest["description"]


def test_hooks_register_sessionstart_and_stop():
    hooks = load(HOOKS_DIR / "hooks.json")["hooks"]
    assert "SessionStart" in hooks and "Stop" in hooks
    ss = hooks["SessionStart"][0]
    assert ss["matcher"] == "startup|clear|compact"
    assert "session-start-memory-recall" in ss["hooks"][0]["command"]
    # Stop takes no matcher
    stop = hooks["Stop"][0]
    assert "matcher" not in stop
    assert "session-end-memory-capture" in stop["hooks"][0]["command"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_plugin_config.py -v`
Expected: FAIL (config files missing → `FileNotFoundError`).

- [ ] **Step 3: Create `memory-curator/.mcp.json`**

```json
{
  "mcpServers": {
    "memory_oauth": {
      "type": "http",
      "url": "https://litellm.fzymgc.house/mcp/memory_oauth",
      "oauth": { "callbackPort": 8765 }
    }
  }
}
```

> **Implementer-verify (Open item #1):** confirm the `.mcp.json` OAuth field is `oauth.callbackPort` against the installed Claude Code version. If the field differs, update both this file and the test's `test_mcp_declares_oauth_server` assertion to match the real schema.

- [ ] **Step 4: Create `memory-curator/plugin.json`**

```json
{
  "name": "memory-curator",
  "description": "Wires the self-hosted memory MCP layer into Claude Code: session-start recall, curation discipline, and a correctable two-tier per-workspace memory scope."
}
```

- [ ] **Step 5: Create `memory-curator/hooks/hooks.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/session-start-memory-recall\"",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/session-end-memory-capture\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run --with pytest pytest memory-curator/hooks/tests/test_plugin_config.py -v`
Expected: PASS (3 tests). Also run `jq empty memory-curator/.mcp.json memory-curator/plugin.json memory-curator/hooks/hooks.json` — expect no output.

- [ ] **Step 7: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 6: `curating-memory` skill

**Files:**

- Create: `memory-curator/skills/curating-memory/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `memory-curator/skills/curating-memory/SKILL.md`:

```markdown
---
name: curating-memory
description: Use when storing or updating durable project memory via the memory_oauth MCP tools — enforces durable-only capture, search-before-store, supersede-on-contradiction, and the two-tier spine/overlay scope. Trigger when the user states a durable decision/preference/convention, on the session-end capture nudge, and before any mcp__memory_oauth__store_memory / update_memory / delete_memory call.
---

# Curating Memory

The memory store is **explicit and zero-junk**: only deliberately chosen durable
facts live in it, and it stays correct over time. Apply this discipline before
every memory write.

## Junk taxonomy

**STORE (durable):** decisions, preferences, conventions, gotchas, and
project-specific facts that outlive the session.

**DO NOT STORE:** transient state, current activity/progress, secrets or API
keys, timestamps, one-off tool output, or anything trivially re-derivable.

## Discipline

1. **Search before store.** Call `mcp__memory_oauth__search_memory` across both
   the spine and (if present) the workspace overlay first. If a near-duplicate
   exists, update it instead of adding a new record.
2. **Supersede on contradiction — within a tier.** When new info conflicts with
   an existing memory, `update_memory` (preferred) or `delete_memory` the stale
   record. Do **not** treat a spine fact and a divergent workspace-overlay fact
   as a contradiction — they are parallel truths by design.
3. **Tier selection.** Default to the **spine** (`Memory spine scope` from
   session start) — most durable facts are repo-wide and should follow the user
   into every workspace. Store to the **overlay** (`Memory workspace scope`)
   only when a fact is genuinely local to this line of work and would be wrong
   or premature elsewhere (e.g. an in-flight decision that contradicts main
   until merged). Promotion of overlay facts to the spine when work merges is
   the `promoting-memory` skill.
4. **Provenance.** Set `source` honestly (`user-said` vs `agent-inferred`). Do
   not set `actor` — it is assigned server-side from the validated OAuth token.

## Tools and auth

All tools are on the `memory_oauth` server: `mcp__memory_oauth__store_memory`,
`…__search_memory`, `…__update_memory`, `…__delete_memory`, `…__list_memory`,
`…__get_memory`. If a call returns 401/403 the server is not authenticated —
tell the user to authenticate via `/mcp` (memory_oauth → Authenticate), and
restate the durable fact so they can re-store it after authenticating; never
drop it silently.
```

- [ ] **Step 2: Lint and verify**

Run: `rumdl check --no-exclude memory-curator/skills/curating-memory/SKILL.md`
Expected: `Success: No issues found`. (If it reports fixable issues, run `rumdl fmt --no-exclude <path>` and re-check.)

- [ ] **Step 3: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 7: `promoting-memory` skill

**Files:**

- Create: `memory-curator/skills/promoting-memory/SKILL.md`

- [ ] **Step 1: Write the skill**

Create `memory-curator/skills/promoting-memory/SKILL.md`:

```markdown
---
name: promoting-memory
description: Use when a line of work completes (merges, lands, or is abandoned) to graduate a workspace's overlay memories into the repo spine and clean up. Trigger on "promote memories", "merge workspace memories", "clean up this workspace's memories", or when finishing/merging a branch. Pairs with dev-flow:finishing-a-development-branch.
---

# Promoting Memory

Capture-time tier selection (the `curating-memory` skill) decides where a *new*
fact goes. This skill reconciles an *existing* workspace overlay against the
repo spine at the natural end of the work. Promotion is deliberate and
user/model-mediated — there is no automatic merge-triggered migration.

## Workflow

1. Use the `Memory spine scope` and `Memory workspace scope` lines from session
   start. If there is **no** workspace scope (primary checkout), there is
   nothing workspace-local to promote — stop.
2. `mcp__memory_oauth__list_memory(<overlay scope>)` to enumerate this
   workspace's local memories. (401/403 → server unauthenticated; tell the user
   to `/mcp` Authenticate and stop.) If empty, report "nothing to promote".
3. For each overlay memory, decide with the user:
   - **Promote** — now true repo-wide. `search_memory(<spine>, …)` first for a
     duplicate/contradiction; then `store_memory(<spine>, …)` (or `update_memory`
     the spine record on contradiction); then `delete_memory` the overlay copy.
   - **Keep** — still genuinely work-local (rare once merged); leave it.
   - **Drop** — no longer relevant; `delete_memory`.
4. Once the workspace is being retired, offer `delete_all(<overlay scope>)` as a
   teardown after promotions are done.

Keep the spine zero-junk: promote only facts that are genuinely durable and
repo-wide, applying the same junk taxonomy as `curating-memory`.
```

- [ ] **Step 2: Lint and verify**

Run: `rumdl check --no-exclude memory-curator/skills/promoting-memory/SKILL.md`
Expected: `Success: No issues found`.

- [ ] **Step 3: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 8: `README.md` (setup + scope convention)

**Files:**

- Create: `memory-curator/README.md`

- [ ] **Step 1: Write the README**

Create `memory-curator/README.md`:

```markdown
# memory-curator

Wires the self-hosted memory MCP layer into Claude Code as a low-friction,
self-correcting part of every session: prior durable context surfaces at
session start, new durable knowledge is captured with discipline, and the store
stays correct over time.

## Setup (one-time)

Authentication is native MCP **OAuth** (Authentik PKCE) — there is no secret to
configure. After installing the plugin, run `/mcp`, select `memory_oauth`, and
choose **Authenticate**. A browser opens for Authentik login; the token is
stored per-user and auto-refreshes, so re-auth is only needed occasionally
(e.g. after a gateway restart).

Auth is interactive: headless/CI sessions that have never authenticated cannot
complete the browser flow and will simply have memory recall unavailable (the
session is never blocked).

## Scope convention

Memory is two-tier, keyed off repository identity (not the working directory):

- **spine** `repo:<host/org/repo>` — repo-wide durable facts, shared across
  every workspace/worktree of the repo.
- **overlay** `repo:<host/org/repo>:ws:<workspace>` — durable context local to a
  named non-default workspace. The primary checkout is spine-only.

The repo id is the normalized `origin` remote (jj-first: a jj workspace resolves
it via `jj git remote list`, since a workspace is not itself a git repo), with a
directory-basename fallback when there is no remote. Store and recall use the
same derivation, so what you store in one session is recalled in the next.

## What it does

- **Session start:** a hook computes the scope(s) and asks Claude to recall this
  repo's durable memories (silent when there are none).
- **During the session:** the `curating-memory` skill enforces durable-only
  capture, search-before-store, and supersede-on-contradiction.
- **Session end:** a hook nudges Claude (once) to capture anything durable.
- **Work completion:** the `promoting-memory` skill graduates workspace-local
  memories into the spine and cleans up.
```

- [ ] **Step 2: Lint and verify**

Run: `rumdl check --no-exclude memory-curator/README.md`
Expected: `Success: No issues found`.

- [ ] **Step 3: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 9: Codex wrapper

**Files:**

- Create: `plugins/memory-curator/.codex-plugin/plugin.json`
- Create symlinks: `plugins/memory-curator/.mcp.json`, `plugins/memory-curator/hooks`, `plugins/memory-curator/skills`
- [ ] **Step 1: Create the wrapper manifest**

Create `plugins/memory-curator/.codex-plugin/plugin.json`:

```json
{
  "name": "memory-curator",
  "description": "Wires the self-hosted memory MCP layer into Claude Code: session-start recall, curation discipline, and a correctable two-tier per-workspace memory scope.",
  "author": {
    "name": "Sean Brandt",
    "email": "4678+seanb4t@users.noreply.github.com",
    "url": "https://github.com/seanb4t"
  },
  "homepage": "https://github.com/fzymgc-house/fzymgc-house-skills",
  "repository": "https://github.com/fzymgc-house/fzymgc-house-skills",
  "license": "UNLICENSED",
  "keywords": ["memory", "mcp", "recall", "curation"],
  "skills": "./skills/",
  "interface": {
    "displayName": "Memory Curator",
    "shortDescription": "Self-hosted memory layer wired into Claude Code.",
    "longDescription": "Codex wrapper for the memory-curator plugin. Reuses the curating-memory and promoting-memory skills and the memory_oauth MCP server via symlinks back to the source plugin.",
    "developerName": "fzymgc-house",
    "category": "Developer Tools",
    "capabilities": ["Read", "Run", "Write"],
    "websiteURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "privacyPolicyURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "termsOfServiceURL": "https://github.com/fzymgc-house/fzymgc-house-skills",
    "defaultPrompt": [
      "Recall the durable memories for this repository.",
      "Capture the durable decisions from this session.",
      "Promote this workspace's memories into the repo spine."
    ],
    "brandColor": "#1D4ED8"
  }
}
```

- [ ] **Step 2: Create the symlinks**

Run (relative targets, matching the existing `plugins/homelab/.mcp.json` pattern):

```bash
cd plugins/memory-curator
ln -s ../../memory-curator/.mcp.json .mcp.json
ln -s ../../memory-curator/hooks hooks
ln -s ../../memory-curator/skills skills
cd ../..
```

- [ ] **Step 3: Verify the symlinks resolve and the manifest is valid**

Run:

```bash
test -e plugins/memory-curator/.mcp.json && \
test -e plugins/memory-curator/hooks/hooks.json && \
test -e plugins/memory-curator/skills/curating-memory/SKILL.md && \
jq empty plugins/memory-curator/.codex-plugin/plugin.json && echo OK
```

Expected: `OK`.

- [ ] **Step 4: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 10: Marketplace registration + Taskfile gates

**Files:**

- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `tests/test_codex_marketplace.py`
- Modify: `Taskfile.yaml`
- Test: `tests/test_memory_curator_plugin.py`
- [ ] **Step 1: Write the failing test**

Create `tests/test_memory_curator_plugin.py`:

```python
"""memory-curator is registered in both marketplaces with a resolvable wrapper."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def test_claude_marketplace_includes_memory_curator():
    mp = load(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    entry = next(p for p in mp["plugins"] if p["name"] == "memory-curator")
    assert entry["source"] == "./memory-curator"


def test_codex_marketplace_includes_memory_curator():
    mp = load(REPO_ROOT / ".agents" / "plugins" / "marketplace.json")
    entry = next(p for p in mp["plugins"] if p["name"] == "memory-curator")
    assert entry["source"] == {"source": "local", "path": "./plugins/memory-curator"}


def test_wrapper_symlinks_resolve():
    wrapper = REPO_ROOT / "plugins" / "memory-curator"
    assert (wrapper / ".mcp.json").resolve().is_file()
    assert (wrapper / "hooks" / "hooks.json").resolve().is_file()
    assert (wrapper / "skills" / "curating-memory" / "SKILL.md").resolve().is_file()
```

- [ ] **Step 2: Update the existing Codex-marketplace test expectations**

In `tests/test_codex_marketplace.py`, add `memory-curator` to both expectation
constants:

```python
EXPECTED_PLUGIN_ORDER = ["homelab", "jj", "dev-flow", "memory-curator"]
EXPECTED_EXTRA_PATHS = {
    "homelab": [".mcp.json"],
    "jj": ["hooks", "commands"],
    "dev-flow": ["agents", "hooks", "references", "scripts"],
    "memory-curator": [".mcp.json", "hooks", "skills"],
}
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run --with pytest pytest tests/test_memory_curator_plugin.py tests/test_codex_marketplace.py -v`
Expected: FAIL (`StopIteration` / marketplace missing the entry).

- [ ] **Step 4: Register in the Claude marketplace**

In `.claude-plugin/marketplace.json`, append to the `plugins` array (after the
`dev-flow` entry):

```json
    {
      "name": "memory-curator",
      "description": "Wires the self-hosted memory MCP layer into Claude Code: session-start recall, curation discipline, and a correctable two-tier per-workspace memory scope.",
      "source": "./memory-curator"
    }
```

- [ ] **Step 5: Register in the Codex marketplace**

In `.agents/plugins/marketplace.json`, append to the `plugins` array (after the
`dev-flow` entry):

```json
    {
      "name": "memory-curator",
      "source": {
        "source": "local",
        "path": "./plugins/memory-curator"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools"
    }
```

- [ ] **Step 6: Update `Taskfile.yaml` gated paths**

In `Taskfile.yaml` `vars`, edit the explicit lists:

- `PYTEST_DIRS`: add a line `memory-curator/hooks/tests/`.
- `MD_FILES`: add `memory-curator/skills/*/SKILL.md` and `memory-curator/README.md`.
- `PLUGIN_JSON`: add `memory-curator/plugin.json` (the wrapper's
  `.codex-plugin/plugin.json` is already covered by the `plugins/*/.codex-plugin/plugin.json` glob).
- Extend the `jq empty` lint command to also validate the MCP config — change it to:
  `jq empty {{.PLUGIN_JSON}} memory-curator/.mcp.json`
- [ ] **Step 7: Run to verify pass**

Run: `uv run --with pytest pytest tests/test_memory_curator_plugin.py tests/test_codex_marketplace.py -v`
Expected: PASS. Also `jq empty .claude-plugin/marketplace.json .agents/plugins/marketplace.json` — no output.

- [ ] **Step 8: Commit**

Commit per `references/vcs-preamble.md`.

---

### Task 11: Full quality-gate verification

**Files:** none (verification only)

- [ ] **Step 1: Format**

Run: `task fmt`
Expected: completes; review any reformatting with `jj diff --git` and re-commit if needed.

- [ ] **Step 2: Lint**

Run: `task lint`
Expected: rumdl, ruff check/format, `jq empty` (incl. `memory-curator/.mcp.json`), evals schema, and ADR gates all pass.

- [ ] **Step 3: Test**

Run: `task test`
Expected: all suites pass, including `memory-curator/hooks/tests/` and the new `tests/test_memory_curator_plugin.py`.

- [ ] **Step 4: Confirm hook executability**

Run: `test -x memory-curator/hooks/session-start-memory-recall && test -x memory-curator/hooks/session-end-memory-capture && echo OK`
Expected: `OK`. (If not executable, `chmod +x` both and re-commit.)

- [ ] **Step 5: Final commit / clean tree**

Ensure the working copy is clean (`jj st`), all tasks committed. Commit any final fixes per `references/vcs-preamble.md`.

---

## Notes for the implementer

- **uv invocation in CI vs. tests:** the hooks ship with a `#!/usr/bin/env -S uv run --script` shebang (repo convention). The tests run them via `sys.executable` (the pytest interpreter), which works because the PEP-723 header is an inert comment and the scripts are stdlib-only. Do not add third-party deps to the hooks without updating the `task test` invocation.
- **Open items carried from the spec** (verify during implementation, do not block on them):
  1. `.mcp.json` OAuth field shape (`oauth.callbackPort`) vs. the installed Claude Code version — Task 5 Step 3.
  2. `jj git remote list` / `.jj/repo` pointer parsing on jj 0.41 — covered by `test_scope.py`; adjust parsing if real output differs.
  3. Scope-string convention acceptance by the deployed service — lock and document in README (Task 8) before relying on cross-session recall.
  4. `jj log -r @ -T working_copies` current-workspace disambiguation when multiple workspaces share `@`'s commit.
  5. Headless detection for the recall hook's optional 401-avoidance — not implemented here (the hook always emits the instruction; Claude handles 401 per the degradation text). Add only if a reliable signal is confirmed.
- **Considered alternative (deferred):** hook-spawned headless `claude -p` for deterministic pre-loaded recall — see the spec's "Considered alternatives". Not in scope for this plan.
<!-- adr-capture: sha256=6e7d3b2a6924be8b; session=4b2561eb; ts=2026-06-01T23:48:22Z; adrs=fhsk-e0u -->
