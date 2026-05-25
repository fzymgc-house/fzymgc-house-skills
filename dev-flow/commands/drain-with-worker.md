---
description: Launch a /drain worker in a detached cmux pane + arm a stall-watchdog (epic-mode drains).
argument-hint: "<drain-id>"
allowed-tools: ["Read", "AskUserQuestion", "PushNotification", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)", "Bash(command -v cmux:*)", "Bash(cmux:*)", "Bash(direnv:*)", "Bash(sleep:*)"]
---

# /drain-with-worker

Launch an autonomous `/drain` worker for an existing **live** drain bead in a detached cmux
pane, and arm a stall-watchdog so the drain self-heals while you walk away. Mint the bead
first with `/drain epic <id>`; pass the bead id it reports here.

**v1 is epic-mode only** (the watchdog stall-probe is epic-specific). set/cascade drains are
refused fail-fast — drain them via the `/goal` condition `/drain` emits.

## Step 1 — Prerequisites (refuse early)

Parse `$ARGUMENTS` as `<drain-id>`. Execute the **Prerequisites** block from
`references/drain-with-worker.md` (type=drain, status=in_progress, mode=epic, non-empty
`drain_workspace`/`drain_scope`/`drain_sentinel`, `cmux` on PATH). On any failure, print the
message and stop.

## Step 2 — Confirm gate (AskUserQuestion)

Show the launch plan — new pane → `cd <workspace>` → `direnv allow` →
`claude --dangerously-skip-permissions` → fire the `/goal` for `<drain-id>` → arm watchdog —
and ask via **AskUserQuestion**: "Launch the autonomous worker for `<drain-id>` now?" with
options **Launch** / **Cancel**. Proceed only on **Launch**. (This gate is the single
confirmation; never launch without it.)

## Step 3 — Follow the reference

Execute the **Launch sequence** and arm the **Watchdog** exactly as specified in
`references/drain-with-worker.md`. Do not improvise the cmux mechanics — each step is
verified-before-next for documented reasons (see the Gotchas table in the reference).
