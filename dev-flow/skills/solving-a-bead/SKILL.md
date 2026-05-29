---
name: solving-a-bead
description: Use when asked to solve, fix, address, or work a specific bead/issue by ID — validates the bead is open and unblocked, creates an isolated workspace off latest main, separates the problem from any suggested fix (treating suggested fixes as non-authoritative hypotheses), then drives a root-caused, TDD solution.
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

Run these from the **main checkout**, before any workspace exists. Any failure
aborts — do not proceed to Phase 1.

1. **Arg present.** No `<bead-id>` supplied → print usage and exit.

2. **Bead exists.** Capture the JSON in a variable (no temp file):

   ```bash
   BEAD_JSON=$(bd show "$BEAD_ID" --json) || { echo "ABORT: bead $BEAD_ID not found"; exit 1; }
   ```

   (`bd show --json` returns a single-element array; read fields via `.[0]`.)

3. **Status is workable.**

   ```bash
   STATUS=$(jq -r '.[0].status' <<<"$BEAD_JSON")
   case "$STATUS" in
     open)        : ;;                                   # proceed
     in_progress) echo "NOTE: $BEAD_ID already claimed — resuming" ;;
     *)           echo "ABORT: $BEAD_ID status is '$STATUS' (need open/in_progress)"; exit 1 ;;
   esac
   ```

   `closed` and `in_review` abort: their implementation phase is over.

4. **No unmet dependencies (HARD-BLOCK).**

   ```bash
   # --type blocks filters to blocker deps; --direction=down (default) lists
   # what this bead depends on. Each record carries the dependency's own status.
   OPEN_BLOCKERS=$(bd dep list "$BEAD_ID" --type blocks --json 2>/dev/null \
     | jq -r '[.[] | select(.status != "closed")] | .[].id')
   if [ -n "$OPEN_BLOCKERS" ]; then
     echo "ABORT: $BEAD_ID has unmet blocker dependencies:"; echo "$OPEN_BLOCKERS"
     echo "Finish those beads first, then re-run /solving-a-bead $BEAD_ID"; exit 1
   fi
   ```

   A bead's dependency graph expresses correctness preconditions, not scheduling
   hints — building a fix on an unmet blocker risks invalidation. See
   ADR `fhsk-3xn`.

## Phase 1 — Claim & isolate

5. **Capture context** from the `bd show --json` you already read: title, type,
   description, acceptance criteria, notes, and labels (`model:*`, `agent:*`).

6. **Claim — from the main checkout:**

   ```bash
   bd update "$BEAD_ID" --claim
   ```

   Atomic; sets `in_progress` + assignee. Claim from the main checkout (not from
   inside the workspace you are about to create) to avoid the macOS sandbox
   SQLite-write-in-worktree issue.

7. **Isolate.** Invoke `dev-flow:using-worktrees` to create an isolated
   workspace off **latest main** (it fetches first and selects git worktree /
   jj workspace by VCS detection), and move into it. The sequence is deliberate:
   validate → workspace → triage.

## Phase 2 — Triage (the core mechanism)

8. **Restate the problem in your own words**, then split the bead body into two
   explicitly labeled buckets:

   - **Problem / symptom / desired outcome** — *authoritative.* This is what you
     must actually solve.
   - **Candidate solutions (NON-AUTHORITATIVE — to be validated, never followed
     blindly)** — every "fix it by…", "do X", "the solution is Y" sentence from
     the bead lands here, demoted to hypothesis status.

   Never skip this split, even when the bead's suggested fix looks obviously
   correct. See ADR `fhsk-ypt`.

9. **Route by classification:**

   | Bead shape | Route |
   |---|---|
   | `bug` / defect / error / unexpected behavior | `dev-flow:systematic-debugging` — its Iron Law (*NO FIXES WITHOUT ROOT CAUSE FIRST*) is the guarantee; each candidate solution enters as a hypothesis, adopted only if the confirmed root cause demands it |
   | Ambiguous / feature / unclear approach | `dev-flow:brainstorming`, scoped to this bead |
   | Clear, well-specified `task` / `chore` | Straight to Phase 3 |

## Red Flags

These thoughts mean STOP — you are about to treat a hypothesis as an instruction:

| Thought | Reality |
|---|---|
| "The bead says to fix it by doing X" | X is a hypothesis. Confirm the root cause requires X before implementing. |
| "The reporter already diagnosed it" | Reporter diagnosis is a lead, not a conclusion. Reproduce and verify. |
| "This is obviously the fix" | Obvious fixes mask root causes. systematic-debugging Phase 1 first. |

## Phase 3 — TDD implementation

10. Invoke `dev-flow:test-driven-development`: write a failing test that encodes
    the bead's acceptance criteria (or reproduces the bug) → watch it fail →
    write minimal code to pass → refactor. Drive in TDD as far as the work
    allows; for genuinely untestable changes (config, docs, generated content),
    use TDD's documented exception and ask the human partner before skipping.

11. Run the bead's verification commands (from its `--notes`) plus the project
    quality gates relevant to the surface you changed.

## Phase 4 — Verify & hand off

12. Apply `dev-flow:verification-before-completion` — show the actual command
    output before claiming anything passes. Evidence before assertions.

13. Record the outcome on the bead:

    ```bash
    bd note "$BEAD_ID" "Root cause: <…>. Fix: <…>."
    ```

    **Leave the bead `in_progress`.** Closure happens at merge, not here — do not
    close it and do not open a PR automatically. See ADR `fhsk-hj3`.

14. **Ask the operator whether to finish the branch now** via
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
| 0 Validate | exists + status workable + no unmet blockers | missing / closed / in_review / blocked |
| 1 Claim & isolate | `bd update --claim`, then `using-worktrees` | — |
| 2 Triage | split problem vs candidate fix; route by type | — |
| 3 TDD | failing test → minimal code → refactor → gates | — |
| 4 Verify & hand off | evidence, `bd note`, leave `in_progress`, `AskUserQuestion` → finish now or keep working | — |
