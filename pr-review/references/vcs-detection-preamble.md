# VCS Detection Preamble

Standard startup procedure for agents and skills operating in
repositories that may use git or jj (Jujutsu).

## Steps

1. **Detect VCS:** `if test -d .jj; then echo "jj"; elif test -d .git; then echo "git"; else echo "none"; fi`
   - If the result is "none", STOP and report
     STATUS: FAILED -- "No VCS detected (no .jj/ or .git/ directory)"
2. **Verify location:**
   - jj: Run `jj workspace list` and `jj log -r @ --no-graph -T 'change_id.short(8)'`.
     The workspace list shows `<name>: <short-change-id> <commit-id> <description>`
     per line. Match the short change-id from `jj log -r @` to identify which
     workspace you are in. Verify the matched workspace name starts with
     `worktree-`. If you are in the `default` workspace, STOP and report
     STATUS: FAILED -- "Operating in default workspace (main
     equivalent). Dispatch to a worktree workspace instead."
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
