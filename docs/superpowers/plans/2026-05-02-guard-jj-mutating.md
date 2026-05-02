<!-- markdownlint-disable MD013 -->

# guard-jj-mutating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PreToolUse/Bash hook that blocks `jj op restore` and `jj op abandon` invocations in jj repos unless the agent appends a `# jj-op-approved` marker, escalating marked invocations to ASK so the human can decide.

**Architecture:** New Python hook script (`jj/hooks/guard-jj-mutating`) using `uv run --script` shebang, mirroring the structural pattern of the existing `guard-git-mutating`. Pytest-based tests under `jj/hooks/tests/`. One config edit to `jj/plugin.json` to register the hook on the existing PreToolUse/Bash matcher (alongside `guard-git-mutating`). No shared module — each hook stays single-file.

**Tech Stack:** Python 3.11+, `uv` (script runner), `pytest`, JSON-over-stdin/stdout (Claude Code hook protocol).

**Spec:** `docs/superpowers/specs/2026-05-02-guard-jj-mutating-design.md`

**Bead:** `fhsk-406`

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `jj/hooks/guard-jj-mutating` | Create | The hook script. ~100 lines. Reads JSON from stdin, returns ASK on marker, DENY on matched command in jj repo, ALLOW silently otherwise. |
| `jj/hooks/tests/test_guard_jj_mutating.py` | Create | Pytest tests covering edge cases, marker bypass, repo detection, blocked commands, and allowed commands. ~150 lines. |
| `jj/plugin.json` | Modify (1 line added) | Register the new hook alongside `guard-git-mutating` in the existing PreToolUse/Bash array. |

The hook intentionally **does not** share code with `guard-git-mutating` — extracting a common module is a non-goal until a third hook lands (per spec).

---

## Task 1: Skeleton hook with edge-case handling

**Goal:** Create a hook that gracefully handles every malformed/empty input case by exiting 0 (silent allow). This is the foundation — every later task layers logic on top.

**Files:**

- Create: `jj/hooks/guard-jj-mutating`
- Create: `jj/hooks/tests/test_guard_jj_mutating.py`
- [ ] **Step 1: Write the failing edge-case tests**

Create `jj/hooks/tests/test_guard_jj_mutating.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All tests FAIL with `FileNotFoundError` (the hook script doesn't exist yet) or similar.

- [ ] **Step 3: Create the skeleton hook**

Create `jj/hooks/guard-jj-mutating`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""PreToolUse hook: gate jj op restore/abandon behind explicit approval.

Mirrors guard-git-mutating's response model. DENYs `jj op restore` and
`jj op abandon` invocations in jj repos unless the agent appends a
`# jj-op-approved` marker (which escalates to ASK so the human can
decide).

