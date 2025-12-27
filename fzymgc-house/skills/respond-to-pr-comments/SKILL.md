---
name: respond-to-pr-comments
description: Process GitHub PR review comments, extract and prioritize action items by severity (blocking/important/suggestion), summarize feedback, and delegate fixes to coding agents. Use when the user asks to process PR comments, address PR feedback, fix review issues, or respond to pull request reviews. Handles inline code comments, general review feedback, and review decisions.
---

# PR Comment Processor

Process GitHub pull request review comments, extract actionable items, prioritize by severity, and systematically address feedback.

## Workflow

**CRITICAL REQUIREMENT**: You MUST use the provided scripts (`scripts/fetch_pr_comments.py` and `scripts/parse_action_items.py`) for ALL comment fetching and parsing. These scripts are NON-NEGOTIABLE and ensure complete comment text is captured without truncation. Do NOT use `gh` CLI commands directly or implement your own parsing logic.

### 1. Fetch PR Comments

You MUST get the PR number from the user (or infer from current context if on a PR branch).

**MANDATORY**: You MUST use the provided script to fetch PR comments. Do NOT use `gh pr view` directly or any other method.

```bash
scripts/fetch_pr_comments.py <pr-number> [repo]
```

The script fetches the COMPLETE, UNTRUNCATED text of all comments including:

- Review comments (inline code comments) with full `body` field
- Reviews (approve/request changes/comment) with full `body` field
- All metadata (author, URL, line numbers, IDs for reactions)

If no repo specified, uses current directory's repo. Save output to a file for processing:

```bash
scripts/fetch_pr_comments.py 123 > pr_data.json
```

**Why this script is mandatory**: The `gh` CLI can truncate long output. This script ensures complete comment text is captured and properly structured for parsing.

### 2. Parse and Prioritize Action Items

**MANDATORY**: You MUST use the provided parsing script. Do NOT manually parse or filter the JSON output.

```bash
scripts/parse_action_items.py pr_data.json > action_items.json
```

Or pipe directly:

```bash
scripts/fetch_pr_comments.py 123 | scripts/parse_action_items.py > action_items.json
```

The parser preserves COMPLETE comment text while classifying items into severity levels:

- **blocking**: Critical issues, security vulnerabilities, must-fix items
- **important**: Bugs, problems, required changes (includes CHANGES_REQUESTED reviews)
- **suggestion**: Nits, minor improvements, optional changes
- **comment**: Informational, approved reviews

### 3. Present Summary to User

You MUST create a clear summary showing:

```text
PR #<number>: <title>
Review Status: <reviewDecision>
Branch: <headRefName>

Action Items Summary:
- Blocking: X items
- Important: Y items
- Suggestions: Z items

Blocking Issues:
1. [Author] File:Line - <full comment text>
2. ...

Important Issues:
1. [Author] File:Line - <full comment text>
2. ...

Suggestions:
1. [Author] - <full comment text>
2. ...
```

For each item, you MUST include:

- Author name
- File path and line number (if inline comment)
- **Complete, untruncated comment text** (NOT excerpts or summaries)
- Link to comment

### 4. Confirm Scope with User

Before proceeding, ask which items to address:

- "Address all blocking items?" (recommended starting point)
- "Address blocking + important items?"
- "Address specific items by number?"

You MUST use TodoWrite to create a todo item for each action item being addressed.

### 5. Checkout PR Branch

```bash
gh pr checkout <pr-number>
```

You MUST verify you're on the correct branch before making changes.

### 6. Delegate to Coding Agents

For each action item to address:

#### Option A: Sequential Processing (default)

Use the Task tool with appropriate subagent for each item:

- For code fixes: Use `general-purpose` or domain-specific agents
- For test additions: Consider test-focused workflows
- For refactoring: Use refactoring-focused approaches

You MUST present each fix to the user for approval before moving to the next item. Show:

- The comment being addressed
- The proposed changes (diff or description)
- Ask: "Apply this fix?"

#### Option B: Parallel Processing (for independent items)

If multiple action items are independent (different files, no shared state), launch multiple Task agents in parallel:

