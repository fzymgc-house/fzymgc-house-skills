# Pass 2 Synthesis Summary

Entry point for `gsd-roadmapper`. Isolated Pass 2 ingest; does NOT modify any
Pass 1 file. Mode: merge. Precedence: ADR > SPEC > PRD > DOC.

## Doc counts by type

- ADR: 35 (all high-confidence)
  - Active LOCKED (Accepted): 31
  - Superseded (historical only): 4 — fhsk-0o2, fhsk-7y4, fhsk-rqh, fhsk-toy
- SPEC: 0
- PRD: 0
- DOC: 0

## Decisions

- Locked decisions contributed: 31 (see decisions.md)
- Superseded decisions recorded as historical context: 4
- Sources: docs/adr/fhsk-*.md (35 files)

## Requirements

- Extracted: 0 (no PRDs). Derived downstream by roadmapper from LOCKED decisions.

## Constraints

- Formal SPEC constraints: 0 (no SPECs).
- Operational constraints implied by LOCKED ADRs are noted in constraints.md
  (drain-launch gating, bead-blocker hard-block, /goal emit-not-invoke, ADR
  frontmatter/CI checks, PR-title commit validation).

## Context topics

- 4 running topics captured in context.md (corpus shape, decision clusters,
  supersession lineage, merge-mode alignment with Pass 1).

## Conflicts

- BLOCKERS: 0
- WARNINGS (competing variants): 0
- INFO (auto-resolved / transparency): 7
- Detail: ../../INGEST-CONFLICTS-pass2.md

## Merge alignment with Pass 1 locked decisions

- fhsk-dgo AGREES with DEC-release-please-versioning (LOCKED) and advances GOV-01.
- No ADR touches DEC-jj-op-log-recovery-gate (LOCKED).
- Bead-workflow ADRs extend the still-proposed DEC-beads-review-persistence
  (unlocked) — no blocker possible.

## Cycle detection

- Two supersession back-reference pairs (fhsk-0o2 ↔ fhsk-eqt, fhsk-buu ↔ fhsk-rqh).
- Superseded nodes pruned from active synthesis; active graph is acyclic. No
  synthesis loops. No cycle blockers.

## Per-type intel files

- decisions.md — 31 active LOCKED + 4 superseded
- requirements.md — empty (no PRDs)
- constraints.md — empty of formal SPECs; operational notes only
- context.md — cross-cutting themes and provenance

## Status

READY — safe to route. No blockers, no competing variants. All 7 conflict entries
are INFO (agreements, supersession, cycle-safe back-references).
