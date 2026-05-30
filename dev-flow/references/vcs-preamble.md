# VCS Preamble

Detect the active VCS and use the appropriate commands throughout the skill or
agent. The **core sections** (Detection through Note on jj Rebase Flag) apply to
all consumers. The **Worktree-Isolated Agent Startup** and **Orchestrator
Contract** sections at the end apply only to worktree-isolated review agents and
the orchestrator skills that dispatch them.

## Detection

```bash
VCS=$( \
  if jj root >/dev/null 2>&1; then echo "jj"; \
  elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; \
  else echo "none"; fi \
)
if [[ "$VCS" == "none" ]]; then
  echo "STATUS: FAILED -- No VCS detected (not inside a jj or git repository)"
  exit 1
fi
```

- `jj root` succeeds in any jj workspace (including workspaces where `.jj/` is
  absent from the working directory).
- `git rev-parse --git-dir` succeeds in git worktrees where `.git` is a file
  rather than a directory.
- If the result is "none", the block above exits. Backup prose instruction:
  STOP and report `STATUS: FAILED -- No VCS detected`.

## Command Mapping

| Operation | git | jj |
|-----------|-----|-----|
| Create workspace | `git worktree add ../<repo>_worktrees/<name> -b <branch>` | `jj workspace add ../<repo>_worktrees/<name> --name <name>` |
| List workspaces | `git worktree list` | `jj workspace list` |
| Remove workspace | `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` |
| Commit | `git add <files> && git commit -m "msg"` | `jj commit -m "msg"` |
| Describe/amend | `git commit --amend -m "msg"` | `jj describe -m "msg"` |
| New change | N/A (implicit with commit) | `jj new` |
| Create branch/bookmark | `git checkout -b <name>` | `jj bookmark create <name> -r @` |
| Push | `git push -u origin <branch>` | `jj bookmark set <name> -r @ && jj git push -b <name>` |
| Fetch | `git fetch` / `git pull` | `jj git fetch` |
| Diff range (review) | `git diff <base_sha>..<head_sha>` | `jj diff --from <rev1> --to <rev2>` |
| Integrate fix | `git cherry-pick <sha>` | `jj rebase -r <change-id> -o <target>` |
| Merge to main | `git checkout main && git merge <branch>` | `jj rebase -s <rev> -o main --skip-emptied` |
| Delete branch/bookmark | `git branch -d <name>` | `jj bookmark delete <name>` |
| Force delete | `git branch -D <name>` | `jj abandon <rev>` + `jj bookmark delete <name>` |
| Current location | `git branch --show-current` | `jj log -r @ --no-graph -T 'change_id.short(8)'` |
| Status | `git status` | `jj st` |

## Ensure Current Before You Work

Stale state is a silent failure: triaging a bug, brainstorming, or basing a
worktree on an out-of-date checkout produces confident conclusions about code
that no longer exists. Before you analyze code or create a workspace, make your
base current against the right target.

**Pick the currency target from context** — do not assume `main`:

- New work (a fresh bead / feature) → origin's default branch (`origin/main` / `main@origin`).
- Continuing an existing branch → that branch's upstream (`origin/<branch>` / `<branch>@origin`).
- Reviewing a PR → the PR branch's tip.

**Fetch, then base/verify against that target:**

| | git | jj |
|---|---|---|
| Refresh | `git fetch origin` | `jj git fetch` |
| Current target rev | `origin/main` (post-fetch) | `trunk()` (post-fetch; resolves to the remote trunk) |
| Worktree off it | `git worktree add <path> -b <name> origin/main` | `jj workspace add <path> --name <name> -r 'trunk()'` |

**The jj trap (the most common cause of stale work):** `jj git fetch` advances
`main@origin` but **not** the local `main` bookmark. So `jj new main` or
`jj workspace add` with no `-r` silently bases off the *stale* local `main`.
Base off `trunk()` (or `main@origin`), never bare `main` — `jj new 'trunk()'`,
`jj workspace add … -r 'trunk()'`. The native worktree tool (`EnterWorktree`) and
`dev-flow:using-worktrees` now do this for you; when you create a workspace or
move `@` by hand, do it explicitly.

## Workspace Path Convention

All workspaces use the **sibling directory** pattern to avoid confusing LSP servers:

```text
<repo>/                    # main repo
<repo>_worktrees/          # workspace parent (sibling)
  feature-auth/            # one workspace per task
  fix-bug-123/
```

## jj-Specific Rules

When VCS is jj, follow these additional rules:

