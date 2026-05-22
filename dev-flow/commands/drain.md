---
description: Autonomous bead iteration via /goal. Modes: init, epic, set, cascade, resume.
argument-hint: "init | epic <id> | set <id...> | cascade <id...> | resume <drain-id>"
allowed-tools: ["Read", "Grep", "Glob", "Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd types:*)", "Bash(bd formula list:*)", "Bash(bd formula show:*)", "Bash(bd --json mol pour:*)", "Bash(bd mol pour:*)", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd ready:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd close:*)", "Bash(bd dep list:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.formula.toml\" .beads/formulas/:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(date:*)"]
---

# /drain

Autonomous bead-iteration harness. Drives `subagent-driven-development` across a queue of beads via Claude Code's built-in `/goal` Stop hook. See `dev-flow:draining-beads` for the canonical reference (sentinel design, halt conditions, lessons mechanism, edge cases).

Parse `$ARGUMENTS` as one of:

- `init` — Bootstrap this repo: register `drain` custom type; copy formula into `.beads/formulas/`.
- `epic <epic-id>` — Drain all open beads under `<epic-id>`.
- `set <id1> <id2> ...` — Drain only the listed beads.
- `cascade <id1> <id2> ...` — Drain seeds + transitive dependents (via `bd dep list --direction=up`).
- `resume <drain-id>` — Resume a halted drain run (recovers `mode`/`scope` from drain bead's metadata fields `drain_mode`, `drain_scope`, `drain_started_at`).
- anything else / missing — Print this usage and exit.

Remaining mode bodies are filled in by Tasks 3–8 of `docs/superpowers/plans/2026-05-22-drain-skill.md`. This stub MUST refuse all modes other than usage until those tasks land.
