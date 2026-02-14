---
name: respond-to-pr-comments
description: >-
  This skill should be used when the user asks to "list PR comments",
  "check PR feedback", "get PR reviews", "acknowledge comments",
  "respond to PR comments", or "check what reviewers said".
  Provides minimal-token operations for viewing and managing GitHub PR
  review comments and feedback.
argument-hint: "[pr-number]"
allowed-tools:
  - "Bash(${CLAUDE_PLUGIN_ROOT}/skills/respond-to-pr-comments/scripts/pr_comments.py *)"
  - Read
  - Write
metadata:
  author: fzymgc-house
  version: 0.2.0
---

# PR Comment Operations

Minimal operations for GitHub PR comment management with markdown output.

All PR comment operations MUST use the bundled script:

```text
${CLAUDE_PLUGIN_ROOT}/skills/respond-to-pr-comments/scripts/pr_comments.py
```

## Commands

### List Comments

```bash
pr_comments.py list <pr-number>            # All comments
pr_comments.py list <pr-number> --unacked  # Only unacknowledged
```

Output includes comment ID (`RC_*` for review comments, `R_*` for reviews),
acknowledgment status (`[✓]`/`[○]`), author, file location, body, and
ready-to-run ack commands.

### Get Specific Comment

```bash
pr_comments.py get <pr-number> <comment-id>
pr_comments.py get <pr-number> <comment-id> --save /path/to/file.md
```

Returns full comment details with acknowledgment status, file location,
review state, and URL. The `--save` flag writes output to a file.

### Get Latest Comment

```bash
pr_comments.py latest <pr-number>
```

Returns the most recent comment from any source.

### Acknowledge Comment

```bash
pr_comments.py ack <pr-number> <comment-id>
```

Adds a 👍 reaction to the comment. Acknowledge comments after addressing them.

### Add Comment

```bash
pr_comments.py comment <pr-number> --file /path/to/comment.md  # Preferred
pr_comments.py comment <pr-number> "Short inline text"
```

Posts a comment to the PR conversation. Prefer `--file` for multi-line or
formatted comments to avoid shell escaping issues.

## Comment IDs

| Prefix | Type                              |
|--------|-----------------------------------|
| `RC_*` | Review comment (inline on code)   |
| `R_*`  | Review (approve/request/comment)  |

## Acknowledgment Tracking

The script checks the GitHub reactions API to determine if the authenticated
user has already reacted with 👍. This enables `--unacked` filtering and
status display in all outputs.

## Integration Notes

- Commands MAY be used in any order or combination.
- Acknowledge comments after addressing feedback.
- Summary comments MAY be posted after batch fixes.
- MUST NOT create additional parsing or processing scripts.
- MUST use the comment ID formats provided in output.

This skill provides tools only — no mandatory workflows, delegation patterns,
commit structures, or processing steps are imposed.
