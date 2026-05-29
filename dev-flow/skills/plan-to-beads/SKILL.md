---
name: plan-to-beads
description: >-
  Materialize an implementation plan's task table into bd issues, dependency
  edges, and parent linkages per the design-bead lifecycle (Rule 6). Use after
  writing-plans + plan-reviewer return READY, after capture-adrs has fired, and
  before subagent-driven-development or executing-plans. Reads the plan's task
  table directly (no `## Bead chain structure` section). Always dry-runs first
  and requires explicit user approval before mutating bd state.
allowed-tools: >-
  Read, Grep, Glob, Bash, AskUserQuestion,
  mcp__probe__search_code, mcp__probe__extract_code, mcp__probe__grep,
  mcp__context7__resolve-library-id, mcp__context7__query-docs
metadata:
  author: fzymgc-house
  origin: holomush bead-chain-from-plan, adapted per dev-flow Rules 3/4/6
---

# Plan to Beads

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**

## Overview

Translate the task table of an implementation plan into a concrete sequence
of `bd` operations: design-bead lifecycle transition (promote / retitle /
close), child task-bead creation, dependency edges, label and skills
routing.

Plans are the one-shot input. Once materialized, **bd is the source of
truth** for graph topology (Rule 4). The plan markdown is not edited by
this skill. Re-runs against an already-materialized plan are refused unless
`--force-update` is passed.

**Announce at start:** "I'm using the plan-to-beads skill to materialize
the plan's task table into bd."

## When to invoke

- Auto-fired by `writing-plans` after `plan-reviewer` returns READY and
  `capture-adrs` has stamped its idempotency marker.
- Manually when the user says "create the beads", "materialize the plan",
  or names a plan path and asks to track the work in bd.
- Never auto-fire on a NOT-READY plan — materializing beads against a
  broken target wastes the work.

## Inputs

- **Plan path** (positional or detected from recent context): a markdown
  file under `docs/superpowers/plans/`.
- **Design bead ID** (`--design-bead <id>`): the bead opened by
  `brainstorming` that this skill will promote/retitle/close per Rule 6.
  Required unless the user opts out of the design-bead lifecycle (rare;
  most flows include one).
- **`--dry-run`** (default for the first pass): emit the manifest of
  `bd create` / `bd update` / `bd close` / `bd dep add` shell commands to
  stdout. Mutate nothing.
- **`--force-update`**: override the already-materialized guard from
  Step 2. Dangerous; user opts in explicitly.

## Spec references

- `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
  §"Rule 3" (bd flag inventory), §"Rule 4" (no duplicate state, plan
  task table semantics), §"Rule 6" (design-bead lifecycle table), §"Skill
  Inventory" (`plan-to-beads` row).

The spec is authoritative for flag names, lifecycle transitions, and
error behavior. Consult it for any ambiguity rather than guessing.

## Workflow

### Step 1: Read the plan

Read the entire plan file. Locate every `### Task N:` (or `### Task N.M:`)
heading inside any `## Phase N:` section. For each task, extract:

- Title (the heading text after `Task N:` / `Task N.M:`).
- `**Files:**` sub-list — the approximate file paths the task touches.
- Any explicit `--acceptance`, verification commands, dependencies, or
  labels the plan author included in the task body.

If the plan uses a different task-table format than this convention,
ask the user how to interpret it before proceeding. Do not silently
fall back to chain-section parsing (the `## Bead chain structure`
section is intentionally not used in dev-flow per Rule 4).

### Step 2: Detect already-materialized state

```bash
bd list --spec <plan-path>
```

> bd flag naming note: `bd list` uses `--spec` for the spec_id prefix
> filter. `bd create` / `bd update` use `--spec-id`. Both are correct;
> this is verified bd CLI behavior, not a typo.

If the result is non-empty and `--force-update` was not passed:

- Print the existing bead IDs that match this `<plan-path>`.
- Refuse with a clear error message: "Plan already materialized
  (beads: <id>, <id>, ...). Re-run with `--force-update` to override."
- Exit without changes.

If `--force-update` is passed, surface the existing beads to the user,
require an explicit `yes/no/abort` AskUserQuestion before proceeding, and
proceed only on `yes`.

### Step 3: Classify the plan by task count (Rule 6)

| Task count | Lifecycle |
|---|---|
| 3 or more | Promote design bead to epic. File children with `--parent`. |
| 1-2 | Retitle design bead to first task; optionally file second task as a sibling (no parent). |
| 0 | Close design bead with rationale; skip child creation. |

The full transition table lives in the spec under §"Rule 6 → Lifecycle".
Refer to it verbatim — do not paraphrase the bd commands.

### Step 4: Build the manifest

Compose, but do not execute, the ordered list of bd operations:

1. **Design-bead lifecycle transition** per Step 3 (one of `bd update
   <id> --type=epic`, `bd update <id> --title=...`, `bd close <id>
   --reason=...`).
2. **Child task beads** (only for the 3+ and 1-2 cases). Each child is a
   `bd create` invocation using bd's structured flags per Rule 3 (spec
   §"Rule 3" table is authoritative for the flag inventory).
3. **Decision-bead linkages** if `capture-adrs` filed decision beads for
   this plan: `bd dep add <epic-id> <decision-bead-id>` edges.
4. **Inter-task dependency edges**, encoded via `--deps` on `bd create`
   where possible, otherwise as `bd dep add` after creation.
5. **Skills and labels** per Rule 5 (model selection) and the plan
   author's hints: `--labels model:<tier>` and `--labels agent:<type>` (the
   routing signal). `--skills <comma-separated>` appends a `## Required Skills`
   capability hint to the description; it does NOT route. Never set
   `agent:code-reviewer` on an implementer bead (that agent needs the review-pr
   orchestrator contract).

