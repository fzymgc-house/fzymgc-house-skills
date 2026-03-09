# VCS Detection Preamble

Standard startup procedure for agents and skills operating in
repositories that may use git or jj (Jujutsu).

## Steps

1. **Detect VCS:** `if test -d .jj; then echo "jj"; elif test -d .git; then echo "git"; else echo "none"; fi`
   - `test -d` already ensures `.jj` is a directory (not a regular file).
   - If the result is "none", STOP and report
     STATUS: FAILED -- "No VCS detected (no .jj/ or .git/ directory)"
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

## Path Rules

- Use ONLY relative paths for all file operations
- Do NOT `cd` outside your working directory
- Do NOT use absolute paths from diffs or PR metadata -- translate them
  to relative paths within your worktree
