<!-- markdownlint-disable MD013 -->

# solving-a-bead Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `solving-a-bead` dev-flow skill plus a 1:1 `/solving-a-bead <bead-id>` slash command that drives one bead interactively from validation → isolated workspace → triage → root-caused TDD fix → hand-off.

**Architecture:** A thin orchestrator skill (markdown SKILL.md) that delegates to existing rigid skills (`using-worktrees`, `systematic-debugging`, `brainstorming`, `test-driven-development`, `verification-before-completion`, `finishing-a-development-branch`). The slash command is a thin operator entry that parses `<bead-id>` and invokes the skill.

**Tech Stack:** Markdown (rumdl-linted, 140-char width), bd (beads) CLI, jj/git VCS detection. No executable code — the verification surface is `rumdl check` + structural `rg` checks.

**Spec:** `docs/superpowers/specs/2026-05-29-solving-a-bead-design.md`
**Design bead:** `fhsk-eip`
**Model (all tasks):** `sonnet` — markdown authoring only; no hard reasoning or mechanical bulk work (Rule 5 default).

> **Before running any VCS commands, read `dev-flow/references/vcs-preamble.md` and use the appropriate commands for the detected VCS (git or jj).**

**Note on TDD for this plan:** The deliverable is documentation, which falls under TDD's documented "configuration files / generated content" exception. The "failing test → green" loop is realized as **validation gates**: write content → run `rumdl check` / structural `rg` assertion → confirm it passes. Each task's verification step is the analogue of "watch the test pass."

**Release note:** As of PR #115 (ADR `fhsk-7y4`), the repo uses a single repo-wide cocogitto version; the per-package release-please streams and their config/manifest files were removed. Adding a skill registers nothing — no manifest edits, no marketplace.json change (it lists plugins, not skills; skills auto-discover).

---

## File Structure

| File | Responsibility |
|---|---|
| `dev-flow/skills/solving-a-bead/SKILL.md` (create) | Canonical phased workflow reference; frontmatter, VCS preamble, Phase 0-4, triage red-flags table |
| `dev-flow/commands/solving-a-bead.md` (create) | Thin operator entry; parses `$ARGUMENTS` as `<bead-id>`, invokes the skill |

