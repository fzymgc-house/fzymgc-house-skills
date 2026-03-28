# jj Workflow Reference

End-to-end workflow recipes for common jj + GitHub patterns.

## Recommended Aliases

Add to `~/.config/jj/config.toml`:

```toml
[aliases]
# Fetch and rebase current work onto main, dropping landed commits
sync = ["util", "exec", "--", "sh", "-c", "jj git fetch && jj rebase -o main --skip-emptied"]

# Abandon all local commits whose content is already in main
landed = ["abandon", "-r", "ancestors(bookmarks()) & ~ancestors(main)"]

# Move the closest bookmark to the closest pushable change (solves "forgot to advance bookmark")
tug = ["bookmark", "move", "--from", "heads(::@ & bookmarks())", "--to", "@"]
```

Usage:

```bash
jj sync     # After any PR merges -- one command to reconcile
jj landed   # Clean up stale local bookmarks whose content landed
jj tug      # Advance nearest bookmark to current change before pushing
```

The `tug` alias solves the most common footgun: bookmarks don't auto-advance in jj,
so `jj git push -b my-feature` pushes stale content unless you `jj bookmark set` first.
With `tug`, the workflow becomes: edit → `jj tug` → `jj git push`.

## Single PR Lifecycle (Detailed)

### 1. Start Work

```bash
jj git fetch                     # Always fetch first
jj new main                      # New change on top of main
# ... make changes ...
jj describe -m "feat: my feature"
jj bookmark create my-feature -r @
jj git push -b my-feature
gh pr create --head my-feature --title "feat: my feature" --body "..."
```

### 2. Address Review Comments

Two styles for incorporating feedback:

**Rewrite style** (amend the original commit):

```bash
jj edit <change-id>              # Edit the original commit directly
# ... make fixes ...
jj git push -b my-feature        # Force-pushes the rewritten commit
```

**Squash style** (new commit folded in):

```bash
jj new my-feature                # New child of bookmark tip
# ... make fixes ...
jj squash                        # Fold into parent
jj git push --bookmark my-feature
```

**Important:** Once you've pushed, do NOT locally `jj describe` or `jj squash`
to tweak the commit further. This creates divergence when the PR is merged.

### 3. After Squash-Merge on GitHub

```bash
jj git fetch
jj rebase -o main --skip-emptied
jj bookmark delete my-feature
```

### 4. Continue

```bash
jj new main                      # Fresh start on updated main
```

## Stacked PRs Workflow

Stacked PRs are multiple dependent PRs where each builds on the previous.

### Creating a Stack

```bash
# First PR
jj new main
# ... implement feature A ...
jj describe -m "feat: feature A"
jj bookmark create feature-a -r @
jj git push -b feature-a

# Second PR (depends on A)
jj new feature-a
# ... implement feature B ...
jj describe -m "feat: feature B (depends on A)"
jj bookmark create feature-b -r @
jj git push -b feature-b

# Third PR (depends on B)
jj new feature-b
# ... implement feature C ...
jj describe -m "feat: feature C (depends on B)"
jj bookmark create feature-c -r @
jj git push -b feature-c
```

### After First PR Lands (Squash-Merged)

When feature-a's PR is squash-merged on GitHub:

```bash
jj git fetch
jj rebase -s <change-id-of-feature-b> -o main --skip-emptied
jj bookmark delete feature-a
```

What happens:

- feature-a's commit becomes empty (content already in main) and is auto-abandoned
- feature-b rebases cleanly onto new main
- feature-c follows feature-b (descendants move together with `-s`)

### After Second PR Lands

```bash
jj git fetch
jj rebase -s <change-id-of-feature-c> -o main --skip-emptied
jj bookmark delete feature-b
```

### Key Points

- Always use `-s` (source + descendants) when rebasing stacked PRs
- `--skip-emptied` handles the abandoned commits automatically
- Use change IDs (not commit hashes) -- they survive the rebase

## Divergence Recovery

When `(divergent)` appears in `jj log`, a commit has diverged (modified both locally and remotely).

### Identify the Problem

