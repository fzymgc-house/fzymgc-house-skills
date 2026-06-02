"""Tests for memory-curator scope derivation."""

from __future__ import annotations

import sys
from pathlib import Path


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
    assert (
        scope._normalize_remote("git@github.com:org/repo.git") == "github.com/org/repo"
    )
    assert (
        scope._normalize_remote("https://github.com/org/repo.git")
        == "github.com/org/repo"
    )
    assert (
        scope._normalize_remote("ssh://git@github.com/org/repo")
        == "github.com/org/repo"
    )


def test_jj_repo_uses_jj_remote_never_git(monkeypatch):
    fake = make_fake_run(
        [
            (["jj", "--no-pager", "root"], "/repo"),
            (
                ["jj", "--no-pager", "git", "remote", "list"],
                "origin git@github.com:org/repo.git",
            ),
        ]
    )
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/repo") == "github.com/org/repo"
    assert not any(a and a[0] == "git" for a in fake.calls)


def test_git_repo_uses_origin(monkeypatch):
    fake = make_fake_run(
        [
            (["jj", "--no-pager", "root"], None),
            (["git", "remote", "get-url", "origin"], "https://github.com/org/repo.git"),
        ]
    )
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/x") == "github.com/org/repo"


def test_remoteless_jj_default_workspace_uses_basename(monkeypatch, tmp_path):
    (tmp_path / ".jj" / "repo").mkdir(parents=True)  # default ws: repo is a dir
    fake = make_fake_run(
        [
            (["jj", "--no-pager", "root"], str(tmp_path)),
            (["jj", "--no-pager", "git", "remote", "list"], ""),
        ]
    )
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id(str(tmp_path)) == tmp_path.name


def test_remoteless_jj_secondary_workspace_resolves_pointer(monkeypatch, tmp_path):
    primary = tmp_path / "myrepo"
    (primary / ".jj").mkdir(parents=True)
    ws = tmp_path / "myrepo_worktrees" / "feat"
    (ws / ".jj").mkdir(parents=True)
    (ws / ".jj" / "repo").write_text("../../../myrepo/.jj/repo")  # pointer file
    fake = make_fake_run(
        [
            (["jj", "--no-pager", "root"], str(ws)),
            (["jj", "--no-pager", "git", "remote", "list"], ""),
        ]
    )
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id(str(ws)) == "myrepo"


def test_no_repo_returns_none(monkeypatch):
    fake = make_fake_run([])  # everything returns None
    monkeypatch.setattr(scope, "_run", fake)
    assert scope._repo_id("/nowhere") is None
