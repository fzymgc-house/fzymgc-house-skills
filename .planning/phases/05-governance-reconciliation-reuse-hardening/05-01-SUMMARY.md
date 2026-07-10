---
phase: 05-governance-reconciliation-reuse-hardening
plan: 01
subsystem: docs
tags: [adr, governance, release-please, supersession, bd, layout]

# Dependency graph
requires: []
provides:
  - "fhsk-o9o: corrected release-please versioning ADR (six synced manifests) superseding fhsk-dgo"
  - "fhsk-wdk: shipped 5-plugin root layout ADR, Related to fhsk-o9o and fhsk-a6v"
  - "docs/adr/README.md index regenerated with both new ADRs and fhsk-dgo flipped to Superseded"
affects: [05-02, GOV-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct bd create --type decision + render-adr path for retrospective ADR authoring (evolve-adr /adr new semantics), bypassing the interactive capture-adrs approval loop when no main-session AskUserQuestion is available"

key-files:
  created:
    - docs/adr/fhsk-o9o-use-release-please-file-plugin-versions-across-six-shipped-m.md
    - docs/adr/fhsk-wdk-record-shipped-5-plugin-root-layout-superseding-design-plan.md
  modified:
    - docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md
    - docs/adr/README.md

key-decisions:
  - "fhsk-o9o re-homes (not reverses) the release-please decision, correcting the synced-manifest list from four to the current six (adds tmux/plugin.json, grepping/plugin.json)"
  - "fhsk-wdk records the shipped 5-plugin root layout (homelab, jj, dev-flow, tmux, grepping) and marks the release-please design plan's fzymgc-house/skills/* per-skill package layout superseded-in-practice via prose only (no bd dep edge, since the design plan is not a bd bead)"
  - "fhsk-wdk is standalone: zero outgoing supersedes edges; Related to fhsk-o9o and fhsk-a6v as body bullets in its References section"
  - "fhsk-toy and fhsk-7y4 remain superseded by fhsk-dgo only; the new supersedes edge targets fhsk-dgo exclusively, keeping the chain unbroken"

patterns-established:
  - "Real bd-assigned ids substituted for the plan's fhsk-AAA/fhsk-BBB placeholders: fhsk-AAA -> fhsk-o9o, fhsk-BBB -> fhsk-wdk"

requirements-completed: [GOV-01]

coverage:
  - id: D1
    description: "fhsk-o9o authored (bd decision bead + rendered ADR), supersedes fhsk-dgo via a bd dep edge, and its Decision section names all six current release-please-config.json extra-files manifests"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "bd dep list fhsk-dgo --direction=up --type=supersedes (returns fhsk-o9o); rg grepping/plugin.json + tmux/plugin.json docs/adr/fhsk-o9o-*.md"
        status: pass
      - kind: other
        ref: "dev-flow/scripts/adr-doctor (INV-A22 no drift, INV-A25 title frontmatter)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fhsk-dgo re-rendered to Superseded by fhsk-o9o; fhsk-toy/fhsk-7y4 remain superseded by fhsk-dgo only (chain unbroken, no re-declaration)"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "rg 'Superseded by fhsk-o9o' docs/adr/fhsk-dgo-*.md; rg -q 'Supersedes: fhsk-toy|fhsk-7y4' docs/adr/fhsk-o9o-*.md returns no match"
        status: pass
    human_judgment: false
  - id: D3
    description: "fhsk-wdk authored recording the shipped 5-plugin layout, marking fzymgc-house/skills/* superseded-in-practice in prose, Related (not Supersedes) to fhsk-o9o and fhsk-a6v, with zero outgoing supersedes edges"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "rg 'Related: fhsk-a6v' + 'Related: fhsk-o9o' docs/adr/fhsk-wdk-*.md; bd dep list fhsk-wdk --direction=down --type=supersedes returns empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/adr/README.md index regenerated with rows for fhsk-o9o and fhsk-wdk, fhsk-dgo row flipped to Superseded by fhsk-o9o; task lint and tests/test_adr_docs.py both green"
    requirement: "GOV-01"
    verification:
      - kind: other
        ref: "task lint (rumdl, ruff, jq, evals schema, adr-doctor all clean)"
        status: pass
      - kind: unit
        ref: "tests/test_adr_docs.py -q --import-mode=importlib (4 passed)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-10
status: complete
---

# Phase 05 Plan 01: Governance ADR Reconciliation Summary

**Two new ADRs (fhsk-o9o, fhsk-wdk) authored via the direct bd + render-adr path close GOV-01: fhsk-o9o corrects the release-please synced-manifest list from four to six and supersedes fhsk-dgo; fhsk-wdk records the shipped 5-plugin root layout and marks the design plan's per-skill package layout superseded-in-practice.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-10T03:10:10Z
- **Completed:** 2026-07-10T03:16:28Z
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified) plus `.beads/interactions.jsonl`

