---
name: respond-to-pr-comments
description: >-
  Manages GitHub PR review comments. Use when the user asks to "list PR comments",
  "check PR feedback", "respond to PR comments", "address reviewer feedback",
  "fix PR review issues", "work through PR review", or "acknowledge comments".
  Handles both quick lookups and full review-response workflows.
argument-hint: "[pr-number]"
allowed-tools:
  - "Bash(${CLAUDE_PLUGIN_ROOT}/skills/respond-to-pr-comments/scripts/pr_comments *)"
  - "Bash(git *)"
  - "Bash(gh *)"
  - "Bash(task *)"
  - Read
  - Edit
  - Write
  - Grep
  - Glob
metadata:
  author: fzymgc-house
  version: 0.3.0
---

# PR Comment Operations

**Execute** the bundled script using the full absolute path from
your allowed-tools Bash pattern. The script outputs ready-to-run
commands with its own absolute path — copy-paste those directly.

## Commands

```bash
scripts/pr_comments list <pr> [--unacked]       # List comments
scripts/pr_comments get <pr> <id> [--save <p>]  # Get comment
scripts/pr_comments latest <pr>                 # Most recent
scripts/pr_comments ack <pr> <id>               # Acknowledge
scripts/pr_comments comment <pr> --file <path>  # Post comment
scripts/pr_comments comment <pr> "text"         # Post inline
```

Comment IDs: `RC_*` = review comment (inline on code), `R_*` = review (approve/request/comment).

## Quick lookup vs full workflow

**Quick lookup** (e.g., "list PR comments", "check what reviewers said"):
Run the relevant command above and present the output. Done.

**Full workflow** (e.g., "address PR feedback", "fix PR review issues"):
Follow the workflow below.

---

## Full Review-Response Workflow

Copy this checklist and update as you go:

```text
- [ ] Phase 1: Read unacked comments, locate worktree
- [ ] Phase 2: Categorize comments, confirm with user
- [ ] Phase 3: Implement fixes (bug/style) and ask about (feature/design/question)
- [ ] Phase 4: All quality gates pass (test, build, lint)
- [ ] Phase 5: Commit, push, post summary comment
```

### Phase 1: Setup

1. **Identify the PR.** Use `$ARGUMENTS` if provided, otherwise determine
   from context or ask.

2. **Read all unresolved comments:** `list <pr-number> --unacked`.
   If none exist, report and stop.

3. **Locate the worktree.** Run `git worktree list` and check whether one
   exists for the PR's branch. If so, `cd` into it and verify with
   `git branch --show-current`. If not, ask the user whether to create one.
   **MUST** use an existing worktree if one matches.

### Phase 2: Categorize, clarify, and confirm

This phase has three distinct steps. Do NOT combine them.

**Step 2a — Categorize internally.** For each comment, assign a
**category**, **complexity**, and **model**. Do not present to the
user yet.

| Category     | Description                        | Action |
|--------------|------------------------------------|--------|
| **bug**      | Logic error, missing edge case     | Fix    |
| **style**    | Naming, formatting, lint issues    | Fix    |
| **feature**  | New functionality request          | Ask    |
| **design**   | Architecture, pattern, API shape   | Ask    |
| **question** | Clarification, "why did you..."    | Ask    |

| Complexity | Criteria                                    | Model  |
|------------|---------------------------------------------|--------|
| **low**    | Single file, mechanical change, obvious fix  | haiku  |
| **medium** | Few files, some judgment, clear approach     | sonnet |
| **high**   | Cross-cutting, architectural, needs context  | opus   |

**Step 2b — Gather clarifications.** For every comment categorized as
feature, design, or question: present it to the user one at a time
with full context (comment text, file location, surrounding code).
Ask exactly one question per comment. Wait for the user's response
before presenting the next. Record each answer.

**Step 2c — Present plan for approval.** Show the full categorized
list to the user in a single summary:

- Each comment's ID, category, complexity, and recommended model
- For bug/style: the proposed fix approach
- For feature/design/question: the user's answer from Step 2b
  and the planned action

Ask the user to confirm or adjust before proceeding. Do NOT begin
implementation until the user approves.

