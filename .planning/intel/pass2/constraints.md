# Constraints (SPEC intel — Pass 2)

No SPEC-classified documents in the Pass 2 source set. The 35 ingested docs are all
ADRs.

No api-contract / schema / nfr / protocol constraints extracted from this ingest.

Several LOCKED ADRs in `decisions.md` imply operational constraints that
`gsd-roadmapper` should honor (recorded there, not duplicated as formal constraints):

- Drain worker launches MUST be gated behind AskUserQuestion (fhsk-dtk).
- Skill entry MUST hard-block on unmet bead blocker dependencies (fhsk-3xn).
- Skills MUST NOT invoke /goal directly; emit the condition instead (fhsk-e4i).
- ADR files MUST carry YAML frontmatter title, no body H1 (fhsk-slp), enforced by
  the bd-free INV-A25 CI check (fhsk-bmn).
- Conventional-commit validation lives at the PR-title boundary in CI, not a local
  git hook (fhsk-h3z).

Existing Pass 1 constraints remain authoritative in `.planning/intel/constraints.md`
and `.planning/PROJECT.md` (not modified by this pass).
