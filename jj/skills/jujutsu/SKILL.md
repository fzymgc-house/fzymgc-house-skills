---
name: jujutsu
description: >-
  Jujutsu (jj) VCS workflow guidance. MUST activate on ANY VCS
  operation when `.jj/` exists in the repo root. Use when the user
  mentions jj, jujutsu, or when a colocated jj repo is detected.
allowed-tools:
  - "Bash(jj *)"
  - "Bash(test *)"
metadata:
  author: fzymgc-house
  version: 0.1.0 # x-release-please-version
---

# Jujutsu (jj) VCS Workflow

## Contents

- [Detection](#detection)
- [Agent Environment Rules](#agent-environment-rules)
- [Core Concepts](#core-concepts)
- [Essential Workflow](#essential-workflow)
- [Refining Commits](#refining-commits)
- [Bookmarks](#bookmarks)
- [Workspaces](#workspaces)
- [Git Integration](#git-integration)
- [Conflict Handling](#conflict-handling)
- [Quick Reference](#quick-reference)
- [See Also](#see-also)

## Detection

Before any VCS operation, check for `.jj/` in the repo root:

```bash
test -d .jj && echo "jj repo detected"
```

If `.jj/` exists:

- Use `jj` for ALL version control operations
- Do NOT use `git commit`, `git checkout`, `git branch`, `git merge`, `git rebase`, or other
  mutating git commands
- `gh` (GitHub CLI) is fine -- it only reads `.git/` metadata
- Read-only git commands (`git log`, `git diff`, `git status`, `git rev-parse`) are safe to use

## Agent Environment Rules

Agents run non-interactively. Follow these constraints strictly:

- Always use `-m` for commit/describe messages -- never open an editor
- Verify state with `jj st` after any mutation
- Always use `--no-pager` or pass `--config ui.paginate=never` if pager interferes

**Never use these interactive commands:**

| Command | Why | Alternative |
|---------|-----|-------------|
| `jj split` | Opens editor to select hunks | Manually edit files, commit separately |
| `jj resolve` | Opens merge tool | Edit conflict markers directly |
| `jj squash -i` | Interactive hunk selection | Use `jj squash` (non-interactive) |

## Core Concepts

### Working Copy Is a Commit

In jj, the working copy is always a commit (`@`). There is no staging area. Every file change
is automatically part of the working-copy commit.

### Change IDs vs Commit IDs

| Property | Change ID | Commit ID |
|----------|-----------|-----------|
| Format | Short alpha string (e.g., `kxryzmsp`) | SHA hex (e.g., `a1b2c3d4`) |
| Stability | Stable across rewrites | Changes on rewrite |
| Use for | Referring to logical changes | Pinpointing exact versions |

Prefer change IDs when referring to revisions -- they survive `squash`, `rebase`, and `amend`.

### Key Revsets

| Symbol | Meaning |
|--------|---------|
| `@` | Working copy (current change) |
| `@-` | Parent of working copy |
| `@--` | Grandparent of working copy |
| `root()` | Root commit |
| `trunk()` | Main branch tracking commit |

## Essential Workflow

### Create and Describe Commits

```bash
# Describe current change and start a new empty one (like git commit)
jj commit -m "feat(scope): add new feature"

# Create a new empty change on top of current
jj new

# Update description of current change without creating a new one
jj describe -m "fix(scope): correct the bug"
```

### View History and Changes

```bash
# View commit log (default: current branch ancestry)
jj log

# View log with all revisions
jj log -r 'all()'

# Show diff of current working copy
jj diff

# Show diff of a specific revision
jj show <rev>

# Status of working copy
jj st
```

## Refining Commits

### Squash Changes

```bash
# Move all changes from @ into @- (squash into parent)
jj squash

# Move changes from @ into a specific revision
jj squash --into <rev>
```

### Absorb Changes

```bash
# Auto-distribute working copy changes to the commits that last modified those lines
jj absorb
```

This automatically routes each hunk to the right ancestor commit (similar to the
third-party `git-absorb` tool, but built into jj).

### Abandon, Undo, and Restore

```bash
# Remove a commit (changes are rebased into descendants)
jj abandon <rev>

# Undo the last jj operation
jj undo

# Discard all changes in the working copy
jj restore

# Restore a specific file from a revision
jj restore --from <rev> <path>
```

**Note:** `jj split` is interactive and not safe for agents. To split a commit manually,
create a new change, move specific files, then squash the rest.

## Bookmarks

Bookmarks are jj's equivalent of git branches.

```bash
# Create a bookmark at the current change
jj bookmark create <name>

# Move a bookmark to a specific revision (creates if missing)
jj bookmark set <name> -r <rev>

# List all bookmarks
jj bookmark list

# Delete a bookmark
jj bookmark delete <name>
```

Short forms: `jj b c`, `jj b s`, `jj b l`, `jj b d`.

Bookmarks do NOT auto-advance when you create new commits. You must explicitly update
them before pushing:

```bash
jj bookmark set my-feature -r @
jj git push -b my-feature
```

## Workspaces

Workspaces provide isolated working copies sharing the same repo storage. They replace
git worktrees.

```bash
# Create a workspace
jj workspace add ../my-workspace --name my-workspace

# List workspaces
jj workspace list

# Forget a workspace (de-register, does NOT delete files)
jj workspace forget <name>

# Fix a stale workspace after concurrent edits
jj workspace update-stale
```

Key behaviors:

- `jj workspace list` shows all workspaces (format: `<name>: <change-id-prefix> <commit-id-prefix> <description>`,
  e.g. `default: rwoumssn 094ee48c (empty) (no description set)`); there is no
  `(current)` marker — identify the current workspace from the working directory
  path (sibling worktrees use `<repo>_worktrees/<workspace-name>/`) or via
  `jj workspace root`
- Each workspace has its own working-copy commit (`@`)
- Changes committed in one workspace are immediately visible in others
- Use `jj workspace update-stale` if a workspace falls behind

## Git Integration

For full details, read `references/jj-git-interop.md`.

### Push and Fetch

```bash
# Push a bookmark to its remote
jj git push -b <bookmark>

# Push the current change (auto-generates a bookmark named push-<id>)
jj git push --change @

# Fetch from all remotes
jj git fetch
```

### Colocated Repos

In colocated repos (both `.jj/` and `.git/` present), every `jj` command auto-syncs
with the underlying git repo. The `gh` CLI works normally because it reads `.git/`.

### Creating a PR

```bash
# Ensure bookmark exists and is at the right revision
jj bookmark set my-feature -r @
jj git push -b my-feature

# Create PR via GitHub CLI
gh pr create --head my-feature --title "..." --body "..."
```

## Conflict Handling

jj allows committing conflicts -- they are tracked as part of the commit, not blocking.

### Detecting Conflicts

```bash
jj st   # Shows "Conflict" markers if present
jj log  # Conflicted commits show a conflict icon
```

### Resolving Conflicts

1. Open the conflicted file and remove conflict markers (`<<<<<<<`, `>>>>>>>`)
2. Save the file
3. Run `jj st` to verify the conflict is resolved

Do NOT use `jj resolve` -- it launches an interactive merge tool that hangs in agent
environments.

## Quick Reference

| Task | Command |
|------|---------|
| Commit and start new change | `jj commit -m "msg"` |
| Describe current change | `jj describe -m "msg"` |
| New empty change | `jj new` |
| New change on specific parent | `jj new <rev>` |
| New merge change | `jj new <rev1> <rev2>` |
| View log | `jj log` |
| View diff | `jj diff` |
| Show revision | `jj show <rev>` |
| Status | `jj st` |
| Squash into parent | `jj squash` |
| Absorb into ancestors | `jj absorb` |
| Abandon change | `jj abandon <rev>` |
| Undo last operation | `jj undo` |
| Restore working copy | `jj restore` |
| Rebase onto new parent | `jj rebase -s <src> -d <dest>` |
| Cherry-pick (single rev) | `jj rebase -r <change-id> -d <dest>` |
| Create bookmark | `jj bookmark create <name>` |
| Move bookmark | `jj bookmark set <name> -r <rev>` |
| Push bookmark | `jj git push -b <name>` |
| Fetch remotes | `jj git fetch` |
| List files | `jj file list` |
| Current location | `jj log -r @ --no-graph -T 'change_id.short(8)'` |
| Add workspace | `jj workspace add <path> --name <name>` |
| List workspaces | `jj workspace list` |
| Remove workspace | `jj workspace forget <name>` |

## See Also

For session-level change management (splitting, describing, inserting changes),
see the `jjagent` plugin.
