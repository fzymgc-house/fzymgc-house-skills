---
name: bead-create-smart
description: >-
  Create a tracked bd issue using structured flags (per Rule 3) rather than an
  8-section description heredoc. Use for ad-hoc beads outside the
  plan-to-beads materialization flow — reviewer findings, bug reports,
  follow-up beads at session close, or single tasks the user wants tracked.
  Accepts an optional `--model haiku|sonnet|opus` that maps to the
  `--labels model:<value>` convention per Rule 5.
allowed-tools: Read, Bash, AskUserQuestion
metadata:
  author: fzymgc-house
  version: 0.1.0 # x-release-please-version
  origin: holomush bead-create-smart, shrunk to structured-flag helper
---

# Bead Create (Smart)

## Overview

Thin helper around `bd create` that assembles bd's structured flags from
named arguments. The description body carries narrative only (Goal, Plan
reference, Files touched, Out of scope). Acceptance criteria,
verification, dependencies, design links, etc. all go to their
dedicated bd flags.

**Announce at start:** "I'm using the bead-create-smart skill to file a
tracked bead."

## When to use

- Filing a follow-up bead for a reviewer finding (design-reviewer,
  plan-reviewer, code-reviewer).
- Filing a bug report or known-defect bead mid-session.
- Filing remaining-work beads at session close (the
  `finishing-a-development-branch` skill calls this).
- Creating a single ad-hoc task the user wants tracked without writing a
  full plan.

**Skip** for: trivial scratch notes (use `bd note` instead), or for
materializing a multi-task plan (use `plan-to-beads` instead).

## Spec references

- `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
  §"Rule 3" (bd flag inventory — authoritative), §"Rule 5" (model
  selection labels), §"Skill Inventory" (`bead-create-smart` row).

## Inputs

| Input | Maps to | Required | Notes |
|---|---|---|---|
| Title | positional or `--title` | yes | Imperative-voice summary. |
| Type | `--type task\|feature\|bug\|epic\|chore\|decision` | no (default `task`) | bd's built-in vocabulary. |
| Parent | `--parent <epic-id>` | no | Hierarchical link to an epic. |
| Priority | `--priority 0-4` | no (default `2`) | 0=critical, 2=default, 4=backlog. |
| Acceptance | `--acceptance` | no | RFC2119 MUST/SHOULD checks. |
| Design link | `--spec-id <path>` + `--design <string>` or `--design-file <path>` | no | `--spec-id` is the spec doc path. Use `--design-file` for >1-line bead-specific design notes. |
| Verification | `--notes` | no | Concrete shell commands. |
| Dependencies | `--deps blocks:<id>` / `--deps blocked-by:<id>` | no | Or `bd dep add` after creation. |
| Labels | `--labels` | no | Namespaced tags. `model:<tier>` is set via the `--model` arg below. |
| Required skills | `--skills` | no | Dispatch routing hints (e.g. `jj,proto`). |
| Model | `--model haiku\|sonnet\|opus` | no (default `sonnet`) | Translated to `--labels model:<value>` per Rule 5. |
| External ref | `--external-ref <url>` | no | PR / issue / Linear URL. |
| Description body | `--description` or `--body-file` | no | Narrative only (see below). |

## Description body shape (narrative only)

```text
## Goal
<one paragraph: what this task accomplishes>

## Plan reference
- Plan: `<plan-path>` (read verbatim before starting)
- Task: <task-id or section anchor>

## Files touched
- `<path>` — <what change>
- `<path>` — <what change>

## Out of scope
- <adjacent work that belongs to a separate bead>
```

There is **no `## Acceptance criteria` section** in the description body.
That content goes in `--acceptance`. There is **no `## Verification
steps` section**; that goes in `--notes`. There is **no `## Dependencies`
section**; that goes in `--deps` or `bd dep add`. There is **no `## Design
reference` section**; that goes in `--spec-id` / `--design` /
`--design-file`. Rule 3 is non-negotiable here.

## Workflow

### Step 1: Gather context

If the bead is for a follow-up under an epic, run `bd show <epic-id>` to
confirm the epic is open. If filing during `finishing-a-development-branch`,
pull the epic ID from the session's design-bead context.

### Step 2: Build the description body

Compose the narrative-only sections per the shape above. If the user
supplies a description longer than ~1 line, write it to a temp file and
use `--body-file <path>` rather than inlining via `--description`.

### Step 3: Assemble the `bd create` invocation

Construct the command using only structured flags. Example shape (Rule 3
is the authoritative inventory):

```bash
bd create \
  --title "<title>" \
  --type task \
  --priority 2 \
  --parent <epic-id> \
  --labels "model:sonnet,aspect:<x>,area:<y>" \
  --skills "<comma-separated>" \
  --spec-id "<plan-or-spec-path>" \
  --acceptance "<RFC2119 MUST/SHOULD checks>" \
  --notes "<verification commands>" \
  --deps "blocks:<id>" \
  --body-file /tmp/bead-desc.md \
  --validate
```

Show the assembled command to the user before running (dry-run preview)
unless the user explicitly requested non-interactive creation.

### Step 4: Execute

Run the command. Capture the new bead ID from stdout.

### Step 5: Wire additional dependencies

If `--deps` did not cover all edges, run `bd dep add <new-id>
<blocked-by-id>` for each remaining edge.

### Step 6: Verify

```bash
bd show <new-id>
```

Confirm: title, type, parent (if any), labels (including `model:<tier>`),
skills, acceptance, notes, and the narrative description body are all
present.

## Constraints

- **Description body is narrative only.** Acceptance, verification,
  dependencies, design links live in their own flags. Re-read Rule 3 if
  this feels constraining — the structured fields are queryable by bd's
  filters; the description body is not.
- **`--parent` long form**, not `-p`.
- **Always pass `--description` or `--body-file`**; never let `bd create`
  open an editor.
- **Use `bd note <id> "..."` to append** later content; do NOT use `bd
  update --notes` (it overwrites the entire notes field per holomush's
  bd anti-pattern note).
- **Model floor for sub-agent dispatch is sonnet**; haiku is for
  mechanical work only (Rule 5).
- **Never run multiple `bd create` calls in parallel** — bd has an
  ID-allocation race; parallel calls report the same ID but only one
  commits. Always sequential.

## Origin

Adapted from holomush's `bead-create-smart` skill (May 2026). Major
adaptations:

- Shrunk from an 8-section description-format helper to a structured-flag
  assembler. Per Rule 3, acceptance / verification / design / deps each
  live in dedicated bd flags, not in description sections.
- Added `--model haiku|sonnet|opus` arg mapping to `--labels
  model:<value>` per Rule 5.
- Description body collapsed to 4 narrative sections (Goal, Plan
  reference, Files touched, Out of scope).
