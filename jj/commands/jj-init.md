---
name: jj-init
description: >-
  Initialize a colocated jj repo in an existing git repository.
  Use when the user asks to "set up jj", "init jj", or "colocate jj".
user_invocable: true
allowed-tools:
  - "Bash(jj *)"
  - "Bash(git *)"
  - Read
  - Edit
  - Write
---

# Initialize Colocated jj Repo

## Steps

1. **Check prerequisites** — Run `git rev-parse --show-toplevel` to confirm this is a git
   repository. If not, tell the user to run `git init` first or use `jj init` for a standalone
   (non-colocated) repo.

2. **Check if already initialized** — Run `test -d .jj`. If the directory exists, tell the user
   "This repo already has jj initialized." and stop.

3. **Initialize colocated repo** — Run:

   ```bash
   jj git init
   ```

   Colocation is the default behavior; no extra flags are needed.

4. **Add .jj/ to .gitignore** — Check whether `.gitignore` exists and already contains `.jj/`.
   If not present, append `.jj/` to `.gitignore`:

   ```bash
   grep -qxF '.jj/' .gitignore 2>/dev/null || echo '.jj/' >> .gitignore
   ```

5. **Verify** — Run `jj st` and `jj log --no-graph -n 3` to confirm the repo is working.
   Report success: "Colocated jj repo initialized. Both `jj` and `git` commands work in this
   directory."
