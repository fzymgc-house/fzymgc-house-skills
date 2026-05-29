---
name: requesting-code-review
description: >-
  Use when completing tasks, implementing major features, or before merging
  to verify work meets requirements (supports git and jj)
metadata:
  author: fzymgc-house
---

# Requesting Code Review

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**

Dispatch a code reviewer subagent to catch issues before they
cascade. The reviewer gets precisely crafted context for evaluation --
never your session's history. This keeps the reviewer focused on the work
product, not your thought process, and preserves your own context for
continued work.

**Core principle:** Review early, review often.

## This vs `/review-pr`

These are two tiers of review, not alternatives:

| | `requesting-code-review` (this skill) | `/review-pr` (`dev-flow:review-pr`) |
|---|---|---|
| When | In the task loop, **before** a PR exists | **After** the PR is opened |
| Reviewer | One `general-purpose` subagent, one lens | Full aspect agent set (code, security, tests, types, …) |
| Output | Inline verdict you act on now | Findings filed as beads + a PASS verdict |
| Role | Catch issues early so they don't compound | The merge gate (`finishing-a-development-branch` loops it to PASS) |

Use this skill at task checkpoints. It does **not** replace the post-PR
`/review-pr` gate, and it does **not** file beads. For multi-aspect coverage,
open the PR and run `/review-pr`.

## VCS Detection

```bash
if jj root >/dev/null 2>&1; then
  VCS=jj
else
  VCS=git
fi
```

## When to Request Review

**Mandatory:**

- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**

- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get commit SHAs:**

**git:**

```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**jj:**

In jj, `@` is the empty working-copy commit. `@-` is the meaningful
commit (your latest change), and `@--` is its parent (the base for review).

```bash
BASE_SHA=$(jj log -r '@--' --no-graph -T 'commit_id.short(12)')
HEAD_SHA=$(jj log -r '@-' --no-graph -T 'commit_id.short(12)')
```

**2. Dispatch code reviewer subagent:**

Use Task tool with `general-purpose` type, fill template at `code-reviewer.md`

**Placeholders:**

- `{DESCRIPTION}` - Brief summary of what you built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit
- `{FOCUS}` - Optional lens to emphasize for this task (e.g. `security`,
  `tests`, `types`, `error handling`). Default: general code quality. This is
  a single-reviewer hint, not multi-aspect fan-out — for full coverage use
  `/review-pr` after the PR is open.

**3. Act on feedback:**

Severity vocabulary matches the shared rubric (`dev-flow/references/review-stance.md`):
`critical` / `important` / `suggestion`.

- Fix `critical` issues immediately
- Fix `important` issues before proceeding
- Note `suggestion` issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

**git:**

```text
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  FOCUS: (none — general review)
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
```

**jj:**

```text
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(jj log -r '@--' --no-graph -T 'commit_id.short(12)')
HEAD_SHA=$(jj log -r '@-' --no-graph -T 'commit_id.short(12)')

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  FOCUS: error handling
  BASE_SHA: a7981ec3d2f1
  HEAD_SHA: 3df7661b8a04
```

## Integration with Workflows

**Subagent-Driven Development:**

- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**

- Review after each task or at natural checkpoints
- Get feedback, apply, continue

**Ad-Hoc Development:**

- Review before merge
- Review when stuck

## Red Flags

**Never:**

- Skip review because "it's simple"
- Ignore `critical` issues
- Proceed with unfixed `important` issues
- Argue with valid technical feedback
- Treat this in-session pass as the merge gate — `/review-pr` (post-PR) is the
  gate `finishing-a-development-branch` loops to PASS

**If reviewer wrong:**

- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: requesting-code-review/code-reviewer.md
