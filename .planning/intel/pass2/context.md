# Context (DOC intel — Pass 2)

No DOC-classified documents in the Pass 2 source set. Running notes below are
cross-cutting themes and provenance observed while synthesizing the 35 ADRs.

## Topic: ADR corpus shape

- 35 ADRs from `docs/adr/` (fhsk-*), all high-confidence classifications.
- 31 active LOCKED (Accepted), 4 Superseded (fhsk-0o2, fhsk-7y4, fhsk-rqh, fhsk-toy).
- source: docs/adr/ (whole corpus)

## Topic: Dominant decision clusters

- **Drain harness / autonomous drains** (largest cluster): fhsk-0cd, fhsk-5dj,
  fhsk-8g6, fhsk-8xn, fhsk-ce3, fhsk-dtk, fhsk-eqt, fhsk-thw, fhsk-e4i, fhsk-buu,
  fhsk-zds — cohesive: /goal-driven, bead-carried, explicitly-initialized, gated at
  launch, autonomous after launch.
- **Bead workflow substrate**: fhsk-3xn, fhsk-bj8, fhsk-hj3, fhsk-s15, fhsk-57f,
  fhsk-ypt — extend bd as the coordination/handoff/lifecycle layer.
- **Miniflux / homelab curation**: fhsk-0qz, fhsk-pqw, fhsk-qs9.
- **ADR tooling / docs build**: fhsk-slp, fhsk-nlw, fhsk-bmn.
- **Memory-curator plugin**: fhsk-e0u, fhsk-p07.
- **Multiplexer / plugin taxonomy**: fhsk-a6v, fhsk-8yz, fhsk-5dj.
- **Release + CI**: fhsk-dgo, fhsk-h3z (plus superseded fhsk-7y4, fhsk-toy).
- **Review pipeline**: fhsk-2us (slop-hunter dedup).

## Topic: Supersession lineage (cross-ref back-references)

- fhsk-dgo supersedes fhsk-toy and fhsk-7y4 (release automation lineage).
- fhsk-buu supersedes fhsk-rqh (drain bead creation lineage).
- fhsk-0o2 (Superseded) supersedes fhsk-eqt (Accepted) and back-references it.
- These supersedes/superseded-by pairs create bidirectional reference edges
  (fhsk-0o2 ↔ fhsk-eqt, fhsk-buu ↔ fhsk-rqh). After pruning Superseded nodes from
  the active synthesis set, no cycles remain in the active graph. Cycle-safe.
- source: cross_refs across the 35 classifications

## Topic: Merge-mode alignment with Pass 1 locked decisions

- fhsk-dgo AGREES with existing DEC-release-please-versioning (LOCKED). It also
  advances Pass 1 GOV-01 (author a superseding release ADR restoring in-file
  versions) — no contradiction, an advancement.
- No ADR in this set touches DEC-jj-op-log-recovery-gate (LOCKED).
- The bead-workflow cluster is consistent with (and extends) the still-proposed
  DEC-beads-review-persistence; since that decision is unlocked, no blocker is
  possible regardless.
- source: .planning/PROJECT.md <decisions>, .planning/intel/decisions.md
