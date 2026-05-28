---
name: finishing-a-development-branch
description: >-
  Use when implementation is complete, all tests pass, and you need to
  decide how to integrate the work (git or jj) - guides completion of
  development work by presenting structured options for merge, PR, or cleanup
metadata:
  author: fzymgc-house
  version: 0.2.0 # x-release-please-version
---

# Finishing a Development Branch

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Detect environment → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## VCS Detection

```bash
if jj root >/dev/null 2>&1; then
  VCS=jj
else
  VCS=git
fi
```

## The Process

### Step 0: Pre-flight bd Check

Before verifying tests or presenting options, reconcile the bd state for this branch's epic. Open beads at this point typically indicate work that the user thinks is complete but the tracker doesn't yet know about.

1. **Identify the epic / design bead.** Determine the bd ID associated with this branch's work:

   - If a design bead was opened during `brainstorming` and promoted by `plan-to-beads`, its ID is the epic. Read it from session context, or query `bd list --spec <plan-path>` to find the epic for the spec/plan tied to this branch.
   - If no design bead exists (branch was created outside the dev-flow pipeline), skip this step and proceed to Step 1.

2. **List open child beads:** run `bd list --status=open --parent <epic-id>`. Also list `--status=in_progress` to catch claimed-but-not-closed beads.

3. **If any open or in-progress beads exist:**

   a. **Display them** with title, status, and a short description. Highlight `in_progress` (claimed) beads — those represent active work that the user may have forgotten to close.

   b. **Ask via `AskUserQuestion`:** "Resolve <N> open bead(s) before finishing? Choose one: Close all / File follow-ups / Defer / Continue anyway".

   c. **Close all:** for each open bead, prompt the user inline for a one-line `--reason` and run `bd close <id> --reason="<reason>"`.

   d. **File follow-ups:** for each open bead, invoke `dev-flow:bead-create-smart` to file a sibling follow-up bead capturing the leftover work, then `bd close <original-id> --reason="Deferred to follow-up <new-bd-id>"`.

   e. **Defer:** for each open bead, run `bd update <id> --defer=+30d`. The bead stays open but drops out of `bd ready` for 30 days.

   f. **Continue anyway:** print a loud warning ("⚠️  <N> open bead(s) remain after this branch is finished; bd state will drift from VCS state"), then proceed.

4. **If no open beads:** proceed to Step 1 silently.

**Degraded mode:** If `bd` is unavailable, print a warning and skip the pre-flight check. Open beads are not reconciled in this run.

### Step 1: Verify Tests

**Before presenting options, verify tests pass:**

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:**

```text
Tests failing (<N> failures). Must fix before completing:

[Show failures]

Cannot proceed with merge/PR until tests pass.
```

Stop. Don't proceed to Step 2.

**If tests pass:** Continue to Step 2.

### Step 2: Detect Environment

**Determine workspace state before presenting options.** Drives both menu choice and cleanup behavior.

**git:**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
SUPERPROJECT=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
```

`GIT_DIR != GIT_COMMON` is also true inside git submodules — `SUPERPROJECT` distinguishes a submodule from a linked worktree.

| State | Menu | Cleanup |
|-------|------|---------|
| `GIT_DIR == GIT_COMMON` (normal repo, or submodule) | Standard 4 options | No worktree to clean up |
| `GIT_DIR != GIT_COMMON` AND `SUPERPROJECT` empty AND `BRANCH` non-empty (linked worktree, named branch) | Standard 4 options | Provenance-based (Step 6) |
| `GIT_DIR != GIT_COMMON` AND `SUPERPROJECT` empty AND `BRANCH` empty (linked worktree, detached HEAD) | Reduced 3 options (no merge) | No cleanup — externally managed |

**jj:**

```bash
WORKSPACE_NAME=$(jj workspace list 2>/dev/null | awk -F: 'NR==1{print $1}')  # current workspace
DEFAULT_WS="default"
WORKSPACE_PATH=$(jj workspace root 2>/dev/null)
REPO_ROOT=$(jj root 2>/dev/null)
BOOKMARK=$(jj log -r '@-' --no-graph -T 'bookmarks' --limit 1 2>/dev/null)
```

| State | Menu | Cleanup |
|-------|------|---------|
| `WORKSPACE_PATH == REPO_ROOT` (default workspace) | Standard 4 options | No workspace to clean up |
| `WORKSPACE_PATH != REPO_ROOT` AND `BOOKMARK` non-empty (additional workspace, bookmark set) | Standard 4 options | Provenance-based (Step 6) |
| `WORKSPACE_PATH != REPO_ROOT` AND `BOOKMARK` empty (additional workspace, no bookmark) | Reduced 3 options (no merge) | No cleanup — externally managed |

### Step 3: Determine Base Branch

**git:**

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

**jj:**

```bash
# Find the trunk bookmark (main or master)
jj log -r 'trunk()' --no-graph -T 'bookmarks' --limit 1
```

Or ask: "This branch split from main - is that correct?"

### Step 4: Present Options

**Normal repo and named-branch worktree/workspace — present exactly these 4 options:**

```text
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Detached HEAD / bookmark-less workspace — present exactly these 3 options:**

