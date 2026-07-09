# Requirements (PRD intel)

No PRD-classified documents were present in this ingest set (distribution: 3 ADR, 5 SPEC, 12 DOC; 0 PRD).

Therefore **zero requirements were extracted at synthesis time**, and there are no competing acceptance-criteria variants to resolve.

Downstream (`gsd-roadmapper`) must derive requirements from:

- `decisions.md` — locked/proposed decisions (release-please versioning, jj op-log recovery gate, beads review persistence)
- `constraints.md` — the 5 SPEC-derived technical constraints (terraform skill, address-review-findings, agent/plugin restructure, worktree isolation, codex marketplace)
- `context.md` — 12 supporting implementation/design plans

No `REQ-*` IDs are asserted here to avoid inventing acceptance criteria the source docs do not contain.