- Always `jj git fetch` at the start of any task
- Always `jj commit -m "..."` before `jj new` — `jj new` moves `@` and files
  in the old change leave the working directory (lost-work footgun)
- Use **change IDs** (not commit hashes) — they survive rewrites
- Do NOT `jj describe` or rewrite commits that have been pushed
- Use `--skip-emptied` for cleanup rebases (auto-abandons empty commits)
- Prefer `jj rebase --skip-emptied` over manual `jj abandon`
- `@` is the empty working-copy commit; use `@-` for the meaningful committed
  state when verifying or reviewing

## Note on jj Rebase Flag

The destination flag for `jj rebase` is `-o` / `--onto` (not `-d` /
`--destination`, which is deprecated). All examples in this file use `-o`.

---

## Worktree-Isolated Agent Startup

> Worktree-isolated review agents MUST follow this section after Detection.
> General workflow skills, and orchestrator skills running from the main repo
> root, skip everything below this line.

### Verify location

Confirm the agent is operating inside a worktree workspace (sibling
`_worktrees/` directory), not the default workspace:

- **jj:**

  ```bash
  _cwd=$(pwd -P 2>/dev/null) || _cwd=$(pwd)
  _parent_dir=$(basename "$(dirname "$_cwd")")
  case "$_parent_dir" in
    *_worktrees) ;;  # good
    *)
      echo "STATUS: FAILED -- Operating in default workspace (direct parent '$_parent_dir' does not end in _worktrees). Dispatch to a worktree workspace instead."
      exit 1
      ;;
  esac
  ```

  The check verifies the **direct parent directory** ends with `_worktrees`, so
  a repo at `/home/user/code_worktrees/myrepo` (parent: `myrepo`) does not
  trigger a false positive.

  > **Known limitation:** The `*_worktrees` parent-directory check relies on the
  > naming convention established by the WorktreeCreate hook. A **false-positive**
  > (agent incorrectly thinks it's in a worktree) occurs only if the direct
  > parent directory happens to end with `_worktrees` for unrelated reasons —
  > uncommon. A **false-negative** (agent thinks it's in the default workspace
  > when actually in a worktree) occurs if the hook naming convention changes —
  > more dangerous, since the worktree check is skipped. This is an accepted
  > trade-off since `jj workspace list` does not mark the current workspace
  > (jj 0.39+). A false-negative causes an unnecessary `STATUS: FAILED` — the
  > agent refuses to proceed. This is a **safe failure mode**: no data
  > corruption, and the operator can retry after correcting the naming. Note the
  > asymmetry: this jj check is **heuristic** (directory naming), while the git
  > check below is **authoritative** (branch name matching `worktree/*`).

  Do NOT rely on `jj workspace list` output to identify the current workspace;
  jj 0.39+ emits no `(current)` marker.

- **git:**

  ```bash
  _branch=$(git branch --show-current 2>/dev/null) || {
    echo "STATUS: FAILED -- git branch check failed"; exit 1
  }
  [[ -z "$_branch" ]] && {
    echo "STATUS: FAILED -- detached HEAD in git worktree — expected branch worktree/*"; exit 1
  }
  case "$_branch" in
    worktree/*) ;;  # good — operating on a worktree branch
    *)
      echo "STATUS: FAILED -- On branch '$_branch', expected worktree/*"
      exit 1
      ;;
  esac
  ```

If anything looks wrong, STOP and report `STATUS: FAILED`.

### CRITICAL — Path Rules (worktree agents)

- Use ONLY relative paths for all file operations.
- Do NOT `cd` outside your working directory.
- Do NOT use absolute paths from diffs or PR metadata — translate them to
  relative paths within your worktree.

Use the detected VCS for all operations. When jj is detected, you MUST use jj
for ALL mutating VCS operations (commits, workspaces, rebases, status). Never
use mutating git commands in jj repos. Read-only git and `gh` CLI are safe. See
`dev-flow/references/vcs-equivalence.md` for command equivalents.

## Orchestrator Contract

When a worktree-isolated agent reports `STATUS: FAILED` with a VCS detection
failure message:

1. **Do NOT retry** — VCS detection failure is deterministic; the worktree was
   created without proper VCS initialization.
2. **Log the failure** — include the agent name and worktree path.
3. **Clean up the worktree** — it is unusable without VCS.
4. **Re-queue the finding** — mark FAILED with the VCS error detail.

Orchestrator skills (`address-findings`, `review-pr`) should check for
`STATUS: FAILED` in agent responses before parsing VCS-specific fields
(`WORKTREE_BRANCH`, `CHANGE_ID`).
