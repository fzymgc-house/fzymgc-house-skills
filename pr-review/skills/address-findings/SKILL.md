---
name: address-findings
description: >-
  Processes findings from review-pr by working through beads in the review
  epic. Use when the user asks to "address review findings", "fix review
  issues", "work through review beads", or "process review findings".
argument-hint: "[pr-number]"
allowed-tools:
  - Task
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - "Bash(git *)"
  - "Bash(jj *)"
  - "Bash(gh *)"
  - "Bash(bd --version)"
  - "Bash(bd create *)"
  - "Bash(bd list *)"
  - "Bash(bd update *)"
  - "Bash(bd show *)"
  - "Bash(bd dep *)"
  - "Bash(bd query *)"
  - "Bash(bd comments *)"
  - "Bash(bd search *)"
metadata:
  author: fzymgc-house
  version: 1.0.0 # x-release-please-version
---

# Address Findings

## Contents

- [VCS Detection](#vcs-detection)
- [Phase 1: Load](#phase-1-load)
- [Phase 2: Analyze Dependencies](#phase-2-analyze-dependencies)
- [Phase 3: Triage](#phase-3-triage)
- [Phase 4: Fix Loop](#phase-4-fix-loop)
- [Phase 5: Verify](#phase-5-verify)
- [Phase 6: Ship](#phase-6-ship)
- [Hard Constraints](#hard-constraints)

## VCS Detection

Follow the procedure in `pr-review/references/vcs-detection-preamble.md` to
detect git vs jj and verify your location. Use `gh` CLI for GitHub
operations regardless of VCS.

Process findings from a `review-pr` run by working through beads in the
review epic. Findings are triaged, fixed by isolated agents in worktrees,
batch-reviewed, and closed.

**Read** `references/bd-reference.md` for the full `bd` CLI reference.

## Phase 1: Load

1. **Identify the PR.** Use `$ARGUMENTS` if provided, otherwise ask.

2. **Verify `bd`**: run `bd --version`. If it fails, stop and tell the
   user: "beads CLI (`bd`) is required but not found."

3. **Check out the PR branch.** Worktree-isolated agents inherit
   their base from the orchestrator's current HEAD. If you are on
   `main`, every worktree will be based on `main` and agents will
   not see PR-specific code.

   ```bash
   gh pr checkout <number>
   ```

   **Verify checkout (VCS-dependent):**
   - git: `git branch --show-current` — confirm you are on the PR branch
   - jj: After checkout, verify the PR bookmark exists:
     `jj bookmark list | grep <pr-branch-name>`. If not found, run
     `jj git fetch` to import git branches as bookmarks, then check
     again. Once confirmed, run `jj new <pr-bookmark>` to create a
     working-copy change. Verify with `jj log -r @- --no-graph -n 1`
     (parent should be the PR bookmark tip).

   If checkout fails, check the error:
   - **PR not found** (GraphQL/404 error): stop and tell the user
     "PR #N not found. Verify the number and try again."
   - **Dirty working tree**: commit or stash, then retry.
   - **Other error**: report the error and stop.

   **Do NOT proceed on `main`.**

4. **Query the review epic:**

   ```bash
   bd list --label "pr-review,pr:<number>" --status open --json
   ```

   If no epic exists, stop: "No review findings for PR #N. Run
   `/review-pr <number>` first."

5. **Load all open findings:**

   ```bash
   bd list --parent <epic-id> --status open --json
   ```

   If none, report "All findings already addressed" and stop.

6. No manual worktree discovery needed -- fix-worker agents create
   their own worktrees via `isolation: worktree`.

7. **Validate findings against PR branch HEAD.** For each finding, verify the
   referenced file and line range still exist and the code matches
   the review snapshot. Discard stale findings:

   ```bash
   # Check file exists and content matches the finding's context
   # git repos:
   git log --oneline -1  # note current HEAD
   # jj repos:
   jj log -r @- --no-graph -n 1  # note current HEAD (parent of working copy)
   ```

   For each finding, read the referenced file location. If the code
   has changed since the review (e.g., the finding references code
   that no longer exists or has been refactored), close it as stale:

   ```bash
   bd update <finding-id> --status closed
   bd comments add <finding-id> "Closed: finding is stale — code at \
     <path>:<line> has changed since review. Re-run /review-pr if needed."
   ```

   Report discarded findings to the user before continuing.

## Phase 2: Analyze Dependencies

Review all open findings and identify dependency relationships:

**File overlap** -- Two findings touching the same file MUST be
serialized. Set a dependency so the higher-priority finding is
addressed first. This is critical for merge safety.

**Conceptual overlap** -- A design finding and a bug finding about the
same component. Resolve the design finding first (it may change the fix
approach).

**Severity ordering** -- Critical findings block lower-severity findings
in the same file or area.

Encode relationships:

```bash
bd dep add <lower-priority> --depends-on <higher-priority>
```

The fix loop's "query ready findings" naturally respects the dependency
graph -- a finding cannot be picked up while its dependencies are open.

## Phase 3: Triage

For each open finding, evaluate:

1. **Complexity** -- Straightforward fix or requires judgment?
2. **Scope** -- Mechanical tweak or design/contract shift?
3. **Deviation** -- Follows existing patterns or introduces new ones?

**Auto-fixable** (no user input needed):

- Clear bug with an obvious correct fix
- Mechanical changes (formatting, naming, lint)
- Low deviation from existing code and patterns

**Needs human judgment** -- present via `AskUserQuestion`:

- Fix requires a design or architectural choice
- Fix changes a spec, plan, or public contract
- Multiple valid approaches with meaningful trade-offs

For needs-human findings, use `AskUserQuestion` with:

- Concrete fix approach options
- A recommendation marked "(Recommended)" when clear
- A "Defer" option
- `AskUserQuestion` provides "Other" automatically

**Model assignment:**

| Criteria | Model |
|---------------------------------------------------|--------|
| Single file, mechanical, obvious fix | sonnet |
| Few files, some judgment, clear approach | sonnet |
| Cross-cutting, architectural, needs context | sonnet |
| Vague, under-specified, no clear precedent | opus |
| Design changes requiring architectural judgment | opus |

**Deferral handling:** When the user chooses "Defer":

1. Add label: `bd update <finding-id> --add-label deferred`
2. Create deferred work bead with full context:

   ```bash
   bd create "<description>" --type task \
     --labels "deferred,aspect:<aspect>,from-pr:<number>" \
     --external-ref "https://github.com/{owner}/{repo}/pull/<number>" \
     --description "<context, file location, reason>" --silent
   ```

3. Link: `bd dep add <deferred-bead> --depends-on <finding-id> --type discovered-from`

## Phase 4: Fix Loop

**Before entering the loop**, verify branch and working tree state:

```bash
# git repos:
git branch --show-current   # MUST be the PR branch, NOT main
git status --porcelain      # MUST be clean

# jj repos:
jj log -r @- --no-graph -n 1   # MUST show PR bookmark (parent of working copy)
jj st                          # MUST be clean
```

If on `main`, stop — you skipped step 3. If there are uncommitted
changes, commit them first. A clean working tree on the correct PR
branch is required before dispatching worktree-isolated agents.

Loop while open, non-deferred findings remain:

1. **Query ready findings** (deps all closed):

   ```bash
   bd list --parent <epic-id> --status open --json
   ```

   Filter to findings whose dependencies are all closed.

2. **Pick up to 3** ready findings. No same-file overlap in a batch.

3. **Create work bead** per finding:

   ```bash
   bd create "Fix(<finding-id>): <short desc>" \
     --type task --parent <epic-id> \
     --description "<work to be done>" \
     --deps "blocks:<finding-id>" --silent
   ```

4. **Launch fix-worker agents** via Task (up to 3 concurrent):

   ```text
   subagent_type: "fix-worker"
   isolation: worktree
   model: sonnet  (or opus for complex/vague findings)
   prompt: |
     FINDING_BEAD_ID: <finding-id>
     WORK_BEAD_ID: <work-bead-id>
     FILE_LOCATION: <relative-path:line>
     SUGGESTED_FIX: <from finding description>
     Implement the fix. Commit with message:
       fix(<finding-id>): <one-line description>
     Report STATUS, VCS, FILES_CHANGED, DESCRIPTION, WORKTREE_BRANCH (git) or CHANGE_ID (jj).
    VCS must be "git" or "jj" to indicate which integration method to use.
     Do NOT close or update any beads.
   ```

   Note: FILE_LOCATION **must** use a relative path. Strip any absolute
   prefix before dispatching.

5. **Collect results** from each agent: STATUS, VCS, FILES_CHANGED,
   DESCRIPTION, WORKTREE_BRANCH (git) or CHANGE_ID (jj).

### Phase 4b: Integrate Fix Commits

Integration method depends on VCS:

| VCS | Integration | Identifier | Cleanup |
|-----|-------------|------------|---------|
| git | `git cherry-pick` | WORKTREE_BRANCH | `git worktree remove` |
| jj | `jj rebase` + `jj bookmark set` | CHANGE_ID | `jj workspace forget` + `rm -rf` |

#### Git repos

For each FIXED result, in dependency order:

1. Identify the fix commit on the worktree branch:

   ```bash
   git log --oneline <worktree-branch> -1
   ```

2. Cherry-pick onto the PR branch:

   ```bash
   git cherry-pick <commit-sha>
   ```

3. If cherry-pick conflict: abort (`git cherry-pick --abort`), mark
   FAILED, add bead comment, re-queue for next round.
4. Clean up worktree (sibling directory):

   ```bash
   git worktree remove ../<repo>_worktrees/<worktree-name>
   ```

Same-file findings serialized in Phase 2 prevent most conflicts.

#### Jj repos

For each FIXED result (fix worker reports CHANGE_ID instead of
WORKTREE_BRANCH):

1. Rebase the fix onto the PR bookmark:

   ```bash
   jj rebase -r <change-id> -d <pr-bookmark>
   ```

   If rebase fails (conflict):

   1. Run `jj undo`
   2. Verify undo succeeded: `jj log -r @ --no-graph -n 1` — confirm the
      working copy parent matches the pre-rebase state. If not, STOP and
      report STATUS: FAILED with "jj undo did not restore expected state".
   3. Mark FAILED, add bead comment, re-queue for next round.

2. Update the bookmark:

   ```bash
   jj bookmark set <pr-bookmark> -r <change-id>
   ```

   If bookmark set fails:

   1. Run `jj undo` once to revert the rebase (the failed bookmark set
      did not create a successful operation to undo).
   2. Verify: `jj log -r @ --no-graph -n 1` — confirm pre-rebase state.
   3. Mark FAILED, add bead comment, re-queue for next round.

3. Forget the workspace and remove the directory:

   ```bash
   jj workspace forget worktree-<name>
   rm -rf ../<repo>_worktrees/<worktree-name>
   ```

   If `jj workspace forget` fails (e.g., workspace already forgotten
   or jj not installed), log a warning but proceed with directory
   cleanup. The directory removal is the critical step.

   Note: the `WorktreeRemove` hook (`.claude/hooks/worktree-remove.sh`)
   performs the same `jj workspace forget` + `rm -rf` sequence. The
   explicit instructions here are for orchestrators running outside
   the hook system (e.g., direct Task dispatch without worktree hooks).

#### Post-batch verification

**Post-batch: Verify clean state.** After all commits in a
   batch are integrated, verify the working tree is clean before
   the next loop iteration:

   ```bash
   git status --porcelain   # git repos
   jj st                    # jj repos
   ```

   This prevents worktree-isolated agents in the next round from
   corrupting the working tree via stale branch references. Never
   dispatch new fix-worker agents with uncommitted changes in the
   main working tree.

### Phase 4c: Review Gate

Dispatch a review-gate agent to validate fixes:

```text
subagent_type: "review-gate"
model: sonnet
prompt: |
  FINDING_IDS: <comma-separated>
  Review the following changes against the original findings.
  <VCS diff of integrated changes>
  Generate the diff:
  - git: git diff <before-sha>..HEAD
  - jj: jj diff --from <pre-rebase-change-id> --to <pr-bookmark>
  Return per-finding: PASS | FAIL: <reason>
```

- **PASS**: close work bead (`bd update <work-id> --status closed`)
  then close finding (`bd update <finding-id> --status closed`)
- **FAIL**: add comment (`bd comments add <finding-id> "Review failed: <reason>"`),
  re-queue for next round

Max 2 retries per finding. After 2 failures, escalate to user.

## Phase 5: Verify

Build a **fix manifest** from the collected fix-worker results:

| Finding | Problem | Proposed Fix | Actual Changes |
|---------|---------|--------------|----------------|
| bead-id | from finding description | suggested fix | files + description from fix-worker |

Select the verification model based on batch complexity:

| Batch composition | Model |
|---|---|
| All mechanical / single-file fixes | sonnet |
| Any cross-cutting / architectural / vague fix in batch | opus |

Dispatch a verification-runner agent:

```text
subagent_type: "verification-runner"
isolation: worktree
model: <sonnet or opus per table above>
prompt: |
  ## Fix Manifest

  <fix manifest table from above>

  Validate fix alignment and run quality gates.
  Report per-finding alignment AND gate status.
```

- **Any MISALIGNED finding**: treat as review-gate FAIL, re-queue
- **Gate FAIL**: report failure details to user. Do NOT proceed to Phase 6.
- **All ALIGNED + gates PASS**: proceed.

## Phase 6: Ship

1. **Commit** changes:
   - git repos: Use the `commit-commands:commit` skill.
   - jj repos: All fixes are already committed (fix-workers commit individually,
     orchestrator integrates via `jj rebase`). Skip unless the working copy has
     uncommitted manual edits, in which case run
     `jj commit -m "fix: address review findings for PR #<number>"`.
2. **Push** to the PR branch: `git push` (or `jj git push -b <pr-bookmark>` in jj repos)
3. **Post summary comment** on the PR:

   ```bash
   gh pr comment <number> --body-file /tmp/review-response.md
   ```

   Template:

   ```markdown
   <!-- address-findings:<epic-id>:response -->
   ## Review Response

   Fixed N | Deferred N | Failed N

   | Finding | Status | Work |
   |---------|--------|------|
   | <finding-id> | Fixed | <work-bead-id> |
   | <finding-id> | Deferred | <deferred-bead-id> |
   | <finding-id> | Failed (escalated) | -- |
   ```

## Hard Constraints

| Constraint | Reason |
|--------------------------------------|---------------------------|
| **MUST NOT** close the review epic | PR merge triggers closure |
| **MUST NOT** merge the PR | Reviewer's decision |
| **MUST** use `AskUserQuestion` for human judgment | Structured input |
| **MUST** filter `--status open` in all bead queries | Skip handled findings |
| **MUST NOT** let sub-agents close beads | Orchestrator owns lifecycle |
| **MUST** use long flags for all `bd` commands | Clarity for agents |
| **MUST** validate findings against HEAD before fixing | Prevent stale false positives |
| **MUST** commit between fix-worker rounds | Prevent worktree branch corruption |
| **MUST** verify clean working tree before dispatching agents | Prevent data loss |
| **MUST** be on the PR branch before dispatching agents | Worktrees inherit base from HEAD |
| **MUST NOT** proceed with fixes while on `main` | Agents would work against wrong code |
