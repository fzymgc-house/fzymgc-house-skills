---
name: respond-to-pr-comments
description: Use when user asks to list PR comments, check PR feedback, get PR reviews, acknowledge comments, or respond to PR comments. Provides minimal-token operations for viewing and managing GitHub PR review comments and feedback.
---

# PR Comment Operations

Minimal operations for GitHub PR comment management with markdown output.

## Script Usage

You MUST use `scripts/pr_comments.py` for all PR comment operations.

### Commands

#### List Comments

```bash
# List all comments on a PR
scripts/pr_comments.py list <pr-number>

# List only unacknowledged comments
scripts/pr_comments.py list <pr-number> --unacked
```

Output includes:

- Comment ID (format: `RC_*` for review comments, `R_*` for reviews)
- Acknowledgment status (`[✓]` acked, `[○]` unacked)
- Author, file location (for inline comments), comment body
- Ready-to-run ack command for unacked comments

#### Get Specific Comment

```bash
# Display comment to stdout
scripts/pr_comments.py get <pr-number> <comment-id>

# Save comment to file
scripts/pr_comments.py get <pr-number> <comment-id> --save /path/to/file.md
```

Output includes:

- Full comment details with acknowledgment status
- File location and line number (for inline comments)
- Review state (for review comments)
- Comment URL
- Ready-to-run ack command if unacked

When `--save` is used, writes output to file and prints confirmation message.

#### Get Latest Comment

```bash
scripts/pr_comments.py latest <pr-number>
```

Returns the most recent comment from any source (review comments or reviews).

#### Acknowledge Comment

```bash
scripts/pr_comments.py ack <pr-number> <comment-id>
```

Adds a 👍 reaction to the specified comment. You SHOULD acknowledge comments after addressing them.

#### Add Comment

```bash
# From file (preferred - avoids heredoc complications)
scripts/pr_comments.py comment <pr-number> --file /path/to/comment.md

# Inline text (for short comments only)
scripts/pr_comments.py comment <pr-number> "Your comment text here"
```

Posts a new comment to the PR conversation. You SHOULD use `--file` for multi-line or formatted comments to avoid shell escaping issues.

## Output Format

All commands use markdown output to minimize tokens. Output is structured for readability and includes inline ack commands where applicable.

## Comment IDs

- `RC_*` prefix: Review comment (inline code comment)
- `R_*` prefix: Review (approve/request changes/comment with body)

## Acknowledgment Tracking

The script checks GitHub reactions API to determine if the authenticated user has already added a 👍 reaction to a comment. This allows filtering with `--unacked` and shows status in all outputs.

## Workflow Examples

**Review unacknowledged comments:**

```bash
scripts/pr_comments.py list 123 --unacked
```

**Get details on specific comment:**

```bash
scripts/pr_comments.py get 123 RC_456789
```

**Acknowledge after addressing:**

```bash
scripts/pr_comments.py ack 123 RC_456789
```

**Check latest feedback:**

```bash
scripts/pr_comments.py latest 123
```

## Integration Notes

- You MAY use these commands in any order or combination
- You SHOULD acknowledge comments after addressing feedback
- You MAY add summary comments to PR after batch fixes
- You MUST NOT create additional parsing or processing scripts
- You MUST use the comment ID formats provided in output

## No Mandatory Workflows

This skill provides tools only. You MAY choose how to use them based on user requests. There are NO required delegation patterns, commit structures, or processing steps.
