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
```

Usage:

```bash
jj sync     # After any PR merges -- one command to reconcile
jj landed   # Clean up stale local bookmarks whose content landed
```

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
