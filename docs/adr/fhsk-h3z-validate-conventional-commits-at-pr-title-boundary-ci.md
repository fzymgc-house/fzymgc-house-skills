---
title: "Validate conventional commits at the PR-title boundary in CI"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-h3z; do not edit manually; use `/adr update fhsk-h3z` -->

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-h3z
**Deciders:** Sean Brandt

## Context

jj operations do not fire git commit-msg hooks reliably in a colocated repo, so the lefthook commit-msg `cog verify` gate was unreliable. PRs land via squash-merge, so the PR title becomes the commit message cog reads for bump computation.

## Decision

Remove the lefthook commit-msg hook and validate the PR title with `cog verify` in a CI workflow on all pull_request events targeting main.

## Rationale

- jj VCS operations bypass git hooks, making local commit-msg validation unreliable here.
- With squash-merge, the PR title is the exact string `cog bump --auto` reads; validating it is more accurate than validating intermediate commits.
- A CI gate is enforceable as a required status check, unlike an opt-out-able local hook.

## Alternatives Considered

- **Local git commit-msg hook via lefthook** (rejected): catches violations pre-push, but does not fire on jj operations — false coverage.
- **CI cog verify on PR title** (chosen): always fires regardless of VCS client; validates the string cog actually uses.

## Consequences

- Positive: validation reliable whether contributors use git or jj; PR title checked against the bump-computation string.
- Negative: feedback arrives at PR open/edit, not at commit time.
- Neutral: the lefthook pre-commit hook is retained; only commit-msg is removed.
