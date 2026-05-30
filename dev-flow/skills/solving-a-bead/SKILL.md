---
name: solving-a-bead
description: Use when asked to solve, fix, address, or work a specific bead/issue by ID — validates the bead is open and unblocked, creates an isolated workspace off latest main, separates the problem from any suggested fix (treating suggested fixes as non-authoritative hypotheses), then drives a root-caused, TDD solution.
argument-hint: "[bead-id]"
metadata:
  author: fzymgc-house
---

# Solving a Bead

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**

## Overview

Drive a single bead, interactively and in this session, from validation through
a root-caused, test-driven fix to a clean hand-off.

This fills the gap between two existing skills: `handoff-prompt` briefs a
*fresh* session on a bead, and `draining-beads` runs a queue of beads
*autonomously*. Neither works **one bead, interactively, here, now** — that is
this skill.

**Core principle:** A suggested fix written in a bead is a **hypothesis to
validate, never an instruction to follow.** The bead authoritatively states the
*problem*; any "fix it by…" text is a lead, confirmed or discarded by root-cause
analysis.

**Announce at start:** "I'm using the solving-a-bead skill to resolve `<bead-id>`."

## Checklist

Work through these phases in order. The target bead (tracked in `bd`) is the
unit of work — do not open a separate TodoWrite list.

- [ ] **Phase 0 — Validate** (hard gates; abort on failure)
- [ ] **Phase 1 — Claim & isolate**
- [ ] **Phase 2 — Triage** (separate problem from candidate fixes; route)
- [ ] **Phase 3 — TDD implementation**
- [ ] **Phase 4 — Verify & hand off**

## Phase 0 — Validate (hard gates; abort on any failure)

Run from the **main checkout**, before any workspace exists.

