---
name: using-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git/jj fallback
metadata:
  author: fzymgc-house
---

# Using Worktrees

> **Before running any VCS commands, read `references/vcs-preamble.md` and use
> the appropriate commands for the detected VCS (git or jj).**

## Overview

Ensure work happens in an isolated workspace. Prefer your platform's
native worktree tools. Fall back to manual git worktrees or jj workspaces
only when no native tool is available.

- **git**: linked worktrees via `git worktree add`
- **jj**: additional workspaces via `jj workspace add` (MUST use this, never `git worktree add` in jj repos)

**Core principle:** Detect existing isolation first. Then use native tools. Then fall back to git/jj. Never fight the harness.

**Announce at start:** "I'm using the using-worktrees skill to set up an isolated workspace."

## VCS Detection

```bash
if jj root >/dev/null 2>&1; then
  VCS=jj
  jj git fetch  # refresh origin so trunk() is current (local `main` stays stale)
else
  VCS=git
  git fetch origin  # refresh origin so origin/<default> is current
fi
```

## Step 0: Detect Existing Isolation

**Before creating anything, check if you are already in an isolated workspace.**

**git:**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
SUPERPROJECT=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
```

`GIT_DIR != GIT_COMMON` is also true inside git submodules — `SUPERPROJECT` distinguishes a submodule from a linked worktree.

- **`GIT_DIR != GIT_COMMON` AND `SUPERPROJECT` empty**: You are already
  in a linked worktree. Skip to Step 3 (Project Setup). Do NOT create
  another worktree.
  - On a branch: "Already in isolated workspace at `<path>` on branch
    `<BRANCH>`."
  - Detached HEAD (empty `BRANCH`): "Already in isolated workspace at
    `<path>` (detached HEAD, externally managed). Branch creation needed
    at finish time."
- **`GIT_DIR == GIT_COMMON` (or in a submodule)**: You are in a normal repo checkout — continue to Step 1.

**jj:**

```bash
REPO_ROOT=$(jj root 2>/dev/null)
WORKSPACE_PATH=$(jj workspace root 2>/dev/null)
WORKSPACE_NAME=$(jj workspace list 2>/dev/null | awk -F: 'NR==1{print $1}')
BOOKMARK=$(jj log -r '@-' --no-graph -T 'bookmarks' --limit 1 2>/dev/null)
```

- **`WORKSPACE_PATH != REPO_ROOT`**: You are already in an additional jj workspace. Skip to Step 3 (Project Setup). Do NOT create another workspace.
  - With bookmark: "Already in isolated workspace `<WORKSPACE_NAME>` at `<path>` (bookmark `<BOOKMARK>`)."
  - No bookmark: "Already in isolated workspace `<WORKSPACE_NAME>` at
    `<path>` (no bookmark — externally managed). Bookmark creation needed
    at finish time."
- **`WORKSPACE_PATH == REPO_ROOT`**: You are in the default workspace — continue to Step 1.

### Consent

Has the user already indicated their worktree preference in your
instructions (CLAUDE.md, AGENTS.md, or this session)? If yes, honor it
without asking. If not:

> "Would you like me to set up an isolated worktree? It protects your current branch from changes."

If the user declines consent, work in place and skip to Step 3.

## Step 1: Create Isolated Workspace

**You have two mechanisms. Try them in this order.**

### 1a. Native Worktree Tools (preferred)

The user has asked for an isolated workspace (Step 0 consent). Do you already have a way to create a worktree? It might be:

- A tool named `EnterWorktree`, `WorktreeCreate`, or similar
- A `/worktree` slash command
- A `--worktree` flag on the command you're invoking
- A `WorktreeCreate`/`WorktreeRemove` hook. The dev-flow plugin ships VCS-aware
  ones (`dev-flow/hooks/worktree-create`, `worktree-remove`) declared in its
  `hooks.json`: a configured `WorktreeCreate` hook *replaces* `EnterWorktree`'s
  built-in git-worktree behavior, so in a jj or colocated jj+git repo
  `EnterWorktree` creates a sibling jj **workspace** (trunk-based + bookmarked),
  not a `.claude/worktrees/` git worktree.

If you have one, use it and skip to Step 3.

Native tools handle directory placement, branch/bookmark creation, hook
installation, and cleanup automatically. Using `git worktree add` or
`jj workspace add` when you have a native tool creates phantom state your
harness can't see or manage.

> **`ExitWorktree` caveat (jj):** `ExitWorktree`'s uncommitted-change check is
> git-only — in a jj workspace it reports "Could not verify worktree state" and
> requires `discard_changes: true` to remove. That bypasses its safety check, so
> before removing a jj worktree confirm your work is committed/pushed yourself
> (or finish via `finishing-a-development-branch`, which forgets the workspace
> explicitly). Removal itself works: the `WorktreeRemove` hook runs
> `jj workspace forget` + `rm -rf`.

Only proceed to Step 1b if you have no native worktree tool available.

### 1b. Manual Fallback

**Only use this if Step 1a does not apply.**

#### Workspace Directory Convention

Use the **sibling directory** pattern to avoid confusing LSP servers with nested repos:

```text
<repo>/                    # main repo
<repo>_worktrees/          # workspace parent (sibling)
  feature-auth/            # one workspace per task
  fix-bug-123/
