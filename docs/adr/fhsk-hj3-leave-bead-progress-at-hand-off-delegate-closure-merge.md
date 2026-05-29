<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-hj3; do not edit manually; use `/adr update fhsk-hj3` -->

# Leave bead in_progress at hand-off; delegate closure to merge

**Date:** 2026-05-29
**Status:** Accepted
**Decision:** fhsk-hj3
**Deciders:** Sean Brandt

## Context

At the end of Phase 4, `solving-a-bead` has produced a root-caused, test-covered fix. It must decide the bead's terminal state: close it now (fix committed), auto-open a PR, or leave it `in_progress` and hand off to `finishing-a-development-branch`. This choice defines the lifecycle boundary between `solving-a-bead` and the downstream finishing skill, and determines what state the bead is in when the next skill picks it up.

## Decision

Phase 4 writes a bd note summarizing root cause and fix, leaves the bead in `in_progress` status, and suggests (but does not invoke) `dev-flow:finishing-a-development-branch`. Bead closure happens at merge, not at fix commit.

## Rationale

- Bead closure is semantically tied to merge-time verification, not to commit; closing at fix commit produces false-positive issue-tracker state.
- Auto-opening a PR duplicates `finishing-a-development-branch`'s deliberate gate sequence and bypasses operator judgment on branch readiness.
- `in_progress` accurately reflects "fix committed, not yet merged" — the most informative state for a collaborator reading the issue tracker.
- This is the same boundary used by the `/drain` → `finishing-a-development-branch` handoff pattern; `solving-a-bead` is consistent with the existing skill lifecycle contract.

## Alternatives Considered

- **Auto-close the bead at hand-off** (rejected): single-skill resolution, but conflates "fix implemented" with "fix merged and verified" and forces a false positive if the PR is later rejected.
- **Auto-open a PR at hand-off** (rejected): reduces manual steps, but bypasses `finishing-a-development-branch`'s gate sequence and operator judgment on branch readiness.
- **Leave in_progress; suggest finishing-a-development-branch** (chosen): clean separation of concerns; bd note records root cause and approach for continuity; bead status accurately reflects work-done-but-not-merged.

## Consequences

- Positive: bead status accurately reflects work state at all times — no false-positive closures; clean skill responsibility boundary; bd note provides continuity context for the next invocation.
- Negative: requires a second explicit skill invocation to complete the PR/merge workflow; a bead left `in_progress` after a stalled branch creates tracker noise.
- Neutral: consistent with the `/drain` skill's hand-off pattern, which also leaves integration to `finishing-a-development-branch`.
