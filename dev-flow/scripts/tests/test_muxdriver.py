"""Tests for _muxdriver.detect() multiplexer selection.

Pure-logic tests: no multiplexer is spawned. The environment markers
($TMUX for tmux, CMUX_SURFACE_ID / CMUX_WORKSPACE_ID for cmux) and the
PATH probe (shutil.which) are both stubbed so the precedence table is
asserted deterministically.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _muxdriver
from _muxdriver import CmuxDriver, TmuxDriver, detect

# Every env var detect() may consult; cleared before each case.
_MARKERS = ("TMUX", "CMUX_SURFACE_ID", "CMUX_WORKSPACE_ID")


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch):
    """Return a setter that controls session markers and PATH availability.

    Usage::

        env(markers={"TMUX": "/tmp/x,1,0"}, on_path={"cmux", "tmux"})
    """
    for name in _MARKERS:
        monkeypatch.delenv(name, raising=False)

    def _set(markers: dict[str, str] | None = None, on_path: set[str] | None = None):
        for name, value in (markers or {}).items():
            monkeypatch.setenv(name, value)
        available = on_path or set()
        monkeypatch.setattr(
            _muxdriver.shutil,
            "which",
            lambda name: f"/usr/bin/{name}" if name in available else None,
        )

    return _set


# --- explicit choice always wins ------------------------------------------


def test_explicit_cmux(env):
    env(markers={"TMUX": "/tmp/s,1,0"}, on_path={"tmux"})  # hostile env ignored
    assert isinstance(detect("cmux"), CmuxDriver)


def test_explicit_tmux(env):
    env(markers={"CMUX_SURFACE_ID": "surface:4"}, on_path={"cmux"})
    assert isinstance(detect("tmux"), TmuxDriver)


def test_explicit_unknown_raises(env):
    env(on_path={"cmux", "tmux"})
    with pytest.raises(ValueError):
        detect("screen")


# --- auto: session markers beat PATH availability -------------------------


def test_auto_in_tmux_session_picks_tmux_even_with_cmux_on_path(env):
    env(markers={"TMUX": "/tmp/s,1,0"}, on_path={"cmux", "tmux"})
    mux = detect("auto")
    assert isinstance(mux, TmuxDriver)
    assert mux._in_tmux is True


def test_auto_in_cmux_surface_picks_cmux_even_with_tmux_on_path(env):
    # The "vice versa" case: a cmux surface must not yield tmux just because
    # the tmux binary is available. cmux is detected by session, not PATH.
    env(markers={"CMUX_SURFACE_ID": "surface:4"}, on_path={"cmux", "tmux"})
    assert isinstance(detect("auto"), CmuxDriver)


def test_auto_cmux_workspace_marker_also_signals_cmux(env):
    env(markers={"CMUX_WORKSPACE_ID": "workspace:2"}, on_path={"cmux", "tmux"})
    assert isinstance(detect("auto"), CmuxDriver)


def test_auto_nested_both_markers_tmux_wins(env):
    # Realistic nesting is `tmux` launched inside a cmux surface: the operator
    # is looking at a tmux pane, so innermost ($TMUX) wins.
    env(
        markers={"TMUX": "/tmp/s,1,0", "CMUX_SURFACE_ID": "surface:4"},
        on_path={"cmux", "tmux"},
    )
    mux = detect("auto")
    assert isinstance(mux, TmuxDriver)
    assert mux._in_tmux is True


def test_auto_in_cmux_surface_but_cmux_missing_refuses(env):
    # Inside a cmux surface with no cmux binary, refuse loudly rather than
    # silently spawning tmux (which would re-introduce the bug).
    env(markers={"CMUX_SURFACE_ID": "surface:4"}, on_path={"tmux"})
    with pytest.raises(RuntimeError):
        detect("auto")


# --- auto: no session markers -> PATH fallback ----------------------------


def test_auto_no_markers_prefers_cmux_on_path(env):
    env(on_path={"cmux", "tmux"})
    assert isinstance(detect("auto"), CmuxDriver)


def test_auto_no_markers_falls_back_to_tmux(env):
    env(on_path={"tmux"})
    mux = detect("auto")
    assert isinstance(mux, TmuxDriver)
    assert mux._in_tmux is False


def test_auto_no_multiplexer_refuses(env):
    env(on_path=set())
    with pytest.raises(RuntimeError):
        detect("auto")
