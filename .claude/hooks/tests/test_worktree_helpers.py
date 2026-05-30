"""Tests for worktree_helpers.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worktree_helpers import (
    cleanup_empty_parent,
    detect_repo_root,
    fetch_origin,
    git_fresh_base_ref,
    jj_fresh_base_args,
    run_cmd,
    sanitize_for_output,
    validate_safe_name,
)


def _cp(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Build a fake CompletedProcess for stubbing the `run` dependency."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# sanitize_for_output
# ---------------------------------------------------------------------------


class TestSanitizeForOutput:
    def test_plain_text_unchanged(self):
        assert sanitize_for_output("hello world") == "hello world"

    def test_preserves_tab(self):
        assert sanitize_for_output("a\tb") == "a\tb"

    def test_preserves_newline(self):
        assert sanitize_for_output("a\nb") == "a\nb"

    def test_preserves_cr(self):
        assert sanitize_for_output("a\rb") == "a\rb"

    def test_strips_nul(self):
        assert sanitize_for_output("a\x00b") == "ab"

    def test_strips_backspace(self):
        assert sanitize_for_output("a\x08b") == "ab"

    def test_strips_vertical_tab(self):
        assert sanitize_for_output("a\x0bb") == "ab"

    def test_strips_form_feed(self):
        assert sanitize_for_output("a\x0cb") == "ab"

    def test_strips_so(self):
        # 0x0E = Shift Out
        assert sanitize_for_output("a\x0eb") == "ab"

    def test_strips_unit_separator(self):
        # 0x1F = Unit Separator (last C0 before space)
        assert sanitize_for_output("a\x1fb") == "ab"

    def test_strips_del(self):
        assert sanitize_for_output("a\x7fb") == "ab"

    def test_strips_c1_controls(self):
        # 0x80-0x9F
        assert sanitize_for_output("a\x80b\x9fc") == "abc"

    def test_preserves_space(self):
        # 0x20 = space, should be kept
        assert sanitize_for_output("a b") == "a b"

    def test_empty_string(self):
        assert sanitize_for_output("") == ""

    def test_unicode_preserved(self):
        assert sanitize_for_output("héllo") == "héllo"


# ---------------------------------------------------------------------------
# validate_safe_name
# ---------------------------------------------------------------------------


class TestValidateSafeName:
    def test_valid_simple(self):
        validate_safe_name("my-feature", "branch")  # must not raise

    def test_valid_alphanumeric(self):
        validate_safe_name("abc123", "name")

    def test_valid_with_underscore(self):
        validate_safe_name("my_branch", "branch")

    def test_valid_with_hyphen(self):
        validate_safe_name("my-branch", "branch")

    def test_valid_with_dot(self):
        validate_safe_name("v1.2.3", "version")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_safe_name("", "branch")

    def test_leading_dot_raises(self):
        with pytest.raises(ValueError, match="no leading dot"):
            validate_safe_name(".hidden", "branch")

    def test_trailing_dot_raises(self):
        with pytest.raises(ValueError, match="trailing dot"):
            validate_safe_name("name.", "branch")

    def test_double_dot_raises(self):
        with pytest.raises(ValueError, match="double-dot"):
            validate_safe_name("a..b", "branch")

    def test_slash_raises(self):
        with pytest.raises(ValueError):
            validate_safe_name("a/b", "branch")

    def test_space_raises(self):
        with pytest.raises(ValueError):
            validate_safe_name("a b", "branch")

    def test_special_char_raises(self):
        with pytest.raises(ValueError):
            validate_safe_name("a$b", "branch")

    def test_label_appears_in_error(self):
        with pytest.raises(ValueError, match="mybranch"):
            validate_safe_name("", "mybranch")


# ---------------------------------------------------------------------------
# run_cmd
# ---------------------------------------------------------------------------


class TestRunCmd:
    def test_success(self, tmp_path):
        result = run_cmd(["echo", "hello"], cwd=tmp_path)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_failure_does_not_raise(self, tmp_path):
        result = run_cmd(["false"], cwd=tmp_path)
        assert result.returncode != 0

    def test_captures_stdout(self, tmp_path):
        result = run_cmd(["echo", "test output"], cwd=tmp_path)
        assert result.stdout.strip() == "test output"

    def test_captures_stderr(self, tmp_path):
        result = run_cmd(
            ["python3", "-c", "import sys; sys.stderr.write('err\\n')"],
            cwd=tmp_path,
        )
        assert "err" in result.stderr


# ---------------------------------------------------------------------------
# detect_repo_root
# ---------------------------------------------------------------------------


class TestDetectRepoRoot:
    def test_detects_git_repo(self, git_repo):
        root = detect_repo_root(cwd=git_repo)
        assert root == git_repo

    @pytest.mark.skipif(
        not __import__("shutil").which("jj"), reason="jj is not installed"
    )
    def test_detects_jj_repo(self, jj_repo):
        root = detect_repo_root(cwd=jj_repo)
        assert root == jj_repo

    def test_detects_from_subdirectory(self, git_repo):
        subdir = git_repo / "subdir"
        subdir.mkdir()
        root = detect_repo_root(cwd=subdir)
        assert root == git_repo

    def test_raises_outside_repo(self, tmp_path):
        # tmp_path is not a git repo; ensure jj is not available or also fails
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="not inside a git/jj repository"):
                detect_repo_root(cwd=tmp_path)

    def test_raises_when_both_fail(self, tmp_path):
        # Simulate git failing and jj failing
        with patch("worktree_helpers.shutil.which", return_value="/usr/bin/jj"):
            with patch("worktree_helpers.run_cmd") as mock_run:
                mock_run.return_value = type(
                    "R", (), {"returncode": 1, "stdout": "", "stderr": "no repo"}
                )()
                with pytest.raises(
                    RuntimeError, match="not inside a git/jj repository"
                ):
                    detect_repo_root(cwd=tmp_path)

    def test_warns_on_git_empty_stdout(self, tmp_path, capsys):
        """When git rev-parse succeeds but returns empty stdout, warns and tries jj."""
        with patch("worktree_helpers.run_cmd") as mock_run:
            # First call (git): success but empty stdout
            # Second call (jj): also fails
            mock_run.side_effect = [
                type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                type("R", (), {"returncode": 1, "stdout": "", "stderr": "no repo"})(),
            ]
            with patch("worktree_helpers.shutil.which", return_value="/usr/bin/jj"):
                with pytest.raises(RuntimeError):
                    detect_repo_root(cwd=tmp_path)
        captured = capsys.readouterr()
        assert "git rev-parse succeeded but returned unusable path" in captured.err


# ---------------------------------------------------------------------------
# cleanup_empty_parent
# ---------------------------------------------------------------------------


class TestCleanupEmptyParent:
    def test_removes_empty_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        cleanup_empty_parent(empty_dir)
        assert not empty_dir.exists()

    def test_skips_nonexistent_dir(self, tmp_path):
        nonexistent = tmp_path / "nonexistent"
        cleanup_empty_parent(nonexistent)  # should not raise

    def test_does_not_remove_nonempty_dir(self, tmp_path):
        nonempty = tmp_path / "nonempty"
        nonempty.mkdir()
        (nonempty / "file.txt").write_text("data")
        cleanup_empty_parent(nonempty)
        assert nonempty.exists()

    def test_warns_on_rmdir_failure(self, tmp_path, capsys):
        empty_dir = tmp_path / "dir"
        empty_dir.mkdir()
        with patch.object(Path, "rmdir", side_effect=OSError("permission denied")):
            cleanup_empty_parent(empty_dir)
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "permission denied" in captured.err

    def test_accepts_string_path(self, tmp_path):
        empty_dir = tmp_path / "str_dir"
        empty_dir.mkdir()
        cleanup_empty_parent(str(empty_dir))
        assert not empty_dir.exists()


# ---------------------------------------------------------------------------
# fetch_origin — refresh upstream before worktree creation (best-effort)
# ---------------------------------------------------------------------------


class TestFetchOrigin:
    def test_jj_issues_jj_git_fetch_and_succeeds(self):
        calls = []

        def fake_run(args, *, cwd):
            calls.append(args)
            return _cp(0)

        assert fetch_origin("/repo", is_jj=True, run=fake_run) is True
        assert calls == [["jj", "--no-pager", "git", "fetch"]]

    def test_git_issues_git_fetch_origin(self):
        calls = []

        def fake_run(args, *, cwd):
            calls.append(args)
            return _cp(0)

        fetch_origin("/repo", is_jj=False, run=fake_run)
        assert calls == [["git", "fetch", "origin"]]

    def test_failure_warns_and_returns_false_not_raises(self, capsys):
        # A failed fetch (offline / no remote) must NOT abort worktree creation.
        def fake_run(args, *, cwd):
            return _cp(1, stderr="fatal: no remote")

        assert fetch_origin("/repo", is_jj=True, run=fake_run) is False
        assert "WARNING" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# jj_fresh_base_args — base a jj workspace on current remote trunk
# ---------------------------------------------------------------------------


class TestJjFreshBaseArgs:
    def test_remote_trunk_present_bases_on_trunk(self):
        def fake_run(args, *, cwd):
            return _cp(0, stdout="abcdef012345\n")

        assert jj_fresh_base_args("/repo", run=fake_run) == ["-r", "trunk()"]

    def test_no_remote_trunk_falls_back_to_default_and_warns(self, capsys):
        # trunk() collapses to root() in a local-only repo -> empty result.
        def fake_run(args, *, cwd):
            return _cp(0, stdout="\n")

        assert jj_fresh_base_args("/repo", run=fake_run) == []
        assert "WARNING" in capsys.readouterr().err

    def test_command_error_falls_back_to_default(self):
        def fake_run(args, *, cwd):
            return _cp(1, stderr="boom")

        assert jj_fresh_base_args("/repo", run=fake_run) == []


# ---------------------------------------------------------------------------
# git_fresh_base_ref — base a git worktree on origin's default branch
# ---------------------------------------------------------------------------


class TestGitFreshBaseRef:
    def test_symbolic_ref_resolves_origin_default(self):
        def fake_run(args, *, cwd):
            if "symbolic-ref" in args:
                return _cp(0, stdout="origin/main\n")
            return _cp(1)

        assert git_fresh_base_ref("/repo", run=fake_run) == "origin/main"

    def test_falls_back_to_origin_main_when_no_symbolic_ref(self):
        def fake_run(args, *, cwd):
            if "symbolic-ref" in args:
                return _cp(1)
            if args[-1] == "origin/main":  # rev-parse --verify origin/main
                return _cp(0, stdout="deadbeef\n")
            return _cp(1)

        assert git_fresh_base_ref("/repo", run=fake_run) == "origin/main"

    def test_falls_back_to_head_and_warns_when_no_remote(self, capsys):
        def fake_run(args, *, cwd):
            return _cp(1)

        assert git_fresh_base_ref("/repo", run=fake_run) == "HEAD"
        assert "WARNING" in capsys.readouterr().err
