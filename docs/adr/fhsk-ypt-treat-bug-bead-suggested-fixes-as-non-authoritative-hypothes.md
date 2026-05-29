<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-ypt; do not edit manually; use `/adr update fhsk-ypt` -->

# Treat bug bead suggested fixes as non-authoritative hypotheses

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-ypt
**Deciders:** Sean Brandt

## Context

Bug beads frequently contain suggested fixes ("fix it by doing X", "the solution is Y"). Treating these as instructions short-circuits root-cause analysis and produces symptom patches. The `solving-a-bead` skill needed a firm policy on how to classify and route bead-embedded fix suggestions during triage, since this choice shapes Phase 2 routing, the red-flags table, and the delegation contract to `systematic-debugging`.

## Decision

Every "fix it by…" or "the solution is…" sentence in a bug bead is demoted to hypothesis status during Phase 2 triage and routed through `systematic-debugging`; it may be adopted only if the confirmed root cause independently demands it.

## Rationale

- `systematic-debugging`'s Iron Law (NO FIXES WITHOUT ROOT CAUSE FIRST) is the existing discipline guarantee — delegating to it rather than reimplementing preserves consistency.
- Reporter diagnosis is a lead, not a conclusion; treating it as an instruction masks root causes and produces patches instead of fixes.
- The red-flags table codifies this for future agents: "The bead says to fix it by doing X" → "X is a hypothesis; confirm root cause requires X first."
- This choice shapes the entire Phase 2 routing logic and the allowed behavior of any future skill that processes bug beads.

## Alternatives Considered

- **Treat suggested fix as an instruction to execute** (rejected): faster path to implementation and respects reporter intent, but short-circuits root-cause analysis, produces symptom patches that miss the actual defect, and undermines `systematic-debugging`'s Iron Law.
- **Treat suggested fix as a non-authoritative hypothesis routed through systematic-debugging** (chosen): preserves root-cause-first discipline; every candidate solution is validated against the confirmed root cause before adoption; consistent with the existing debugging contract; explicitly captured in a red-flags table.

## Consequences

- Positive: root-cause discipline is enforced structurally, not left to agent judgment; consistent with `systematic-debugging`'s existing contract; red-flags table gives future contributors an explicit reference for why hypothesis-first is required.
- Negative: triage adds overhead when the reporter's diagnosis happens to be correct; Phase 2 requires explicit bucket-splitting of bead content.
- Neutral: bug beads with no suggested fix are unaffected — they go straight to `systematic-debugging` without the demotion step.