```text
Implementation complete. You're in an externally-managed workspace
(detached HEAD or no bookmark). Merge isn't safe from here.

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)
3. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 5: Execute Choice

#### Option 1: Merge Locally

**git:**

```bash
# Get main repo root for CWD safety — avoid running cleanup from inside the worktree
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"

# Merge first — verify success before removing anything
git checkout <base-branch>
git pull
git merge <feature-branch>

# Verify tests on merged result
<test command>
```

Only after merge succeeds: cleanup workspace (Step 6), **then** delete branch:

```bash
git branch -d <feature-branch>
```

**jj:**

```bash
# jj has no "worktree blocks branch delete" problem, but the same
# ordering applies: rebase + verify before removing the workspace.
cd "$(jj root)"

# Rebase feature onto base branch, skip commits that become empty
jj rebase -s <rev> -o main --skip-emptied

# Verify tests on merged result
<test command>
```

Then: cleanup workspace (Step 6), then drop the bookmark:

```bash
jj bookmark delete <name>
```

#### Option 2: Push and Create PR

**git:**

```bash
# Push branch
git push -u origin <feature-branch>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

**jj:**

```bash
# Set bookmark and push
jj bookmark set <name> -r @-
jj git push -b <name>

# Create PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets of what changed>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

**Do NOT clean up workspace** — user needs it alive to iterate on PR feedback.

After the PR is created, suggest (do NOT run automatically):

> "PR #<n> created. Consider running `/review-pr <n>` to get a structured
> multi-aspect review before requesting human review."

#### Option 3: Keep As-Is

Report: "Keeping branch/bookmark <name>. Workspace preserved at <path>."

**Don't cleanup workspace.**

#### Option 4: Discard

**Confirm first:**

```text
This will permanently delete:
- Branch/bookmark <name>
- All commits: <commit-list>
- Workspace at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

If confirmed:

**git:**

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
```

Then: cleanup workspace (Step 6), then force-delete branch:

```bash
git branch -D <feature-branch>
```

**jj:**

```bash
cd "$(jj root)"
jj abandon <rev>
jj bookmark delete <name>
```

Then: cleanup workspace (Step 6).

### Step 5.5: Post-Merge Interactive Close (Options 1 and 2)

After **Option 1 (merge)** or **Option 2 (PR)** succeeds, reconcile bd state by closing beads whose work landed with this branch. Skip this step for Options 3 (keep) and 4 (discard).

1. **List in-flight beads in the epic:** `bd list --parent <epic-id> --status=in_progress --status=open` (covers both claimed and unclaimed). If no epic is associated with this branch, skip the step.

2. **Ask via `AskUserQuestion` (multi-select):** "Which beads merged with this work? (select all that apply)". Present each candidate with title and ID. Pre-select beads whose `--claim` matches the current actor as a hint.

3. **For each selected bead:** run `bd close <id> --reason="Merged in <branch-name>"`. For Option 2 (PR), use `--reason="Merged in <branch-name> via PR #<number>"` if the gh CLI returned a PR number.

4. **Epic auto-close:** after closing children, check `bd list --parent <epic-id> --status=open --status=in_progress`. If zero remain, run `bd close <epic-id> --reason="Epic complete; all children closed"`. The design bead's full audit trail (grounding notes, reviewer rounds, ADR IDs, materialization) is preserved on the closed epic.

5. **For un-selected open beads:** leave them open. They represent work that did NOT merge with this branch — likely candidates for the next branch or for follow-up beads.

**Degraded mode:** If `bd` is unavailable, print a warning and skip. The user is responsible for closing beads manually later.

### Step 6: Cleanup Workspace

**Only runs for Options 1 and 4.** Options 2 and 3 always preserve the workspace.

**Provenance check — only clean up workspaces we created.**

**git:**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)
```

