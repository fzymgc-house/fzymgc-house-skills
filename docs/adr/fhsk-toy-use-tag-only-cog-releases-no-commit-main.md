---
title: "Use tag-only cog releases with no commit to main"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-toy; do not edit manually; use `/adr update fhsk-toy` -->

**Date:** 2026-05-29
**Status:** Superseded by fhsk-dgo
**Decision:** fhsk-toy
**Deciders:** Sean Brandt

## Context

release-please creates release PRs that commit CHANGELOG.md and bumped version fields to main. This is a colocated jj+git repo on a protected main; committing release metadata needs bypass tokens and adds noise commits. The goal is GitHub Releases as the changelog surface without touching main.

## Decision

Configure cog with `disable_bump_commit = true` and `disable_changelog = true` so the release workflow creates only a `vX.Y.Z` git tag and a GitHub Release; the release process never pushes a commit to main.

## Rationale

- Avoids a GitHub App token / branch-protection bypass for release commits (plain GITHUB_TOKEN + contents:write suffices).
- `cog changelog <range>` produces equivalent human-readable release notes.
- Tag-only is proven in the holomush repo with the same cog 7.x toolchain.
- Keeps main history free of release-metadata commits.

## Alternatives Considered

- **release-please PRs committing changelog to main** (rejected): in-repo CHANGELOG.md, but commits non-functional metadata to protected main and needs the release-PR merge cycle.
- **cog tag-only (disable_bump_commit + disable_changelog)** (chosen): no commit to main; tag + GitHub Release is the changelog surface.

## Consequences

- Positive: release needs only contents:write via default GITHUB_TOKEN; main carries only functional changes.
- Negative: no in-repo CHANGELOG.md — changelog lives only in GitHub Releases.
- Neutral: cog.toml must use top-level keys (no [settings] wrapper) and must omit an empty [commit_types] block (empty {} disables a type).

## References

- Superseded by: fhsk-dgo