## Accomplishments

- Authored `fhsk-o9o` (bd decision bead, closed/Accepted) — re-homes the LOCKED release-please decision intact, correcting the synced-manifest enumeration to the current six `release-please-config.json` extra-files paths (adding `tmux/plugin.json` and `grepping/plugin.json`); supersedes `fhsk-dgo` via a `bd dep add ... --type=supersedes` edge
- Re-rendered `fhsk-dgo` to `Superseded by fhsk-o9o`; `fhsk-toy` and `fhsk-7y4` remain superseded by `fhsk-dgo` only (chain unbroken, no re-declaration on the new ADR)
- Authored `fhsk-wdk` (bd decision bead, closed/Accepted) — records the shipped 5-plugin root layout (`homelab`, `jj`, `dev-flow`, `tmux`, `grepping`), marks the release-please design plan's `fzymgc-house/skills/*` per-skill package layout superseded-in-practice (prose only, no dep edge — the design plan is not a bd bead), and records that PR-review work landed inside `dev-flow` rather than as a standalone plugin; `Related: fhsk-o9o` and `Related: fhsk-a6v` authored as literal body bullets in `## References`
- Regenerated `docs/adr/README.md`'s index table between the `BEGIN/END INDEX` sentinels (37 rows, sorted by date desc), adding rows for both new ADRs and flipping `fhsk-dgo`'s status column
- Full lint gate green: `task lint` (rumdl, ruff check/format, jq, evals schema, `adr-doctor`) and `tests/test_adr_docs.py` (4 tests) both pass with zero findings

## Task Commits

Each task was committed atomically:

1. **Task 1: Author fhsk-AAA (release-please versioning ADR) and supersede fhsk-dgo** - `12e9bc7` (feat) — real id: `fhsk-o9o`
2. **Task 2: Author fhsk-BBB (shipped 5-plugin layout ADR, Related to fhsk-AAA + fhsk-a6v)** - `fca9ba1` (feat) — real id: `fhsk-wdk`
3. **Task 3: Regenerate the ADR index and gate the whole set through adr-doctor** - `d76446d` (docs)

*Note: no separate plan-metadata commit yet — this SUMMARY.md + STATE.md + ROADMAP.md commit follows as the final commit.*

## Files Created/Modified

- `docs/adr/fhsk-o9o-use-release-please-file-plugin-versions-across-six-shipped-m.md` - new rendered ADR; release-please decision re-homed, six-manifest sync list, `Supersedes: fhsk-dgo`
- `docs/adr/fhsk-wdk-record-shipped-5-plugin-root-layout-superseding-design-plan.md` - new rendered ADR; shipped layout, `Related: fhsk-o9o` / `Related: fhsk-a6v`
- `docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md` - re-rendered; `## References` gains `- Superseded by: fhsk-o9o`
- `docs/adr/README.md` - index table regenerated between sentinels (two new rows, `fhsk-dgo` row flipped)
- `.beads/interactions.jsonl` - bd audit trail for the `bd create`/`bd close`/`bd dep add` calls in this plan

## Decisions Made

- Used the **direct bd + render-adr path** (evolve-adr's `/adr new` + `/adr supersede` semantics) rather than the interactive `capture-adrs` approval loop, per the plan's project gotcha: this executor runs as a subagent with no main-session `AskUserQuestion` (INV-A19).
- Real bd-assigned ids substituted for the plan's placeholders: **fhsk-AAA → fhsk-o9o**, **fhsk-BBB → fhsk-wdk**.
- Verified the plan's Task 2 automated verify command (`bd list --type decision --json` without `--status`) returns an empty set because `bd list` defaults to open-only status filtering, and both new decision beads are closed (Accepted). Re-ran the equivalent query with `--status open,in_progress,blocked,deferred,closed` (or `--all`) to confirm the underlying facts (Related bullets, dep-edge absence) — all passed. This is a plan-script gap, not a functional failure; no code or ADR content was affected.

## Deviations from Plan

None — plan executed exactly as written. The one item above (Task 2's literal verify command needing a `--status`/`--all` flag to see closed decision beads) is a verification-script observation, not a deviation from the plan's intent; the underlying acceptance criteria were all independently confirmed true.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GOV-01 requirement satisfied: the shipped 5-plugin layout is now recorded in a superseding ADR (`fhsk-wdk`), and the release-please versioning record (`fhsk-o9o`) is accurate against the current `release-please-config.json`.
- `docs/adr/README.md` and the full `task lint` gate are consistent and green — no drift for future ADR authoring to inherit.
- GOV-02 (low-friction cross-project adoption documentation) remains open and is unaffected by this plan.

---

*Phase: 05-governance-reconciliation-reuse-hardening*
*Completed: 2026-07-10*

## Self-Check: PASSED

All created/modified files and all task commit hashes verified present in the working tree and git log.
