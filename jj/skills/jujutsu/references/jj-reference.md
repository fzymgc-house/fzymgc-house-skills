# jj Command Reference

Detailed command reference for Jujutsu (jj) operations beyond the essentials in SKILL.md.

## Revset Expressions

Revsets are jj's query language for selecting revisions.

### Common Revsets

| Expression | Meaning |
|------------|---------|
| `@` | Working copy commit |
| `@-` | Parent of working copy |
| `@--` | Grandparent |
| `trunk()` | Main branch tip |
| `root()` | Repository root |
| `all()` or `::` | All revisions |
| `visible_heads()` | All head revisions |
| `bookmarks()` | All bookmarked revisions |
| `remote_bookmarks()` | All remote-tracking bookmarks |
| `mine()` | Revisions authored by you |
| `empty()` | Empty revisions (no diff) |
| `conflict()` | Revisions with unresolved conflicts |
| `description(pattern)` | Revisions matching description |
| `author(pattern)` | Revisions by author |

### Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `x & y` | Intersection | `mine() & bookmarks()` |
| `x \| y` | Union | `@- \| @--` |
| `~x` | Complement (not) | `~empty()` |
| `x-` | Parents | `@-` (parent of @) |
| `x+` | Children | `trunk()+` (children of trunk) |
| `x..y` | Range (ancestors of y, not ancestors of x) | `trunk()..@` |
| `::x` | Ancestors of x (inclusive) | `::@` |
| `x::` | Descendants of x (inclusive) | `trunk()::` |

### Useful Queries

```bash
# All your unpushed work
jj log -r 'mine() & ~ancestors(trunk())'

# Commits on current branch not yet on main
jj log -r 'trunk()..@'

# All bookmarked commits that are empty
jj log -r 'bookmarks() & empty()'

# Commits with conflicts
jj log -r 'conflict()'

# All mutable (non-immutable) commits
jj log -r 'mutable()'
```

## Templates

Templates control output formatting in `jj log`, `jj show`, etc.

```bash
# Show only change IDs (useful for scripting)
jj log -r @ --no-graph -T 'change_id.short(8)'

# Show change ID and commit ID together
jj log -T 'change_id.short(8) ++ " " ++ commit_id.short(8) ++ " " ++ description.first_line()'

# Get the full change ID of current revision
jj log -r @ --no-graph -T 'change_id'
```

## Advanced Rebase

### Rebase Variants

```bash
# Rebase a single revision (detach from its current location)
jj rebase -r <rev> -o <dest>

# Rebase a subtree (revision and all descendants)
jj rebase -s <rev> -o <dest>

# Rebase a range (branch of revisions)
jj rebase -b <rev> -o <dest>

# Rebase with auto-abandon of emptied commits
jj rebase -o <dest> --skip-emptied
```

### Key Differences

| Flag | Behavior |
|------|----------|
| `-r` | Moves only the specified revision; children are rebased onto its parent |
| `-s` | Moves the revision and all its descendants |
| `-b` | Moves the entire branch containing the revision |
| `--skip-emptied` | Auto-abandons commits that become empty after rebase |

## Bookmark Management

### Tracking and Untracking

```bash
# Start tracking a remote bookmark (auto-merge on fetch)
jj bookmark track <name>@<remote>

# Stop tracking
jj bookmark untrack <name>@<remote>

# List with tracking info
jj bookmark list --all
```

### Bookmark Patterns

```bash
# Move bookmark to current working copy
jj bookmark set <name> -r @

# Move bookmark to parent (useful after jj new)
jj bookmark set <name> -r @-

# Force-push after bookmark move
jj git push -b <name>
```

## File Operations

```bash
# List all tracked files
jj file list

# List files in a specific revision
jj file list -r <rev>

# Show file at a specific revision (like git show <rev>:<file>)
jj file show -r <rev> <path>

# Show changes to a specific file
jj diff <path>
jj diff -r <rev> <path>
```

## Operation Log

jj tracks all operations for undo/redo:

```bash
# View operation history
jj op log

# Undo last operation
jj undo

# Restore to a specific operation
jj op restore <op-id>
```

**Important:** The op log only records **successful** operations. A failed command
leaves no op-log entry. `jj undo` always targets the most recent successful
operation -- never "undo twice" to account for a failure.

## Diff Formats

```bash
# Default diff
jj diff

# Git-style diff
jj diff --git

# Summary only (files changed)
jj diff --summary

# Stat (insertions/deletions per file)
jj diff --stat

# Diff between two revisions
jj diff --from <rev1> --to <rev2>
```
