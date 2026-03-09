# VCS Detection Preamble

Standard startup procedure for agents and skills operating in
repositories that may use git or jj (Jujutsu).

## Steps

1. **Detect VCS:**

   ```bash
   if jj root 2>/dev/null >&2; then echo "jj"
   elif git rev-parse --git-dir 2>/dev/null >&2; then echo "git"
   else echo "none"; fi
   ```

   - `jj root` succeeds in any jj workspace (including workspaces where `.jj/` is absent from the working directory).
   - `git rev-parse --git-dir` succeeds in git worktrees where `.git` is a file rather than a directory.
   - If the result is "none", STOP and report
     STATUS: FAILED -- "No VCS detected (not inside a jj or git repository)"
2. **Verify location** *(worktree-isolated agents only — orchestrator
   skills running from the main repo root should skip this step):*
   - jj: Check whether the current directory is under a `_worktrees`
     sibling directory using a path pattern match:

     ```text
     case "$(pwd)" in
       *_worktrees/*) ;; # In a worktree workspace — proceed
       *) STOP and report STATUS: FAILED -- "Operating in default workspace
          (main equivalent). Dispatch to a worktree workspace instead." ;;
     esac
     ```

     Do NOT rely on `jj workspace list` output to identify the current
     workspace; jj 0.39+ does not emit a `(current)` marker.
   - git: Run `pwd` and `git branch --show-current` -- verify you are on
     a `worktree/*` branch, NOT `main`
3. If anything looks wrong, STOP and report STATUS: FAILED

Use the detected VCS for all operations in this session. Consult
`pr-review/references/vcs-equivalence.md` for command equivalents.

## Orchestrator Contract

When a worktree-isolated agent reports `STATUS: FAILED` with a VCS
detection failure message:

1. **Do NOT retry** — VCS detection failure is deterministic. The
   worktree was created without proper VCS initialization.
2. **Log the failure** — include the agent name and worktree path.
3. **Clean up the worktree** — the worktree is unusable without VCS.
4. **Re-queue the finding** — mark FAILED with the VCS error detail.

Orchestrator skills (address-findings, review-pr) should check for
`STATUS: FAILED` in agent responses before attempting to parse VCS-specific
fields (WORKTREE_BRANCH, CHANGE_ID).

## Path Rules

- Use ONLY relative paths for all file operations
- Do NOT `cd` outside your working directory
- Do NOT use absolute paths from diffs or PR metadata -- translate them
  to relative paths within your worktree
