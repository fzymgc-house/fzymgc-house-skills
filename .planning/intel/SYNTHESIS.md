# Synthesis Summary

Single entry point for `gsd-roadmapper`. Consolidates 20 classified planning docs into per-type
intel plus a conflicts report. Mode: `new` (bootstrap; no prior PROJECT/REQUIREMENTS/ROADMAP).

## Doc counts by type

- ADR: 3 (2 LOCKED, 1 Draft/PROPOSED)
- SPEC: 5
- PRD: 0
- DOC: 12
- Total: 20

## Decisions

File: `decisions.md`

- LOCKED (2):
  - DEC-release-please-manifest-versioning — docs/plans/2026-02-16-release-please-design.md
  - DEC-jj-op-log-recovery-gate — docs/plans/2026-05-01-jj-skill-op-log-recovery-rule-design.md
- PROPOSED (1, Draft — not locked):
  - DEC-beads-review-persistence — docs/plans/2026-02-15-beads-review-integration-design.md

## Requirements

File: `requirements.md`

- 0 extracted (no PRD-classified docs). No competing acceptance variants. Roadmapper must derive requirements from decisions/constraints/context.

## Constraints

File: `constraints.md` — 5 total (all Draft SPECs)

- protocol/api-contract: CON-terraform-skill
- protocol/schema: CON-address-review-findings
- architecture/protocol: CON-agent-plugin-restructure (conflicts with LOCKED release-please ADR — auto-resolved)
- protocol: CON-worktree-isolation-fix
- schema/api-contract: CON-codex-marketplace

## Context topics

File: `context.md` — 12 DOC-derived notes across topics: grafana token efficiency (2), terraform impl (1), beads review impl (1), address-review-findings impl (1), release-please impl (1), agent/plugin restructure impl (1), worktree isolation impl (1), jj VCS support (2), codex marketplace impl (1), jj op-log recovery impl (1).

## Conflicts

Report: `../INGEST-CONFLICTS.md`

- Blockers: 0
- Competing variants (warnings): 0
- Auto-resolved (info): 2 (LOCKED ADR > SPEC/DOC on plugin directory layout)

## Cross-ref integrity

Cross-ref graph is an acyclic DAG (implementation docs reference their design docs only). Cycle detection passed; max depth well under the 50 cap.

## Downstream note

The dominant open thread for the roadmapper: the repo's plugin layout evolved (`fzymgc-house` -> `homelab` + `pr-review` + `jj` + Codex layer) across the SPEC/DOC set, but the only LOCKED ADR touching layout still encodes the `fzymgc-house` naming. No hard block, but a superseding ADR is the clean resolution before planning around the restructured paths.