Grounding (verified against `main` @ #115): `dev-flow/skills/` and `dev-flow/commands/` exist. `dev-flow/plugin.json` does NOT enumerate skills/commands (auto-discovered) — no edit needed there. No release manifests to update (release-please removed in #115; single cog version). `.claude-plugin/marketplace.json` lists plugins, not skills — no edit needed.

---

## Task 1: Create the SKILL.md

**Files:**

- Create: `dev-flow/skills/solving-a-bead/SKILL.md`

- [ ] **Step 1: Create the directory and write frontmatter + VCS preamble**

Create `dev-flow/skills/solving-a-bead/SKILL.md` starting with this exact frontmatter and preamble line:

```markdown
---
name: solving-a-bead
description: Use when asked to solve, fix, address, or work a specific bead/issue
  by ID — validates the bead is open and unblocked, creates an isolated workspace
  off latest main, separates the problem from any suggested fix (treating suggested
  fixes as non-authoritative hypotheses), then drives a root-caused, TDD solution.
metadata:
  author: fzymgc-house
---

# Solving a Bead

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**
```

- [ ] **Step 2: Write the Overview + announce line**

Add an `## Overview` section. Required content:

- One-sentence purpose: interactive, in-session resolution of a single bead.
- The niche statement: fills the gap between `handoff-prompt` (briefs a fresh session) and `draining-beads` (autonomous) — this drives one bead interactively, here, now.
- Core principle (bold): **A suggested fix in a bead is a hypothesis to validate, never an instruction to follow.**
- Announce line (bold): "I'm using the solving-a-bead skill to resolve `<bead-id>`."
- [ ] **Step 3: Write the Checklist section**

Add `## Checklist` instructing the implementer to create one TodoWrite task per phase and complete in order: (0) Validate, (1) Claim & isolate, (2) Triage, (3) TDD implementation, (4) Verify & hand off.

- [ ] **Step 4: Write Phase 0 — Validate (hard gates), with exact commands**

Add `## Phase 0 — Validate (hard gates; abort on any failure)`. Run from the **main checkout**. Include these exact gate commands and their abort semantics:

````markdown
1. **Arg present.** No `<bead-id>` → print usage, exit.
2. **Bead exists.**

   ```bash
   bd show "$BEAD_ID" --json > /tmp/bead.json || { echo "ABORT: bead $BEAD_ID not found"; exit 1; }
   ```

3. **Status workable.**

   ```bash
   STATUS=$(jq -r '.[0].status' /tmp/bead.json)
   case "$STATUS" in
     open)        : ;;                                  # proceed
     in_progress) echo "NOTE: $BEAD_ID already claimed — resuming" ;;
     *)           echo "ABORT: $BEAD_ID status is '$STATUS' (need open/in_progress)"; exit 1 ;;
   esac
   ```

4. **No unmet dependencies (HARD-BLOCK).**

   ```bash
   # bd dep list defaults to --direction=down (what this bead depends on).
   # Each record carries `dependency_type` and the dependency's own `status`.
   # A `dependency_type=="blocks"` record that is not closed is an unmet blocker.
   OPEN_BLOCKERS=$(bd dep list "$BEAD_ID" --json 2>/dev/null \
     | jq -r '[.[] | select(.dependency_type=="blocks") | select(.status != "closed")] | .[].id' )
   if [ -n "$OPEN_BLOCKERS" ]; then
     echo "ABORT: $BEAD_ID has unmet blocker dependencies:"; echo "$OPEN_BLOCKERS"
     echo "Finish those beads first, then re-run /solving-a-bead $BEAD_ID"; exit 1
   fi
   ```

   Verified against bd 1.0.4: the per-record field is `dependency_type` (not
   `type`), and `--direction=down` (the default) lists this bead's own
   dependencies, so blocker records appear directly. The contract: abort if any
   `blocks` dependency is not closed.
````

- [ ] **Step 5: Write Phase 1 — Claim & isolate**

Add `## Phase 1 — Claim & isolate`. Required content:

- Step: capture context fields from the already-read `bd show --json` (title, type, description, acceptance, notes, `model:*` / `agent:*` labels).
- Step: claim **from the main checkout** — `bd update "$BEAD_ID" --claim` — with the note: claiming from the main checkout (not inside the new workspace) avoids the macOS sandbox SQLite-write-in-worktree issue.
- Step: invoke `dev-flow:using-worktrees` to create an isolated workspace off **latest main** (it fetches first; handles git worktree / jj workspace) and move into it.
- [ ] **Step 6: Write Phase 2 — Triage, including the verbatim red-flags table**

Add `## Phase 2 — Triage`. Required content:

- Instruction to **restate the problem in your own words**, then split the bead body into two explicitly labeled buckets:
  - **Problem / symptom / desired outcome** (authoritative).
  - **Candidate solutions (NON-AUTHORITATIVE — to be validated, never followed blindly)** — every "fix it by…", "do X", "the solution is…" sentence demoted to hypothesis status.
- A routing table:

  ```markdown
  | Bead shape | Route |
  |---|---|
  | `bug` / defect / error / unexpected behavior | `dev-flow:systematic-debugging` — each candidate solution enters as a hypothesis, adopted only if the confirmed root cause demands it |
  | Ambiguous / feature / unclear approach | `dev-flow:brainstorming`, scoped to the bead |
  | Clear, well-specified `task` / `chore` | Straight to Phase 3 |
  ```

- This exact red-flags table:

  ```markdown
  ## Red Flags

  | Thought | Reality |
  |---|---|
  | "The bead says to fix it by doing X" | X is a hypothesis. Confirm the root cause requires X before implementing. |
  | "The reporter already diagnosed it" | Reporter diagnosis is a lead, not a conclusion. Reproduce and verify. |
  | "This is obviously the fix" | Obvious fixes mask root causes. systematic-debugging Phase 1 first. |
  ```

- [ ] **Step 7: Write Phase 3 — TDD implementation**

Add `## Phase 3 — TDD implementation`. Required content:

- Invoke `dev-flow:test-driven-development`: failing test encoding the bead's acceptance criteria (or reproduced bug) → watch it fail → minimal code → refactor.
- "As much as possible" honored via TDD's own documented exceptions (config / docs / throwaway — ask the human partner before skipping).
- Run the bead's verification commands (from its `--notes`) + project quality gates for the changed surface.
- [ ] **Step 8: Write Phase 4 — Verify & hand off**

Add `## Phase 4 — Verify & hand off`. Required content:

- Apply `dev-flow:verification-before-completion` — show actual command output before any "done" claim.
- `bd note "$BEAD_ID"` summarizing root cause / approach + fix.
- **Leave the bead `in_progress`** — closure happens at merge, not here. State this explicitly.
- Suggest `dev-flow:finishing-a-development-branch` (offers merge/PR/cleanup). Does **not** auto-open a PR.
- [ ] **Step 9: Run validation gate (the "test")**

Run:

```bash
rumdl check dev-flow/skills/solving-a-bead/SKILL.md
```

Expected: `Success: No issues found`. Also assert structure:

```bash
rg -c '^## Phase [0-4]' dev-flow/skills/solving-a-bead/SKILL.md   # expect 5
head -1 dev-flow/skills/solving-a-bead/SKILL.md | grep -q '^---$' && echo "frontmatter ok"
```

Expected: `5` and `frontmatter ok`.

- [ ] **Step 10: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`. Suggested message: `feat(dev-flow): add solving-a-bead skill`.

---

## Task 2: Create the slash command

**Files:**

- Create: `dev-flow/commands/solving-a-bead.md`

- [ ] **Step 1: Write the command file**

Create `dev-flow/commands/solving-a-bead.md` with this exact frontmatter:

```markdown
---
description: Solve a single bead interactively — validate, isolate, triage, TDD fix, hand off.
argument-hint: "<bead-id>"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Skill(dev-flow:*)", "Bash(bd show:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd dep list:*)", "Bash(jj root:*)", "Bash(jj st:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(jq:*)"]
---

# /solving-a-bead

Resolve a single bead interactively. See `dev-flow:solving-a-bead` for the
canonical reference (phase gates, triage discipline, hand-off).

Parse `$ARGUMENTS` as a single `<bead-id>`. If missing or empty, print this
usage and exit:

> Usage: `/solving-a-bead <bead-id>` — validates the bead is open and
> unblocked, creates an isolated workspace off latest main, then drives a
> root-caused, TDD solution.

Otherwise, invoke the `dev-flow:solving-a-bead` skill with that bead ID.
```

- [ ] **Step 2: Run validation gate**

Run:

```bash
rumdl check dev-flow/commands/solving-a-bead.md
```

Expected: `Success: No issues found`.

- [ ] **Step 3: Commit**

Commit per `references/vcs-preamble.md`. Suggested message: `feat(dev-flow): add /solving-a-bead command`.

---

## Task 3: Integration validation

**Files:** (no new files — validates the whole deliverable)

- [ ] **Step 1: Run the full local quality gate for the changed surface**

Run:

```bash
rumdl check dev-flow/skills/solving-a-bead/SKILL.md dev-flow/commands/solving-a-bead.md docs/superpowers/plans/2026-05-29-solving-a-bead.md docs/superpowers/specs/2026-05-29-solving-a-bead-design.md
```

Expected: rumdl `Success: No issues found`.

- [ ] **Step 2: Confirm skill name ↔ directory match and command references the skill**

Run:

```bash
grep -q '^name: solving-a-bead$' dev-flow/skills/solving-a-bead/SKILL.md && echo "name matches dir"
grep -q 'dev-flow:solving-a-bead' dev-flow/commands/solving-a-bead.md && echo "command references skill"
```

Expected: `name matches dir` and `command references skill`.

- [ ] **Step 3: Verify the five phase gates and the non-authoritative-fix language are present**

Run:

```bash
rg -c '^## Phase [0-4]' dev-flow/skills/solving-a-bead/SKILL.md            # expect 5
rg -q 'NON-AUTHORITATIVE' dev-flow/skills/solving-a-bead/SKILL.md && echo "candidate-fix guard present"
rg -q 'HARD-BLOCK|unmet blocker' dev-flow/skills/solving-a-bead/SKILL.md && echo "dependency hard-block present"
```

Expected: `5`, `candidate-fix guard present`, `dependency hard-block present`.

- [ ] **Step 4: Commit any fixes**

If steps 1-3 surfaced issues, fix them and commit per `references/vcs-preamble.md`. Otherwise no-op.
<!-- adr-capture: sha256=74e18db560f65db3; session=cli; ts=2026-05-29T14:50:02Z; adrs=fhsk-ypt,fhsk-3xn,fhsk-hj3 -->
