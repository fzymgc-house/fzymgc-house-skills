---
phase: 05-governance-reconciliation-reuse-hardening
plan: 02
subsystem: docs
tags: [adoption, discovery, catalog, ci-drift-gate, documentation, pytest, rumdl]

# Dependency graph
requires:
  - phase: 05-governance-reconciliation-reuse-hardening (plan 01)
    provides: Phase 05 context and locked ADR decisions (D-07..D-11) driving GOV-02
provides:
  - "Complete README plugin->skill catalog covering all 32 shipped skills across 5 plugins (homelab, jj, dev-flow, tmux, grepping), including the previously-missing homelab/miniflux row"
  - "docs/adoption.md: canonical adoption guide with Claude install, Codex install, complete skill discovery index, and Codex named-agent-dispatch troubleshooting"
  - "tests/test_skill_catalog.py: CI-gated drift test that fails if any shipped skill is missing from the README catalog or the adoption.md index"
  - "Taskfile.yaml MD_FILES gated docs/adoption.md for rumdl markdown linting"
affects: [governance, documentation, ci]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Filesystem-as-source-of-truth drift gate: enumerate */skills/*/SKILL.md on disk, assert membership in doc surfaces, rather than hardcoding a skill list in the test"

key-files:
  created:
    - tests/test_skill_catalog.py
    - docs/adoption.md
  modified:
    - README.md
    - Taskfile.yaml

key-decisions:
  - "Scoped the skill-enumeration glob to exclude dot-prefixed top-level directories (e.g. .claude/skills/core.gc-*), since those are locally-installed Claude Code skills from other marketplaces, not skills this repo ships"
  - "No PYTEST_DIRS or CI-yaml edit needed: tests/ was already listed in Taskfile.yaml PYTEST_DIRS, and CI invokes task lint / task test directly, so the new test is auto-discovered by placement alone"
  - "Kept docs/adoption.md as plain markdown (no YAML title frontmatter) — the fhsk-slp Starlight frontmatter convention applies to docs/adr/*.md specifically; docs/adoption.md follows the existing docs/dev-flow-pipeline.md convention of a plain H1"
  - "Removed a stale .rumdl_cache directory that caused a false-positive MD057 (relative link does not exist) for the newly-created docs/adoption.md — a Rule 3 blocking-fix, not a scope change"

patterns-established:
  - "Skill catalog completeness is enforced by test, not discipline: any future skill addition that omits a README/adoption.md row now fails task test in CI"

requirements-completed: [GOV-02]

coverage:
  - id: D1
    description: "README '## Plugins' catalog lists every shipped skill (32 total, incl. homelab/miniflux) as a **name** row"
    requirement: GOV-02
    verification:
      - kind: unit
        ref: "tests/test_skill_catalog.py#test_every_skill_in_readme_catalog"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/adoption.md exists as the canonical adoption guide with Claude install, Codex install, a complete skill discovery index, and Codex-dispatch troubleshooting"
    requirement: GOV-02
    verification:
      - kind: unit
        ref: "tests/test_skill_catalog.py#test_every_skill_in_adoption_index"
        status: pass
    human_judgment: false
  - id: D3
    description: "CI drift gate demonstrably went RED (miniflux named in failure output, pre-fix) then GREEN, wired into task test / task lint"
    requirement: GOV-02
    verification:
      - kind: unit
        ref: "tests/test_skill_catalog.py (both functions)"
        status: pass
      - kind: other
        ref: "task lint (rumdl/ruff/jq/schema/adr-doctor, exit 0)"
        status: pass
      - kind: other
        ref: "task test (571 passed)"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-07-10
status: complete
---

# Phase 05 Plan 02: Skill Catalog Discovery + Adoption Guide Summary

**Closed the homelab/miniflux README gap, added a canonical docs/adoption.md, and wired a CI-gated pytest that fails if any shipped skill is undocumented in either surface.**

## Performance

- **Duration:** ~70 min (first task commit 23:22:48 -> final task commit 00:29:24)
- **Tasks:** 3
- **Files modified:** 4 (README.md, Taskfile.yaml, tests/test_skill_catalog.py created, docs/adoption.md created)

## Accomplishments

- Proved the drift gate RED first: `tests/test_skill_catalog.py` enumerated all 32 shipped skills via `*/skills/*/SKILL.md` and failed, naming `miniflux` and the missing `docs/adoption.md`
- Completed the README `## Plugins` catalog: added the missing `**miniflux**` row to homelab, and replaced dev-flow's partial "Highlights + pointer" section with a table covering all 26 dev-flow skill directories (kept the existing Highlights and PR-review groupings intact)
- Added a short `### Adopt a skill in a new repo` pointer under `## Installation` linking to `docs/adoption.md`, per D-07 (README stays shallow, adoption.md holds the depth)
- Created `docs/adoption.md`: Claude install path, Codex install path (repo-local marketplace + wrapper plugins), a complete 32-skill discovery index grouped by plugin, and a troubleshooting section carrying the Codex named-agent-dispatch limitation (D-08), referencing `dev-flow/skills/using-superpowers/references/codex-tools.md`
- Added `docs/adoption.md` to Taskfile.yaml `MD_FILES` so `task lint` rumdl-gates it; no `PYTEST_DIRS` or CI-yaml change was needed because `tests/` was already listed and CI invokes `task lint`/`task test` directly
- Full gate verified green: `task lint` (rumdl/ruff/jq/schema/adr-doctor) exits 0, `task test` exits 0 with 571 passed including both `test_skill_catalog.py` functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tests/test_skill_catalog.py (RED)** - `5755020` (test)
2. **Task 2: Complete README plugin catalog + adoption quickstart pointer** - `2371c4c` (docs)
3. **Task 3: Create docs/adoption.md + markdown-gate it (GREEN)** - `824c2b8` (docs)

*TDD-style RED->GREEN sequence: Task 1's `test` commit demonstrably failed (output contained `miniflux`) before Tasks 2-3 turned it green — this plan is `type: execute`, not a formal `type: tdd` plan, so the plan-level TDD gate enforcement doesn't strictly apply, but the RED->GREEN discipline was followed as directed by the plan's task instructions.*

## Files Created/Modified

- `tests/test_skill_catalog.py` - Enumerates `*/skills/*/SKILL.md` (excluding dot-prefixed dirs) and asserts every skill name appears as a `**name**` token in both README.md's `## Plugins` region and docs/adoption.md
- `README.md` - Added `**miniflux**` row to homelab table; replaced dev-flow's partial catalog with full 26-skill coverage; added `### Adopt a skill in a new repo` pointer section
- `docs/adoption.md` - New canonical adoption guide: Claude install, Codex install, complete 32-skill discovery index by plugin, Codex-dispatch troubleshooting
- `Taskfile.yaml` - Added `docs/adoption.md` to `MD_FILES` for rumdl gating

## Decisions Made

- Scoped the skill-enumeration glob (`*/skills/*/SKILL.md`) to exclude dot-prefixed top-level directories. The initial RED run surfaced 7 unexpected `core.gc-*` entries from `.claude/skills/` — these are locally-installed Claude Code skills from an unrelated marketplace (gastown), not skills this repo ships. Filtering by `not path.relative_to(REPO_ROOT).parts[0].startswith(".")` restores the intended 32-skill, 5-plugin scope without hardcoding plugin names.
- No `PYTEST_DIRS` or CI-yaml edit: `tests/` was already in Taskfile.yaml `PYTEST_DIRS`, and `.github/workflows/ci.yaml` invokes `task lint` / `task test` directly rather than enumerating test paths itself, so the new test is discovered automatically by file placement alone.
- `docs/adoption.md` uses plain markdown (H1, no YAML `title:` frontmatter). The fhsk-slp Starlight-frontmatter ADR convention is scoped to `docs/adr/*.md`; the existing `docs/dev-flow-pipeline.md` (a comparable non-ADR doc) uses a plain H1, and adoption.md follows that precedent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed stale `.rumdl_cache` causing a false-positive MD057 lint failure**

- **Found during:** Task 3 (wiring `docs/adoption.md` into `task lint`)
- **Issue:** `rumdl check` reported `README.md:141:22: [MD057] Relative link 'docs/adoption.md' does not exist` even though the file existed on disk and was git-staged. Isolated reproduction in a scratch directory showed the same link pattern passing cleanly, narrowing the cause to repo-local state.
- **Fix:** Found and removed a stale `.rumdl_cache` directory at the repo root; after removal, `rumdl check` correctly resolved the link and passed.
- **Files modified:** none (cache directory only, not a tracked repository file)
- **Verification:** `rumdl check --no-exclude README.md AGENTS.md CLAUDE.md docs/adoption.md` and the full `task lint` both exit 0 afterward
- **Committed in:** n/a (cache artifact, not committed; regenerates on next rumdl run)

**2. [Rule 1 - Bug] Scoped the skill glob to exclude `.claude/skills/` locally-installed skills**

- **Found during:** Task 1 (initial RED verification run)
- **Issue:** The naive `*/skills/*/SKILL.md` glob matched 7 `core.gc-*` skill dirs under `.claude/skills/` — these are locally-installed skills from an unrelated marketplace (gastown), not part of this repo's five shipped plugins, and would have forced them into the README/adoption.md catalogs incorrectly.
- **Fix:** Filtered the glob to skip paths whose top-level directory name starts with `.`.
- **Files modified:** tests/test_skill_catalog.py
- **Verification:** Re-ran the test; failure output now lists only the 25 real gaps (including `miniflux`) against the 32-skill, 5-plugin scope described in the plan
- **Committed in:** `5755020` (part of Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking lint-cache fix, 1 bug fix to the enumeration scope)
**Impact on plan:** Both fixes were necessary to make the drift gate correctly scoped and to unblock the lint gate; no scope creep beyond the plan's stated artifacts.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GOV-02 is satisfied: a new org repo can discover and install any of the 32 shipped skills via `docs/adoption.md`, and catalog drift is now caught by CI (`task test`) rather than relying on discipline.
- No blockers for subsequent Phase 05 work; this was the final plan (2 of 2) for the phase.

---

*Phase: 05-governance-reconciliation-reuse-hardening*
*Completed: 2026-07-10*

## Self-Check: PASSED

All created/modified files verified present on disk; all three task commit
hashes (5755020, 2371c4c, 824c2b8) verified in `git log --oneline --all`.
