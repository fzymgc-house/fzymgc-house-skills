<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-dtk; do not edit manually; use `/adr update fhsk-dtk` -->

# Gate drain worker launch behind AskUserQuestion, never auto-fire

**Date:** 2026-05-25
**Status:** Accepted
**Decision:** fhsk-dtk
**Deciders:** Sean

## Context

Launching a `claude --dangerously-skip-permissions` worker in a detached cmux pane is a high-privilege, hard-to-interrupt action. `/drain-with-worker` (and `/drain`'s inline launch branch) needed an explicit confirmation mechanism before firing. Two mechanisms were available: a shell `read` prompt in a Bash step, or Claude's `AskUserQuestion` tool.

## Decision

Every direct invocation of `/drain-with-worker` gates the launch behind an `AskUserQuestion` prompt (Launch / Cancel). The sole bypass is the `/drain` "Launch now" branch, which has already confirmed via its own `AskUserQuestion` — no flag, env var, or sentinel file encodes the pre-confirmed state. A `--dangerously-skip-permissions` worker is never auto-fired silently.

## Rationale

- A privileged auto-launched worker must never fire without operator consent — this is a correctness constraint, not a nicety.
- `AskUserQuestion` is reliable in every Claude execution context and renders as a structured choice; a Bash `read` inside prompt-expanded command execution has no interactive stdin and can hang or be silently skipped.
- The pre-confirmed bypass is auditable via the allowed-tools contract (only `/drain`'s inline branch qualifies), not via a fragile runtime signal.

## Alternatives Considered

**Shell `read` prompt (rejected):** familiar pattern, no special tool — but unreliable inside non-interactive prompt-expanded command execution; can hang on absent stdin or be skipped.

**AskUserQuestion confirm gate (chosen):** structured UI choice, never silently skipped, works in all Claude contexts; options make intent explicit. Cost: `AskUserQuestion` must appear in `allowed-tools` for every command that can trigger launch.

## Consequences

- Positive: no silent auto-launch of a privileged worker; the bypass path is auditable (only `/drain`'s inline launch branch).
- Negative: `AskUserQuestion` must be in `allowed-tools` for `drain.md` and `drain-with-worker.md`; omitting it blocks at launch time.
- Neutral: consistent with how `/drain` already gates state transitions.