```bash
jj log    # Look for (divergent) markers on commits
```

### Standard Fix

```bash
# Find the stale local copy (the one you don't want)
jj log -r 'divergent()'

# Abandon the stale local copy
jj abandon <stale-commit-hash>

# Rebase remaining work
jj rebase -o main --skip-emptied
```

### Nuclear Option (Start Fresh)

If divergence is widespread:

```bash
jj git fetch
jj abandon 'mine() & ~ancestors(trunk()) & empty()'
jj rebase -o main --skip-emptied
```

## Daily Sync Routine

Run at the start of each work session:

```bash
jj git fetch
jj rebase -o main --skip-emptied
jj log -r 'mine() & ~ancestors(trunk())'   # Review your active work
```

Or with the alias:

```bash
jj sync
jj log -r 'mine() & ~ancestors(trunk())'
```

## Agent-Specific Patterns

### Task Start

Every agent should begin with:

```bash
jj git fetch
jj rebase -o main --skip-emptied
```

### Scripting with Change IDs

Always use change IDs for stability:

```bash
# Get change ID for scripting
CHANGE_ID=$(jj log -r @ --no-graph -T 'change_id.short(8)')

# Reference later (survives rewrites)
jj show "$CHANGE_ID"
jj rebase -r "$CHANGE_ID" -o main
```

### Handling Divergence in Scripts

```bash
# Check for divergent commits
if jj log -r 'divergent()' --no-graph -T 'change_id' 2>/dev/null | grep -q .; then
  echo "Divergent commits detected -- abandoning stale copies"
  jj abandon 'divergent() & mutable()'
  jj rebase -o main --skip-emptied
fi
```

## Agent Fan-Out Workspace Pattern

Dispatch N agents to N workspaces, then merge results. jj workspaces are
superior to git worktrees for this because conflicts don't block work,
all changes are immediately visible across workspaces, and dependent
branches auto-rebase.

### Setup Phase (Orchestrator)

```bash
cd /path/to/repo
jj git fetch

# Create N workspaces, each starting from main
jj workspace add ../repo_worktrees/agent-1 --name agent-1 -r main
jj workspace add ../repo_worktrees/agent-2 --name agent-2 -r main
jj workspace add ../repo_worktrees/agent-3 --name agent-3 -r main
```

### Execution Phase (Agents Work in Parallel)

Each agent works independently. Concurrent jj commands are safe (lock-free
op log). Changes auto-commit into each workspace's `@`.

```bash
# Agent 1 (in ../repo_worktrees/agent-1/)
jj describe -m "feat: auth system"
# ... work ...
jj commit -m "feat: implement JWT auth"

# Agent 2 (in ../repo_worktrees/agent-2/)
jj describe -m "fix: database queries"
# ... work ...
jj commit -m "fix: add connection pooling"
```

### Integration Phase — Three Patterns

**A) Merge commit (parallel integration):**

```bash
# Back in main workspace — capture change IDs
A1=$(cd ../repo_worktrees/agent-1 && jj log -r @- --no-graph -T 'change_id.short(8)')
A2=$(cd ../repo_worktrees/agent-2 && jj log -r @- --no-graph -T 'change_id.short(8)')
A3=$(cd ../repo_worktrees/agent-3 && jj log -r @- --no-graph -T 'change_id.short(8)')

# Create merge commit
jj new $A1 $A2 $A3 -m "merge: integrate agent work"
```

**B) Linear rebase (sequential stack):**

```bash
jj rebase -s $A2 -o $A1
jj rebase -s $A3 -o $A2
# Result: main → agent1 → agent2 → agent3
```

**C) Megamerge → absorb (cross-cutting edits):**

```bash
jj new $A1 $A2 $A3 -m "merge: dev workspace"
jj new  # empty working copy for edits
# ... make cross-cutting fixes ...
jj absorb  # auto-routes hunks to correct ancestor commits
```

### Cleanup Phase

```bash
jj workspace forget agent-1 && rm -rf ../repo_worktrees/agent-1
jj workspace forget agent-2 && rm -rf ../repo_worktrees/agent-2
jj workspace forget agent-3 && rm -rf ../repo_worktrees/agent-3
```

