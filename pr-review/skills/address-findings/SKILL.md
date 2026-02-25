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

Process findings from a `review-pr` run by working through beads in the
review epic. Findings are triaged, fixed by isolated agents in worktrees,
batch-reviewed, and closed.

**Read** `references/bd-reference.md` for the full `bd` CLI reference.

## Phase 1: Load

1. **Identify the PR.** Use `$ARGUMENTS` if provided, otherwise ask.
2. **Verify `bd`**: run `bd --version`. If it fails, stop and tell the
   user: "beads CLI (`bd`) is required but not found."
3. **Query the review epic:**

   ```bash
   bd list --label "pr-review,pr:<number>" --status open --json
   ```

   If no epic exists, stop: "No review findings for PR #N. Run
   `/review-pr <number>` first."

4. **Load all open findings:**

   ```bash
   bd list --parent <epic-id> --status open --json
   ```

   If none, report "All findings already addressed" and stop.

5. No manual worktree discovery needed -- fix-worker agents create
   their own worktrees via `isolation: worktree`.

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
     FILE_LOCATION: <path:line>
     SUGGESTED_FIX: <from finding description>
     Implement the fix. Report STATUS, FILES_CHANGED, WORKTREE_BRANCH.
     Do NOT close or update any beads.
   ```

5. **Collect results** from each agent: STATUS, FILES_CHANGED,
   WORKTREE_BRANCH.

### Phase 4b: Merge Fix Branches

For each FIXED result, in dependency order:

1. Merge into the PR branch:

   ```bash
   git merge --no-ff <worktree-branch> -m "fix(<finding-id>): <description>"
   ```

2. If merge conflict: mark FAILED, add bead comment, re-queue for
   next round.
3. Clean up: `git worktree remove <worktree-path>`

Same-file findings serialized in Phase 2 prevent most conflicts.

### Phase 4c: Review Gate

Dispatch a review-gate agent to validate fixes:

```text
subagent_type: "review-gate"
model: sonnet
prompt: |
  FINDING_IDS: <comma-separated>
  Review the following changes against the original findings.
  <git diff of merged changes>
  Return per-finding: PASS | FAIL: <reason>
```

- **PASS**: close work bead (`bd update <work-id> --status closed`)
  then close finding (`bd update <finding-id> --status closed`)
- **FAIL**: add comment (`bd comments add <finding-id> "Review failed: <reason>"`),
  re-queue for next round

Max 2 retries per finding. After 2 failures, escalate to user.

## Phase 5: Verify

Dispatch a verification-runner agent:

```text
subagent_type: "verification-runner"
isolation: worktree
model: sonnet
prompt: |
  Run all quality gates for this project:
  1. Detect project type (Taskfile.yml, pyproject.toml, package.json, etc.)
  2. Run unit tests, integration tests, build, lint
  3. If failures: review error, fix, re-run (max 3 attempts)
  4. Report PASS or FAIL with details
```

- **FAIL**: report failure details to user. Do NOT proceed to Phase 6.
- **PASS**: proceed.

## Phase 6: Ship

1. **Commit** using the `commit-commands:commit` skill.
2. **Push** to the PR branch: `git push`
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
