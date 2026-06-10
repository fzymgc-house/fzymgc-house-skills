#!/usr/bin/env python3
"""Shared helpers for the worktree-create and worktree-remove hooks.

Functions:
    sanitize_for_output(s)          — strip control chars for safe logging
    validate_safe_name(name, label) — reject path traversal/metacharacters
    run_cmd(args, *, cwd)           — thin subprocess wrapper, never raises
    detect_repo_root(*, cwd)        — find repo root via git or jj
    setup_beads_redirect(root, wt)  — point a jj workspace's bd at the main DB
    cleanup_empty_parent(parent)    — rmdir if directory exists and is empty
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def sanitize_for_output(s: str) -> str:
    """Strip C0 control chars (0x00-0x1F) except tab/newline/CR, DEL (0x7F),
    and C1 control chars (0x80-0x9F).

    Preserving \\t (0x09), \\n (0x0A), \\r (0x0D) allows multi-line messages
    to remain readable. This matches the bash:
        tr -d '\\000-\\010\\013\\014\\016-\\037\\177\\200-\\237'
    """
    # Build a set of code points to remove:
    # 0x00-0x08 (NUL..BS), 0x0B (VT), 0x0C (FF), 0x0E-0x1F (SO..US),
    # 0x7F (DEL), 0x80-0x9F (C1 controls)
    remove_chars = (
        set(range(0x00, 0x09))  # 0x00-0x08
        | {0x0B, 0x0C}  # VT, FF
        | set(range(0x0E, 0x20))  # 0x0E-0x1F
        | {0x7F}  # DEL
        | set(range(0x80, 0xA0))  # 0x80-0x9F
    )
    return "".join(ch for ch in s if ord(ch) not in remove_chars)


def validate_safe_name(name: str, label: str) -> None:
    """Validate that *name* is safe for use as a filesystem component.

    Raises ValueError for:
    - Empty names
    - Characters outside [a-zA-Z0-9_.-]
    - Leading dot, trailing dot, or double-dot anywhere in the name
    """
    if not name:
        raise ValueError(f"{sanitize_for_output(label)} must not be empty")

    invalid = (
        not re.fullmatch(r"[a-zA-Z0-9_.-]+", name)
        or name.startswith(".")
        or name.endswith(".")
        or ".." in name
    )
    if invalid:
        safe_name = sanitize_for_output(name)
        safe_label = sanitize_for_output(label)
        raise ValueError(
            f"invalid {safe_label} '{safe_name}' "
            "(alphanumeric, dots, hyphens, underscores only; "
            "no leading dot, trailing dot, or double-dot)"
        )


def run_cmd(args: list[str], *, cwd: Path | str) -> subprocess.CompletedProcess:
    """Run *args* as a subprocess in *cwd*.

    Returns a CompletedProcess. Never raises: returns a synthetic
    result with returncode=127 and descriptive stderr on OSError
    (executable not found, permission denied, etc.).
    """
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=args, returncode=127, stdout="", stderr=f"{type(exc).__name__}: {exc}"
        )


def detect_repo_root(*, cwd: Path | str) -> Path:
    """Return the repository root for the working directory *cwd*.

    Tries ``git rev-parse --show-toplevel`` first, then ``jj root`` if jj
    is in PATH. Raises RuntimeError if neither succeeds.
    """
    result = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if result.returncode == 0:
        root = result.stdout.strip()
        if root and Path(root).is_dir():
            return Path(root)
        print(
            f"WARNING: git rev-parse succeeded but returned unusable path "
            f"{repr(root)} — trying jj",
            file=sys.stderr,
        )

    # git failed or returned unusable path — try jj
    if shutil.which("jj") is None:
        raise RuntimeError(
            "not inside a git/jj repository (git rev-parse failed; jj not in PATH)"
        )

    jj_result = run_cmd(["jj", "--no-pager", "root"], cwd=cwd)
    if jj_result.returncode == 0:
        jj_root = jj_result.stdout.strip()
        if jj_root and Path(jj_root).is_dir():
            return Path(jj_root)
        if not jj_root:
            raise RuntimeError(
                "not inside a git/jj repository "
                "(git rev-parse failed; jj root returned empty output)"
            )
        raise RuntimeError(
            f"not inside a git/jj repository "
            f"(git rev-parse failed; jj root returned "
            f"'{sanitize_for_output(jj_root)}' but directory does not exist)"
        )

    jj_err = sanitize_for_output(jj_result.stderr.strip())
    raise RuntimeError(
        f"not inside a git/jj repository "
        f"(git rev-parse and jj root both failed"
        f"{'; jj: ' + jj_err if jj_err else ''})"
    )


def fetch_origin(repo_root: Path | str, *, is_jj: bool, run=run_cmd) -> bool:
    """Best-effort refresh of the origin remote so a new worktree can be based
    on *current* upstream state rather than stale local refs.

    Never fails the caller: returns False and warns to stderr when the fetch
    fails (offline, or a local-only repo with no remote). jj is especially prone
    to silent staleness — ``jj git fetch`` advances ``main@origin`` but not the
    local ``main`` bookmark, so basing a workspace off local ``main`` keeps
    last-known state. Fetching first is what makes ``trunk()`` current.
    """
    cmd = ["jj", "--no-pager", "git", "fetch"] if is_jj else ["git", "fetch", "origin"]
    result = run(cmd, cwd=repo_root)
    if result.returncode != 0:
        label = "jj git fetch" if is_jj else "git fetch origin"
        print(
            f"WARNING: {label} failed (offline or no remote?) — basing worktree "
            f"on last-known state: {sanitize_for_output((result.stderr or '').strip()[:200])}",
            file=sys.stderr,
        )
        return False
    return True


def jj_fresh_base_args(repo_root: Path | str, *, run=run_cmd) -> list[str]:
    """Revision args for ``jj workspace add`` that base the new workspace on the
    current remote trunk.

    Returns ``["-r", "trunk()"]`` when a remote trunk resolves (so the workspace
    starts from current origin main, not the stale local working-copy parent),
    or ``[]`` for a local-only repo where ``trunk()`` collapses to ``root()`` —
    preserving jj's default base so isolated work still works offline.
    """
    result = run(
        [
            "jj",
            "--no-pager",
            "log",
            "-r",
            "trunk() ~ root()",
            "--no-graph",
            "-T",
            'change_id.short(12) ++ "\n"',
        ],
        cwd=repo_root,
    )
    if result.returncode == 0 and result.stdout.strip():
        return ["-r", "trunk()"]
    print(
        "WARNING: no remote trunk resolved (local-only repo?) — basing jj "
        "workspace on the default working-copy parent",
        file=sys.stderr,
    )
    return []


def git_fresh_base_ref(repo_root: Path | str, *, run=run_cmd) -> str:
    """The ref a new git worktree should branch from: origin's default branch
    when resolvable, else ``HEAD``.

    Resolves ``refs/remotes/origin/HEAD`` (set by clone), falling back to
    ``origin/main`` / ``origin/master``. Returns ``HEAD`` for a local-only repo
    so worktree creation still works without a remote.
    """
    head = run(
        ["git", "symbolic-ref", "--short", "--quiet", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
    )
    if head.returncode == 0 and head.stdout.strip():
        return head.stdout.strip()
    for candidate in ("origin/main", "origin/master"):
        check = run(
            ["git", "rev-parse", "--verify", "--quiet", candidate], cwd=repo_root
        )
        if check.returncode == 0 and check.stdout.strip():
            return candidate
    print(
        "WARNING: no origin default branch resolved (local-only repo?) — basing "
        "git worktree on current HEAD",
        file=sys.stderr,
    )
    return "HEAD"


def setup_beads_redirect(repo_root: Path | str, worktree_path: Path | str) -> bool:
    """Point a new workspace's ``.beads/`` at the main repo's beads database.

    jj workspaces are not git worktrees, so bd's git common-directory
    discovery does not apply: the workspace's checked-out ``.beads/`` (tracked
    config files, no database) resolves as a standalone workspace and bd
    commands fail there. bd's documented mechanism for sharing a database is
    an untracked ``.beads/redirect`` file containing a single path to the
    shared ``.beads`` directory; relative paths resolve from the workspace
    root.

    Never fails the caller: returns False and warns to stderr when the
    redirect cannot be written. No-op (returns False, no warning) when the
    main repo has no ``.beads`` directory.
    """
    repo_root = Path(repo_root)
    worktree_path = Path(worktree_path)
    main_beads = repo_root / ".beads"
    if not main_beads.is_dir():
        return False
    target = os.path.relpath(main_beads, worktree_path)
    worktree_beads = worktree_path / ".beads"
    try:
        worktree_beads.mkdir(mode=0o700, exist_ok=True)
        (worktree_beads / "redirect").write_text(target + "\n")
    except OSError as exc:
        print(
            f"WARNING: failed to write .beads/redirect in "
            f"'{sanitize_for_output(str(worktree_path))}' — bd commands in this "
            f"worktree will not resolve the shared database: "
            f"{sanitize_for_output(str(exc))}",
            file=sys.stderr,
        )
        return False
    return True


def cleanup_empty_parent(parent: Path | str) -> None:
    """Remove *parent* if it exists and is empty. Warns to stderr on failure."""
    parent = Path(parent)
    if not parent.exists():
        return
    try:
        contents = list(parent.iterdir())
    except OSError as exc:
        print(
            f"WARNING: failed to list parent directory "
            f"'{sanitize_for_output(str(parent))}': "
            f"{sanitize_for_output(str(exc))}",
            file=sys.stderr,
        )
        return
    if contents:
        return
    try:
        parent.rmdir()
    except OSError as exc:
        print(
            f"WARNING: failed to remove empty parent "
            f"'{sanitize_for_output(str(parent))}': "
            f"{sanitize_for_output(str(exc)[:500])}",
            file=sys.stderr,
        )
