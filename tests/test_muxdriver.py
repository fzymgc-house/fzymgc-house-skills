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
        "cmux",
        "send",
        "--surface",
        "surface:7",
        "hi",
    ]
    assert m.send_enter_argv("surface:7") == [
        "cmux",
        "send-key",
        "--surface",
        "surface:7",
        "Enter",
    ]
    assert m.read_screen_argv("surface:7") == [
        "cmux",
        "read-screen",
        "--surface",
        "surface:7",
    ]
    assert m.parse_ref("surface:7\n") == "surface:7"


def test_tmux_argv_construction() -> None:
    m = _load().TmuxDriver(in_tmux=True)
    assert m.name == "tmux"
    assert m.send_text_argv("%7", "hi") == ["tmux", "send-keys", "-t", "%7", "-l", "hi"]
    assert m.send_enter_argv("%7") == ["tmux", "send-keys", "-t", "%7", "Enter"]
    assert m.read_screen_argv("%7") == ["tmux", "capture-pane", "-p", "-t", "%7"]
    assert m.parse_ref("%7\n") == "%7"


def test_tmux_spawn_placement_branch() -> None:
    mod = _load()
    inside = mod.TmuxDriver(in_tmux=True).spawn_argv("ep-1")
    # -d so the worker window does not steal the operator's focus
    assert inside == ["tmux", "new-window", "-d", "-P", "-F", "#{pane_id}"]
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
    monkeypatch.setattr(
        mod.shutil, "which", lambda c: "/usr/bin/cmux" if c == "cmux" else None
    )
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