1. **Execute the validator** — one read-only script runs all four Phase 0 gates
   (exists → not `phase:design` → status workable → no unmet blockers):

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/skills/solving-a-bead/scripts/validate-bead" "$BEAD_ID"
   ```

   `${CLAUDE_PLUGIN_ROOT}` is substituted with the plugin's install directory, so
   the script resolves regardless of the current working directory (you are in the
   consumer's repo, not this plugin's source tree). Do not use a repo-relative path.

   Branch on its **exit code**; any non-zero aborts — do not proceed to Phase 1.
   On exit `0` it prints the captured context, which also satisfies Phase 1
   step 2 (no second `bd show` needed).

   | Exit | Gate | Meaning / action |
   |---|---|---|
   | `0` | all pass | Proceed. Context (title / type / status / labels / description / notes) is on stdout. |
   | `1` | missing / usage | No such bead, or no id supplied. Stop. |
   | `2` | `phase:design` | Design-lifecycle bead (Rule 6) — **HARD-REDIRECT**, never claimed. The script prints the note-aware next step (`brainstorming` / `writing-plans` / `plan-to-beads`). Stop. |
   | `3` | status | `closed` / `in_review` / other — its implementation phase is over. Stop. |
   | `4` | unmet blockers | A non-closed `blocks` dependency exists; finish it first. Stop. |

   The blocker gate is a hard block because a bead's dependency graph expresses
   correctness preconditions, not scheduling hints — building a fix on an unmet
   blocker risks invalidation (ADR `fhsk-3xn`). Do not hand-reimplement these
   checks; the script is the source of truth and handles bd's quirks
   (`bd show --json` returns a single-element array; the type field is
   `issue_type`).

## Phase 1 — Claim & isolate

2. **Capture context.** The Phase 0 validator already printed title, type,
   status, description, notes, and labels — note the acceptance criteria and the
   `model:*` / `agent:*` labels for routing and model selection.

3. **Claim — from the main checkout:**

   ```bash
   bd update "$BEAD_ID" --claim
   ```

   Atomic; sets `in_progress` + assignee. Claim from the main checkout (not from
   inside the workspace you are about to create) to avoid the macOS sandbox
   SQLite-write-in-worktree issue.

4. **Isolate.** Invoke `dev-flow:using-worktrees` to create an isolated
   workspace off **latest main** (it fetches first and selects git worktree /
   jj workspace by VCS detection), and move into it. The sequence is deliberate:
   validate → workspace → triage.

## Phase 2 — Triage (the core mechanism)

5. **Restate the problem in your own words**, then split the bead body into two
   explicitly labeled buckets:

   - **Problem / symptom / desired outcome** — *authoritative.* This is what you
     must actually solve.
   - **Candidate solutions (NON-AUTHORITATIVE — to be validated, never followed
     blindly)** — every "fix it by…", "do X", "the solution is Y" sentence from
     the bead lands here, demoted to hypothesis status.

   Never skip this split, even when the bead's suggested fix looks obviously
   correct. See ADR `fhsk-ypt`.

6. **Route by classification:**

   | Bead shape | Route |
   |---|---|
   | `bug` / defect / error / unexpected behavior | `dev-flow:systematic-debugging` — its Iron Law (*NO FIXES WITHOUT ROOT CAUSE FIRST*) is the guarantee; each candidate solution enters as a hypothesis, adopted only if the confirmed root cause demands it |
   | Ambiguous / feature / unclear approach | `dev-flow:brainstorming`, scoped to this bead |
   | Approach is concrete — bug reproduced, or acceptance criteria specific and the path mechanical | Straight to Phase 3 |

   The type field is **not** a specification: never send a bead straight to
   Phase 3 merely because it is typed `task` / `chore`. Skip brainstorming only
   when the approach is genuinely concrete; when in doubt, brainstorm.

   The scoped brainstorm has two terminal outcomes:

   - **Converges** on a clear, one-bead approach → continue into Phase 3 here.
   - **Reveals design-scale work** — spec-worthy, spans subsystems, or would
     materialize into multiple beads → **stop. Do not build.** Leave the bead
     `in_progress`, `bd note` the finding, and pivot to the formal lifecycle
     (open/continue a design bead → `brainstorming` → `writing-plans` →
     `plan-to-beads`). One-bead TDD is structurally wrong for design-scale work.

## Red Flags

These thoughts mean STOP — you are about to treat a hypothesis as an instruction:

| Thought | Reality |
|---|---|
| "The bead says to fix it by doing X" | X is a hypothesis. Confirm the root cause requires X before implementing. |
| "The reporter already diagnosed it" | Reporter diagnosis is a lead, not a conclusion. Reproduce and verify. |
| "This is obviously the fix" | Obvious fixes mask root causes. systematic-debugging Phase 1 first. |
| "It's typed `task`, so it's clear enough to build" | Type is not specification. Brainstorm unless the approach is concrete or the bug is reproduced. |

## Phase 3 — TDD implementation

7. Invoke `dev-flow:test-driven-development`: write a failing test that encodes
   the bead's acceptance criteria (or reproduces the bug) → watch it fail →
   write minimal code to pass → refactor. Drive in TDD as far as the work
   allows; for genuinely untestable changes (config, docs, generated content),
   use TDD's documented exception and ask the human partner before skipping.

8. Run the bead's verification commands (from its `--notes`) plus the project
   quality gates relevant to the surface you changed.

## Phase 4 — Verify & hand off

9. Apply `dev-flow:verification-before-completion` — show the actual command
   output before claiming anything passes. Evidence before assertions.

10. Record the outcome on the bead:

    ```bash
    bd note "$BEAD_ID" "Root cause: <…>. Fix: <…>."
    ```

    **Leave the bead `in_progress`.** Closure happens at merge, not here — do not
    close it and do not open a PR automatically. See ADR `fhsk-hj3`.

11. **Ask the operator whether to finish the branch now** via
    `AskUserQuestion` — do not stop at a passive text suggestion. The bead
    stays `in_progress` either way; this only decides whether to integrate now.

    > "Bead solved and left `in_progress`. Finish the development branch now,
    > or keep working on it?"

    - **Finish now** — **REQUIRED SUB-SKILL:** Use
      `dev-flow:finishing-a-development-branch` (Step 0 pre-flight reconciles
      bead state; tests → merge / PR / cleanup options → execute; Step 5.5
      closes the epic at merge). Announce: "I'm using the
      finishing-a-development-branch skill to complete this work."
    - **Keep working** — stop here. The bead remains `in_progress`; finish
      later when the branch's remaining beads are solved (closure still
      happens at merge, per ADR `fhsk-hj3`).

    If `AskUserQuestion` is unavailable (non-interactive context), default to
    **Finish now** and invoke the sub-skill directly.

## Quick Reference

| Phase | Action | Abort/Stop condition |
|-------|--------|----------------------|
| 0 Validate | exists + not `phase:design` + status workable + no unmet blockers | missing / `phase:design` / closed / in_review / blocked |
| 1 Claim & isolate | `bd update --claim`, then `using-worktrees` | — |
| 2 Triage | split problem vs candidate fix; route by approach-clarity | design-scale → pivot to formal lifecycle |
| 3 TDD | failing test → minimal code → refactor → gates | — |
| 4 Verify & hand off | evidence, `bd note`, leave `in_progress`, `AskUserQuestion` → finish now or keep working | — |