```

```bash
if [ "$VCS" = "jj" ]; then
  repo_root=$(jj root)
else
  repo_root=$(git rev-parse --show-toplevel)
fi
project=$(basename "$repo_root")
worktree_parent="$(dirname "$repo_root")/${project}_worktrees"
mkdir -p "$worktree_parent"
```

The parent directory is `../<repo-basename>_worktrees/`. This is determined automatically — no user prompt needed.

#### Create the Workspace

Base the new worktree on **current origin trunk**, not stale local state (you
fetched above; see `references/vcs-preamble.md` § "Ensure Current Before You
Work" for the currency target and the jj-local-`main` trap).

**git:**

```bash
# origin/main is the current default branch; resolve a different default if needed
git worktree add "$worktree_parent/$BRANCH_NAME" -b "$BRANCH_NAME" origin/main
cd "$worktree_parent/$BRANCH_NAME"
```

**jj:**

```bash
# -r 'trunk()' bases the workspace on the fetched remote trunk, not the stale
# local `main` bookmark (which jj git fetch does NOT advance).
jj workspace add "$worktree_parent/$WORKSPACE_NAME" --name "$WORKSPACE_NAME" -r 'trunk()'
cd "$worktree_parent/$WORKSPACE_NAME"
# Create a bookmark for the workspace (needed for pushing/PRs)
jj bookmark create "$WORKSPACE_NAME" -r @
# If the repo uses beads, point bd at the main repo's database. jj workspaces
# are NOT git worktrees, so bd's git common-directory discovery cannot find
# the shared database — without this, bd commands fail in the workspace.
# (.beads/redirect is untracked; .beads/.gitignore already covers it.)
if [ -d "$REPO_ROOT/.beads" ]; then
  mkdir -p .beads
  echo "$REPO_ROOT/.beads" > .beads/redirect
fi
```

**Sandbox fallback:** If `git worktree add` / `jj workspace add` fails
with a permission error (sandbox denial), tell the user the sandbox
blocked workspace creation and you're working in the current directory
instead. Then run setup and baseline tests in place.

## Step 2: Install Hooks

If the repo uses git hooks, install them in the new workspace:

```bash
[[ -f lefthook.yaml ]] && lefthook install
[[ -f .pre-commit-config.yaml ]] && pre-commit install
[[ -f .beads/config.yaml ]] && bd hooks install --chain
```

## Step 3: Project Setup

Auto-detect and run appropriate setup:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

## Step 4: Verify Clean Baseline

Run tests to ensure workspace starts clean:

```bash
# Use project-appropriate command
npm test / cargo test / pytest / go test ./...
```

**If tests fail:** Report failures, ask whether to proceed or investigate.

**If tests pass:** Report ready.

### Report

```text
Workspace ready at <full-path>
VCS: <git|jj>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| Already in linked worktree / additional jj workspace | Skip creation (Step 0) |
| In a submodule (git) | Treat as normal repo (Step 0 guard) |
| Native worktree tool available | Use it (Step 1a) |
| Repo has `WorktreeCreate` hook | Native tool — Step 1a |
| No native tool, VCS is git | Manual git worktree (Step 1b) |
| No native tool, VCS is jj | Manual jj workspace (Step 1b) |
| Tests fail during baseline | Report failures + ask |
| No package.json/Cargo.toml | Skip dependency install |
| Permission error on create | Sandbox fallback, work in place |

## Cleanup

Cleanup happens in `finishing-a-development-branch` using a provenance
check — only workspaces created under known superpowers/repo-owned paths
(`<repo>_worktrees/`, `.worktrees/`, `worktrees/`,
`~/.config/superpowers/worktrees/`) are removed. Harness-owned workspaces
are left in place for the host to manage.

## Common Mistakes

