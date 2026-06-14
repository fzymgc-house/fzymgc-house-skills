---
name: drain-with-worker
description: Launch an autonomous /drain worker in a detached cmux or tmux surface and arm a surface-aware watchdog (epic-mode drains). Use when the user runs `/drain-with-worker [cmux|tmux] DRAIN_ID` or accepts the `/drain` worker handoff. Takes an optional worker-type (auto-detected when omitted).
allowed-tools: ["Read", "AskUserQuestion", "PushNotification", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)", "Bash(command -v cmux:*)", "Bash(command -v tmux:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/drain-watchdog:*)"]
---

# drain-with-worker

Launch an autonomous `/drain` worker for an existing **live** drain bead in a
detached multiplexer surface (cmux or tmux), and arm a surface-aware watchdog so
the drain self-heals — and wakes you on a question or API error — while you walk
away. Mint the bead first with `/drain epic <id>`; pass the bead id here.

**v1 is epic-mode only.** set/cascade drains are refused fail-fast by the launch
script — drain them via the `/goal` condition `/drain` emits.

## Step 1 — Parse the invocation

Parse the argument string as `[worker-type] <drain-id>`:

- If the first token is `cmux` or `tmux`, it is the **worker-type**; the next
  token is the **drain-id**.
- Otherwise the only token is the **drain-id** and worker-type is `auto`.

`auto` resolves at runtime: inside tmux (`$TMUX`) → tmux; else cmux on PATH →
cmux; else tmux on PATH → tmux; else the launch script refuses.

## Step 2 — Validate + show the plan (no side effects)

Run the launch script in check mode:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch --check --drain-id <drain-id> --worker-type <worker-type>
```

It validates the bead (type=drain, in_progress, epic-mode, workspace/scope/
sentinel present) and resolves the multiplexer. On a non-zero exit, surface the
printed reason to the user and stop. On success it prints `multiplexer=`,
`workspace=`, `scope=`, `sentinel=` — capture `multiplexer` and `scope`.

## Step 3 — Confirm gate (AskUserQuestion)

Show the launch plan — new surface → `cd <workspace>` → `direnv allow` →
`claude --dangerously-skip-permissions` → fire `/goal` for `<drain-id>` → arm
the surface-aware watchdog — and ask via **AskUserQuestion**: "Launch the
autonomous worker for `<drain-id>` via `<multiplexer>` now?" with options
**Launch** / **Cancel**. Proceed only on **Launch**. This gate is the single
confirmation; never launch without it.

## Step 4 — Launch

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch --drain-id <drain-id> --worker-type <worker-type>
```

It spawns the surface and drives the verified `cd → direnv → claude → trust →
/goal` sequence, then prints `multiplexer=<name>` and `surface=<ref>`. Capture
both. If it exits non-zero, surface the reason and stop.

## Step 5 — Arm the surface-aware watchdog

Arm the watchdog as a **background** task (`run_in_background: true`), passing
the captured multiplexer + surface:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/drain-watchdog --multiplexer <multiplexer> --drain-id <drain-id> --scope <scope> --surface <surface>
```

When it exits with an `EXIT=<reason>` marker, react per the reaction table in
`dev-flow/references/drain-with-worker.md` and **re-arm** it (relaunch the same
command), except on `EXIT=complete`. Do not improvise the watchdog mechanics —
the reference documents every gotcha.
