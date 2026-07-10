# Roadmap: fzymgc-house-skills

## Overview

A retrospective map of a shipped skills marketplace. The org needed reusable, single-source
agent skills that install with low friction on both Claude Code and Codex. The journey ran
from foundation skills (infra + tooling), through the dev-flow PR review/fix pipeline, to
multi-VCS (jj) support, and finally to automated release and dual-marketplace distribution —
the machinery that makes cross-project reuse real. As of v1.0 all five phases are shipped,
with the plugin-layout governance reconciled against the release-please ADR and cross-project
adoption documented and CI-enforced.

## Milestones

- ✅ **v1.0 Skills Marketplace** — Phases 1-5 (shipped 2026-07-10)

## Phases

<details>
<summary>✅ v1.0 Skills Marketplace (Phases 1-5) — SHIPPED 2026-07-10</summary>

- [x] Phase 1: Foundation Skills (Infrastructure & Tooling) — reusable single-source infra, QA, terminal, and search skills
- [x] Phase 2: PR Review & Autonomous Fix Pipeline — multi-agent review with bead-backed findings and a worktree-isolated fix loop
- [x] Phase 3: Multi-VCS Workflow Support (Jujutsu) — jj plugin, VCS detection, and a safe op-log recovery gate
- [x] Phase 4: Release Automation & Dual-Marketplace Distribution — one repo-wide version, Claude + Codex install over single source
- [x] Phase 5: Governance Reconciliation & Reuse Hardening (2/2 plans) — superseding layout ADRs (fhsk-o9o + fhsk-wdk) + documented low-friction adoption (completed 2026-07-10)

Full phase details (goals, success criteria, requirements): [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1. Foundation Skills | v1.0 | Complete (pre-GSD) | shipped |
| 2. PR Review & Fix Pipeline | v1.0 | Complete (pre-GSD) | shipped |
| 3. Multi-VCS (jj) | v1.0 | Complete (pre-GSD) | shipped |
| 4. Release Automation & Dual-Marketplace | v1.0 | Complete (pre-GSD) | shipped |
| 5. Governance Reconciliation & Reuse Hardening | v1.0 | Complete (GSD, 2/2 plans) | 2026-07-10 |

---

*v1.0 shipped 2026-07-10. See `.planning/MILESTONES.md` for the milestone summary and `milestones/v1.0-ROADMAP.md` for full phase details. Next milestone: `/gsd-new-milestone`.*
