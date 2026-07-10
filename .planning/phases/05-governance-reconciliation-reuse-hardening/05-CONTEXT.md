# Phase 5: Governance Reconciliation & Reuse Hardening - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>

## Phase Boundary

Close the last open thread of the marketplace project by reconciling governance
docs with shipped reality and making cross-project reuse explicit:

- **GOV-01** — Author superseding ADR(s) that record the shipped plugin layout
  (`homelab`/`jj`/`dev-flow`/`tmux`/`grepping`) and mark the release-please
  design plan's `fzymgc-house/skills/*` per-skill package layout superseded.
- **GOV-02** — Document low-friction cross-project adoption (install path +
  skill discovery) so a new org repo can add a skill following minimal, explicit
  steps.

**Scope anchor — this is a documentation/governance phase.** It reconciles and
documents already-shipped structure; it does NOT restructure plugins, change
release-please behavior, or reverse any locked decision. The release-please
decision (manifest mode, one repo-wide version) stays fully in force.

</domain>

<decisions>

## Implementation Decisions

### GOV-01 — ADR strategy (two ADRs, split concerns)

- **D-01 (supersession):** Author **two** new ADRs, not one and not an in-place
  amendment. The user chose formal supersession over "standalone + leave
  `fhsk-dgo` untouched" and over "evolve `fhsk-dgo` in place."
- **D-02 (`fhsk-AAA` — versioning):** New ADR that **`Supersedes: fhsk-dgo`**,
  carrying the release-please decision (release-please GitHub Action, manifest
  mode, one repo-wide version, automated CHANGELOG + manifest sync) forward
  **intact and still in force**. "Superseded" means *re-homed into a corrected
  record*, NOT reversed.
- **D-03 (`fhsk-AAA` has a real delta — required):** `fhsk-dgo`'s decision text
  is stale: it enumerates only **4** version-synced manifests
  (`.claude-plugin/marketplace.json`, `homelab/plugin.json`, `jj/plugin.json`,
  `dev-flow/plugin.json`). The live `release-please-config.json` `extra-files`
  syncs **6** — it adds `tmux/plugin.json` and `grepping/plugin.json` (added
  after `fhsk-dgo` was written). `fhsk-AAA` MUST correct the list to the current
  6. This drift is the substantive justification for superseding rather than
  leaving `fhsk-dgo` as-is.
- **D-04 (`fhsk-BBB` — layout):** New standalone ADR that records the shipped
  5-plugin root layout (`homelab`/`jj`/`dev-flow`/`tmux`/`grepping`) and marks
  the `fzymgc-house/skills/*` per-skill package layout (from the release-please
  **design plan**) superseded-in-practice. `Related: fhsk-AAA, fhsk-a6v` — NOT
  `Supersedes` (the design plan is not a `bd` decision bead, so no formal
  supersession edge exists; the supersession is stated in prose). `fhsk-BBB`
  should also record that PR-review work landed **inside `dev-flow`**, not as a
  standalone `pr-review` plugin.
- **D-05 (supersession chain):** After this phase the chain is
  `fhsk-toy`/`fhsk-7y4` → `fhsk-dgo` → `fhsk-AAA`. `fhsk-AAA` supersedes **only**
  `fhsk-dgo`; it MUST NOT re-declare `Supersedes: fhsk-toy`/`fhsk-7y4` (already
  superseded by `fhsk-dgo`). `fhsk-dgo`'s index status flips to Superseded.
- **D-06 (authoring path):** ADRs are NOT hand-written markdown. They pair a
  markdown file with a `bd` decision bead, are `render-adr`-generated
  (`<!-- adr-render: source=bd:... -->`), carry YAML `title:` frontmatter with
  no body H1, and MUST pass `adr-doctor` (`task lint`). Use the `capture-adrs` /
  `evolve-adr` skills and `render-adr` tooling; update `docs/adr/README.md`
  index (incl. flipping `fhsk-dgo` → Superseded).

### GOV-02 — Adoption documentation (both surfaces)

