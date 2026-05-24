<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-0o2; do not edit manually; use `/adr update fhsk-0o2` -->

# Split drain harness into formula, command, and skill

**Date:** 2026-05-24
**Status:** Superseded by fhsk-eqt
**Decision:** fhsk-0o2
**Deciders:** Sean Brandt (@seanb4t)

## Context

The `/drain` harness must carry three distinct payloads: scaffolding for the per-run drain bead (typed, titled, labeled, var-substituted from operator args), the `/goal` Stop-hook iteration body (executed on every Stop event), and the canonical reference for halt / lesson / sentinel semantics (read by the operator or orchestrator when needed). Three consolidation points were considered: put everything in the formula, put everything in the skill, or split across three files.

## Decision

Three-piece split: `dev-flow/.beads/formulas/formula-drain.toml` (bead scaffolding only), `dev-flow/commands/drain.md` (operator entry point AND the `/goal` Stop-hook iteration body), `dev-flow/skills/draining-beads/SKILL.md` (canonical reference, read-only). The iteration body lives in the slash command body so it is part of the cached session prompt — no per-iteration tool calls or file reads.

## Rationale

- Per-iteration I/O cost is the primary optimization target inside a long `/goal` session.
- Keeping the iteration body in the slash command means it is parsed once at session start and cached — no additional tool calls per Stop-hook firing.
- The formula stays small (TOML scaffolding only) and version-controlled independently of iteration logic.
- The skill is stable human-readable reference without execution coupling; it is not invoked per iteration.

## Alternatives Considered

**Iteration body in the formula step description — rejected.** Strengths: single source of truth; formula is the canonical artifact. Weaknesses: forces a per-iteration formula read to surface the body; adds I/O cost and latency on every Stop-hook firing. The formula system is designed for bead scaffolding, not for runtime-executed prose.

**Iteration body in the skill SKILL.md — rejected.** Strengths: discoverable via the skill index; co-locates semantics and execution. Weaknesses: forces a per-iteration `Skill` tool call; contradicts the skill's role as a read-reference rather than an execution target.

## Consequences

**Positive.** Zero per-iteration I/O overhead for the iteration body. Formula file stays small and version-controlled. Skill remains a stable reference. Each piece has a single responsibility.

**Negative.** Iteration logic is only in the slash command body, not surfaced by `bd formula show`. Three files must be kept consistent if halt-condition semantics change (mitigated by the spec being the canonical source of truth).

**Neutral.** Skill sections are authoritatively enumerated in the spec (overview, when-to-use, sentinel, halt, lessons, edge-cases, references); implementer controls ordering.

## References

- Superseded by: fhsk-eqt
