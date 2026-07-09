# Pass 3 Synthesis Summary

Single entry point for `gsd-roadmapper`. Pass 3 ingest, MERGE mode, against the authoritative
Pass 1 + Pass 2 locked baseline (34 LOCKED decisions in `.planning/PROJECT.md`). Precedence:
ADR > SPEC > PRD > DOC.

## Doc counts by type

- Total docs synthesized: 44
- ADR: 1 (Proposed, `locked: false`)
- SPEC: 20
- PRD: 0
- DOC: 23
- UNKNOWN / low-confidence: 0

## Decisions

- New locked decisions: 0
- The lone ADR (handoff-bead-type-design, Proposed) AGREES with existing LOCKED
  DEC-adr-fhsk-s15 / fhsk-57f / fhsk-8xn — folded as design elaboration, not a new decision.
- Superseded/historical recorded: cog release flow (superseded by locked release-please
  fhsk-dgo); original drain-skill design superseded by the cold-boot redesign.
- All 44 docs subordinated to the locked baseline (43 SPEC/DOC as constraints/context +
  1 Proposed ADR folded into an existing locked decision). See `decisions.md`.

## Requirements

- Requirements extracted: 0 (no PRDs). No competing acceptance variants. See `requirements.md`.

## Constraints (NEW)

- 19 NEW implementation contracts / NFRs / protocols / schemas extracted from the 20 SPECs, each
  subordinate to a locked decision. Type breakdown: api-contract 6, schema 5, protocol 5, nfr 2,
  structural 3 (some entries carry two type tags). See `constraints.md`.

## Context (NEW)

- 23 DOCs recorded across 21 topic groups (2 reference docs — dev-flow-pipeline architecture and
  ADR README — plus implementation runbooks; the drain-lineage group folds 4 runbooks). All
  subordinate to the locked baseline + their Pass-3 SPEC contracts. See `context.md`.

## Conflicts

- Blockers: 0
- Competing variants (warnings): 0
- Auto-resolved / info: 6
- Detail: `.planning/INGEST-CONFLICTS-pass3.md`

## Cross-ref graph

- 44 nodes, 37 in-set edges, max depth 1. 4 benign companion plan↔spec (or design↔README)
  2-cycles, each deterministically ordered by SPEC > DOC precedence — synthesized normally.

## Intel files (this pass)

- `.planning/intel/pass3/decisions.md`
- `.planning/intel/pass3/requirements.md`
- `.planning/intel/pass3/constraints.md`
- `.planning/intel/pass3/context.md`
- Conflicts: `.planning/INGEST-CONFLICTS-pass3.md`

## Routing status

READY — safe to route. No blockers, no warnings. Pass 3 adds supporting detail only; the
locked baseline is unchanged.
