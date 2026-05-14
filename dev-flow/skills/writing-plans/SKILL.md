---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
allowed-tools: "Read, Edit, Write, Bash, AskUserQuestion, mcp__probe__*, mcp__context7__*, mcp__deepwiki__*, mcp__exa__*, mcp__firecrawl-mcp__firecrawl_scrape"
---

> **Before running any VCS commands, read references/vcs-preamble.md and use the appropriate commands for the detected VCS (git or jj).**

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `superpowers:using-worktrees` skill at execution time. A design bead may already exist from `brainstorming` (Rule 6) — read the design bead ID from the prior session context, OR query `bd list --spec <spec-path>` to recover it. Every grounding-trace note and reviewer-round note below references this bead. If no design bead exists, the skill proceeds without bd tracking (degraded mode).

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

- (User preferences for plan location override this default)
- After saving, append `bd note <design-bead-id> "Plan: <path>"`.

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**

- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**

- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`
- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:

- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember

- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Rule 7 Grounding Verification (before self-review)

After the plan is written but **before** the self-review pass, verify the plan's content against reality. The plan-reviewer agent will re-check these afterward; doing it here saves a NOT READY round.

- **File paths in "Files touched" exist on disk.** For each `Create:` / `Modify:` / `Test:` path in every task, run `mcp__probe__search_code "<path component>"` (or `mcp__probe__grep`) to confirm the directory and any sibling files exist. New-create paths should land in directories that already exist or are explicitly created by an earlier task. Append `bd note <design-bead-id> "grounding/probe-paths: verified N file paths"` on success; flag inline any path you couldn't verify.
- **Function signatures cited in plan code blocks match the codebase.** For each `def foo(...)` / `class Bar` referenced in plan code blocks, run `mcp__probe__extract_code <symbol>` to confirm the signature matches what the plan asserts. Wrong signature in a plan → wrong code in implementation.
- **Library APIs cited in the plan match current upstream.** Any library named in the spec must be re-checked via `mcp__context7__resolve-library-id` + `query-docs`. Training-data drift is the single most common cause of plans that fail at runtime. Append `bd note <design-bead-id> "grounding/context7-reverify: <lib-id> — <one-line summary>"` per library.
- **Optional: deepwiki re-check for upstream conventions.** If the spec referenced upstream-repo conventions (proto layout, plugin API, migration discipline), re-verify via `mcp__deepwiki__ask_question <repo> "<targeted question>"`. Append `bd note <design-bead-id> "grounding/deepwiki-reverify: <repo> — <summary>"`.

**Degraded mode:** If a grounding tool is unavailable, note the gap inline. `plan-reviewer` will flag the missing trace as a finding but will not treat absence as a hard error.

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Plan Review Gate

After the self-review pass, the skill MUST invoke the `plan-reviewer` agent before any auto-fire chain. The reviewer is read-only and adversarial; its job is to flag ungrounded plans (Rule 7), bad file-path claims, and signature drift.

1. **Invoke `plan-reviewer`** against the plan path. Pass the design bead ID as additional context — the reviewer uses `bd show <id>` to read grounding-trace notes and verify that named libraries / file paths were grounded.
2. **Parse the first non-empty line** of the reviewer's output via exact-match regex `^VERDICT: (READY|NOT READY)$`.
3. **Branch on the verdict:**

   - **READY:** Append `bd note <design-bead-id> "plan-review READY (round N)"`. Proceed to the auto-fire chain below.
   - **NOT READY:** Append `bd note <design-bead-id> "plan-review round N NOT READY: <one-line finding summary>"`. Print the reviewer's full findings inline. Exit. The user revises the plan and re-invokes writing-plans for the next round.
   - **Missing or unparseable VERDICT line:** Treat as NOT READY. Print the agent's full output and append `bd note "plan-review round N NOT READY: unparseable verdict"`.

4. **No automatic retry.** Loops are user-paced.

## Auto-Fire Chain (on plan-reviewer READY)

The chain runs in this strict order — capture-adrs BEFORE plan-to-beads, per the Ordering Invariants in the spec's Workflow Shape section. Decision beads must exist before the epic is created so the epic can wire `bd dep add` edges to them at materialization time.

1. **Auto-fire `capture-adrs <plan-path>`.** Invoke the skill (not the slash command). The skill runs the heuristic pre-scan, dispatches `adr-extractor`, triages each candidate, writes `docs/adr/<bd-id>-<slug>.md` files, creates `bd create -t decision` records, and stamps the spec/plan idempotency marker.

   - **Zero-candidate flow:** The marker is **still stamped** with `adrs=` empty so the `nudge-adr-capture` hook does not re-fire on subsequent edits. Continue silently.
   - **Some candidates:** Append `bd note <design-bead-id> "ADRs: <bd-ids>"` with the comma-joined decision-bead IDs.

2. **Count plan tasks** (count of `### Task N:` headers in the plan).

3. **Branch on task count** (per Rule 6 lifecycle):

   - **3+ tasks:** Auto-invoke `plan-to-beads <plan-path>`. The skill promotes the design bead to `--type=epic`, retitles it to the feature name, and files children with `--parent <design-bead-id>`. Decision beads filed by capture-adrs get `bd dep add` edges wired to the new epic.
   - **1-2 tasks:** Prompt the user via `AskUserQuestion`: "Plan has <N> task(s). Materialize beads with plan-to-beads, or skip? (Materialize / Skip)". On Materialize: invoke `plan-to-beads <plan-path>` — the design bead stays `type=task`, inherits the first task's title, and a sibling bead is filed if there's a second task.
   - **0 tasks:** Run `bd close <design-bead-id> --reason="Design-only; no implementation tracked"`. No epic, no children.

4. **After plan-to-beads completes**, offer execution choice:

   **"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Beads materialized: <bd-id-list>. Two execution options:**

   **1. Subagent-Driven (recommended)** — dispatch a fresh subagent per bead (driven by `bd ready`), review between tasks, fast iteration

   **2. Inline Execution** — execute beads serially in this session via executing-plans

   **Which approach?"**

   - **If Subagent-Driven chosen:**
     - **REQUIRED SUB-SKILL:** Use `dev-flow:subagent-driven-development` (bd-driven task pickup; reads `model:*` labels for dispatch)
   - **If Inline Execution chosen:**
     - **REQUIRED SUB-SKILL:** Use `dev-flow:executing-plans` (bd-driven serial execution; reads `model:*` labels as guidance)

**Degraded mode:** If `bd` is unavailable, the skill prints a warning, skips the design-bead notes and plan-to-beads auto-fire, and falls back to the legacy "user invokes executing-plans manually" handoff. Capture-adrs still runs (it tolerates missing bd by stamping the marker and writing only the markdown files).
