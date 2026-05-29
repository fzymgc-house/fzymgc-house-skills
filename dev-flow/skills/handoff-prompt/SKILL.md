---
name: handoff-prompt
description: >-
  Generate a self-contained briefing prompt that a fresh Claude (or other
  agent) session uses to pick up a bead's work without inheriting the
  current session's context. Pulls model hint from the bead's `model:*`
  label (default sonnet), routes via the bead's `agent:*` label, and defers
  workspace setup to `dev-flow:using-worktrees`. Use when the user asks
  for a handoff, kickoff prompt, session starter, or wants to spin up a
  fresh session for a specific bead.
allowed-tools: Read, Bash, AskUserQuestion
metadata:
  author: fzymgc-house
  origin: holomush handoff-prompt, adapted for dev-flow + bd model labels
---

# Handoff Prompt

## Overview

Produce a paste-ready briefing text for a fresh session. The briefing is
self-contained: a smart colleague with zero context for the current
session should be able to read it, run the bootstrap commands, and pick
up the work.

**Announce at start:** "I'm using the handoff-prompt skill to generate a
session briefing."

## When to invoke

- User says: "give me a handoff", "kickoff prompt for that", "a prompt
  to start it in a new session", "session resume for X", "spin up X in
  its own session".
- One phase completes and the user wants the next phase to start fresh
  (clean context budget, independent review cadence).
- A bead is large enough to warrant its own brainstorm → spec → plan →
  execute cycle and should not ride alongside other in-flight work.

## Spec references

- `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
  §"Skill Inventory" (`handoff-prompt` row), §"Rule 5" (model selection),
  §"Skill interfaces" (`handoff-prompt` output contract).

## Inputs

- **Bead ID** (required): the `bd` issue the new session will work on.
  If the bead doesn't exist yet, ask whether to file one first via
  `bead-create-smart`.
- **Optional model override**: if the user explicitly names a model
  different from the bead's `model:*` label, respect the override and
  note both values in the briefing.

## Workflow

### Step 1: Gather grounding from the bead

```bash
bd show <bead-id>
bd show <bead-id> --json
```

From the JSON output, extract:

- Title, type, priority, status.
- Parent epic ID (if any).
- Labels — in particular the `model:*` label. bd's JSON output is an
  array; the labels live at `.[0].labels[]?`. Filter for the
  `model:`-prefixed entry; default to `sonnet` if absent (Rule 5: no
  fallback to "highest available"; explicit default keeps cost
  predictable).
- `agent:*` label — the dispatch routing signal (documented lookup; general-purpose fallback). `--skills` is a capability hint only (appended as `## Required Skills` in the description).
- `--spec-id` — the spec doc path.
- Description body, acceptance, notes.

Example model-label extraction:

```bash
bd show <bead-id> --json | jq -r '.[0].labels[]?' | grep '^model:' | head -1
```

If the bead references related beads (parent epic, dependencies,
decision beads), `bd show` each one briefly and capture relevant
context. Do not deep-dive — extract enough to make the briefing
self-contained without becoming the work itself.

### Step 2: Verify cited resources are reachable

A briefing that names a spec or plan path is making a promise that the
new session can `cat <path>` and find content. For each cited path:

```bash
git ls-tree main -- '<path>'             # reachable from main right now?
git log --all --oneline -- '<path>' | head -3
```

If the path is not on `main`, surface to the user before writing the
briefing: "The spec at `<path>` is not on main. The new session will
start in a workspace forked from main and won't see it." Resolve by
landing the orphan first, or by including a `git fetch` + `git
checkout` step (or `jj new <bookmark>` for jj-colocated repos) in the
briefing's setup block.

### Step 3: Identify the cross-cutting surface

If the bead's `Files touched` section names approximate paths, list
them. Optionally run targeted searches to confirm:

```bash
rg -l "<key-symbol>"
```

The briefing should name specific files, not vague module references.

### Step 4: Compose the briefing

Output a single markdown code block (text fence) the user can copy.
Structure:

