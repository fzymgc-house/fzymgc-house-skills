<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-e0u; do not edit manually; use `/adr update fhsk-e0u` -->

# Use two-tier spine/overlay memory scope model

**Date:** 2026-06-01
**Status:** Accepted
**Decision:** fhsk-e0u
**Deciders:** Sean Brandt

## Context

The memory-curator plugin needs a scope model that lets durable facts be shared across all workspaces of a repository while also isolating workspace-local, in-flight context. A jj repo may have many sibling workspaces sharing one `origin` remote; a fact true on the trunk checkout may be premature or wrong on a feature branch. The scope string is the single key on which store and recall must agree deterministically.

## Decision

Adopt a two-tier scope. The **spine** `repo:<id>` (keyed on the normalized `origin` remote, not the working directory) is shared across every workspace of a repo. The **overlay** `repo:<id>:ws:<workspace>` is added only for named non-default workspaces. The primary checkout is **spine-only** — there is no `ws:default` bucket. Recall merges both tiers (spine wins on duplicate ids); store defaults to the spine, using the overlay only for facts genuinely local to a line of work.

## Rationale

- Store↔recall determinism requires a key that is stable from any workspace; the spine (keyed on the origin remote) satisfies this invariant from every workspace of a repo.
- Overlay isolation prevents an in-flight branch decision from polluting recall in peer workspaces or the main checkout — they are parallel truths, not contradictions.
- Defaulting store to the spine means conventions and preferences propagate to every new workspace without user action; the overlay is opt-in only when divergence is intentional.
- Eliminating `ws:default` keeps the model clean: the spine *is* the primary-checkout view, so no special-casing is needed there.

## Alternatives Considered

### Single repo scope + workspace as record metadata (rejected)

- Strengths: simpler — one scope string, no overlay management; every memory visible everywhere immediately.
- Weaknesses: divergent in-flight branch decisions surface together with trunk conventions on every recall; no isolation. The workspace metadata tag is advisory only — no filtering is enforced by the service.

### Workspace-scoped only (rejected)

- Strengths: hard per-workspace isolation; clean per-worktree boundary.
- Weaknesses: repo-wide conventions do not propagate to a freshly created workspace; preferences must be re-taught per worktree, defeating the core use-case of durable shared context.

## Consequences

**Positive:**

- Repo-wide durable facts (conventions, gotchas, preferences) are automatically available in every new workspace without re-teaching.
- In-flight branch decisions that contradict trunk can be stored in the overlay without corrupting the spine.
- The promoting-memory skill provides a natural graduation path when work merges.

**Negative:**

- Overlay facts can linger as stale context after a workspace is abandoned; requires active promotion or teardown.
- Scope derivation must resolve a stable workspace name (jj `working_copies` or git worktree basename) on every session start.

**Neutral:**

- The service's scope field is a plain string; the two-tier convention is entirely client-enforced.
