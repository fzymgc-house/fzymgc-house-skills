---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** Tell your human partner that Superpowers works much better with access to subagents. The quality of its work will be significantly higher if run on a platform with subagent support (such as Claude Code or Codex). If subagents are available, use superpowers:subagent-driven-development instead of this skill.

**Autonomous mode alternative:** If your platform supports `/goal` and your work is shaped as an epic / set / cascade of beads, consider `dev-flow:draining-beads` (operator entry: `/drain <mode> <scope>`). It drains autonomously via the Stop hook without a human in the loop between beads.

## The Process

### Step 1: Load Plan + Confirm bd State

1. Read the plan file for context (acceptance criteria, ordering hints, architecture). The plan is **reference material**; the source of truth for "what work remains" is `bd ready`.
2. Verify `bd ready` returns at least one bead tied to this plan's spec/epic. If empty:
   - If the plan was never materialized (`plan-to-beads` didn't run), invoke `plan-to-beads <plan-path>` first.
   - Otherwise: all work is closed; jump to Step 3.
3. Review the plan critically — identify any questions or concerns. If concerns: raise them with your human partner before starting.

### Step 2: Execute Beads Serially

This skill is the single-session, serial counterpart to `subagent-driven-development`. Same `bd ready` loop, but each bead is executed in the **current session** instead of via a fresh subagent dispatch.

For each bead:

1. **`bd ready --json | jq '.[0]'`** — get the next unblocked bead.
2. **`bd update <id> --claim`** — atomically claim it. If the claim fails (race with another actor), loop back.
3. **Note the bead's `model:*` label as guidance.** Because this skill executes in the current session (not a fresh subagent), you cannot change models mid-task. Treat the label as a heads-up about expected reasoning load:
   - `model:opus` beads suggest the user may want to run this skill in a Claude Max / opus session. If the current session is sonnet or haiku and the bead is labeled opus, **warn the user** and let them choose: continue in-session, dispatch a subagent (handing off to `subagent-driven-development`), or pause.
   - `model:haiku` and `model:sonnet` beads proceed inline without warning.
4. **`bd show <id>`** — read the full description + acceptance criteria + notes + `--spec-id`.
5. **Execute the bead's work** in the current session: write code, run tests, commit. Follow the bite-sized steps from the corresponding plan task if the bead references it.
6. **Run verifications** as specified in the bead's acceptance criteria.
7. **`bd close <id> --reason="<one-line summary>"`** on completion. Append a `bd note <id>` with anything noteworthy (deviations, follow-ups identified).
8. **Loop to step 1** until `bd ready` returns empty.

### Step 3: Complete Development

After `bd ready` returns empty:

- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use `dev-flow:finishing-a-development-branch`
- Follow that skill: Step 0 pre-flight reconciles any stragglers; tests → options → execute choice; Step 5.5 closes the epic on merge.

**Degraded mode:** If `bd` is unavailable, fall back to reading the plan's `### Task N:` headers directly, executing each task inline. No model-label guidance; no atomic claim; no close-on-completion accounting.

## When to Stop and Ask for Help

**STOP executing immediately when:**

- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**

- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember

- `bd ready` drives task pickup; the plan is reference material
- `bd update --claim` before starting; `bd close` after completion
- Heed `model:opus` labels — warn the user if running in a weaker session
- Follow plan steps exactly when the bead references them
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**

- **superpowers:using-worktrees** - Ensures isolated workspace (creates one or verifies existing)
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
