---
description: Read-only adversarial review of a plan. Emits VERDICT: READY|NOT READY + findings.
argument-hint: "[plan-path]"
allowed-tools: "Read, Grep, Glob, Bash, mcp__probe__*, mcp__context7__*, mcp__deepwiki__*"
---

# /review-plan

Dispatch the `plan-reviewer` agent against the plan at `$ARGUMENTS`.

The agent is read-only. It returns a machine-parseable verdict on its first
non-empty line (`VERDICT: READY` or `VERDICT: NOT READY`, matching
`^VERDICT: (READY|NOT READY)$`) followed by grounded findings in markdown.

The agent verifies Rule 7 grounding traces by reading the design bead's
notes via `bd show <design-bead-id>` (read-only). It also probe-verifies
file paths and function signatures cited in the plan.

If the verdict is `NOT READY`, revise the plan based on the findings and
re-invoke this command. There is no auto-retry — review loops are user-paced.

If the verdict is missing or unparseable, treat the result as NOT READY and
inspect the agent's full output.
