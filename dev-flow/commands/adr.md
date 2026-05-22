---
description: ADR lifecycle operations. Modes: init, new, propose, update, supersede, addendum, accept, deprecate, render, migrate.
argument-hint: "init | new | propose | update <id> | supersede <old-id> | addendum <id> --text \"...\" | accept <id> | deprecate <id> --reason \"...\" | render <id> | migrate [--apply]"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Bash(bd:*)", "Bash(jq:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-adr.formula.toml\" .beads/formulas/:*)", "Bash(dev-flow/scripts/render-adr:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(date:*)"]
---

# /adr

ADR lifecycle operations. bd is the source of truth; this command mutates bd state and re-renders `docs/adr/<id>-<slug>.md` via `dev-flow/scripts/render-adr`. See `dev-flow:evolve-adr` for the canonical reference (capture-vs-propose distinction, status mechanics, migration).

Parse `$ARGUMENTS` as one of:

- `init` — Bootstrap this repo: copy `formula-adr.formula.toml` into `.beads/formulas/`. Idempotent.
- `new` — Retrospective documentation. Creates ADR + auto-closes (Accepted).
- `propose` — Forward-looking. Creates ADR (Proposed; bd status=open).
- `update <id>` — Edit an ADR's body or sections; re-render.
- `supersede <old-id>` — Create a new ADR that supersedes `<old-id>`; wire the dep edge; re-render both.
- `addendum <id> --text "..."` — Append clarification as a bd note; re-render.
- `accept <id>` — Close a Proposed ADR (status flips to Accepted); re-render.
- `deprecate <id> --reason "..."` — Add `adr:deprecated` label; re-render.
- `render <id>` — Re-render only; no bd mutation.
- `migrate [--apply]` — Backfill metadata + re-render legacy ADRs. Defaults to dry-run; `--apply` mutates.

Remaining mode bodies are filled in by Tasks 4–7 of `docs/superpowers/plans/2026-05-22-adr-evolution.md`. This stub MUST refuse all modes other than usage until those tasks land.
