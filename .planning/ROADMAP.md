# Roadmap: fzymgc-house-skills

## Overview

A retrospective map of a shipped skills marketplace. The org needed reusable, single-source
agent skills that install with low friction on both Claude Code and Codex. The journey ran
from foundation skills (infra + tooling), through the dev-flow PR review/fix pipeline, to
multi-VCS (jj) support, and finally to automated release and dual-marketplace distribution —
the machinery that makes cross-project reuse real. Phases 1-4 are shipped (confirmed by the
2026-07-08 codebase map); Phase 5 is the one open thread: reconciling the superseded plugin
layout with the LOCKED release-please ADR and hardening cross-project adoption.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)
- [x] **Phase 1: Foundation Skills (Infrastructure & Tooling)** - Reusable single-source infra, QA, terminal, and search skills
- [x] **Phase 2: PR Review & Autonomous Fix Pipeline** - Multi-agent review with bead-backed findings and a worktree-isolated fix loop
- [x] **Phase 3: Multi-VCS Workflow Support (Jujutsu)** - jj plugin, VCS detection, and a safe op-log recovery gate
- [x] **Phase 4: Release Automation & Dual-Marketplace Distribution** - One repo-wide version, Claude + Codex install over single source
- [x] **Phase 5: Governance Reconciliation & Reuse Hardening** - Superseding layout ADR and documented low-friction adoption (completed 2026-07-10)

## Phase Details

### Phase 1: Foundation Skills (Infrastructure & Tooling)

**Goal**: Reusable, single-source skills for infrastructure operations, skill QA, terminal
control, and shell search exist as installable plugins and establish the SKILL.md + gateway
conventions the rest of the marketplace builds on.
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, TOOL-01, TOOL-02
**Success Criteria** (what must be TRUE):

1. A user can invoke the terraform skill to run read-only Terraform Cloud operations without loading 30+ MCP tool definitions into context
2. A user can run skill-qa to validate a SKILL.md against best-practice checks
3. A user can drive tmux/cmux sessions and panes from an agent via the tmux skill
4. A user gets rg/ast-grep/grep guidance and receives advisory nudges steering grep toward rg

**Plans**: TBD (retrospective — shipped)
**Status**: Complete (retrospective)

### Phase 2: PR Review & Autonomous Fix Pipeline

**Goal**: dev-flow delivers multi-agent PR review with findings persisted as beads and an
autonomous, worktree-isolated fix loop, so review state survives sessions and fixes never
clobber the base repo.
**Depends on**: Phase 1
**Requirements**: REV-01, REV-02, REV-03, REV-04
**Success Criteria** (what must be TRUE):

1. Running review-pr dispatches specialized review agents and records findings as child beads under a PR-review parent bead that survive across sessions
2. address-findings triages finding beads and drives fix-worker → review-gate → verification until clean
3. respond-to-comments handles human PR comments using prior review state queried from beads
4. Fix/verification agents operate in isolated sibling worktrees and commit their changes without editing the base repo

**Plans**: TBD (retrospective — shipped)
**Status**: Complete (retrospective)

### Phase 3: Multi-VCS Workflow Support (Jujutsu)

**Goal**: The dev-flow pipeline and a standalone jj skill work in Jujutsu repos (including
colocated git+jj) with correct VCS detection and a safety gate that prevents op-log-rewind
accidents across concurrent workspaces.
**Depends on**: Phase 2
**Requirements**: VCS-01, VCS-02
**Success Criteria** (what must be TRUE):

1. A user in a jj repo gets Jujutsu workflow guidance with correct VCS detection in colocated git+jj repos
2. Agents are blocked (MUST NOT) from op-log-rewind ops (`jj op restore`/`jj op abandon`) without explicit approval and are guided to the safe recovery ladder

**Plans**: TBD (retrospective — shipped)
**Status**: Complete (retrospective)

### Phase 4: Release Automation & Dual-Marketplace Distribution

**Goal**: A single repo-wide version releases automatically from conventional-commit PRs, and
the same single-source skills install on both Claude Code and Codex — the distribution and
versioning machinery that makes cross-project reuse low-friction.
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: REL-01, REL-02, DIST-01, DIST-02, DIST-03
**Success Criteria** (what must be TRUE):

1. Merging conventional-commit PRs produces a release PR that bumps one repo-wide version, syncs plugin manifests, and updates CHANGELOG on merge
2. Any org repo can install a plugin by name from the Claude marketplace manifest
3. The same plugins install via the Codex marketplace layer through symlink wrappers with no content duplication
4. CI fails when the marketplaces or release config drift from the single-source plugin directories

**Plans**: TBD (retrospective — shipped)
**Status**: Complete (retrospective)

### Phase 5: Governance Reconciliation & Reuse Hardening

**Goal**: Close the one open thread — formally reconcile the shipped plugin layout with the
LOCKED release-please ADR, and make cross-project adoption explicitly low-friction so the
core value (reuse) is documented, not just implicit.
**Depends on**: Phase 4
**Requirements**: GOV-01, GOV-02
**Success Criteria** (what must be TRUE):

1. A superseding ADR records the shipped `homelab`/`jj`/`dev-flow`/`tmux`/`grepping` layout and marks the release-please ADR's `fzymgc-house/skills/*` package layout superseded
2. A new org repo can discover and install a skill following documented, minimal-friction steps

**Plans**: 2/2 plans complete

- [x] 05-01-PLAN.md — Author two superseding ADRs (release-please versioning + shipped 5-plugin layout), flip fhsk-dgo to Superseded, regenerate the ADR index
- [x] 05-02-PLAN.md — Complete the skill catalog (README + docs/adoption.md), add the adoption guide, and add a CI drift-gate test

**Status**: Planned

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation Skills | -/- | Complete (retrospective) | Shipped as of 2026-07-08 |
| 2. PR Review & Fix Pipeline | -/- | Complete (retrospective) | Shipped as of 2026-07-08 |
| 3. Multi-VCS Support (jj) | -/- | Complete (retrospective) | Shipped as of 2026-07-08 |
| 4. Release & Distribution | -/- | Complete (retrospective) | Shipped as of 2026-07-08 |
| 5. Governance Reconciliation | 2/2 | Complete    | 2026-07-10 |
