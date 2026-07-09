# Decisions (ADR intel — Pass 3)

Provenance: Pass 3 ingest, MERGE mode. Source set = 44 design/spec/plan elaborations
behind the already-locked Pass 1 + Pass 2 decisions. Precedence: ADR > SPEC > PRD > DOC.

The authoritative locked baseline is unchanged: 34 LOCKED decisions (3 Pass-1 `DEC-*` +
31 Pass-2 `DEC-adr-fhsk-*`) in `.planning/PROJECT.md` and `.planning/intel/{decisions.md,
pass2/decisions.md}`. **Pass 3 introduces ZERO new locked decisions.** Every SPEC/DOC in
this set elaborates a decision that is already locked, so by precedence the locked baseline
wins and these docs are recorded as supporting constraints/context, not re-litigated.

---

## Lone ADR-classified doc — subordinated to an existing locked decision

### handoff-bead-type-design (ADR, Proposed — NOT locked)

- source: docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md
- classification: ADR, confidence medium, `locked: false` (Status: Proposed)
- Decision content: make `handoff` a first-class persistent bd type with create/resume
  workflows, replacing the ephemeral handoff-prompt skill; carry session-state via bead
  dependency links.
- **Resolution: AGREES with existing LOCKED `DEC-adr-fhsk-s15`** (use a custom bd type for
  handoffs, not a label or note) and `DEC-adr-fhsk-57f` (package create+resume as one
  conditional-workflow skill) and `DEC-adr-fhsk-8xn` (carry session-state delta, not a full
  re-snapshot). No contradiction. Recorded as the **design elaboration** of those locked
  decisions, NOT as a new independent locked decision. Its concrete body-schema contract is
  captured in `constraints.md` as `CON-p3-handoff-body-schema`.

---

## Superseded / historical decision material (recorded, NOT active)

- **cog tag-only release flow** (spec `2026-05-29-cog-release-flow-design.md` + plan
  `2026-05-29-cog-release-flow.md`): describes replacing release-please with cocogitto.
  **SUPERSEDED in practice** by LOCKED `DEC-adr-fhsk-dgo` / `DEC-release-please-*versioning`
  (release-please with in-file plugin versions). Both docs self-mark Superseded. Recorded as
  historical context only; cog is NOT resurrected as active. Reaffirms the already-superseded
  ADRs fhsk-toy and fhsk-7y4.

- **drain-skill original design** (spec `2026-05-22-drain-skill-design.md`) is superseded on
  the drain-goal handoff mechanics by the later `2026-05-24-drain-goal-handoff-redesign-design.md`
  (explicit "Redesign — Cold-Boot Worker Contract"). Both remain subordinate to the LOCKED
  drain ADRs (fhsk-thw, fhsk-zds, fhsk-e4i, fhsk-eqt, fhsk-0cd, fhsk-ce3, fhsk-8g6, fhsk-dtk,
  fhsk-5dj, fhsk-8yz, fhsk-a6v, fhsk-buu). Supersession is by explicit redesign, not timestamp.

---

## No new locked decisions

No document in the Pass 3 set carries `locked: true`. No LOCKED-vs-LOCKED contradiction is
possible from this set (0 locked ADRs ingested). See `INGEST-CONFLICTS-pass3.md`.