### Fighting the harness

- **Problem:** Using `git worktree add` / `jj workspace add` when the platform already provides isolation
- **Fix:** Step 0 detects existing isolation. Step 1a defers to native tools.

### Skipping detection

- **Problem:** Creating a nested workspace inside an existing one
- **Fix:** Always run Step 0 before creating anything

### Using git worktree in jj repos

- **Problem:** Creates a git worktree that jj doesn't track, causing sync issues
- **Fix:** Always detect VCS first; use `jj workspace add` in jj repos

### Forgetting to create a bookmark (jj)

- **Problem:** Can't push or create PRs without a bookmark
- **Fix:** Always `jj bookmark create <name> -r @` after workspace creation (Step 1b)

### Missing .beads/redirect (jj)

- **Problem:** bd resolves the workspace's checked-out `.beads/` (tracked config
  files, no database) as a standalone workspace, so bd commands fail — jj
  workspaces are not git worktrees, and bd's git common-directory discovery
  can't find the shared database
- **Fix:** Write `.beads/redirect` pointing at the main repo's `.beads` after
  `jj workspace add` (Step 1b). Native worktree tools get this from the
  WorktreeCreate hook automatically.

### Forgetting to fetch (jj)

- **Problem:** Workspace starts with stale state
- **Fix:** Always `jj git fetch` before creating workspace (VCS Detection block)

### Nesting workspaces inside the repo

- **Problem:** LSP servers see nested repos, causing indexing confusion
- **Fix:** Always use sibling directory pattern (`<repo>_worktrees/`)

### Proceeding with failing tests

- **Problem:** Can't distinguish new bugs from pre-existing issues
- **Fix:** Report failures, get explicit permission to proceed

## Red Flags

**Never:**

- Create a workspace when Step 0 detects existing isolation
- Use `git worktree add` / `jj workspace add` when you have a native worktree tool. This is the #1 mistake — if you have it, use it.
- Skip Step 1a by jumping straight to Step 1b's commands
- Use `git worktree add` in jj repos
- Skip the `jj bookmark create` step in jj workspaces
- Skip the `.beads/redirect` setup in jj workspaces when the repo uses beads
- Skip baseline test verification
- Proceed with failing tests without asking

**Always:**

- Run Step 0 detection first
- Detect VCS before running commands
- Prefer native tools over manual fallback
- Use sibling `<repo>_worktrees/` layout for manual creation
- `jj git fetch` before creating a jj workspace
- Auto-detect and run project setup
- Verify clean test baseline

## Example Workflow

**git (manual fallback):**

```text
You: I'm using the using-worktrees skill to set up an isolated workspace.

[VCS detected: git]
[Step 0: GIT_DIR == GIT_COMMON → normal repo, continue]
[Step 1a: no native worktree tool detected]
[Step 1b: git worktree add ../myproject_worktrees/auth -b feature/auth]
[Step 2: lefthook install]
[Step 3: npm install]
[Step 4: npm test — 47 passing]

Workspace ready at /Users/dev/myproject_worktrees/auth
VCS: git
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

**jj (manual fallback):**

```text
You: I'm using the using-worktrees skill to set up an isolated workspace.

[VCS detected: jj]
[jj git fetch]
[Step 0: WORKSPACE_PATH == REPO_ROOT → default workspace, continue]
[Step 1a: no native worktree tool detected]
[Step 1b: jj workspace add ../myproject_worktrees/auth --name auth]
[Step 1b: jj bookmark create auth -r @]
[Step 2: lefthook install]
[Step 3: npm install]
[Step 4: npm test — 47 passing]

Workspace ready at /Users/dev/myproject_worktrees/auth
VCS: jj
Tests passing (47 tests, 0 failures)
Ready to implement auth feature
```

**git (already in worktree — Step 0 skip):**

```text
You: I'm using the using-worktrees skill to set up an isolated workspace.

[VCS detected: git]
[Step 0: GIT_DIR != GIT_COMMON, not a submodule → already isolated]

Already in isolated workspace at /Users/dev/myproject_worktrees/auth on branch feature/auth.
[Step 3: npm install]
[Step 4: npm test — 47 passing]
Ready to implement auth feature
```

## Integration

**Called by:**

- **brainstorming** — REQUIRED when design is approved and implementation follows
- **subagent-driven-development** — REQUIRED before executing any tasks
- **executing-plans** — REQUIRED before executing any tasks
- Any skill needing isolated workspace

**Pairs with:**

- **finishing-a-development-branch** — Handles cleanup with the same provenance check
