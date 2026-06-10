<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-8g6; do not edit manually; use `/adr update fhsk-8g6` -->

# Drain finishes the branch autonomously (push + PR) at the clean sentinel

**Date:** 2026-06-10
**Status:** Accepted
**Decision:** fhsk-8g6
**Deciders:** Sean Brandt (@seanb4t)

## Context

At the clean drain sentinel the worker handed off to `dev-flow:finishing-a-development-branch` with a soft "invoke", and that skill always presents an interactive 4-option menu (merge / PR / keep / discard) plus `AskUserQuestion` prompts at its bd pre-flight and post-merge steps. A drain is hands-off: it runs under `/goal` with no operator between iterations, so a menu or prompt mid-loop strands the run — the worker stops at "ready to push" awaiting input that never arrives.

## Decision

At the clean sentinel the drain worker MUST finish the branch autonomously by invoking `finishing-a-development-branch` in a new non-interactive mode. That mode skips the Step 4 option menu, fixes the action to Option 2 (push + create PR) followed by the `/review-pr` gate, and replaces the Step 0 / Step 5.5 `AskUserQuestion` points with non-interactive defaults (file follow-ups; auto-close landed beads). Merge, keep, and discard remain human-only and are never auto-selected. Only a genuine push/PR failure routes to drain halt condition #3 — never a prompt back to the operator.

## Rationale

- A drain is autonomous by definition; an interactive menu mid-`/goal` contradicts that and strands the loop.
- Option 2 (push + PR) is the only safe terminal action to automate: it is additive and reversible (a PR can be closed), whereas merge / keep / discard each need human judgment.
- The `/review-pr` gate is preserved, so removing the menu does not lower the quality bar — autonomous mode removes the *prompt*, not the *gate*.

## Alternatives Considered

- **Keep the soft "invoke finishing" handoff and trust the worker to pick Option 2:** fragile — the menu invites a stop-and-ask and "ready to push" reads as a natural stopping point. Rejected.
- **Fork a separate autonomous-finish skill:** duplicates the VCS / test / gate logic and risks drift from the interactive skill. Rejected in favour of an opt-in mode on the existing skill.
- **Auto-merge at the sentinel instead of opening a PR:** removes human review of the integrated result; unsafe for an unattended loop. Rejected.

## Consequences

- Positive: a clean drain runs fully hands-off through to an open PR + gate PASS, with no operator round-trip.
- Positive: the behavior is opt-in per caller (selected by an explicit non-interactive directive), so normal interactive use of `finishing-a-development-branch` is unchanged.
- Negative: an autonomous worker can open a PR with no human in the loop until the review gate; mitigated by the gate and the human-only carve-out for merge / keep / discard.
- Neutral: the contract is documented across the `draining-beads` skill, the `finishing-a-development-branch` skill, and the drain design spec; this ADR records the decision rationale.