Why these two commands are gated: both rewind the global jj op log.
In multi-workspace repos, sibling workspaces go stale and
`jj workspace update-stale` may silently resurrect pre-rewind content,
losing later edits. See jj-vcs/jj#9208 and the recovery ladder in
jj/skills/jujutsu/SKILL.md.
"""

from __future__ import annotations

import json
import sys


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        tool_input = data.get("tool_input") or {}
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    except (json.JSONDecodeError, OSError, AttributeError):
        sys.exit(0)

    if not command:
        sys.exit(0)

    # Marker check, repo check, and regex match come in later tasks.
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Make the hook executable**

Run: `chmod +x /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills/jj/hooks/guard-jj-mutating`

Verify: `ls -la /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills/jj/hooks/guard-jj-mutating` shows `-rwxr-xr-x`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All 7 `TestEdgeCases` tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
git add jj/hooks/guard-jj-mutating jj/hooks/tests/test_guard_jj_mutating.py
git commit -m "$(cat <<'EOF'
feat(jj/hooks): add guard-jj-mutating skeleton with edge-case handling

Skeleton PreToolUse hook for fhsk-406. Reads JSON from stdin, returns
exit 0 on every malformed input (empty stdin, malformed JSON, null
tool_input, non-dict tool_input, missing tool_input, missing cwd,
empty command). Marker, repo, and regex logic land in subsequent
commits.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Approval marker → ASK escalation

**Goal:** When `# jj-op-approved` appears anywhere in the command string, emit an ASK JSON response so the human gets prompted. This check runs **before** the repo check — the marker signals intent regardless of whether `.jj/` is found.

**Files:**

- Modify: `jj/hooks/guard-jj-mutating` (insert marker check)
- Modify: `jj/hooks/tests/test_guard_jj_mutating.py` (add `TestApprovedMarker`)
- [ ] **Step 1: Write the failing marker tests**

Append to `jj/hooks/tests/test_guard_jj_mutating.py`:

```python
class TestApprovedMarker:
    """The `# jj-op-approved` marker escalates to ASK regardless of context."""

    @pytest.mark.parametrize(
        "command",
        [
            "jj op restore # jj-op-approved",
            "jj op abandon # jj-op-approved",
            "jj operation restore # jj-op-approved",
            "jj operation abandon # jj-op-approved",
            "jj --at-op=abc op restore # jj-op-approved",
            "jj op restore && echo done # jj-op-approved",
        ],
    )
    def test_marker_escalates_to_ask(self, jj_repo: Path, command: str) -> None:
        result = run_hook(command, str(jj_repo))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "ask"
        assert "jj-op-approved" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_marker_works_outside_jj_repo(self, tmp_path: Path) -> None:
        """Marker check fires before repo check — ASK even with no .jj/."""
        result = run_hook("jj op restore # jj-op-approved", str(tmp_path))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "ask"

    def test_marker_with_unrelated_command(self, jj_repo: Path) -> None:
        """Marker on a command we don't gate also escalates (defensive)."""
        result = run_hook("ls # jj-op-approved", str(jj_repo))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "ask"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py::TestApprovedMarker -v`

Expected: All 8 `TestApprovedMarker` tests FAIL with `json.decoder.JSONDecodeError` (hook currently exits silently with empty stdout).

- [ ] **Step 3: Add the marker check to the hook**

Edit `jj/hooks/guard-jj-mutating`. Replace the comment-and-exit block at the end of `main()`:

```python
    if not command:
        sys.exit(0)

    # Marker check, repo check, and regex match come in later tasks.
    sys.exit(0)
