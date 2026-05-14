---
description: Read-only adversarial review of a spec. Emits VERDICT: READY|NOT READY + findings.
argument-hint: "[spec-path]"
allowed-tools: "Read, Grep, Glob, mcp__probe__*, mcp__context7__*, mcp__deepwiki__*"
---

# /review-design

Dispatch the `design-reviewer` agent against the spec at `$ARGUMENTS`.

The agent is read-only. It returns a machine-parseable verdict on its first
non-empty line (`VERDICT: READY` or `VERDICT: NOT READY`, matching
`^VERDICT: (READY|NOT READY)$`) followed by grounded findings in markdown.

If the verdict is `NOT READY`, revise the spec based on the findings and
re-invoke this command. There is no auto-retry — review loops are user-paced.

If the verdict is missing or unparseable, treat the result as NOT READY and
inspect the agent's full output.