Each child bead's `--description` is **narrative only** per Rule 3: Goal
(one paragraph), Plan reference (`<plan-path>#task-<N>` plus
verbatim-read directive), Files touched (approximate), Out of scope
(explicit non-goals). Acceptance criteria, verification commands, design
links, and dependencies go in their dedicated flags — never duplicated
into the description body.

### Step 5: Dry-run preview

Emit the manifest to stdout as a numbered list, including the exact
shell invocations the skill will run. Group them by phase: lifecycle
transition first, then creations, then edges, then linkages.

Display a summary table with: op number, op type, target (existing bead
ID or `(new)`), one-line title or rationale.

For each child bead creation, show the title and a 100-char preview of
the Goal paragraph so the user can spot a wrong scope.

If `--dry-run` was passed: exit here. The user reviews the output, edits
the plan if necessary, and re-invokes without `--dry-run` (or pipes the
output to `bash` themselves if they prefer).

### Step 6: Get user confirmation

If not `--dry-run`, use AskUserQuestion to ask:

> "Apply N operations to bd? (yes / no / modify)"

- `yes` — execute in order, capturing new bead IDs.
- `no` — exit without changes.
- `modify` — accept edit directions, rebuild the manifest, re-display,
  re-prompt with the same question against the new state. Never apply
  inferred edits without re-confirming.

### Step 7: Execute

For each operation in the approved manifest:

1. Print the exact `bd` command.
2. Run it.
3. Capture stdout (new bead IDs from `bd create`).
4. On any failure: STOP, surface the error, ask the user how to proceed
   (retry, skip, abort).

Substitute real bead IDs returned by `bd create` into subsequent
`bd dep add` operations. Do not let `bd create` open an editor — always
pass `--description` explicitly.

### Step 8: Post-state summary

After all operations succeed, print:

- The design bead's new state (epic / retitled task / closed).
- The list of new child bead IDs.
- The first ready task (`bd ready` top entry).
- If a Dolt remote is configured (`bd dolt remote list` is non-empty),
  remind the user to run `bd dolt push` to publish bd state.
- **Remind the user to land the docs on `main` before executing
  subagents** — the spec, plan, and any ADRs filed by `capture-adrs`
  are still local-only at this point. The
  `subagent-driven-development` skill expects them to be reachable
  from `main` (fresh-worktree subagents pull from there). Suggest a
  small docs-only PR covering `docs/superpowers/specs/`,
  `docs/superpowers/plans/`, and `docs/adr/` before invoking the
  execution sub-skill. See `writing-plans` step 4 for the full
  rationale.

## Constraints

- **Description is narrative only** (Rule 3). Acceptance criteria,
  verification commands, design links, and dependencies live in their
  dedicated flags. Never inline a `## Acceptance` heading into the
  description body.
- **Never use `--force` flags** without explicit user direction.
- **Always pass `--description` explicitly** to `bd create`; never let
  it open an editor.
- **`--parent` long form**, not `-p` (project rule).
- **Use `--body-file` for descriptions longer than a few lines** so
  heredoc quoting is not a source of bugs.
- **Honor the design-bead lifecycle exactly** as the spec's Rule 6
  table prescribes. Title transitions in the 1-2 case use "title of
  first plan task"; do not invent alternative titles.
- **No plan-file mutation.** This skill reads the plan; bd state is
  the only thing that mutates (Rule 4).

## Failure modes

- **Plan has no task table.** Surface to user: "No `### Task N:`
  headings found under any `## Phase N:` section. Is this a design-only
  spec?" Offer to close the design bead per the 0-task lifecycle.
- **Plan already materialized, no `--force-update`.** Refuse with the
  existing bead IDs listed (Step 2).
- **bd unavailable or uninitialized.** Bail with a clear error per
  spec §"Degraded-mode behavior" — `bd init` or `bd doctor` first.
- **Design bead does not exist.** Ask the user: "No `--design-bead`
  supplied and no design bead detected in session context. Create one
  now (`bd create --type=task --labels=phase:design`) and re-invoke,
  or skip the design-bead lifecycle (uncommon)?"
- **Forward-reference between child beads.** Expected — bd handles
  cross-references that resolve during this run. Do not pre-validate.

## Why the chain-section is gone

The holomush ancestor of this skill (`bead-chain-from-plan`) read a
`## Bead chain structure` section that the plan author wrote by hand or
via `bead-chain-design`. That convention duplicated bd's native graph
state and was dropped per Rule 4. The plan's task table is now the
one-shot input; bd owns the graph after materialization. Editing the
plan after materialization does not retroactively change beads — file
follow-ups via `bead-create-smart` or re-invoke with `--force-update`.

## Origin

Adapted from holomush's `bead-chain-from-plan` skill (May 2026). Major
adaptations:

- Dropped `## Bead chain structure` section parsing (Rule 4).
- Read the plan's task table (`### Task N:` headers) directly.
- Wired full bd flag set per Rule 3 (`--acceptance`, `--design-file`,
  `--spec-id`, `--notes`, `--deps`, `--labels` (incl. `model:*` and `agent:*`),
  `--skills` (Required-Skills hint, not routing), `--parent`,
  `--type`, `--priority`); description is narrative only.
- Implemented Rule 6 design-bead lifecycle (promote / retitle / close
  by task count).
- Honored `--dry-run` and `--force-update`.
- Detected already-materialized state via `bd list --spec <plan-path>`
  (note: bd's flag naming is inconsistent — `--spec` for `list`, but
  `--spec-id` for `create` / `update`; both are verified-correct).