### Colocated Workspace Limitation

Secondary workspaces do NOT get a `.git/` directory — only `.jj/`. Tools
requiring `.git/` (IDEs, npm, nix) may not work in secondary workspaces.
See jj-vcs/jj PR #4644 for tracking.

## Megamerge Pattern (Simultaneous Branch Work)

Create a merge commit with all active branches as parents. Work on everything
simultaneously, then squash/absorb changes to the correct branch.

```bash
# Merge all branch tips into one working commit
jj new branch-a branch-b branch-c -m "merge: working on everything"
jj new  # empty @ for squash workflow

# Make edits, then route them to the right branch:
# Option 1: squash into a specific parent
jj squash --into <branch-a-change-id> file1.py

# Option 2: absorb (auto-routes by blame)
jj absorb

# Rebase all branches onto updated main at once
jj git fetch
jj rebase -s 'all:roots(trunk()..@)' -o trunk() --skip-emptied
```

## GitHub Interactions

### Avoid "Update Branch" Button

GitHub's "Update branch" button (merge or rebase mode) creates commits that
diverge from your local state. This causes **bookmark conflicts** (`bookmark??`
in jj log). Always rebase locally instead:

```bash
jj git fetch
jj rebase -b <stack-tip> -o main
jj git push --bookmark <name>
```

### Push All Tracked Bookmarks

```bash
jj git push --tracked   # one command to push everything
```

## Third-Party Stacking Tools

| Tool | Stars | Language | Key Feature |
|------|-------|----------|-------------|
| jj-spr | 124 | Rust | Append-only PR branches (clean reviewer diffs) |
| jj-stack | 77 | TypeScript | Simple bookmark-to-PR mapping |
| jjpr | ~10 | Rust | Multi-forge (GH/GL/Forgejo), `watch` mode |
| jj-domino | ~1 | Go | Minimal, auto-bookmark via `--change` |

**jj-spr** is the most mature. Install and alias:

```bash
cargo install jj-spr
jj config set --user aliases.spr '["util", "exec", "--", "jj-spr"]'

# Usage:
jj spr diff --all    # create/update stacked PRs
jj spr land -r @--   # squash-merge bottom PR
```

## Empty Merge Commit as Future Merge Point

Pattern from "Flames of Code": use an empty merge commit (`----`) as a
synthetic integration point. All feature branches merge into it; WIP branches
fork from it.

```bash
# Create the merge point
jj new feature-a feature-b feature-c -m "----"

# WIP branches fork from it
jj new <merge-point-change-id> -m "wip: experimental refactor"

# Conflicts at ---- = features can't land independently (signal!)
# Conflicts above ---- = only WIP branches affected (safe to push features)
```

## Common Footguns

### Lost Work After `jj new`

**Symptom:** You write files, run `jj new main`, and the files are "gone."

**What actually happens:** jj auto-snapshots the working copy into a commit, then
`jj new main` creates a new empty `@` on `main`. The old change still exists in
history but has no bookmark or description, making it hard to find. The files are
no longer in the working directory because `@` moved.

**Prevention:** Always commit or describe before creating a new change:

```bash
# Write files...
jj commit -m "feat: my work"    # Commit first, then start new work
jj new main                      # Now safe -- previous work is committed

# Or at minimum, describe and bookmark:
jj describe -m "wip: my work"
jj bookmark create my-work
jj new main
```

**Recovery:** If you already lost track:

```bash
# Find orphaned changes (no bookmark, not ancestor of @)
jj log -r 'mine() & ~ancestors(@) & ~empty()'

# Edit the lost change to get files back
jj edit <change-id>
```

### Forgetting to Update Bookmarks Before Push

**Symptom:** `jj git push -b my-feature` pushes stale content.

**What happens:** Bookmarks don't auto-advance in jj. After creating new commits,
the bookmark still points at the old revision.

**Fix:** Always set the bookmark before pushing:

```bash
jj bookmark set my-feature -r @
jj git push -b my-feature
```
