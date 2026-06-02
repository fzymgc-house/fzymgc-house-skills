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
        proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _normalize_remote(url: str) -> str:
    """git@github.com:org/repo.git -> github.com/org/repo."""
    u = url.strip()
    for scheme in ("https://", "http://", "ssh://", "git://"):
        if u.startswith(scheme):
            u = u[len(scheme) :]
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
        origin = _origin_from_jj(
            _run(["jj", "--no-pager", "git", "remote", "list"], cwd)
        )
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


def _workspace(cwd: str) -> str | None:
    """Per-workspace name for the overlay; None for the primary checkout."""
    if _run(["jj", "--no-pager", "root"], cwd) is not None:
        wc = _run(
            [
                "jj",
                "--no-pager",
                "log",
                "-r",
                "@",
                "--no-graph",
                "-T",
                "working_copies",
            ],
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
