<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-2us; do not edit manually; use `/adr update fhsk-2us` -->

# Use ACTIVE_ASPECTS deferral for cross-aspect deduplication in slop-hunter

**Date:** 2026-05-28
**Status:** Accepted
**Decision:** fhsk-2us
**Deciders:** Sean Brandt

## Context

Several slop catalog patterns are co-owned by adjacent pr-review aspects: C-1 (comment restates code) by comment-analyzer, C-9 (swallowed errors) by silent-failure-hunter, C-4/C-5/C-10 (YAGNI variants) by code-reviewer, and C-13 (copy-paste clone) by code-simplifier. The design-reviewer found that a catalog-ID rule alone (every slop finding must cite a pattern ID) was insufficient: it only constrains slop-hunter, not the other agents, so both would still file findings on the same hunk — the #1 known failure mode of the review system.

## Decision

slop-hunter suppresses each co-owned pattern when its owning aspect is present in the ACTIVE_ASPECTS variable (passed by the orchestrator as the comma-separated aspect keys of the current run, excluding slop), and raises it only when that aspect is absent. Under the default `all` run the co-owned patterns are deferred to their specialist owners; in a lone `slop` run slop-hunter raises the full catalog as a "catch what the specialists miss" net.

## Rationale

- The design-reviewer (round 1) flagged the catalog-ID rule as a false premise: it binds only slop-hunter, not the agents that already own those patterns.
- Modifying existing stable agent contracts (comment-analyzer, silent-failure-hunter, code-reviewer, code-simplifier) to defer to slop-hunter is more invasive than adding one variable to the orchestrator.
- ACTIVE_ASPECTS is passed only to slop-hunter; no other agent variable set changes, minimizing orchestrator blast radius.

## Alternatives Considered

- Accept overlap (both agents file independently): rejected — produces duplicate beads on the same hunk, the known #1 failure mode.
- Make the other agents defer to slop-hunter: rejected — requires modifying four stable, pre-existing agent contracts.
- slop-hunter defers via ACTIVE_ASPECTS (chosen): only slop-hunter changes; existing agents untouched; correct in both `all` and lone-`slop` runs.

## Consequences

Positive: zero duplicate findings between slop and adjacent aspects in normal operation; existing agent contracts unchanged; slop-hunter useful both as an `all`-mode net and standalone.
Negative: the co-owned pattern table must stay in sync with other agents (if comment-analyzer drops C-1 coverage, deferral silently stops working); the ACTIVE_ASPECTS format (aspect keys, not agent names) is a new contract future orchestrator edits must respect.
Neutral: the orchestrator builds ACTIVE_ASPECTS after the Select-Applicable-Agents step and passes it in the slop-hunter task prompt.
