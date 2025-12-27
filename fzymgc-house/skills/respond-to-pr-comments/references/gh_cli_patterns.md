# GitHub CLI Patterns for PR Comment Processing

## Fetching PR Data

### Basic PR Information

```bash
gh pr view <number> --json number,title,state,reviewDecision,body,author,url,headRefName
```

### Review Comments (Inline Code Comments)

```bash
gh pr view <number> --json comments --jq '.comments'
```

Returns array of comment objects with:
- `body`: Comment text
- `author.login`: Comment author username
- `path`: File path (for inline comments)
- `line`: Line number
- `diffHunk`: Surrounding code context
- `createdAt`: Timestamp
- `url`: Direct link to comment

### Reviews (Approve/Request Changes/Comment)

```bash
gh pr view <number> --json reviews --jq '.reviews'
```

Returns array of review objects with:
- `body`: Review summary text
- `author.login`: Reviewer username
- `state`: One of APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
- `submittedAt`: Timestamp
- `url`: Direct link to review

### Repository Specification

When working outside the repo or with different repos:

```bash
gh pr view <number> -R owner/repo --json ...
```

## Checkout PR Branch for Fixes

After identifying action items, checkout the PR branch:

```bash
gh pr checkout <number>
```

Or manually:

```bash
# Get branch name from PR info
gh pr view <number> --json headRefName --jq '.headRefName'

# Checkout the branch
git fetch origin <branch-name>
git checkout <branch-name>
```

## Pushing Fixes

After making changes:

```bash
git add <files>
git commit -m "fix: address review comment - <brief description>"
git push origin HEAD
```

## Comment on PR

To acknowledge processing or provide updates:

```bash
gh pr comment <number> --body "🤖 Processing review comments..."
```

## Add Reactions to Comments/Reviews

After addressing feedback, acknowledge with a thumbs-up reaction:

### For Review Comments (inline code comments)

```bash
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions \
  -X POST -f content='+1'
```

The `comment_id` is available in the parsed action items JSON under `code_ref.comment_id`.

### For Review Summaries

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/reactions \
  -X POST -f content='+1'
```

The `review_id` is available in the parsed action items JSON under `review_id`.

### Getting Owner/Repo

If not already known, extract from PR info:

```bash
# From PR URL: https://github.com/owner/repo/pull/123
# owner = "owner"
# repo = "repo"
```

Or get from current git remote:

```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
# Returns: "owner/repo"
```

## Helpful Filters

### Only Show Unresolved Comments

GitHub CLI doesn't directly filter by resolution status, but you can:
1. Fetch all comments
2. Check for `isResolved` field in comment data
3. Filter in Python/JSON processing

### Filter by Author

```bash
gh pr view <number> --json reviews --jq '.reviews[] | select(.author.login == "username")'
```