```

with:

```python
    if not command:
        sys.exit(0)

    # Approval marker escapes the gate — escalate to ASK so the human decides.
    # Runs before the repo check so the marker signals intent regardless of cwd.
    if "# jj-op-approved" in command:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    "jj-op-approved: agent is requesting to rewind the global "
                    "jj op log (jj op restore/abandon). Review and approve or deny."
                ),
            }
        }
        json.dump(result, sys.stdout)
        return

    # Repo check and regex match come in later tasks.
    sys.exit(0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All `TestEdgeCases` (7) and `TestApprovedMarker` (8) tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
git add jj/hooks/guard-jj-mutating jj/hooks/tests/test_guard_jj_mutating.py
git commit -m "$(cat <<'EOF'
feat(jj/hooks): guard-jj-mutating marker escalates to ASK

When the command contains `# jj-op-approved`, emit a
permissionDecision: "ask" response so the human gets prompted to
approve or deny. Marker check runs before the repo/regex checks —
the marker signals intent regardless of cwd, mirroring how
guard-git-mutating handles `# jj-exempt`.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: jj-repo detection (.jj/ walk)

**Goal:** When the command does not contain the marker, only proceed past this point if `.jj/` is found by walking up from `cwd` (max 50 levels). Outside a jj repo, exit 0 silently — the next task's regex match must not fire in non-jj contexts.

**Files:**

- Modify: `jj/hooks/guard-jj-mutating` (insert .jj/ walk)
- Modify: `jj/hooks/tests/test_guard_jj_mutating.py` (add `TestNotInJjRepo`)
- [ ] **Step 1: Write the failing repo-check tests**

Append to `jj/hooks/tests/test_guard_jj_mutating.py`:

```python
class TestNotInJjRepo:
    """Outside a jj repo, the hook must not block jj op commands."""

    def test_no_jj_dir_anywhere(self, tmp_path: Path) -> None:
        """No .jj/ in cwd or any ancestor → silent allow."""
        result = run_hook("jj op restore", str(tmp_path))
        assert result.returncode == 0
        assert result.stdout == ""

    def test_only_git_dir(self, git_repo: Path) -> None:
        """A pure git repo (no .jj/) → silent allow."""
        result = run_hook("jj op restore", str(git_repo))
        assert result.returncode == 0
        assert result.stdout == ""

    def test_subdirectory_finds_parent_jj(self, jj_repo: Path) -> None:
        """A subdirectory of a jj repo must still be detected as a jj repo."""
        subdir = jj_repo / "src" / "deep"
        subdir.mkdir(parents=True)
        # Without the regex match (Task 4) yet, this currently exits 0 either
        # way; this test will become meaningful once Task 4 lands. For now it
        # asserts no crash from the walk logic on a subdirectory cwd.
        result = run_hook("ls", str(subdir))
        assert result.returncode == 0
```

- [ ] **Step 2: Run tests to verify they pass (already!) but the third test is forward-looking**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py::TestNotInJjRepo -v`

Expected: All 3 `TestNotInJjRepo` tests PASS even before the walk is added (because the hook currently exits 0 on everything past the marker check). They become meaningful regression tests once Task 4 adds the regex match. **This is intentional** — the test file documents the contract; the implementation order makes the contract real progressively.

- [ ] **Step 3: Add the .jj/ walk to the hook**

Edit `jj/hooks/guard-jj-mutating`. First add `import os` at the top (alongside `import json` and `import sys`).

Then replace this block at the end of `main()`:

```python
    # Repo check and regex match come in later tasks.
    sys.exit(0)
```

with:

```python
    cwd = data.get("cwd", "")
    if not cwd:
        sys.exit(0)

    # Walk up from cwd looking for .jj/ (depth-limited to avoid pathological loops).
    jj_found = False
    check_dir = cwd
    for _ in range(50):
        if os.path.isdir(os.path.join(check_dir, ".jj")):
            jj_found = True
            break
        parent = os.path.dirname(check_dir)
        if parent == check_dir:
            break
        check_dir = parent

    if not jj_found:
        sys.exit(0)

    # Regex match comes in the next task.
    sys.exit(0)
```

- [ ] **Step 4: Run tests to verify they still pass**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All tests so far (`TestEdgeCases`, `TestApprovedMarker`, `TestNotInJjRepo`) PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
git add jj/hooks/guard-jj-mutating jj/hooks/tests/test_guard_jj_mutating.py
git commit -m "$(cat <<'EOF'
feat(jj/hooks): guard-jj-mutating walks for .jj/ before gating

Adds the standard depth-limited (max 50) parent walk to detect a jj
repo from cwd or any ancestor. Outside a jj repo (no .jj/ found),
the hook exits 0 silently — the regex match in the next commit must
not fire in non-jj contexts.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Regex matcher and DENY response

**Goal:** Add the `JJ_OP_BLOCKED_RE` regex, emit a DENY JSON response when it matches an unmarked command in a jj repo, and verify that allowed commands (read-only `jj op` siblings, `git status`, `ls`) pass through silently.

**Files:**

- Modify: `jj/hooks/guard-jj-mutating` (add regex + DENY emission)
- Modify: `jj/hooks/tests/test_guard_jj_mutating.py` (add `TestBlocked`, `TestAllowed`)
- [ ] **Step 1: Write the failing blocked/allowed tests**

Append to `jj/hooks/tests/test_guard_jj_mutating.py`:

```python
class TestBlocked:
    """jj op restore/abandon in a jj repo without the marker → DENY."""

    @pytest.mark.parametrize(
        "command",
        [
            "jj op restore",
            "jj op abandon",
            "jj operation restore",
            "jj operation abandon",
            "jj op restore --at-op=abc123",
            "jj op abandon abc123 def456",
            "jj --repo /tmp/repo op restore",
            "jj --at-op=xyz op abandon",
            "jj op restore && echo done",
            "echo start; jj op abandon abc",
            "$(jj op restore)",
            "result=$(jj op abandon abc) || true",
        ],
    )
    def test_blocked_command_denied(self, jj_repo: Path, command: str) -> None:
        result = run_hook(command, str(jj_repo))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "jj op revert" in output["systemMessage"]
        assert "# jj-op-approved" in output["systemMessage"]


class TestAllowed:
    """Commands that don't match the regex must pass through silently."""

    @pytest.mark.parametrize(
        "command",
        [
            "jj op log",
            "jj op show abc",
            "jj op revert abc",
            "jj op diff",
            "jj operation log",
            "jj st",
            "jj new",
            "jj describe -m 'msg'",
            "jj git push",
            "git status",
            "git log --oneline",
            "ls -la",
            "echo 'jj op restore is bad'",  # string mention, not invocation
        ],
    )
    def test_allowed_command_passes(self, jj_repo: Path, command: str) -> None:
        result = run_hook(command, str(jj_repo))
        assert result.returncode == 0
        assert result.stdout == ""
```

- [ ] **Step 2: Run tests to verify the blocked ones fail and allowed ones pass**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All `TestBlocked` (12) FAIL with `json.decoder.JSONDecodeError` (hook currently exits 0 with empty stdout). All `TestAllowed` (13) PASS. All earlier tests still PASS.

- [ ] **Step 3: Add the regex and DENY emission**

Edit `jj/hooks/guard-jj-mutating`. Add `import re` at the top alongside the other imports.

Add the regex constant near the top of the file (between the docstring and `def main`):

```python
# Match `jj op restore`, `jj op abandon`, and the long form `jj operation
# restore` / `jj operation abandon`. Tolerates intervening flags (e.g.
# `jj --repo /x op restore`, `jj --at-op=abc op abandon`). The shell-context
# anchors (\b at start, regex used with .search) handle compound commands
# like `jj op restore && echo ok` and `$(jj op restore)`.
JJ_OP_BLOCKED_RE = re.compile(
    r"\bjj\b(?:\s+(?:--?[A-Za-z][\w-]*(?:=\S+)?|-[A-Za-z]))*\s+(?:op|operation)\s+(?:restore|abandon)\b"
)
```

Replace this block at the end of `main()`:

```python
    if not jj_found:
        sys.exit(0)

    # Regex match comes in the next task.
    sys.exit(0)
```

with:

```python
    if not jj_found:
        sys.exit(0)

    if not JJ_OP_BLOCKED_RE.search(command):
        sys.exit(0)

    reason = (
        "BLOCKED: jj op restore/abandon rewinds the global op log and can "
        "silently lose edits in sibling workspaces. Use `jj op revert <op-id>` "
        "for surgical recovery (see jj skill recovery ladder)."
    )
    system_msg = (
        "jj op restore/abandon was blocked. These commands rewind the global "
        "op log and may silently lose edits in sibling workspaces via "
        "`jj workspace update-stale`. Prefer `jj op revert <op-id>` for "
        "surgical recovery. If the user has explicitly approved this op-log "
        "rewind, append `# jj-op-approved` to the command (escalates to ASK)."
    )

    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": system_msg,
    }
    try:
        json.dump(result, sys.stdout)
    except OSError:
        # Broken pipe — framework closed stdout; exit 2 to block the command
        # rather than silently allowing it.
        sys.exit(2)
