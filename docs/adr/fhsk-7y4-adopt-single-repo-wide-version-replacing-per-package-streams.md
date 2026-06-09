<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-7y4; do not edit manually; use `/adr update fhsk-7y4` -->

# Adopt single repo-wide version replacing per-package streams

**Date:** 2026-05-29
**Status:** Superseded by fhsk-dgo
**Decision:** fhsk-7y4
**Deciders:** Sean Brandt

## Context

The repo used release-please to track 15 independently-versioned packages, each with its own semver stream and changelog. Claude Code (and Codex) install plugins by git commit SHA, so per-package semver streams have no consumer-observable effect. The in-file versions were already inconsistent (e.g. jj/plugin.json 0.1.0 vs manifest 0.6.1) with no breakage.

## Decision

Replace the 15 per-package release-please streams with a single repo-wide semver derived by cocogitto from conventional commits, seeded from the marketplace.json `$.version` at cutover (the canonical v1.x line).

## Rationale

- Installs resolve by git SHA, not in-file semver, so per-package versions are ceremony.\n- Per-package histories were already inconsistent with no observed impact.\n- One version line eliminates manifest drift and the 15-package release-please config surface.\n- Continues the marketplace.json lineage as the canonical v1.x line.

## Alternatives Considered

- **Keep per-package versioning via release-please** (rejected): fine-grained per-skill changelogs, but heavy ceremony, 15 manifests to keep in sync, already drifting, and release PRs commit to main.\n- **Single repo-wide cog tag** (chosen): one version, auto-derived from conventional commits, no manifest drift, matches how installs resolve.

## Consequences

- Positive: release reduces to one tag + one GitHub Release; no manifest sync on new skills.\n- Negative: per-skill/per-package granularity permanently lost; divergent histories (homelab 1.0.0, dev-flow 0.9.0, jj 0.6.1) discarded, not reconciled.\n- Neutral: baseline read live from marketplace.json `$.version` at cutover.

## References

- Superseded by: fhsk-dgo
