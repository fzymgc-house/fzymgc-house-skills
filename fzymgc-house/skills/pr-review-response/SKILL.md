---
name: pr-review-response
description: >-
  This skill should be used when the user asks to "address PR review comments",
  "respond to PR feedback", "fix PR review issues", "handle PR comments",
  "work through PR review", "update PR after review", "address reviewer feedback",
  or wants to systematically process and resolve all feedback on a pull request.
  Orchestrates the full workflow from reading comments through implementation,
  verification, and summary.
disable-model-invocation: true
argument-hint: "[pr-number]"
allowed-tools:
  - "Bash(${CLAUDE_PLUGIN_ROOT}/skills/respond-to-pr-comments/scripts/pr_comments.py *)"
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
  version: 0.1.0
---

# PR Review Response

Orchestrate a complete response to PR review feedback: read comments, categorize,
implement fixes or ask for guidance, verify, commit, push, and summarize.

## Prerequisites

This skill depends on the `respond-to-pr-comments` skill's `pr_comments.py` script
for all PR comment operations (list, get, ack, comment). That skill MUST be available.

## Workflow

### Phase 1: Setup

1. **Identify the PR.** Use `$ARGUMENTS` if provided
   (e.g., `/pr-review-response 87`), otherwise determine
   the PR number from context or ask the user.

2. **Read all unresolved comments.**

   ```bash
   pr_comments.py list <pr-number> --unacked
   ```

   If no unresolved comments exist, report this and stop.

3. **Locate the worktree.** Run `git worktree list` and check whether a worktree
   already exists for the PR's branch. If one exists, `cd` into it and verify
   with `git branch --show-current`. If none exists, ask the user whether to
   create one or work in the current checkout.

   > **MUST** use an existing worktree if one matches the PR branch.

### Phase 2: Categorize

1. **Categorize each comment** into exactly one of:

   | Category     | Description                        | Action |
   |--------------|------------------------------------|--------|
   | **bug**      | Logic error, missing edge case     | Fix    |
   | **style**    | Naming, formatting, lint issues    | Fix    |
   | **feature**  | New functionality request          | Ask    |
   | **design**   | Architecture, pattern, API shape   | Ask    |
   | **question** | Clarification, "why did you..."    | Ask    |

   Present the categorized list to the user for confirmation before proceeding.

### Phase 3: Implement

1. **For bug and style comments:** implement fixes using TDD.
   - Write a failing test that reproduces the issue (when testable).
   - Implement the fix.
   - Confirm the test passes.
   - Acknowledge the comment: `scripts/pr_comments.py ack <pr> <comment-id>`

2. **For feature, design, and question comments:** present each to the user
   one at a time with full context (the comment text, file location, and
   surrounding code). Ask exactly one question per comment. Wait for the
   user's response before proceeding to the next.

   After receiving guidance:
   - For feature/design: implement per the user's direction using TDD.
   - For questions: draft a reply and confirm with the user before posting.
   - Acknowledge: `scripts/pr_comments.py ack <pr> <comment-id>`

### Phase 4: Verify

1. **Run quality gates.** All MUST pass before proceeding:

   ```bash
   task test && task build && task lint
   ```

   If failures occur, fix them and re-run until clean.

### Phase 5: Ship

1. **Commit** using the `commit-commands:commit` skill. The commit message
   SHOULD summarize the review changes addressed (e.g., "address PR review:
   fix error handling and rename helpers"). Defer to the project's commit
   conventions for exact format.

2. **Push** to the PR branch.

3. **Post a summary comment** on the PR using:

    ```bash
    scripts/pr_comments.py comment <pr-number> --file /tmp/pr-summary.md
    ```

    The summary MUST include:
    - A bulleted list of each comment addressed and what was done.
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

## Skill Dependencies

| Skill                            | Used for                |
|----------------------------------|-------------------------|
| `respond-to-pr-comments`         | List, get, ack, comment |
| `test-driven-development`        | TDD for bug/style fixes |
| `commit-commands:commit`         | Creating the commit     |
| `using-git-worktrees`            | Worktree creation       |
| `verification-before-completion` | Final verification      |
