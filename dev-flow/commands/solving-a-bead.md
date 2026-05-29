---
description: Solve a single bead interactively — validate, isolate, triage, TDD fix, hand off.
argument-hint: "<bead-id>"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Skill(dev-flow:*)", "Bash(bd show:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd dep list:*)", "Bash(jj root:*)", "Bash(jj st:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(jq:*)"]
---

# /solving-a-bead

Resolve a single bead interactively. See `dev-flow:solving-a-bead` for the
canonical reference (phase gates, triage discipline, hand-off).

Parse `$ARGUMENTS` as a single `<bead-id>`. If it is missing or empty, print
this usage and exit:

> Usage: `/solving-a-bead <bead-id>` — validates the bead is open and
> unblocked, creates an isolated workspace off latest main, separates the
> problem from any suggested fix (treating suggested fixes as non-authoritative
> hypotheses), then drives a root-caused, TDD solution.

Otherwise, invoke the `dev-flow:solving-a-bead` skill with that bead ID.