```text
I'm going to address these 3 independent issues in parallel:
1. Fix type error in auth.ts
2. Add validation to api.ts
3. Update test in user.test.ts
```

Use a single message with multiple Task tool calls to maximize efficiency.

### 7. Commit and Push (After User Approval)

After each fix is approved:

```bash
git add <affected-files>
git commit -m "fix: <brief description of what was addressed>

Addresses review feedback from @<reviewer>
<optional: link to comment>"
git push origin HEAD
```

You MUST use conventional commit format. You SHOULD reference the reviewer and comment when relevant.

#### Mandatory Comment Acknowledgment

After EVERY commit that addresses a comment or review, you MUST acknowledge it with a thumbs-up reaction. This is NON-NEGOTIABLE.

```bash
# For review comments (get comment ID from action items JSON)
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions \
  -X POST -f content='+1'

# For review summaries (get review ID from action items JSON)
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/reactions \
  -X POST -f content='+1'
```

**CRITICAL**: You MUST acknowledge EVERY processed comment/review. Skipping acknowledgment is a workflow violation.

### 8. Track Progress

You MUST use TodoWrite to mark items completed as you go. You SHOULD update the user periodically:

```text
✅ Addressed 3/5 blocking items
⏳ Working on: "Add error handling in fetchUser"
```

### 9. Post Summary Comment to PR

After all commits are pushed, you MUST post a summary comment to the PR:

```bash
gh pr comment <pr-number> --body "$(cat <<'EOF'
## 🤖 Review Comments Processed

I've addressed the following feedback:

### Blocking Issues (X addressed)
- ✅ [Issue description] - [commit hash]
- ✅ [Issue description] - [commit hash]

### Important Issues (Y addressed)
- ✅ [Issue description] - [commit hash]

### Skipped
- ⏭️ Z suggestions (per user request)

All changes have been committed and pushed. Ready for re-review.

---
🤖 Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

The summary MUST include:

- Which categories of issues were addressed (blocking/important/suggestions)
- Brief description of each fix with commit reference
- What was intentionally skipped and why
- Clear indication that it's ready for re-review

### 10. Final Actions

Present options to the user:

```text
Summary of Changes:
- ✅ Fixed X blocking issues
- ✅ Fixed Y important issues
- ⏭️ Skipped Z suggestions (user choice)

All changes committed, pushed, and summarized on PR #<number>

Would you like me to:
1. Request re-review from specific reviewers?
2. Continue with remaining items?
3. Close this session?
```

## Key Patterns

### Complete Comment Processing

You MUST process the ENTIRE content of each comment without truncation, summarization, or excerpting:

- When presenting comments to the user, show the **full, complete text**
- Do NOT use "..." or ellipsis to shorten comments
- Do NOT summarize or paraphrase comment content
- Do NOT extract only "key points" - show everything
- The user needs to see exactly what the reviewer wrote

This ensures nothing is missed and the full context is preserved for addressing feedback.

### Severity Classification

The parser uses keyword detection:

- **Blocking**: "blocking", "blocker", "must fix", "critical", "security", "breaking"
- **Important**: "should fix", "bug", "problem", "incorrect", or CHANGES_REQUESTED state
- **Suggestion**: "nit", "minor", "consider", "maybe", "optional", "could"

Reviews with CHANGES_REQUESTED state default to "important" severity.

### Code References

For inline review comments, the parser extracts:

- `file`: Path to the file
- `line`: Line number (or approximate position)
- `context`: The diff hunk showing surrounding code

You SHOULD use this information to precisely locate what needs fixing.

### Multiple Sub-Agents

When delegating to agents, consider:

- **Sequential**: Best for dependent changes or when user wants to review each fix
- **Parallel**: Best for independent changes in different files (use single message with multiple Task calls)

### Manual Review Per Fix

Following the user's preference for "manual review per fix":

1. Make the change in working directory
2. Show diff or describe the change
3. Wait for user approval
4. Commit only after approval
5. Move to next item

You MUST NOT batch-commit without showing each change.

## References

- See [gh_cli_patterns.md](references/gh_cli_patterns.md) for detailed `gh` CLI usage patterns

## Example Usage

```text
User: "Process comments on PR 123"
```
