---
name: jujutsu
description: >-
  Jujutsu (jj) VCS workflow guidance. MUST activate on ANY VCS
  operation when `jj root` succeeds or when `.jj/` exists in the repo
  root. Use when the user mentions jj, jujutsu, or when a colocated jj
  repo is detected.
allowed-tools:
  - "Bash(jj log)"
  - "Bash(jj log *)"
  - "Bash(jj diff *)"
  - "Bash(jj st)"
  - "Bash(jj st *)"
  - "Bash(jj show *)"
  - "Bash(jj bookmark *)"
  - "Bash(jj workspace *)"
  - "Bash(jj git *)"
  - "Bash(jj new)"
  - "Bash(jj new *)"
  - "Bash(jj edit *)"
  - "Bash(jj commit *)"
  - "Bash(jj squash)"
  - "Bash(jj squash *)"
  - "Bash(jj restore)"
  - "Bash(jj restore *)"
  - "Bash(jj describe *)"
  - "Bash(jj abandon *)"
  - "Bash(jj rebase *)"
  - "Bash(jj absorb)"
  - "Bash(jj absorb *)"
  - "Bash(jj file *)"
  - "Bash(jj undo)"
  - "Bash(jj undo *)"
  - "Bash(jj root)"
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
- [GitHub Squash-Merge Workflow](#github-squash-merge-workflow)
- [Divergent Changes](#divergent-changes)
- [Conflict Handling](#conflict-handling)
- [Quick Reference](#quick-reference)
- [See Also](#see-also)

## Detection

Before any VCS operation, check for a jj repository:

```bash
if jj root >/dev/null 2>&1; then echo "jj repo detected"; fi
```

If jj is detected:

- Use `jj` for ALL version control operations
- Do NOT use `git commit`, `git checkout`, `git branch`, `git merge`, `git rebase`, or other
  mutating git commands
- `gh` (GitHub CLI) is fine -- it only reads `.git/` metadata
- Read-only git commands (`git log`, `git diff`, `git status`, `git rev-parse`, `git remote -v`) are safe to use

## Agent Environment Rules

Agents run non-interactively. Follow these constraints strictly:

- Run `jj git fetch` at the **start** of any task, not just before push
- Always use `-m` for commit/describe messages -- never open an editor
- Do NOT `jj describe` or rewrite commits that have already been pushed
- When scripting jj operations, always use **change IDs** (not commit hashes) for stability across rewrites
- If you encounter `(divergent)` markers in `jj log`, abandon the local (mutable) copy and rebase remaining work onto main
- Prefer `jj rebase --skip-emptied` over manual `jj abandon` for cleanup -- it's idempotent and handles stacked chains
- **Always `jj commit -m "..."` before `jj new`** -- `jj new` moves `@` to a new change; the old
  change's files leave the working directory. Without a description or bookmark, the old change
  is effectively lost (it still exists in history but is hard to find). Never leave meaningful
  work in an undescribed, unbookmarked change.
- Verify state with `jj st` after any mutation
- Always pass `--config ui.paginate=never` if pager interferes

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
# View commit log (default: mutable revisions with context)
jj log

# View log with all revisions
jj log -r '::'  # all() also works but :: is canonical

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
# Remove a commit (descendants rebased onto its parent; changes are discarded)
jj abandon <rev>

# Undo the last jj operation
jj undo

# Discard all changes in the working copy
jj restore

# Restore a specific file from a revision
jj restore --from <rev> <path>
```

**Note:** `jj split` is interactive and not safe for agents. To split a commit
(extract specific files into a new child):

1. `jj new <commit>` — create a new empty change after the target
2. `jj squash --from <commit> <path1> <path2>` — move only those files from the target into the new change

The target commit retains everything except the moved files.

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

Workspaces provide isolated working copies sharing the same repo storage. When jj
is available, MUST use `jj workspace add` — never `git worktree add`. This applies
to both colocated and pure jj repos.

```bash
# Create a workspace
jj workspace add ../my-workspace --name my-workspace

# List workspaces
jj workspace list

# Forget a workspace (de-register, does NOT delete files — callers must rm -rf the directory after)
jj workspace forget <name>
rm -rf <path>

# Fix a stale workspace after concurrent edits
jj workspace update-stale
```

Key behaviors:

- `jj workspace list` shows all workspaces (format: `<name>: <change-id-prefix> <commit-id-prefix> <description>`,
  e.g. `default: rwoumssn 094ee48c (empty) (no description set)`); there is no
  `(current)` marker — identify the current workspace from the working directory
  path (sibling worktrees use `<repo>_worktrees/<workspace-name>/`)
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

## GitHub Squash-Merge Workflow

GitHub squash-merge creates a **new commit** on `main` with a different hash than your local
commits. jj cannot detect that your work has "landed," causing local commits to appear
alive/divergent after fetch.

### Post Squash-Merge Reconciliation

After a PR is squash-merged on GitHub:

```bash
jj git fetch
jj rebase -o main --skip-emptied
jj bookmark delete <merged-bookmark>
```

`--skip-emptied` is critical -- it automatically abandons commits that become empty after
rebase (their content is already in `main` via the squash merge).

### Stacked PRs

If you had commits A -> B -> C -> D (each a separate PR) and A's PR was just squash-merged:

```bash
jj git fetch
jj rebase -s <change-id-of-B> -o main --skip-emptied
jj bookmark delete <a-bookmark>
```

A becomes empty and is auto-abandoned. B, C, D rebase cleanly onto new `main`.

### Complete PR Lifecycle

```bash
# 1. Start work
jj new main
# ... make changes ...
jj describe -m "feat: my feature"
jj bookmark create my-feature -r @
jj git push

# 2. Address review comments
jj new my-feature   # new child of bookmark tip
# ... make fixes ...
jj squash           # fold fixes into parent
jj git push --bookmark my-feature

# 3. After squash-merge on GitHub
jj git fetch
jj rebase -o main --skip-emptied
jj bookmark delete my-feature

# 4. Start next piece of work
jj new main
```

For detailed workflows and aliases, see `references/workflows-reference.md`.

## Divergent Changes

Divergent changes appear as `(divergent)` in `jj log` when a commit is modified both locally and remotely.

### How Divergence Happens

1. Push a bookmark for PR
2. Locally `jj describe` or `jj squash` to tweak the commit
3. PR gets squash-merged on GitHub (remote bookmark moves)
4. `jj git fetch` -> two commits with the same change ID = divergence

### Prevention Rules

- **Do not modify commits after pushing** -- if the PR is up for review, leave those commits alone
- **Always `jj git fetch` before starting new work**
- **Use change IDs, not commit hashes** -- change IDs survive rewrites

### Resolving Divergence

If divergence occurs, abandon the stale local copy:

```bash
jj abandon <stale-commit-hash>
```

Or use the idempotent approach -- rebase with `--skip-emptied` to clean up automatically.

## Conflict Handling

jj allows committing conflicts -- they are tracked as part of the commit, not blocking.

### Detecting Conflicts

```bash
jj st   # Shows "Conflict" markers if present
jj log  # Conflicted commits show a conflict icon
```

### Resolving Conflicts

1. Open the conflicted file and resolve the conflict markers (jj 0.39 format):
   - `<<<<<<< Conflict N of M` — conflict block start (includes commit references)
   - `+++++++ Contents of side #1` — snapshot of the first side (full content)
   - `%%%%%%% Changes from base to side #2` — diff from base to second side
   - `\\\\\\\` — separator between the diff header and the 'to' snapshot section
   - `>>>>>>> Conflict N of M ends` — conflict block end
2. Edit the file to the desired final content, removing all marker lines
3. Save the file
4. Run `jj st` to verify the conflict is resolved

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
| Rebase onto new parent | `jj rebase -s <src> -o <dest>` |
| Cherry-pick (single rev) | `jj rebase -r <change-id> -o <dest>` |
| Create bookmark | `jj bookmark create <name>` |
| Move bookmark | `jj bookmark set <name> -r <rev>` |
| Push bookmark | `jj git push -b <name>` |
| Fetch remotes | `jj git fetch` |
| List files | `jj file list` |
| Current location | `jj log -r @ --no-graph -T 'change_id.short(8)'` |
| Add workspace | `jj workspace add <path> --name <name>` |
| List workspaces | `jj workspace list` |
| Remove workspace | `jj workspace forget <name>` + `rm -rf <path>` |

## See Also

- `references/jj-reference.md` -- detailed jj command reference, revsets, and advanced operations
- `references/workflows-reference.md` -- end-to-end workflow recipes, aliases, and stacked PR patterns
- `references/jj-git-interop.md` -- colocated repo behavior and git compatibility
- For session-level change management (splitting, describing, inserting changes),
  use `jj commit`, `jj describe`, and `jj new` directly.
