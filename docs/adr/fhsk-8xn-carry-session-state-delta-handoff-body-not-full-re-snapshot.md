<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-8xn; do not edit manually; use `/adr update fhsk-8xn` -->

# Carry session-state delta in the handoff body, not a full re-snapshot

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-8xn
**Deciders:** Sean Brandt (@seanb4t)

## Context

A handoff bead must convey enough context for a cold session to resume work. Two approaches: re-snapshot all relevant state (spec, plan, work-bead contents) into the handoff body, or carry only the delta the source beads and specs do not already record, referencing sources via bd dep related edges.

## Decision

The handoff body carries only the session-state delta (left-off state, in-flight work, VCS snapshot, gotchas, next step, open questions) and references source beads via bd dep related edges; sections are omitted when not applicable. When 0 source beads exist, those sections carry full standalone context.

## Rationale

- Re-snapshots drift immediately; the handoff becomes a stale copy rather than a live pointer.
- Source beads are already the authority for their own type, status, and description; duplicating that is a maintenance burden.
- bd dep related edges produce bidirectional cross-links in bd show, giving resume access to source context without copying it.
- Omitting empty sections keeps the body honest about what the session produced.

## Alternatives Considered

- **Full re-snapshot in the handoff body** — rejected: body immediately becomes a stale duplicate of the work bead and spec; updates to the source are not reflected; the 0-source case is indistinguishable from the N-source case.

## Consequences

- Positive: handoff body stays accurate because it only asserts what source beads cannot know; resume flow is explicit (load handoff, follow related edges, load sources); schema scales (0-source = full context, N-source = delta only).
- Negative: resume must follow edges and read source beads, not just a single bd-show on the handoff; a deleted source bead leaves a dangling edge (partially mitigated by the stale-handoff check).
- Neutral: stale-handoff detection is an explicit resume-flow step.
