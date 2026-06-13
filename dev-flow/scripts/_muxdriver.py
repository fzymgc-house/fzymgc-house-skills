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
