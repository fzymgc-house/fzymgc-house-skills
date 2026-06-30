---
title: "Store drain lessons in bd notes rather than the prompt body"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-ce3; do not edit manually; use `/adr update fhsk-ce3` -->

**Date:** 2026-05-22
**Status:** Accepted
**Decision:** fhsk-ce3
**Deciders:** Sean Brandt (@seanb4t)

**Date:** 2026-05-22
**Status:** Accepted
**Deciders:** Sean Brandt (@seanb4t)

## Context

The holomush `/loop autonomous` pattern accumulated run-time observations by editing the prompt body between iterations (prompt drift). For example, iteration 6 of the Scenes Phase 4 epic added a "CRITICAL: jj-new-first discipline" block after T30 exposed a jj-squash failure mode. This required manual operator intervention every time a generalizable lesson emerged. The `/drain` design needed a structured, queryable alternative that survives `/compact` and is auditable across runs.

## Decision

Lessons are stored as `bd note` entries with a `"lesson: <text>"` prefix on either the drain bead (run-scoped, ephemeral) or the epic bead (epic-scoped, persistent across all future drain runs against that epic). Step 3 of the per-iteration body reads both tiers on every iteration via a prefix filter and injects them into the subagent prompt.

## Rationale

- holomush transcript (`f3a83fe5`) established that prompt-body mutation is the root cause of prompt drift; the prompt body grows ~150 words per round, increasing per-iteration cost.
- bd notes are queryable (`bd notes <id>`), version-controlled (Dolt-backed), and survive context compaction inside the `/goal` session.
- Two tiers cleanly distinguish ephemeral run observations from durable cross-run learning. The orchestrator elevates a lesson to the epic bead when it judges the lesson generalizable beyond the current run.
- Step 3 of the iteration body reads both tiers on every iteration with a single prefix filter — zero additional protocol complexity.

## Alternatives Considered

**Prompt-body mutation between iterations (the holomush pattern) — rejected.** Strengths: lessons immediately visible in the next iteration's context without a bd read. Weaknesses: prompt drift accumulates linearly with iteration count; requires manual operator intervention to inject; not auditable or queryable after the fact; breaks the stable-iteration-body design that makes `/goal` cost-effective.

**Single-tier notes on the drain bead only — rejected.** Strengths: simpler; no elevation judgment required. Weaknesses: lessons are lost when the drain bead closes; no cross-run learning for recurring epics; institutional knowledge does not accumulate.

## Consequences

**Positive.** Prompt body stays stable across all iterations — no drift. Lessons are auditable via `bd notes <id>` at any time. Epic-scoped lessons accumulate institutional knowledge across multiple drain runs.

**Negative.** Orchestrator must make elevation judgments; wrong elevation pollutes epic notes. Epic bead note accumulation is unbounded in v1 (squash recipe deferred to a future hygiene cycle).

**Neutral.** Drain bead notes are also the primary audit log for halt reasons and rejection counts — the lesson convention shares note-space with `rejection:`, `halt:`, and `result:` prefixed entries.

## References

- Spec: `docs/superpowers/specs/2026-05-22-drain-skill-design.md` §Architecture — Lessons mechanism (two-tier)
- Design bead: `fhsk-a67`
- Anti-pattern source: holomush transcript `f3a83fe5` (May 22, 2026) — 26 `/loop autonomous` invocations + 248 bd ops; iteration 6 added "jj-new-first discipline" block after T30 failure.