```

- [ ] **Step 4: Run all tests to verify everything passes**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest jj/hooks/tests/test_guard_jj_mutating.py -v`

Expected: All 5 test classes (`TestEdgeCases`, `TestApprovedMarker`, `TestNotInJjRepo`, `TestBlocked`, `TestAllowed`) PASS.

- [ ] **Step 5: Run the full repo test suite to confirm no collateral damage**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -v`

Expected: All tests PASS, including the existing `test_guard_git_mutating.py` and `test_session_start_jj_detect.py`.

- [ ] **Step 6: Commit**

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
git add jj/hooks/guard-jj-mutating jj/hooks/tests/test_guard_jj_mutating.py
git commit -m "$(cat <<'EOF'
feat(jj/hooks): guard-jj-mutating denies jj op restore/abandon

Adds the JJ_OP_BLOCKED_RE matcher (covers `jj op restore`, `jj op
abandon`, long-form `jj operation` variants, intervening flags, and
shell-compound contexts) and the DENY response: JSON with
permissionDecision: "deny", reason pointing at `jj op revert`, and
systemMessage explaining the multi-workspace blast radius and the
`# jj-op-approved` escape. Falls back to exit 2 only on broken pipe,
mirroring guard-git-mutating's pattern.

Closes the implementation half of fhsk-406 (plugin registration in
the next commit).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Plugin registration

**Goal:** Register the new hook in `jj/plugin.json` so Claude Code actually invokes it on every Bash tool use. Smoke-test the wired-up hook end-to-end.

**Files:**

- Modify: `jj/plugin.json` (append one entry to the existing PreToolUse/Bash array)

- [ ] **Step 1: Inspect current plugin.json**

Run: `cat /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills/jj/plugin.json`

Expected output:

```json
{
  "name": "jj",
  "version": "0.1.0",
  "description": "Jujutsu (jj) VCS workflow guidance for colocated and standalone repos",
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start-jj-detect",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-git-mutating",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Add the new hook entry to the Bash matcher**

Edit `jj/plugin.json`. Find the PreToolUse Bash matcher's `hooks` array (currently containing one entry for `guard-git-mutating`) and append a second entry for `guard-jj-mutating`:

Replace:

```json
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-git-mutating",
            "timeout": 5
          }
        ]
      }
    ]
