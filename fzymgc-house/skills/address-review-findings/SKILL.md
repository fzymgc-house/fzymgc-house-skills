---
name: address-review-findings
description: >-
  Processes findings from review-pr by working through beads in the review
  epic. Use when the user asks to "address review findings", "fix review
  issues", "work through review beads", or "process review-pr findings".
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
  version: 0.1.0
---

# Address Review Findings

Process findings from a `review-pr` run by working through the beads
in the review epic. Each finding is triaged, fixed by a sub-agent,
batch-reviewed, and closed.

**Read** `references/bd-reference.md` for the full `bd` CLI subset
used by this skill.

## Phase 1: Load

1. **Identify the PR.** Use `$ARGUMENTS` if provided, otherwise ask.
2. **Verify `bd`**: run `bd --version`. If it fails, stop and tell the
   user: "beads CLI (`bd`) is required but not found. Install beads and
   run `bd init` in the target project."
3. **Query the review epic bead:**

   ```bash
   bd list --labels "pr-review,pr:<number>" --status open --json
   ```

   If no review epic exists, stop: "No review findings for PR #N.
   Run `/review-pr <number>` first."

4. **Load all open findings:**

   ```bash
   bd list --parent <review-epic-id> --status open --json
   ```

   If no open findings, report "All findings already addressed" and stop.

5. **Locate worktree.** Run `git worktree list` and check whether one
   exists for the PR's branch. If so, `cd` into it and verify with
   `git branch --show-current`. If not, ask the user whether to create
   one. **MUST** use an existing worktree if one matches.

## Phase 2: Analyze Dependencies

Review all open findings and identify dependency relationships:

**File overlap** — Two findings touching the same file should not be
fixed concurrently. Set a dependency so the higher-priority or
earlier-in-file finding is addressed first.

**Conceptual overlap** — A design finding and a bug finding about the
same component. The design finding should be resolved first (it may
change the fix approach).

**Severity ordering** — Critical findings block lower-severity findings
in the same file or area.

Encode all relationships using `bd dep add`:

```bash
bd dep add <lower-priority-finding> --depends-on <higher-priority-finding>
```

The fix loop's "query ready findings" naturally respects the dependency
graph — a finding cannot be picked up while its dependencies are still
open.

## Phase 3: Triage

For each **open** finding bead, read its description and evaluate three
dimensions to determine handling:

1. **Complexity** — Is the fix straightforward or does it require judgment?
2. **Scope of change** — Mechanical tweak or design/spec/contract shift?
3. **Deviation** — Follows existing patterns or introduces new ones?

**Auto-fixable** (no user input needed):

- Clear bug with an obvious correct fix
- Mechanical changes (formatting, naming, lint)
- Low deviation from existing code and patterns

**Needs human judgment** — present to user via `AskUserQuestion`:

- Fix requires a design or architectural choice
- Fix changes a spec, plan, or public contract
- Multiple valid approaches with meaningful trade-offs
- High deviation from existing patterns

Note: The `aspect` label (which review agent found the issue) does NOT
determine auto-fix vs needs-human. A security finding may be a simple
one-liner; a code quality finding may require an architectural decision.
The `aspect` label is used for model selection, not triage routing.

For each needs-human finding, use `AskUserQuestion` with:

- Concrete fix approach options (when the agent can propose them)
- A recommendation marked "(Recommended)" when there's a clear winner
- A "Defer" option
- `AskUserQuestion` provides "Other" automatically

**Complexity/model assignment:**

| Complexity | Criteria | Model |
|------------|---------------------------------------------|--------|
| low | Single file, mechanical change, obvious fix | haiku |
| medium | Few files, some judgment, clear approach | sonnet |
| high | Cross-cutting, architectural, needs context | opus |

**Deferral handling:**

When the user chooses "Defer":

1. Add `deferred` label to the finding:

   ```bash
   bd update <finding-id> --add-label deferred
   ```

2. Create a deferred work bead in the appropriate project epic (or
   top-level if no clear epic):

   ```bash
   bd create "<description of the work>" \
     --type task \
     --parent <project-epic-id-or-omit> \
     --labels "deferred,aspect:<aspect>,from-pr:<number>" \
     --external-ref "https://github.com/{owner}/{repo}/pull/<number>" \
     --description "<full context, file location, reason for deferral>" \
     --silent
   ```

3. Link back to the finding:

   ```bash
   bd dep add <deferred-work-bead> --depends-on <finding-id> --type discovered-from
   ```

## Phase 4: Fix Loop

Loop while open, non-deferred findings remain:

1. **Query ready findings** (no unresolved deps among open beads):

   ```bash
   bd list --parent <epic-id> --status open --json
   ```

   Filter to findings whose dependencies are all closed.

2. **Pick up to 3** ready findings.

3. **For each non-trivial finding**, create a work bead first:

   ```bash
   bd create "Fix(<finding-id>): <short desc>" \
     --type task \
     --parent <review-epic-id> \
     --description "<work to be done>" \
     --deps "blocks:<finding-id>" \
     --silent
   ```

   The work bead blocks the finding bead — the finding cannot be
   closed until the fix work is complete.

4. **Launch fix sub-agents** (up to 3 concurrent). Each receives:

   - Finding bead ID and description
   - Work bead ID (if created)
   - File location and suggested fix from the finding
   - Model assignment from triage

   Sub-agent implements the fix and reports what it did.
   Sub-agent does **NOT** close or update any beads.

5. **Wait** for all sub-agents in this round to complete.

6. **Launch a review agent** (sonnet) for this round's fixes. Receives:

   - `git diff` of changes made
   - Finding descriptions for each fix
   - What each sub-agent reported

   Returns per-finding: `PASS` | `FAIL: <reason>`

7. **For PASS findings:**

   - Orchestrator closes the work bead (if any):
     `bd update <work-id> --status closed`
   - Orchestrator closes the finding bead:
     `bd update <finding-id> --status closed`

8. **For FAIL findings:**

   - Add comment: `bd comments add <finding-id> "Review failed: <reason>"`
   - Re-queue (stays open, eligible for next round)
   - Max 2 retries per finding. After 2 failures, escalate to user.
