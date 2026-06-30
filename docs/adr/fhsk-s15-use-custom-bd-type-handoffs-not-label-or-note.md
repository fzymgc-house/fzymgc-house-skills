---
title: "Use a custom bd type for handoffs, not a label or note"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-s15; do not edit manually; use `/adr update fhsk-s15` -->

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-s15
**Deciders:** Sean Brandt (@seanb4t)

## Context

The prior handoff-prompt skill was ephemeral: nothing persisted, handoffs were not queryable, and the briefing was lost if not pasted immediately. A durable, queryable structure was needed. Three structural options: a custom bd type, a label on the work bead, or a structured note on the work bead.

## Decision

Register a custom bd type named 'handoff' (idempotently, mirroring the drain type pattern) so handoffs are independently queryable, have a clear open/closed lifecycle, and exist as a distinct entity from the work beads they reference.

## Rationale

- bd --type filter is reliable; --label-pattern is a documented no-op in bd <=1.0.4 (fhsk-4ut).
- A distinct type gives handoffs an open/closed lifecycle without repurposing the work bead's lifecycle.
- The 0-source-bead (untracked exploration) case requires a standalone entity with no dependency on a work bead.
- Conceptual separation: a handoff is a baton about work, not the work itself.

## Alternatives Considered

- **Label on the work bead** — rejected: not independently queryable (--label-pattern no-op), no distinct lifecycle, cannot represent the 0-source case, conflates baton with work.
- **Structured note on the work bead** — rejected: not queryable, no lifecycle, breaks the 0-source case, no pending/consumed state.

## Consequences

- Positive: bd list -t handoff --status open enumerates pending batons reliably; closed handoffs form a free session-boundary history; mirrors the already-understood drain registration.
- Negative: type registration is a hard pre-flight (unregistered type fails loudly on bd create); adds a new entity class contributors must understand.
- Neutral: registration is idempotent.