### Phase 3: Implement

Dispatch each fix/response as a **sub-agent** using the Task tool
with the model from Phase 2. Each sub-agent should receive:

- The comment text and file location
- The category and what to do
- For bug/style: instructions to use TDD
- For feature/design/question: the user's guidance from Step 2b

1. **Bug and style:** launch sub-agent with recommended model.
   - Sub-agent writes a failing test (when testable), implements
     fix, confirms pass.
   - Acknowledge after sub-agent completes: `ack <pr> <comment-id>`
   - Independent fixes MAY run as parallel sub-agents.

2. **Feature, design, question:** launch sub-agent with recommended
   model and the user's guidance from Step 2b.
   - Acknowledge after sub-agent completes: `ack <pr> <comment-id>`

### Phase 4: Verify

Launch a **sonnet sub-agent** to run quality gates and fix any failures:

1. Sub-agent detects project type and runs appropriate quality gates:
   - **Detect:** Check for `Taskfile.yml`, `build.gradle`, `pyproject.toml`, `Cargo.toml`, `package.json`, etc.
   - **Run:** Execute project-specific commands for unit tests, integration tests, build, and lint
   - **Examples:**
     - Taskfile: `task test && task test:integration && task build && task lint`
     - Python: `pytest tests/ && pytest tests/integration/ && python -m build && ruff check`
     - Rust: `cargo test && cargo test --test integration && cargo build && cargo clippy`
     - Gradle: `./gradlew test integrationTest build check`
     - Node: `npm test && npm run test:integration && npm run build && npm run lint`
2. If failures: sub-agent reviews error → fixes → re-runs.
3. **Max 3 attempts.** If gates still fail after 3 rounds, sub-agent reports
   the remaining failures and stops. Present the failures to the user for guidance.
4. Do NOT proceed to Phase 4.5 until all gates pass (unit tests, integration tests, build, lint).

### Phase 4.5: Independent Review (Conditional)

**Trigger when ANY of these conditions apply:**

- 3+ comments addressed (high change volume)
- Any comment categorized as "high" complexity
- Any bug fix (category "bug")
- User explicitly requests review before shipping

Launch an **opus sub-agent** (independent context) to review. Sub-agent outputs
ONLY structured results (no explanations) to minimize token use:

**Sub-agent task:**

1. Read Phase 2 categorization (comment IDs, categories, user guidance)
2. Run `git diff` to see actual changes
3. For EACH comment ID, output one line:

   ```text
   <comment-id>: PASS | FAIL: <reason-if-fail>
   ```

4. After all comments, output decision:

   ```text
   DECISION: SHIP | BLOCK
   BLOCK_REASON: <one-line-summary-if-blocked>
   ```

**Example output:**

```text
RC_123: PASS
RC_456: FAIL: Test added but doesn't cover edge case mentioned in comment
R_789: PASS
DECISION: BLOCK
BLOCK_REASON: RC_456 test incomplete
```

If DECISION is BLOCK, return to Phase 3 to address flagged issues, then re-run Phase 4 gates.
If DECISION is SHIP, proceed to Phase 5.

### Phase 5: Ship

1. **Commit** using the `commit-commands:commit` skill.
2. **Push** to the PR branch.
3. **Post summary comment:** `comment <pr-number> --file /tmp/pr-summary.md`
   - Bulleted list of each comment addressed and what was done.
   - Any comments deferred or requiring further discussion.

## Hard Constraints

| Constraint                   | Reason                    |
|------------------------------|---------------------------|
| **MUST NOT** close epic      | PR merge triggers closure |
| **MUST NOT** close issue     | PR merge triggers closure |
| **MUST NOT** merge the PR    | Reviewer's decision       |
| **MUST** use worktree        | Avoid branch conflicts    |
| **MUST** ask for feat/design | Require human judgment    |
| **MUST** use TDD for fixes   | Ensures correctness       |

## Notes

- `--unacked` filters by +1 reaction from the authenticated user.
- Prefer `--file` for multi-line comments (avoids shell escaping).
- MUST NOT create additional parsing or processing scripts.
- MUST use the comment ID formats provided in output.
