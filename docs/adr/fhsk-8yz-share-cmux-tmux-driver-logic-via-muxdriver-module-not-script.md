<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-8yz; do not edit manually; use `/adr update fhsk-8yz` -->

# Share cmux/tmux driver logic via a _muxdriver module, not script duplication

**Date:** 2026-06-13
**Status:** Accepted
**Decision:** fhsk-8yz
**Deciders:** Sean Brandt

## Context

Both `drain-worker-launch` and the existing `drain-watchdog` need cmux and tmux verb construction. These are `uv run --script` (PEP 723) entrypoints with no package manager. The module-sharing mechanism for stdlib-only uv scripts is not prescribed by any existing repo convention. The fork: duplicate the four-verb driver table into each script, or extract a shared module imported via `sys.path` insertion.

## Decision

`_muxdriver.py` is a plain stdlib module (no shebang, no PEP 723 header) in `dev-flow/scripts/`; both entrypoint scripts run `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `import _muxdriver`. It exposes a `Multiplexer` ABC, `CmuxDriver`, `TmuxDriver`, and `detect()`, all pure argv construction.

## Rationale

- Argv construction is the one thing both scripts must agree on exactly — duplication is a correctness hazard (split-brain multiplexer protocol).
- `Path(__file__).resolve()` is reliable for `uv run --script` entrypoints (kernel exec resolves the shebang to an absolute path).
- Pure argv construction enables unit tests that assert driver output without spawning a multiplexer.
- The stdlib-only rule is preserved: `_muxdriver` imports nothing outside the stdlib; it is shared source, not a dependency.

## Alternatives Considered

**Duplicate the driver table into each script** (rejected) — self-contained, no import machinery, but two copies must stay byte-identical; a verb change missing one script yields a split-brain protocol.

**Extract `_muxdriver.py` imported via `sys.path` insertion** (chosen) — single source of truth, pure and unit-testable, `detect()` precedence in one place. Trade-off: the module must carry no PEP 723 header/shebang and is not independently runnable; `sys.path` mutation is the accepted tool for this uv-scripts layout.

## Consequences

**Positive:** single authoritative home for all cmux/tmux verbs; multiplexer argv is unit-testable without a live multiplexer; a third multiplexer is one driver implementation, not N script edits.

**Negative:** `_muxdriver.py` must not get a PEP 723 header or shebang (not independently runnable); `sys.path` mutation is a known anti-pattern, used deliberately here.

**Neutral:** the `detect()` precedence ($TMUX→tmux; cmux on PATH→cmux; tmux on PATH→tmux; else refuse) is encoded once and shared.
