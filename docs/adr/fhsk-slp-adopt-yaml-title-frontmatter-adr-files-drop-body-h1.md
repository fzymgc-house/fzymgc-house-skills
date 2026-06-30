---
title: "Adopt YAML title frontmatter in ADR files, drop body H1"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-slp; do not edit manually; use `/adr update fhsk-slp` -->

**Date:** 2026-06-30
**Status:** Accepted
**Decision:** fhsk-slp
**Deciders:** Sean Brandt (@seanb4t)

## Context

render-adr emitted ADRs in a legacy format: an HTML comment header, a body `# TITLE` H1, and no YAML frontmatter. Astro Starlight builds docs/adr/*.md as a content collection that requires a `title:` frontmatter field on every page and renders its own H1 from it, so a body H1 produces a duplicate. Four ADRs in the homelab repo (issue hl-386w, PR #1290) needed hand-fixes before the docs build went green, exposing the shared render-adr script as the root cause.

## Decision

render-adr emits a YAML frontmatter block (`---` / `title: "<TITLE>"` / `---`) as the first bytes of every ADR file and omits the body `# TITLE` H1. Date, Status, Decision, and Deciders remain as bold body lines.

## Rationale

- Starlight requires `title:` per page and renders its own H1; a body H1 is a visible duplicate.
- Title-only frontmatter preserves every existing adr-doctor grep pattern (INV-A4/A5/A13) without modification.
- Fixing the shared script propagates the fix to all downstream consumers (homelab, future repos) when they bump the plugin cache.

## Alternatives Considered

- **Add `title:` frontmatter + remove body H1 (chosen):** satisfies Starlight's required contract; prevents the duplicate H1; one fix for all consumers.
- **Relax the Starlight schema to derive title from the body H1 (rejected):** unsupported — Starlight does not derive title from a heading; would require patching Starlight internals.
- **Keep the legacy format and hand-fix per downstream repo (rejected):** repeats the manual fix in every repo; scales poorly.
- **Lift Date/Status/Decision/Deciders into frontmatter too (rejected/deferred):** breaks adr-doctor's grep-based invariants and exceeds the Starlight blocker's scope.

## Consequences

- Positive: the Starlight deploy check passes without hand-fixes; a single authoritative ADR format for all consumers.
- Negative: all 32 committed ADR files must be regenerated; downstream repos must bump the plugin cache to re-render consistently.
- Neutral: the inline `<!-- markdownlint-disable MD013 -->` comment is preserved; MD041 is unaffected because docs/adr/ is excluded from the rumdl MD_FILES gate.