````markdown
```text
Starting <bead title> — `<bead-id>` (<priority>, <type>). <One-line
context: why now, what triggers this work.>

**Recommended model:** <opus|sonnet|haiku>
<(Optional rationale if the label was set deliberately; e.g.,
"opus per Rule 5 — cross-cutting refactor with subtle invariants")>

**Required skills (per bead `--skills`):** <comma-separated list>

**Read first (bd is source of truth for work state):**

  bd prime                 # session bootstrap: workflow + conventions
  bd show <bead-id>        # this work — title, acceptance, notes,
                           # description, parent, labels, skills
  bd show <parent-epic>    # only if this bead has a parent epic
  bd show <related-bead>   # any closely-related beads worth scoping

**Source documents to load before acting:**

  - Spec: <spec-path-from-bead-spec-id>
  - Plan: <plan-path>
  - Any ADRs referenced in the bead's notes

**Workspace setup:**

  Defer to `dev-flow:using-worktrees` for isolated workspace creation
  (handles git/jj via VCS detection; uses native WorktreeCreate hook
  where available).

**Cross-cutting surface (verify scope by grepping at design time):**

  rg -n "<key-symbol>"

Per the bead's `Files touched` section, at minimum these need
attention:

  - <file>:<line> — <one-line what>
  - <file> — <one-line what>

**Key design questions (the bead intentionally leaves these open):**

  1. <question> — <hint at the trade-off space, not the answer>
  2. <question> — ...

**Out of scope for `<bead-id>`:**

  - <out-of-scope item from bead's description>
  - <out-of-scope item from bead's description>

**Workflow per project conventions (dev-flow + bd):**

  1. Set up isolated workspace via `dev-flow:using-worktrees`.
  2. Claim the bead atomically:
       bd update <bead-id> --claim
  3. Use `dev-flow:brainstorming` → `dev-flow:writing-plans` (with
     auto-fired design-reviewer + plan-reviewer gates) if the bead is
     pre-design. Otherwise jump to:
       dev-flow:subagent-driven-development   # parallel dispatch
       dev-flow:executing-plans               # serial execution
  4. On completion: `dev-flow:finishing-a-development-branch` handles
     the pre-flight bd check + interactive close + push.

**Mitigating context (safety nets already in place):**

  - <safety net 1, e.g. "the spec's Rule 7 grounding traces are in the
    design bead's notes — read them via `bd show`">
  - <safety net 2>

Start with `dev-flow:brainstorming` if design questions remain, or
claim the bead and dispatch directly if the spec + plan are ready.
```
````

### Step 5: Show the user

Print the briefing as the markdown code block above, with no editorial
content inside the block. After the block, briefly note:

- The bead ID and any related beads referenced.
- That the new session should start in a fresh workspace.
- Whether any of the design decisions have known leaning answers worth
  flagging in the briefing vs. leaving open.

## Constraints

- **No editorial content inside the briefing block.** The briefing is
  for the new session, not the current one. Commentary stays in
  conversation with the current user.
- **Keep the briefing under ~80 lines** when reasonable. A 200-line
  briefing micromanages.
- **Never embed credentials, tokens, or local-machine paths** like
  `~/.config/...` in the briefing.
- **Cite the bead, spec, plan** by absolute or repo-relative path; never
  rely on the new session inheriting current-session state.
- **Don't pre-decide design questions** the new session should answer.
  Surface the trade-off space; let the new session's brainstorming
  pass pick.
- **Default model is sonnet** when no `model:*` label is present (Rule
  5). Do not fall back to "highest available."
- **Verify reachability** of every cited path before finalizing (Step
  2). A briefing that claims "the spec is at X" when X is on an orphan
  commit starts the new session on a false premise.

## Origin

Adapted from holomush's `handoff-prompt` skill (May 2026). Major
adaptations:

- Replaced `task workspace:new` (holomush's Taskfile) with deferral to
  `dev-flow:using-worktrees` (handles git + jj via VCS detection).
- Added explicit model recommendation from the bead's `model:*` label
  (per Rule 5); default sonnet if absent.
- Added `bd prime` + `bd show <id>` as explicit session-bootstrap
  instructions in the briefing.
- Routed dispatch via the bead's `agent:*` label.
- Updated the workflow block to reference `dev-flow:` skill paths and
  the design-bead lifecycle (brainstorming opens, plan-to-beads
  promotes / retitles / closes).
