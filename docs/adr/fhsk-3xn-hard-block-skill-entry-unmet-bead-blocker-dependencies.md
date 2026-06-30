---
title: "Hard-block skill entry on unmet bead blocker dependencies"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-3xn; do not edit manually; use `/adr update fhsk-3xn` -->

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-3xn
**Deciders:** Sean Brandt

## Context

Phase 0 of `solving-a-bead` checks whether any blocker dependencies are open before the skill proceeds. Two responses to unmet blockers were considered: abort with a hard error listing the blocking bead IDs, or warn and allow the operator to proceed anyway. This choice defines the trust boundary at the skill's entry gate and determines whether the skill's correctness guarantees are conditional or absolute.

## Decision

Phase 0 hard-blocks and aborts if any `blocks`-typed dependency of the target bead is not in `closed` status, listing the offending bead IDs so the operator knows exactly what to finish first.

## Rationale

- A bead dependency graph expresses correctness preconditions, not scheduling hints; allowing work on top of unmet blockers produces fixes that may be invalidated later.
- The skill's guarantee — isolated, root-caused, TDD fix — is only meaningful if the work's foundations are confirmed complete.
- Listing blocker IDs makes the abort actionable rather than opaque.
- Consistent with Phase 0's general philosophy: all validation gates are hard failures, not soft warnings.

## Alternatives Considered

- **Warn on unmet blockers, allow proceed** (rejected): flexible and lets the operator override when a dependency is effectively resolved but not yet closed, but silently allows work on a bead whose stated prerequisites are unmet, risks invalidated downstream fixes, and erodes the dependency graph as a correctness signal.
- **Hard-block + abort, listing offending blocker IDs** (chosen): treats the dependency graph as a correctness constraint; the skill cannot be responsible for partial fixes built on unresolved foundations; listing blocker IDs gives an actionable path forward.

## Consequences

- Positive: skill correctness guarantee is unconditional — an invocation that reaches Phase 1 is known-unblocked; operators get an explicit, actionable list of what to finish before retrying; prevents wasted work on unresolved foundations.
- Negative: aborts valid sessions when a blocker is functionally resolved but not yet marked closed in bd; no override flag.
- Neutral: the `bd dep list --direction=down` default and `dependency_type=='blocks'` field are verified against bd 1.0.4; any bd schema change would require a corresponding Phase 0 update.
