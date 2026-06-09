<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-dgo; do not edit manually; use `/adr update fhsk-dgo` -->

# Use release-please with in-file plugin versions (reverse cog tag-only)

**Date:** 2026-06-09
**Status:** Accepted
**Decision:** fhsk-dgo
**Deciders:** Sean Brandt

## Context

The repo previously moved to cog tag-only releases (fhsk-toy) and a single repo-wide version with no in-file version numbers (fhsk-7y4). A key reason for tag-only was avoiding a GitHub App / branch-protection bypass for release commits. Since then the sibling repos weft and engram standardized on release-please, driven by an org-wide release-please GitHub App that is already a bypass actor on protected main — so the bypass-token cost that motivated fhsk-toy is already paid org-wide. Consistency across repos (weft, engram, soon holomush), a reviewable release PR, and an in-repo CHANGELOG.md are now wanted.

## Decision

Reverse to release-please for this repo. release-please (push-triggered on main, authenticated by the org-wide RELEASE_PLEASE_APP_ID / RELEASE_PLEASE_PRIVATE_KEY App) maintains a release PR that bumps a single repo-wide version in .release-please-manifest.json plus the $.version of the source plugin manifests (.claude-plugin/marketplace.json, homelab/plugin.json, jj/plugin.json, dev-flow/plugin.json) via release-please-config.json extra-files, plus CHANGELOG.md; merging the release PR cuts the vX.Y.Z tag and GitHub Release. cog is removed entirely; PR-title conventional-commit validation moves to amannn/action-semantic-pull-request.

## Rationale

- The org-wide release-please GitHub App already exists and is a protect-main bypass actor (weft/engram), so fhsk-toy's bypass-token concern is resolved.
- Consistency with weft/engram (and planned holomush) on one release toolchain.
- release-please produces an in-repo CHANGELOG.md and a reviewable release PR (the release preview).
- In-file $.version restores at-a-glance plugin versions; release-please keeps them in sync atomically, mitigating the manifest drift that motivated fhsk-7y4.

## Alternatives Considered

- Keep cog tag-only (status quo): no commit to main, but no CHANGELOG, diverges from sibling repos, and the no-op-bump path failed CI by re-releasing an existing tag.
- release-please manifest-only (no in-file versions): preserves fhsk-7y4's SHA-only model but diverges from weft/engram which version plugin.json. Rejected in favor of mirroring the sibling repos.

## Consequences

- Positive: in-repo CHANGELOG.md; reviewable release PR; consistent tooling across repos; visible plugin versions.
- Negative: release tooling now commits to main (the release PR) and depends on the release-please GitHub App, its protect-main bypass, and correct app permissions; reintroduces $.version fields that must not be hand-edited (release-please owns them).
- Neutral: one repo-wide version line is retained (a single . package); installs still resolve by git commit SHA.

## References

- Supersedes: fhsk-toy
- Supersedes: fhsk-7y4
