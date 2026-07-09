## Conflict Detection Report

Pass 2 ingest — 35 ADRs from `docs/adr/`, merge mode against Pass 1 `.planning/`.
Precedence: ADR > SPEC > PRD > DOC (no per-doc overrides).

### BLOCKERS (0)

None. No LOCKED-vs-LOCKED contradiction among the 31 active ADRs; no ingest ADR
contradicts a Pass 1 LOCKED decision (DEC-release-please-versioning,
DEC-jj-op-log-recovery-gate); no UNKNOWN/low-confidence docs; no active-graph
reference cycles.

### WARNINGS (0)

None. No PRDs present, so no competing acceptance-criteria variants are possible.

### INFO (7)

[INFO] fhsk-dgo agrees with Pass 1 LOCKED DEC-release-please-versioning
  Found: docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md adopts release-please with in-file plugin versions + CHANGELOG.md
  Note: Consistent with existing LOCKED DEC-release-please-versioning (.planning/PROJECT.md) — release-please, automated version sync. Agreement, not a conflict; no override needed.

[INFO] fhsk-dgo advances Pass 1 GOV-01
  Found: fhsk-dgo is a superseding release ADR restoring in-file plugin versions
  Note: GOV-01 (.planning/PROJECT.md Active) asks for a superseding ADR over the older release-please package layout; fhsk-dgo moves in that direction. Downstream may reconcile GOV-01 against it.

[INFO] fhsk-dgo supersedes fhsk-toy and fhsk-7y4 (release lineage)
  Found: fhsk-toy (tag-only cog) and fhsk-7y4 (single repo-wide version) are Superseded; fhsk-dgo is the active LOCKED decision
  Note: Superseded predecessors recorded as historical context only in decisions.md; they do NOT count as active locked decisions and raise no LOCKED-vs-LOCKED conflict.

[INFO] fhsk-buu supersedes fhsk-rqh (drain-bead-creation lineage)
  Found: fhsk-rqh (bd mol pour) Superseded by fhsk-buu (bd create --type drain)
  Note: Recorded as historical; active decision is fhsk-buu. No conflict.

[INFO] Supersession back-reference pairs are cycle-safe
  Found: bidirectional cross-refs fhsk-0o2 ↔ fhsk-eqt and fhsk-buu ↔ fhsk-rqh
  Note: Each pair contains a Superseded node (fhsk-0o2, fhsk-rqh) excluded from active synthesis. After pruning Superseded nodes, the active reference graph is acyclic (max depth well under 50). No synthesis loop; not a blocker.

[INFO] fhsk-8g6 and fhsk-dtk govern different drain phases
  Found: fhsk-dtk gates worker LAUNCH behind AskUserQuestion; fhsk-8g6 has the worker finish the branch autonomously (push + PR) after launch
  Note: Complementary phases (gated entry, autonomous execution), not a contradiction. Both LOCKED, both retained.

[INFO] Bead-workflow ADRs extend the proposed DEC-beads-review-persistence
  Found: fhsk-s15, fhsk-ce3, fhsk-8xn, fhsk-3xn, fhsk-bj8, fhsk-hj3, fhsk-57f build on bd as the coordination/handoff/lifecycle substrate
  Note: Consistent with the still-PROPOSED (unlocked) Pass 1 DEC-beads-review-persistence. Because that decision is unlocked, no hard block is possible; recorded for downstream reconciliation.
