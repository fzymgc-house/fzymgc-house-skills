<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-e4i; do not edit manually; use `/adr update fhsk-e4i` -->

# Never invoke /goal from a skill; emit the condition for a user or driver to submit

**Date:** 2026-05-24
**Status:** Accepted
**Decision:** fhsk-e4i
**Deciders:** Sean Brandt (@seanb4t)

## Context

The previous `drain.md` Phase D was titled "Fire `/goal`". But `/goal` is a user-only built-in: no `SlashCommand` tool exposes it to the agent, and built-ins execute only from a submitted turn. An agent emitting `/goal …` as output text produces text that never executes — a silent no-op masquerading as an action.

## Decision

The skill and the `/drain` command never invoke `/goal`. Setup commands (`epic`/`set`/`cascade`/`worker`/`resume`) emit the condition string for a user — or a future external driver (Agent SDK `query({prompt})`, cmux/tmux `send-keys`) — to submit as a turn. Phase D is reframed from "Fire `/goal`" to "Emit the `/goal` condition".

## Rationale

- `/goal` is user-only — no tool exposes it to the agent, making invocation impossible, not merely inadvisable.
- The emit-only model is architecturally honest (no silent no-ops) and leaves room for future programmatic drivers without a redesign.
- This is a correctness constraint, not a style preference.

## Alternatives Considered

- **Skill emits `/goal <condition>` as a runnable agent action:** single-command UX with no copy-paste — but no tool exposes `/goal` to the agent, so the output is inert text. Rejected as incorrect behavior.

## Consequences

- Positive: behavior is correct and transparent; the design explicitly accommodates a future Agent SDK / cmux driver.
- Negative: a human (or future driver) step is required between setup and worker boot; no fully automated path exists today.
- Neutral: controller auto-dispatch via cmux/tmux is explicitly deferred to future work.