- **If `GIT_DIR == GIT_COMMON`:** Normal repo, no worktree to clean up. Done.
- **If `WORKTREE_PATH` is under `<repo>_worktrees/`, `.worktrees/`,
  `worktrees/`, or `~/.config/superpowers/worktrees/`:** Superpowers (or
  this repo's `WorktreeCreate` hook) created this — we own cleanup.

  ```bash
  MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
  cd "$MAIN_ROOT"
  git worktree remove "$WORKTREE_PATH"
  git worktree prune  # Self-healing: clean up any stale registrations
  ```

- **Otherwise:** The host environment (harness) owns this workspace. Do
  NOT remove it. If your platform provides a workspace-exit tool, use it.
  Otherwise, leave the workspace in place.

**jj:**

```bash
WORKSPACE_NAME=$(jj workspace list 2>/dev/null | awk -F: 'NR==1{print $1}')
WORKSPACE_PATH=$(jj workspace root 2>/dev/null)
REPO_ROOT=$(jj root 2>/dev/null)
```

- **If `WORKSPACE_PATH == REPO_ROOT`:** Default workspace, no workspace to clean up. Done.
- **If `WORKSPACE_PATH` is under `<repo>_worktrees/`, `.worktrees/`,
  `worktrees/`, or `~/.config/superpowers/worktrees/`:** Superpowers (or
  this repo's `WorktreeCreate` hook) created this — we own cleanup.

  ```bash
  cd "$REPO_ROOT"
  jj workspace forget "$WORKSPACE_NAME"
  rm -rf "$WORKSPACE_PATH"
  ```

  Note: `jj workspace forget` de-registers the workspace but does NOT delete files — you must `rm -rf` after.
- **Otherwise:** The host environment (harness) owns this workspace. Do NOT remove it.

## Quick Reference

| Option | Merge | Push | Keep Workspace | Cleanup Branch |
|--------|-------|------|----------------|----------------|
| 1. Merge locally | yes | - | - | yes |
| 2. Create PR | - | yes | yes | - |
| 3. Keep as-is | - | - | yes | - |
| 4. Discard | - | - | - | yes (force) |

## Common Mistakes

## Skipping test verification

- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

## Open-ended questions

- **Problem:** "What should I do next?" is ambiguous
- **Fix:** Present exactly 4 structured options (or 3 for detached HEAD / bookmark-less workspace)

## Cleaning up worktree for Option 2

- **Problem:** Remove worktree user needs for PR iteration
- **Fix:** Only cleanup for Options 1 and 4

## Deleting branch before removing worktree (git)

- **Problem:** `git branch -d` fails because worktree still references the branch
- **Fix:** Merge first, remove worktree, then delete branch

## Running git worktree remove from inside the worktree

- **Problem:** Command fails silently when CWD is inside the worktree being removed
- **Fix:** Always `cd` to main repo root before `git worktree remove` (or `jj workspace forget`)

## Cleaning up harness-owned workspaces

- **Problem:** Removing a workspace the harness created causes phantom state
- **Fix:** Only clean up workspaces under known superpowers/repo-owned paths (provenance check in Step 6)

## No confirmation for discard

- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

## Using git commands in jj repos

- **Problem:** `git checkout` / `git branch -D` corrupts jj state
- **Fix:** Always detect VCS first; use jj equivalents in jj repos

## Red Flags

**Never:**

- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Use git mutating commands in jj repos
- Remove a worktree/workspace before confirming merge success
- Clean up workspaces you didn't create (provenance check)
- Run `git worktree remove` / `jj workspace forget` from inside the workspace

**Always:**

- Run the bd pre-flight check (Step 0) before verifying tests
- Detect VCS before running commands
- Verify tests before offering options
- Detect environment before presenting menu
- Present exactly 4 options (or 3 for detached HEAD / bookmark-less workspace)
- Get typed confirmation for Option 4
- Run the post-merge interactive close (Step 5.5) after Options 1 and 2
- Clean up workspace for Options 1 and 4 only
- `cd` to main repo root before workspace removal
- Run `git worktree prune` after removal (git)

## Integration

**Called by:**

- **subagent-driven-development** (Step 7) - After all tasks complete
- **executing-plans** (Step 5) - After all batches complete

**Pairs with:**

- **using-worktrees** - Cleans up workspace created by that skill
