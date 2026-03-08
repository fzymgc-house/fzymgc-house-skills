# VCS Detection Preamble

Standard startup procedure for agents and skills operating in
repositories that may use git or jj (Jujutsu).

## Steps

1. **Detect VCS:** `if test -d .jj && [ ! -f .jj ]; then echo "jj"; elif test -d .git; then echo "git"; else echo "none"; fi`
   - The `[ ! -f .jj ]` guard prevents a regular file named `.jj`
     from being mistaken for a jj repository directory.
   - If the result is "none", STOP and report
     STATUS: FAILED -- "No VCS detected (no .jj/ or .git/ directory)"
2. **Verify location:**
   - jj: Run `jj workspace list`. Output shows one workspace per line:
     `<name>: <commit summary>` with `(current)` appended to the
     active workspace's line. Parse the current workspace name by
     finding the line ending with `(current)` and extracting the name
     before the first `:` delimiter. Verify the extracted name starts
     with `worktree-`. If you are in the `default` workspace, STOP
     and report STATUS: FAILED -- "Operating in default workspace
     (main equivalent). Dispatch to a worktree workspace instead."
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
