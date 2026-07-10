---
title: "Use release-please with in-file plugin versions across the six shipped manifests"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-o9o; do not edit manually; use `/adr update fhsk-o9o` -->

**Date:** 2026-07-10
**Status:** Accepted
**Decision:** fhsk-o9o
**Deciders:** Sean Brandt

## Context

fhsk-dgo (Accepted, LOCKED, correct in intent) recorded the release-please
reversal, but its Decision prose enumerates only FOUR version-synced
manifests. Two plugins (tmux, grepping) were added afterward and their
plugin.json version entries are now in the live sync list. Re-home the
decision into a corrected record rather than leave stale prose. This is a
re-home, not a reversal: release-please (manifest mode, one repo-wide
version) stays fully in force.

## Decision

Reverse to release-please for this repo. release-please (push-triggered on
main, authenticated by the org-wide RELEASE_PLEASE_APP_ID /
RELEASE_PLEASE_PRIVATE_KEY App as a protect-main bypass actor) maintains a
release PR that bumps a single repo-wide version in
.release-please-manifest.json plus the $.version of the source plugin
manifests via release-please-config.json extra-files, plus CHANGELOG.md;
merging the release PR cuts the vX.Y.Z tag and GitHub Release. cog is
removed entirely; PR-title conventional-commit validation runs via
amannn/action-semantic-pull-request.

The synced-manifest list is corrected to the CURRENT SIX
release-please-config.json extra-files jsonpaths:

- .claude-plugin/marketplace.json
- homelab/plugin.json
- jj/plugin.json
- dev-flow/plugin.json
- tmux/plugin.json
- grepping/plugin.json

The last two are the delta added since fhsk-dgo. Note that
.agents/plugins/marketplace.json (Codex) is deliberately NOT in
extra-files (the Codex version is not auto-synced) — recorded, not
changed here.

## Rationale

- The four-to-six drift is the substantive justification for superseding
  rather than leaving fhsk-dgo as-is.
- Carrying the decision forward keeps one authoritative, accurate record
  instead of a stale canonical one.
- The release-please mechanism itself (manifest mode, org-wide App bypass
  actor, one repo-wide version) is unchanged and remains correct.

## Alternatives Considered

- **Leave fhsk-dgo untouched and note the drift elsewhere (rejected):**
  keeps a stale canonical record; readers following fhsk-dgo would see an
  incomplete manifest list.
- **Evolve fhsk-dgo in place (rejected):** the user chose formal
  supersession over in-place mutation of an Accepted ADR (D-01).

## Consequences

- Positive: fhsk-dgo flips to Superseded; the corrected six-manifest list
  is now canonical and matches release-please-config.json exactly.
- Negative: none — no behavior change to the release pipeline.
- Neutral: the release-please mechanism, App, and single repo-wide version
  policy are carried forward unchanged.

## References

- Supersedes: fhsk-dgo
