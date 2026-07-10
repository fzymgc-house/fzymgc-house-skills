# Phase 5: Governance Reconciliation & Reuse Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 5-Governance Reconciliation & Reuse Hardening
**Areas discussed:** ADR supersession mechanics, ADR scope & granularity, Adoption doc home & format, Discovery surface

---

## ADR supersession mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone + cross-ref (leave fhsk-dgo) | New Accepted ADR records shipped layout, marks design-plan `fzymgc-house/skills/*` superseded in prose, lists fhsk-dgo/fhsk-a6v as Related, leaves fhsk-dgo untouched | |
| Formally supersede fhsk-dgo | New ADR carries `Supersedes: fhsk-dgo`, re-issuing the release-please decision; fhsk-dgo → Superseded | ✓ |
| Evolve fhsk-dgo in place | No new ADR; amend fhsk-dgo References/body via evolve-adr | |

**User's choice:** Formally supersede fhsk-dgo.
**Notes:** Claude flagged that fhsk-dgo is LOCKED but correct, so superseding must carry the release-please decision forward intact ("re-homed, not reversed"). Supersession chain becomes fhsk-toy/fhsk-7y4 → fhsk-dgo → new ADR; new ADR supersedes only fhsk-dgo.

---

## ADR scope & granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Versioning + layout (tight re-home) | One ADR = fhsk-dgo's decision restated + shipped layout + `fzymgc-house/skills/*` supersession | |
| Full packaging-governance ADR | One broad ADR also folding in pr-review→dev-flow, Codex wrappers, dual-marketplace | |
| Two ADRs (split concerns) | fhsk-AAA versioning (Supersedes fhsk-dgo) + fhsk-BBB standalone layout (Related: fhsk-AAA, fhsk-a6v) | ✓ |

**User's choice:** Two ADRs (split concerns).
**Notes:** Claude then verified `release-please-config.json` syncs **6** manifests (adds tmux + grepping) while fhsk-dgo's prose lists only 4 — giving fhsk-AAA a real corrective delta (not a verbatim re-home). Captured as required planner guidance rather than re-asked.

---

## Adoption doc home & format

| Option | Description | Selected |
|--------|-------------|----------|
| Expand README + new 'Adopt in a new repo' section | Keep everything in README; add minimal quickstart | |
| Dedicated adoption doc | New docs/adoption.md (or CONTRIBUTING.md) canonical; README links | |
| Both (README quickstart + docs page) | Short README pointer + fuller docs/adoption.md (Claude + Codex + discovery + troubleshooting) | ✓ |

**User's choice:** Both.
**Notes:** README stays the short pointer; docs/adoption.md carries depth. Build on the existing README Installation section + Codex agent-dispatch limitation note.

---

## Discovery surface

| Option | Description | Selected |
|--------|-------------|----------|
| Complete human catalog (README table + docs/adoption.md index) | Plugin→skill tables are source of truth; list every skill + trigger; fix miniflux gap | ✓ |
| marketplace.json as machine source + human catalog view | Manifests + frontmatter as machine source, catalog derived | |
| Minimal: install-by-name only | Discovery = 5 plugins + install; no skill-level catalog | |

**User's choice:** Complete human catalog.
**Notes:** Claude surfaced that README's homelab table already omits the shipped `miniflux` skill (drift). Follow-up decision below hardens against recurrence.

### Follow-up — catalog drift enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Add a catalog-completeness CI test | Taskfile+CI-gated pytest asserting every `*/skills/*/SKILL.md` is in the catalog; fails today on miniflux | ✓ |
| Documentation-only (no CI gate) | Fix catalog now, rely on discipline | |

**User's choice:** Add a catalog-completeness CI test (`tests/test_skill_catalog.py`), mirroring `tests/test_codex_marketplace.py`.

## Claude's Discretion

- Real `bd`-assigned ADR IDs (fhsk-AAA/fhsk-BBB are placeholders).
- ADR titles, prose, and Related/Supersedes frontmatter wording (per adr-doctor).
- Catalog table columns + the test's matching heuristic (dir name vs. SKILL.md `name`).
- Whether docs/adoption.md needs YAML title frontmatter for Starlight rendering (per fhsk-slp).

## Deferred Ideas

- Codex `.agents/plugins/marketplace.json` is not version-synced by release-please — possible future consistency item, out of scope for Phase 5.
- Generating the catalog from marketplace.json + SKILL.md frontmatter — deferred in favor of a hand-maintained, CI-guarded catalog.
