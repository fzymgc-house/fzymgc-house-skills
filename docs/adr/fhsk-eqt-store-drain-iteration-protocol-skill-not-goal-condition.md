---
title: "Store the drain iteration protocol in the skill, not the /goal condition"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-eqt; do not edit manually; use `/adr update fhsk-eqt` -->

**Date:** 2026-05-24
**Status:** Accepted
**Decision:** fhsk-eqt
**Deciders:** Sean Brandt (@seanb4t)

## Context

The original `/drain` harness embedded the 12-step iteration body inside the `/goal` condition string, justified by prompt caching (ADR fhsk-0o2). But `/goal`'s condition is a checkable predicate with a documented 4,000-character cap, and the body measured 3,857 chars before variable substitution — real runs have silently approached/exceeded it, risking truncation of the tail steps (close / rejection handling / VCS verify / re-fire) and muddying the evaluator's view of the sentinel.

## Decision

Move the 12-step iteration protocol into the `dev-flow:draining-beads` skill. The `/goal` condition becomes a short cold-boot pointer plus the sentinel predicate (target < 1,500 chars). A gitignored `.drain/<drain-id>.md` file (Approach B) is held in reserve pending an empirical cold-boot spike.

## Rationale

- The 4K cap makes the embedded-body approach a correctness hazard (silent truncation), not a style choice.
- The skill loads once per worker session, so the per-iteration I/O cost that drove fhsk-0o2 does not apply to a one-time skill load.
- Clean separation of carrier roles: condition = boot pointer + predicate; bead = durable state; skill = protocol.

## Alternatives Considered

- **Embed the iteration body in the `/goal` condition (fhsk-0o2's choice):** cached with the command, zero per-iteration tool calls — but bounded by the 4K cap, already at 3,857 chars, risking silent truncation. Rejected.
- **Materialize `.drain/<drain-id>.md` (Approach B):** deterministic even if skill auto-load is unreliable; controller and worker share the workspace — but adds a file lifecycle + gitignore entry. Held as fallback pending the spike.

## Consequences

- Positive: the condition stays well under the cap (regression-tested < 1,500 chars); the protocol is discoverable and editable in one place.
- Negative: cold-boot reliability of skill invocation is unproven — an empirical spike gates Approach A vs B.
- Neutral: the Approach B fallback is preserved in the spec; implementation deferred to the spike result.

## References

- Supersedes: fhsk-0o2
