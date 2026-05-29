<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-57f; do not edit manually; use `/adr update fhsk-57f` -->

# Package handoff create and resume as one conditional-workflow skill

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-57f
**Deciders:** Sean Brandt (@seanb4t)

## Context

The handoff feature requires two distinct flows (create at session end, resume at session start) that share a body-schema reference. Three packaging options: one skill with conditional modes, two single-purpose skills, or evolving handoff-prompt for create plus adding a resume command.

## Decision

Implement one 'handoff' skill with conditional create/resume modes sharing a single body-schema reference file; expose /handoff and /handoff-resume as thin entry-point commands; redirect handoff-prompt to the new skill without deleting it.

## Rationale

- The two modes are tightly coupled through the shared body schema; splitting them would duplicate or externally coordinate that schema.
- The conditional-workflow pattern is an established repo best practice.
- Preserving handoff-prompt as a redirect (not deleting) respects existing references and muscle memory, and keeps its no-bd degraded-mode value.

## Alternatives Considered

- **Two single-purpose skills** — rejected: duplicates the body schema or needs external coordination; doubles files for a tightly-coupled pair.
- **Evolve handoff-prompt for create + add only a resume command** — rejected: splits a unified unit, leaves create under the misleading name 'handoff-prompt', murky supersession.

## Consequences

- Positive: body schema has exactly one authoritative location; contributors find both modes in one place as a lifecycle pair; handoff-prompt redirect avoids broken references.
- Negative: SKILL.md is more complex than a single-mode skill and must stay under the 500-line best-practice limit.
- Neutral: skills auto-discover (no plugin.json enumeration); commands are not Codex-wrapped (consistent with drain).