```

with:

```json
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-git-mutating",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-jj-mutating",
            "timeout": 5
          }
        ]
      }
    ]
```

- [ ] **Step 3: Validate the JSON parses**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && python3 -c "import json; json.load(open('jj/plugin.json'))" && echo OK`

Expected: `OK`

- [ ] **Step 4: End-to-end smoke test the hook directly**

Run a manual invocation that exercises the DENY path with a real `.jj/` directory:

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
TMPDIR=$(mktemp -d) && mkdir "$TMPDIR/.jj" && \
  echo '{"tool_input": {"command": "jj op restore"}, "cwd": "'"$TMPDIR"'"}' \
  | jj/hooks/guard-jj-mutating
```

Expected output (one line of JSON; pretty-printed below for readability):

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "BLOCKED: jj op restore/abandon ..."}, "systemMessage": "jj op restore/abandon was blocked. ..."}
```

Then exercise the marker (ASK) path:

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
echo '{"tool_input": {"command": "jj op restore # jj-op-approved"}, "cwd": "/tmp"}' \
  | jj/hooks/guard-jj-mutating
```

Expected: JSON with `"permissionDecision": "ask"`.

Then exercise the silent-allow path:

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
echo '{"tool_input": {"command": "jj op log"}, "cwd": "/tmp"}' \
  | jj/hooks/guard-jj-mutating
echo "exit=$?"
```

Expected: empty output, `exit=0`.

- [ ] **Step 5: Run the full test suite once more**

Run: `cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills && uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -v`

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/sean/Code/github.com/fzymgc-house/fzymgc-house-skills
git add jj/plugin.json
git commit -m "$(cat <<'EOF'
feat(jj/plugin): register guard-jj-mutating on PreToolUse/Bash

Wires the new hook into the existing PreToolUse/Bash matcher
alongside guard-git-mutating. Both hooks run on every Bash
invocation; ordering is irrelevant because they match disjoint
command sets (mutating git subcommands vs. `jj op restore|abandon`).

Completes fhsk-406.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Checklist

After all tasks complete, verify against the spec (`docs/superpowers/specs/2026-05-02-guard-jj-mutating-design.md`):

| Spec requirement | Implementing task |
|---|---|
| New file `jj/hooks/guard-jj-mutating` (Python, `uv run --script`) | Task 1 |
| Defensive try/except (`JSONDecodeError | OSError | AttributeError`) | Task 1 |
| `isinstance(tool_input, dict)` guard | Task 1 |
| Empty-command early exit | Task 1 |
| Marker check (`# jj-op-approved`) → ASK JSON, before repo check | Task 2 |
| `.jj/` walk (max 50 levels) for repo detection | Task 3 |
| `JJ_OP_BLOCKED_RE` covering both forms + intervening flags + shell context | Task 4 |
| DENY JSON with `permissionDecision: "deny"`, `permissionDecisionReason`, top-level `systemMessage` | Task 4 |
| Broken-pipe fallback `sys.exit(2)` | Task 4 |
| `TestEdgeCases`: 7 cases | Task 1 |
| `TestApprovedMarker`: parametrized + non-jj-repo case + unrelated-command case | Task 2 |
| `TestNotInJjRepo`: no .jj/, only .git/, subdirectory walk | Task 3 |
| `TestBlocked`: parametrized 12 variants | Task 4 |
| `TestAllowed`: parametrized 13 negative cases | Task 4 |
| `jj/plugin.json` PreToolUse/Bash entry | Task 5 |
| CI auto-coverage (no workflow change needed) | Confirmed by `check-skills.yml:77` |

**Acceptance criteria from `fhsk-406`:**

- ✅ Hook blocks both commands by default with message pointing to recovery ladder → Task 4
- ✅ Unit tests under `jj/hooks/tests/` → Tasks 1–4
- ✅ Wired into plugin hook registration → Task 5

**Out-of-scope confirmations** (must NOT appear in any task):

- ❌ No env-var bypass (`JJ_OP_APPROVE`)
- ❌ No blocking of `jj op log/show/revert/diff` (covered by `TestAllowed` in Task 4)
- ❌ No `jj/hooks/_common.py` extraction
- ❌ No SKILL.md edits
