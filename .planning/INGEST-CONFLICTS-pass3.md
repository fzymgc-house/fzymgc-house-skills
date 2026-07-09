## Conflict Detection Report

Pass 3 ingest, MERGE mode. Source set = 44 design/spec/plan elaborations behind the
already-locked Pass 1 + Pass 2 baseline (34 LOCKED decisions). Classification: 1 ADR (Proposed,
not locked), 20 SPEC, 23 DOC, 0 PRD. By precedence (ADR > SPEC > PRD > DOC) the locked baseline
wins every overlap; no SPEC/DOC can produce a LOCKED-vs-LOCKED blocker, and 0 locked ADRs were
ingested. No UNKNOWN/low-confidence docs. Result: no gating conflicts.

### BLOCKERS (0)

None. No LOCKED-vs-LOCKED contradiction is possible: the only ADR-classified doc
(handoff-bead-type-design) is Status: Proposed (`locked: false`), and it AGREES with the
existing locked decisions it maps to. No UNKNOWN/low-confidence docs. No unresolvable reference
cycle (see INFO on cycles).

### WARNINGS (0)

None. There are no PRDs, hence no competing acceptance variants. Every SPEC/DOC overlap with the
baseline is resolved deterministically by precedence (locked ADR wins) or by an explicit
supersession chain — no item requires user resolution before routing.

### INFO (6)

[INFO] Zero new locked decisions; 44 docs subordinated to the locked baseline
  Found: 20 SPEC + 23 DOC + 1 Proposed ADR, all same-scope as one of the 34 existing LOCKED
    decisions in .planning/PROJECT.md.
  Note: Recorded as supporting constraints (constraints.md, 19 NEW contracts) and context
    (context.md, 23 DOCs). None overrides a locked decision. Precedence ADR > SPEC > DOC applied.

[INFO] Lone ADR agrees with an existing locked decision — folded, not re-litigated
  Found: docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md (ADR, Proposed, not
    locked) proposes a first-class `handoff` bd type + create/resume.
  Note: AGREES with LOCKED DEC-adr-fhsk-s15 (custom bd type for handoffs) + fhsk-57f + fhsk-8xn.
    Recorded as their design elaboration (CON-p3-handoff-body-schema), not a new locked decision.

[INFO] Auto-resolved: LOCKED release-please > cog tag-only release flow
  Found: docs/superpowers/specs/2026-05-29-cog-release-flow-design.md and its plan describe
    replacing release-please with cocogitto (cog) tag-only releases.
  Note: SUPERSEDED by LOCKED DEC-adr-fhsk-dgo / DEC-release-please-*versioning (release-please
    with in-file plugin versions). Both cog docs self-mark Superseded. Recorded as historical
    context only; cog is NOT resurrected as active. Reaffirms already-superseded fhsk-toy/7y4.

[INFO] Auto-resolved by explicit supersession: drain-goal handoff redesign > original drain-skill design
  Found: 2026-05-22-drain-skill-design.md and 2026-05-24-drain-goal-handoff-redesign-design.md
    (both SPEC, equal precedence) differ on the drain/goal handoff mechanics.
  Note: The later doc is an explicit "Redesign — Cold-Boot Worker Contract" that supersedes the
    earlier mechanics. Resolved by declared supersession, NOT by timestamp tiebreak. Both remain
    subordinate to the locked drain ADRs (fhsk-thw/zds/e4i/eqt/0cd/ce3/8g6/dtk/5dj/8yz/a6v/buu).

[INFO] Benign companion cross-reference cycles — not synthesis-blocking
  Found: 4 two-node cycles in the cross-ref graph: guard-jj-mutating (plan↔spec),
    cog-release-flow (plan↔spec), solving-a-bead (plan↔spec), and
    dev-flow-beads-integration-design↔docs/adr/README.md.
  Note: Each is a companion plan/spec (or design/README) bidirectional link, deterministically
    ordered by SPEC > DOC precedence (SPEC authoritative, DOC subordinate). Not a
    non-deterministic synthesis loop. Traversal depth 1; well under the 50 cap. Synthesized
    normally.

[INFO] NEW material contributed beyond the baseline
  Found: The 20 SPECs contribute 19 NEW implementation constraints (hook Python runtime, jj
    pager/collision/op-guard, VCS preamble set, upstream-manifest, ADR bd-source + Starlight
    frontmatter, slop catalogs, pr-review consolidation, dev-flow Rules 1–7, skills routing,
    drain sentinel/watchdog/mux-driver protocols, solving-a-bead + handoff + memory-curator +
    miniflux + mermaid contracts). The 23 DOCs contribute background runbooks + 2 reference docs
    (dev-flow-pipeline architecture, ADR README).
  Note: All deduplicated against Pass 1 + Pass 2 and subordinated to the locked baseline. See
    constraints.md and context.md.

---

GSD > No blocking conflicts detected. Safe to route: 0 blockers, 0 warnings, 6 info.
