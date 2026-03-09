# jj-git Interop Reference

How jj and git coexist in colocated repositories.

## Colocated Repo Behavior

A colocated repo has both `.jj/` and `.git/` directories. Most `jj` commands automatically sync
state to the underlying git repo. This means git-based tools (GitHub CLI, IDE git integration) see
an up-to-date `.git/` at all times.

## Bookmark-Branch Sync

jj **bookmarks** map directly to git **branches**:

- On most `jj` commands, git branches are auto-imported as jj bookmarks
- On most `jj` commands, jj bookmark changes are auto-exported as git branches
- `jj bookmark list` shows all bookmarks (equivalent to `git branch -a` after import)
- `jj bookmark create <name>` creates a bookmark at the current change (`@`)
- `jj bookmark set <name> -r <rev>` creates or moves a bookmark to the specified revision

## Push and Fetch

```bash
jj git push -b <bookmark>      # Push a specific bookmark to its remote
jj git push --change <rev>     # Auto-create bookmark and push (e.g., push-kxryzmsp)
jj git push --all               # Push all bookmarks
jj git fetch                    # Fetch from all remotes
jj git fetch --remote origin    # Fetch from a specific remote
```

`jj git push --change <rev>` automatically creates a bookmark named `push-<change-id-prefix>` (e.g.,
`push-kxryzmsp`). The exact prefix length may vary by jj version. Use `jj bookmark list` after pushing
to see the auto-created bookmark name.

After fetching, new remote branches appear as `<bookmark>@<remote>` (e.g., `main@origin`).

## Detached HEAD

jj puts git into **detached HEAD** state. This is normal and expected. Do not attempt to "fix" it
by checking out a branch in git. jj manages the git HEAD internally to track the current working
copy commit.

## GitHub CLI Compatibility

`gh` works in colocated repos because it only needs `.git/`:

```bash
gh pr list                      # Works normally
gh pr create --head <bookmark>  # Use the jj bookmark name as the branch
gh pr view 123                  # Works normally
```

Ensure the bookmark is pushed (`jj git push -b <name>`) before creating a PR.

## Workspaces

Workspaces replace git worktrees in the jj workflow. See the [Workspaces section in
SKILL.md](../SKILL.md#workspaces) for full command reference and key behaviors.

## What NOT To Do

**Avoid mutating git commands** in colocated repos:

| Avoid | Use Instead |
|-------|-------------|
| `git commit` | `jj commit` or `jj describe` + `jj new` |
| `git merge` | `jj new branch1 branch2` (creates merge commit) |
| `git rebase` | `jj rebase -s <source> -d <dest>` |
| `git checkout <branch>` | `jj edit <bookmark>` (edit tip) or `jj new <bookmark>` (new child) |
| `git branch -d` | `jj bookmark delete <name>` |

**Read-only git commands are fine**: `git log`, `git diff`, `git status`, `git remote -v`.

If a mutating git command causes sync issues, use `jj undo` to revert to the previous jj state.
