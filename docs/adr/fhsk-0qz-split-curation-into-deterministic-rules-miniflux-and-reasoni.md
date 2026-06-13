<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-0qz; do not edit manually; use `/adr update fhsk-0qz` -->

# Split curation into deterministic rules (Miniflux) and reasoning (Claude)

**Date:** 2026-06-14
**Status:** Accepted
**Decision:** fhsk-0qz
**Deciders:** Sean

## Context

Miniflux has native per-feed blocklist_rules and keeplist_rules (regex over titles/URLs) applied server-side on every fetch. Claude can rank entries by relevance and propose new rules. The design must assign filtering responsibility to avoid redundancy and ensure durable noise reduction.

## Decision

Deterministic blocklist/keeplist regex rules live in Miniflux (applied server-side); relevance ranking, digest prose, and rule proposals are Claude's responsibility; the suggest-rules then apply-rule command pair is the handoff for converting a soft Claude observation into a durable Miniflux filter.

## Rationale

- Durable server-side rules eliminate recurring noise without per-session LLM cost.
- Claude's judgment is highest-value for ranking and novel pattern detection, not re-filtering known noise.
- The soft-to-hard handoff preserves user control: Claude proposes, user approves, apply-rule commits.
- Mirrors how Miniflux is designed: blocklist/keeplist are first-class feed attributes.

## Alternatives Considered

- **Rules in Miniflux, reasoning in Claude (chosen):** durable, low-cost, user-controlled handoff. Needs two round-trips and a stability judgment.
- **All filtering in Claude (rejected):** single responsibility, but noise recurs every session; no durable state.
- **All filtering in Miniflux (rejected):** deterministic, no LLM cost, but no ranking/digest; misses the AI-curation goal.

## Consequences

- Positive: hardened noise eliminated permanently at zero per-session cost; digest candidates arrive pre-filtered, reducing context.
- Negative: the suggest-rules to apply-rule cycle needs a user confirmation step that cannot be fully automated.
- Neutral: scraper_rules and rewrite_rules are available via update_feed but not first-class commands in this version.
