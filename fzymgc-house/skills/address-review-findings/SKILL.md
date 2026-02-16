---
name: address-review-findings
description: >-
  Processes findings from review-pr by working through beads in the review
  epic. Use when the user asks to "address review findings", "fix review
  issues", "work through review beads", or "process review-pr findings".
argument-hint: "[pr-number]"
allowed-tools:
  - Task
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - "Bash(git *)"
  - "Bash(gh *)"
  - "Bash(bd create *)"
  - "Bash(bd list *)"
  - "Bash(bd update *)"
  - "Bash(bd show *)"
  - "Bash(bd dep *)"
  - "Bash(bd query *)"
  - "Bash(bd comments *)"
  - "Bash(bd search *)"
metadata:
  author: fzymgc-house
  version: 0.1.0
---

# Address Review Findings

Process findings from a `review-pr` run by working through the beads
in the review epic. Each finding is triaged, fixed by a sub-agent,
batch-reviewed, and closed.

**Read** `references/bd-reference.md` for the full `bd` CLI subset
used by this skill.

## Phase 1: Load

1. **Identify the PR.** Use `$ARGUMENTS` if provided, otherwise ask.
2. **Verify `bd`**: run `bd --version`. If it fails, stop and tell the
   user: "beads CLI (`bd`) is required but not found. Install beads and
   run `bd init` in the target project."
3. **Query the review epic bead:**

   ```bash
   bd list --labels "pr-review,pr:<number>" --status open --json
   ```

   If no review epic exists, stop: "No review findings for PR #N.
   Run `/review-pr <number>` first."

4. **Load all open findings:**

   ```bash
   bd list --parent <review-epic-id> --status open --json
   ```

   If no open findings, report "All findings already addressed" and stop.

5. **Locate worktree.** Run `git worktree list` and check whether one
   exists for the PR's branch. If so, `cd` into it and verify with
   `git branch --show-current`. If not, ask the user whether to create
   one. **MUST** use an existing worktree if one matches.
