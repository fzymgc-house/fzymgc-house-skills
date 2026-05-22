<!-- markdownlint-disable MD013 -->

# Use /goal over /loop for autonomous bead-queue drains

**Date:** 2026-05-22
**Status:** Accepted
**Decision:** fhsk-thw
**Deciders:** Sean Brandt (@seanb4t)

## Context

dev-flow needed an autonomous harness to iterate over a queue of bd beads without manual operator re-invocation. Two Claude Code primitives were available: `/loop` (timer-based polling) and `/goal` (Stop-hook driven, session-resident iteration). The holomush era used `/loop autonomous` with a ~1500-word self-evolving prompt across 26 invocations in a single session, accumulating "lessons" by hand-editing the prompt body between iterations (prompt drift).

## Decision

Adopt `/goal` as the sole autonomous-drain primitive in dev-flow. `/loop` is explicitly not referenced as a drain alternative; its timer-polling purpose is left unchanged for external-state polling use cases.

## Rationale

- Verified via Claude Code binary strings (v2.1.148): `/goal` registers a Stop hook with `activeGoal` state and `goal_status` attachment — purpose-built for multi-iteration bounded loops with a model-evaluated sentinel.
- holomush transcript (`f3a83fe5`) demonstrated `/loop autonomous` produces prompt drift: lessons required hand-editing the prompt body between iterations (e.g., iter 6 added "jj-new-first discipline" after T30's jj-squash failure).
- `/goal` eliminates prompt drift by keeping the iteration body constant; lessons are routed through bd notes on the per-run drain bead instead.
- `/loop` has a legitimate distinct purpose (external-state polling on a timer) that must not be conflated with bead-queue drains.

## Alternatives Considered

**`/loop autonomous` (timer-based polling loop) — rejected.** Strengths: already discoverable in dev-flow's skill list (which is why the model reached for it in holomush); supports configurable sleep interval. Weaknesses: designed for polling external state on a timer, not iterating a queue; produces per-iteration prompt cold-start cost (each wake re-pays the cache); the holomush pattern required manual prompt edits between iterations (prompt drift); `/loop`'s real niche is distinct from bead-queue drains.

## Consequences

**Positive.** Per-iteration token cost amortized inside one cached session. Prompt body is stable; no drift between iterations. Clean sentinel detection via bd queries; `/goal` termination is model-driven.

**Negative.** No Codex or non-Claude-Code harness support; manual fallback recipe required (documented in the skill). Trust + hooks must be enabled in the workspace; adds a pre-flight gate. Orchestrator must explicitly call `/goal clear` on halt rather than letting the loop expire.

**Neutral.** `/loop autonomous` is preserved as-is for its timer-polling niche; no other dev-flow assets are affected by this decision.

## References

- Spec: `docs/superpowers/specs/2026-05-22-drain-skill-design.md`
- Design bead: `fhsk-a67`
- Grounding traces: binary-strings extraction of `/goal` from `/Users/sean/.local/share/claude/versions/2.1.148`; holomush transcript `f3a83fe5` analysis recorded on `fhsk-a67`.
