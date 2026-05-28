<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-bj8; do not edit manually; use `/adr update fhsk-bj8` -->

# Use agent:* label as the sole subagent dispatch signal

**Date:** 2026-05-28
**Status:** Accepted
**Decision:** fhsk-bj8
**Deciders:** Sean Brandt

## Context

Three dev-flow skills (subagent-driven-development, draining-beads, handoff-prompt) read a bead "skills[]" JSON field to select subagent_type. Verified behavior: "bd create --skills" leaves the JSON skills field null and appends a "## Required Skills" block to the description. There is no skills[] array and the routing logic was unreachable. A replacement dispatch signal was needed that the Agent/Task tool can consume without erroring on an unregistered type.

## Decision

Introduce an agent:<type> bead label, resolved by a documented static known-registered set in each reader skill, with general-purpose as the unconditional fallback for absent or unrecognized values. --skills is reframed as a Required-Skills capability hint (description annotation), not a routing signal.

## Rationale

- The Agent/Task tool errors on an unregistered subagent_type, making runtime probing impossible.
- A static known-set in each reader is the only safe resolution; it makes the extension point explicit and auditable.
- The fallback guarantees no broken dispatch when a label names a not-yet-registered type.
- Parallels the existing model:<tier> label contract, keeping dispatch reasoning consistent.
- The agent:code-reviewer prohibition encodes the orchestrator/implementer boundary, preventing misuse of review-pr orchestrator agents as implementers.

## Alternatives Considered

- --skills flag / skills[] JSON field: rejected — skills[] is always null at runtime; --skills is a description hint, not a structured dispatch signal; the routing code is unreachable.
- Runtime probe of registered subagent types: rejected — the Agent/Task tool errors on an unregistered subagent_type and there is no introspection API to enumerate registered types at prompt-evaluation time.
- agent:<type> label + documented static known-registered set + general-purpose fallback (chosen): safe, explicit, parallels model:<tier>, forward-compatible.

## Consequences

Positive: dispatch is reachable and correct; the unreachable skills[] branch is eliminated; forward-looking agent:* annotations survive subagent-type registration without bead updates; new types are added by extending the readers known-set with no bead schema change.
Negative: each reader maintains its own copy of the known-registered set (divergence risk if not kept in sync); today all agent:* values resolve to general-purpose so the label carries no current dispatch effect.
Neutral: --skills remains valid as a capability hint; the agent:code-reviewer prohibition must be documented in plan-to-beads and bead-create-smart.