- **D-07 (doc home):** Two surfaces. A short **README quickstart** section
  ("Adopt a skill in a new repo") that points out to a canonical
  **`docs/adoption.md`**. README stays the short pointer; `docs/adoption.md`
  carries the depth (Claude install path, Codex install path, discovery,
  troubleshooting). Keep them in sync by making README the pointer and
  `docs/adoption.md` the detail.
- **D-08 (existing surface to reuse):** README already has a working
  "Installation" section (Claude `plugin marketplace add` + install-by-name;
  Codex marketplace pointer) and a plugin catalog — build on these, do not
  duplicate/replace wholesale. The Codex named-agent-dispatch limitation is
  already documented and should carry into `docs/adoption.md` troubleshooting.

### GOV-02 — Discovery surface (complete human catalog)

- **D-09 (authoritative discovery = human catalog):** The plugin→skill tables in
  README and `docs/adoption.md` are the source of truth for discovery. List
  **every shipped skill** with a one-line description + trigger. No manifest-
  generation tooling as source (rejected the "marketplace.json as machine
  source" option for now).
- **D-10 (fix the known drift):** The README `homelab` catalog currently lists
  only `terraform` and `skill-qa` but **`miniflux`** also ships in
  `homelab/skills/` — add it. Audit all five plugins' skill dirs for other gaps
  while building the complete catalog.
- **D-11 (drift enforcement — CI gate):** Add a harness-independent pytest
  (`tests/test_skill_catalog.py`, Taskfile `PYTEST_DIRS` + CI gated, mirroring
  `tests/test_codex_marketplace.py`) that enumerates `*/skills/*/SKILL.md` and
  asserts each appears in the README catalog (and the `docs/adoption.md` index).
  It should **fail today on `homelab/miniflux`**; the catalog fix (D-10) makes it
  pass. This makes "discoverable" enforceable, not aspirational.

### Claude's Discretion

- ADR IDs (`fhsk-AAA`/`fhsk-BBB` are placeholders — `bd` assigns real 4-char IDs).
- Exact ADR titles, section prose, and `Related`/`Supersedes` frontmatter
  wording (subject to `adr-doctor` rules).
- Exact shape of the catalog table columns and the `test_skill_catalog.py`
  matching heuristic (e.g., match skill dir name vs. SKILL.md `name` frontmatter).
- Whether `docs/adoption.md` needs YAML `title:` frontmatter for external
  Starlight rendering (follow `fhsk-slp` convention if it will be ingested there).

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap

- `.planning/ROADMAP.md` — Phase 5 goal + success criteria (GOV-01, GOV-02).
- `.planning/REQUIREMENTS.md` — GOV-01/GOV-02 exact wording + traceability.
- `.planning/PROJECT.md` — Key Decisions (`DEC-release-please-versioning`,
  locked) + ADR Decision Register (Pass 2), incl. superseded-ADR list.

### GOV-01 — ADRs being reconciled

- `docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md`
  — the release-please ADR to be superseded by `fhsk-AAA`; currently LOCKED/
  Accepted, lists only 4 version-synced manifests (the stale delta).
- `docs/adr/fhsk-a6v-add-tmux-as-standalone-plugin-rather-than-folding-into-dev-f.md`
  — existing layout-precedent ADR; `fhsk-BBB` lists it as `Related`.
- `docs/plans/2026-02-16-release-please-design.md` — the design PLAN that
  contains the `fzymgc-house/skills/*` per-skill package layout being marked
  superseded (source of `DEC-release-please-versioning`).
- `docs/plans/2026-02-23-agent-plugin-restructure-design.md` — documents the
  restructure of the original single `fzymgc-house` plugin into the shipped
  layout (`homelab` + true `dev-flow`); grounding for `fhsk-BBB`.
- `docs/adr/fhsk-7y4-*.md`, `docs/adr/fhsk-toy-*.md` — already-superseded
  predecessors in the versioning chain (context for the chain, do not re-touch).

### GOV-01 — ADR authoring machinery

- `docs/adr/README.md` — ADR index (must be updated) + authoring conventions
  (`<bd-id>-<slug>.md`, capture via `capture-adrs`).
- `dev-flow/skills/capture-adrs/SKILL.md` — ADR materialization workflow.
- `dev-flow/skills/evolve-adr/SKILL.md` — ADR status/supersession changes.
- `dev-flow/scripts/_adr_render.py`, `dev-flow/scripts/_adr_doctor.py` — render +
  validation (INV-A22 content-fidelity, INV-A25 frontmatter-title). See ADRs
  `fhsk-nlw`, `fhsk-slp`, `fhsk-bmn`.

### GOV-02 — Adoption / distribution surfaces

- `README.md` — existing Installation + plugin catalog (extend; fix `miniflux`).
- `AGENTS.md` — "Release Versioning" + repo rules; source of truth (CLAUDE.md is
  a symlink to it).
- `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json` — the two
  marketplace manifests (discovery/install source).
- `release-please-config.json`, `.release-please-manifest.json` — the live
  6-manifest `extra-files` list `fhsk-AAA` must reflect.
- `Taskfile.yaml` — `PYTEST_DIRS`/gates to wire the new `test_skill_catalog.py`.
- `tests/test_codex_marketplace.py` — pattern to mirror for the catalog test.
- `.planning/codebase/STRUCTURE.md` — authoritative shipped directory/skill map.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- **ADR tooling** (`render-adr`, `adr-doctor`, `capture-adrs`, `evolve-adr`) —
  produces + validates both new ADRs; no new tooling needed for GOV-01.
- **README Installation section + plugin catalog** — extend rather than rewrite
  for GOV-02.
- **`tests/test_codex_marketplace.py`** — direct template for the new
  catalog-completeness pytest (enumerate-and-assert, Taskfile + CI wired).

### Established Patterns

- **CI drift-checks are the repo's governance idiom** (DIST-03;
  `test_codex_marketplace.py` hard-asserts the plugin list). A catalog test fits
  this pattern exactly.
