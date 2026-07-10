---
title: "Record the shipped 5-plugin root layout, superseding the design-plan per-skill package layout in practice"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-wdk; do not edit manually; use `/adr update fhsk-wdk` -->

**Date:** 2026-07-10
**Status:** Accepted
**Decision:** fhsk-wdk
**Deciders:** Sean Brandt

## Context

The original single `fzymgc-house` plugin, and the release-please design
plan's `fzymgc-house/skills/*` per-skill package layout, were both
superseded in practice by the shipped restructure. The governance record
never captured the as-shipped layout, leaving a gap between what the
release-please ADR's Decision prose implied about directory paths and what
the marketplace actually ships.

## Decision

Record the shipped 5-plugin ROOT layout: `homelab`, `jj`, `dev-flow`,
`tmux`, `grepping`, each a top-level plugin directory (`plugin.json` +
`skills/`), with Codex thin wrappers under `plugins/<name>/` that symlink
back to the source directory (single source of truth; no content
duplication).

The design plan's `fzymgc-house/skills/*` per-skill package layout
(`fzymgc-house/skills/grafana`, `fzymgc-house/skills/terraform`,
`fzymgc-house/skills/review-pr`, `fzymgc-house/skills/respond-to-pr-comments`,
`fzymgc-house/skills/address-review-findings`, `fzymgc-house/skills/skill-qa`)
is SUPERSEDED-IN-PRACTICE by this shipped layout.

PR-review work landed INSIDE `dev-flow` — the `review-pr`, `address-findings`,
and `respond-to-comments` skills plus their review/fix/verification agents —
NOT as a standalone `pr-review` plugin.

## Rationale

- One-plugin-per-tool-domain taxonomy, consistent with fhsk-a6v's tmux
  precedent.
- Reuse without cross-plugin coupling: a top-level plugin's skills are
  available to any consumer repo without a cross-plugin dependency.
- Matches what actually shipped and what the marketplace manifests and CI
  drift checks already assert.

## Alternatives Considered

- **A single broad packaging-governance ADR folding versioning + layout
  together (rejected):** the user chose to split concerns into two ADRs
  (D-01) — one for the release-please mechanism (fhsk-o9o), one for the
  shipped layout (this ADR).
- **A standalone `pr-review` plugin (rejected):** PR-review work shipped
  inside `dev-flow` as skills + agents, not as its own top-level plugin.

## Consequences

- Positive: the governance record now matches the shipped tree; a reader
  following the ADR trail sees the correct plugin boundaries.
- Negative: none — this is a documentation-only reconciliation with no
  runtime or packaging changes.
- Neutral: the design plan's per-skill package layout remains readable as
  historical context; it is marked superseded-in-practice here rather than
  edited or deleted.

## References

- Related: fhsk-o9o
- Related: fhsk-a6v
