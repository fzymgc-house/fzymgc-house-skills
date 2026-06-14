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
import re
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
            "cmux",
            "new-pane",
            "--type",
            "terminal",
            "--direction",
            "right",
            "--focus",
            "false",
        ]

    def parse_ref(self, spawn_stdout: str) -> str:
        # cmux 0.64.15 `new-pane` prints a status banner, not a bare ref:
        #   OK surface:26 pane:25 workspace:14
        # Extract the `surface:<N>` token the send/read calls require, rather
        # than the whole line (which cmux rejects as `Invalid surface handle`).
        # No token -> empty string; drain-worker-launch fails the launch loudly
        # on `if not ref`. See GitHub #153.
        m = re.search(r"surface:\d+", spawn_stdout)
        return m.group(0) if m else ""

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
            # -d: create the window WITHOUT switching focus to it, so the worker
            # does not hijack the operator's current window (parity with cmux's
            # --focus false and the detached new-session path below).
            return ["tmux", "new-window", "-d", "-P", "-F", "#{pane_id}"]
        return [
            "tmux",
            "new-session",
            "-d",
            "-s",
            f"drain-{drain_id}",
            "-x",
            "220",
            "-y",
            "50",
            "-P",
            "-F",
            "#{pane_id}",
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

    Precedence for ``auto`` (the session you are *inside* beats binary
    availability — picking by PATH when a session signal exists chooses the
    wrong surface):

    1. inside a tmux session (``$TMUX``) → tmux. Innermost wins on nesting:
       running ``tmux`` inside a cmux surface leaves you looking at a tmux
       pane, so ``$TMUX`` takes precedence even when a cmux marker is also set.
    2. inside a cmux surface (``$CMUX_SURFACE_ID`` / ``$CMUX_WORKSPACE_ID``)
       → cmux. Refuse if ``cmux`` is not on PATH rather than falling through
       to tmux — that would spawn tmux while the operator sits in cmux.
    3. else cmux on PATH → cmux.
    4. else tmux on PATH → tmux.
    5. else refuse.

    An explicit ``cmux``/``tmux`` always wins; any other value is an error.
    """
    if explicit == "cmux":
        return CmuxDriver()
    if explicit == "tmux":
        return TmuxDriver()
    if explicit != "auto":
        raise ValueError(f"unknown worker-type: {explicit!r} (want auto|cmux|tmux)")
    if os.environ.get("TMUX"):
        return TmuxDriver(in_tmux=True)
    if os.environ.get("CMUX_SURFACE_ID") or os.environ.get("CMUX_WORKSPACE_ID"):
        if shutil.which("cmux"):
            return CmuxDriver()
        raise RuntimeError(
            "inside a cmux surface but `cmux` is not on PATH; refusing to fall "
            "back to tmux (pass --worker-type explicitly to override)"
        )
    if shutil.which("cmux"):
        return CmuxDriver()
    if shutil.which("tmux"):
        return TmuxDriver(in_tmux=False)
    raise RuntimeError(
        "no usable multiplexer: not inside tmux or a cmux surface and neither "
        "cmux nor tmux on PATH"
    )