- **Single source of truth** — skills live once in source plugin dirs; Codex
  wrappers symlink. Docs must not duplicate skill content, only index it.
- **Supersession discipline** — ADRs supersede via `bd`-bead `Supersedes:` edges
  validated by `adr-doctor`; plans are not in the ADR graph (hence `fhsk-BBB`
  states the plan-layout supersession in prose).

### Integration Points

- `docs/adr/README.md` index table (add 2 ADRs; flip `fhsk-dgo` → Superseded).
- `Taskfile.yaml` `PYTEST_DIRS` + `.github/workflows/ci.yaml` (new test runs in CI).
- `README.md` + new `docs/adoption.md` (adoption + catalog).
- `.planning/` docs are NOT rumdl-gated (not in Taskfile `MD_FILES`); the new
  `README.md`/`docs/adoption.md` edits ARE markdown-gated — run `task fmt`/`lint`.

### Constraint watch-outs

- Repo is jj-first when `jj root` succeeds — mutating VCS ops via jj, read-only
  git allowed.
- `fhsk-dgo` is LOCKED but correct; superseding it is a deliberate re-home with a
  factual delta (D-03), not a reversal — the ADR prose must make that explicit.

</code_context>

<specifics>

## Specific Ideas

- Two-ADR split explicitly chosen (versioning vs. layout) over a single
  consolidated packaging-governance ADR — keep the concerns separate.
- `docs/adoption.md` is the canonical adoption doc name; README carries only a
  short quickstart pointer.
- The catalog test should demonstrably fail on the current `miniflux` gap before
  the catalog fix lands (proof the gate works).

</specifics>

<deferred>

## Deferred Ideas

- **Codex marketplace versioning:** `.agents/plugins/marketplace.json` (Codex) is
  NOT in `release-please-config.json` `extra-files`, so its `$.version` is not
  auto-synced with the repo-wide version. Whether to add it for
  Claude/Codex consistency is a future consistency item — out of scope for
  Phase 5 (GOV is about recording/adopting shipped reality, not changing release
  behavior). Note only; do not change in this phase.
- **Generated catalog:** deriving the skill catalog from `marketplace.json` +
  SKILL.md frontmatter (machine-source discovery) was considered and deferred in
  favor of a hand-maintained catalog guarded by CI. Revisit if the manual
  catalog proves burdensome.

</deferred>

---

*Phase: 5-Governance Reconciliation & Reuse Hardening*
*Context gathered: 2026-07-09*
