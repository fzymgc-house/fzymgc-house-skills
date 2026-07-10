# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Skills Marketplace

**Shipped:** 2026-07-10
**Phases:** 5 (1 GSD-executed; 1-4 pre-GSD historical) | **Plans:** 2 | **Sessions:** 1 (Phase 5 + close)

### What Was Built

- A five-plugin, single-source skills marketplace (`homelab`, `jj`, `dev-flow`, `tmux`,
  `grepping`) installable by name on both Claude Code and Codex — phases 1-4, shipped pre-GSD
  and confirmed by the 2026-07-08 codebase map.
- Phase 5 (the sole GSD-executed phase) closed the last governance thread: two ADRs authored via
  the direct `bd` + `render-adr` path — `fhsk-o9o` (release-please, corrected four→six manifest
  sync, supersedes `fhsk-dgo`) and `fhsk-wdk` (shipped 5-plugin layout) — plus a completed README
  skill catalog, a canonical `docs/adoption.md`, and a CI-gated drift test proving no shipped skill
  is undocumented.

### What Worked

- **Direct `bd create --type decision` + `render-adr`** for ADR authoring (not the interactive
  `/adr` loop) — the correct path for a subagent with no `AskUserQuestion` (INV-A19).
- **Sequential-on-main execution** (worktree isolation auto-degraded) turned out to be *required*
  for the beads-touching plan: the Dolt DB is gitignored and lives only in the main checkout, so an
  isolated worktree would have lost the `bd` writes. The safety fell out of the tooling.
- **RED→GREEN drift gate** — `tests/test_skill_catalog.py` was proven to fail on the `miniflux` gap
  before the fix, so "discoverable" became an enforced contract rather than a promise.
- **Goal-backward verification** re-ran commands against the live codebase (supersedes edge,
  six-manifest diff, both test functions) rather than trusting SUMMARY claims — 12/12, no theater.

### What Was Inefficient

- **Retrospective bootstrap friction:** phases 1-4 have no GSD artifacts, so milestone/phase gates
  reported "unstarted phases" and required `--force` / override closeout.
- **Capability-default false-positives:** with all `workflow.*` config unset, GSD defaults left the
  `ui.plan-gate` (plan-phase) and the `security` `ship:pre` gate active — both genuinely block on a
  zero-frontend, zero-runtime-surface docs repo and needed explicit bypass.
- **Ship-template mismatch:** `/gsd-ship` set a `"Phase 05: …"` PR title, which failed this repo's
  `pr-title` conventional-commit CI check until rewritten to `docs: …`.

### Patterns Established

- On this repo, **GSD execute-phase auto-degrades to sequential-on-main** whenever local `main` is
  ahead of `origin` — and that mode is mandatory for any plan touching `.beads/`.
- **Publishing goes through PRs** (protected `main` + release-please), never direct pushes; feature
  branch → PR → merge, then reset local `main` clean.
- **release-please owns versioning** — GSD milestone completion must **skip** the manual `v1.0` git
  tag to avoid colliding with the `vX.Y.Z` release pipeline.

### Key Lessons

1. Capability gates default to *active* when `workflow.*` config is unset; on a docs/skills repo,
   `ui.plan-gate` and the `security` ship-gate both false-block — set `--skip-ui` /
   `workflow.security_enforcement=false` (or run the real gate) knowingly.
2. Worktree isolation is unsafe for `bd`-writing plans because the Dolt DB is gitignored; the
   base-check auto-degrade to sequential-on-main is the correct behavior, not a limitation.
3. Don't hand-tag milestones on a release-please repo — the planning milestone (`v1.0`) and the
   release version are different namespaces.

### Cost Observations

- Model mix: orchestration on Opus; executors, verifier, and code-reviewer on Sonnet.
- Sessions: 1 (Phase 5 execute → ship → merge → milestone close).
- Notable: lean orchestrator (paths not file contents to subagents) kept main-loop context low
  across a five-subagent phase.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | 1 | 5 (1 via GSD) | First GSD-tracked phase on a retrospectively-bootstrapped, already-shipped project |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | `task test` 571 passing | n/a (docs/governance milestone) | 1 (`tests/test_skill_catalog.py`, stdlib-only) |

### Top Lessons (Verified Across Milestones)

1. On this repo, publish through PRs and let release-please own versioning — never direct-push `main` or hand-tag.
2. GSD capability defaults must be read against actual repo shape; docs/skills repos trip UI and security gates that don't apply.
