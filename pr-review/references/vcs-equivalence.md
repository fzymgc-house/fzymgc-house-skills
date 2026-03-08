# VCS Command Equivalence: git and jj

Use this reference when the repo has `.jj/` (colocated jj repo).
In jj repos, use jj for ALL VCS operations.
Only `gh` CLI remains for GitHub API calls.

**Note:** The detection pattern (see `vcs-detection-preamble.md`) checks for `.jj/`
first, then `.git/`, and reports "none" if neither exists. Agents verify VCS
availability in their Environment startup check (step 2) — if verification fails,
they STOP and report STATUS: FAILED.

## Command Mapping

| Operation | git | jj |
|---|---|---|
| Status | `git status --porcelain` | `jj st` |
| Diff (working copy) | `git diff` | `jj diff` |
| Diff (specific rev) | `git diff <ref>` | `jj diff -r <ref>` |
| Diff (range) | `git diff A..B` | `jj diff --from A --to B` |
| Log | `git log --oneline` | `jj log --no-graph` |
| Log (with patch) | `git log -p` | `jj log -p` |
| Show commit | `git show <ref>` | `jj show <ref>` |
| Current location | `git branch --show-current` | `jj log -r @ --no-graph -T change_id` |
| File list | `git ls-files` | `jj file list` |
| Stage + commit | `git add <files> && git commit -m "..."` | `jj commit -m "..."` |
| Push | `git push` | `jj git push -b <name>` |
| Push (auto-bookmark) | *(no equivalent)* | `jj git push --change <id>` |
| Fetch | `git fetch` | `jj git fetch` |
| Cherry-pick | `git cherry-pick <sha>` | `jj rebase -r <change-id> -d <target>` |
| Undo | `git reset` / `git revert` | `jj undo` |
| Create workspace | `git worktree add <path> -b <branch> HEAD` | `jj workspace add <path> --name <name>` |
| Remove workspace | `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` |
| List workspaces | `git worktree list` | `jj workspace list` |
| Workspace identity | `git branch --show-current` | `jj log -r @ --no-graph -T 'change_id ++ " " ++ description.first_line()'` |

## Key Differences

- **No staging area:** jj tracks all file changes automatically. No `git add`.
- **Change IDs:** Use change IDs (stable across rebases) instead of commit SHAs.
- **Mutable commits:** All commits can be freely modified, split, squashed.
- **Working copy = commit:** The working directory is always a commit (`@`).
- **Bookmarks don't auto-advance:** Must `jj bookmark set` before pushing.

## Agent Output Format

In jj repos, agents report `CHANGE_ID` instead of `WORKTREE_BRANCH`:

```text
git repos: WORKTREE_BRANCH: worktree/fix-abc
jj repos: CHANGE_ID: kkmpptxz
```

Report whichever matches the repo's VCS.

## Operations That Stay git/gh

- `gh pr create/view/diff/checkout` -- GitHub CLI (VCS-independent)
- `gh api` -- GitHub API calls
- `gh pr comment` -- PR comments
