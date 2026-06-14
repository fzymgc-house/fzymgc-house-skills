# Digest Reference

## Digest Workflow

The digest workflow pulls unread entry candidates, ranks them against your reading
interests, generates highlights, and applies triage decisions (mark read, star).

### Reading Interests

Create `~/.config/miniflux/interests.md` to describe your reading focus:

```markdown
# My Reading Interests

## Primary Interest
- Kubernetes
- DevOps tooling
- Cloud architecture

## Secondary Interest
- JavaScript ecosystem
- Open-source tools

## Not interested in
- Celebrity gossip
- Cryptocurrency
```

The digest command uses this file to rank candidates by relevance.

## Get Digest

Retrieve and triage unread entries with optional decision marking:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py digest \
  --category 3 \
  --limit 50 \
  --mark-read 1001 1002 \
  --star 1003 1004
```

### Arguments

- `--category N` - Restrict to category ID (optional)
- `--since <unix-ts>` - Entries published after timestamp (optional)
- `--limit N` - Maximum candidates (default: 50)
- `--mark-read <ids...>` - Mark these entry IDs as read (optional)
- `--star <ids...>` - Star these entry IDs (optional)

### Returns

```yaml
count: 42
candidates:
  - id: 1001
    title: "Kubernetes 1.30 Released"
    url: "https://kubernetes.io/blog/releases/"
    feed: "Kubernetes Blog"
    category: "Technology"
    published: "2026-06-13T08:00:00Z"
    excerpt: "Kubernetes 1.30 is now available with enhanced security features..."
  - id: 1002
    title: "New Node.js Framework"
    url: "https://example.com/nodejs-framework"
    feed: "Node Weekly"
    category: "Technology"
    published: "2026-06-13T07:58:20Z"
    excerpt: "A lightweight framework for building scalable applications..."
marked_read:
  - 1001
  - 1002
starred:
  - 1003
  - 1004
```

### Response Fields

- `count` - Total number of candidates returned
- `candidates` - Array of unread entries with fields:
  - `id` - Entry ID
  - `title` - Entry title
  - `url` - Entry URL
  - `feed` - Feed title (string, not id)
  - `category` - Category title
  - `published` - ISO 8601 publication timestamp from the API
  - `excerpt` - HTML-stripped, truncated summary (~280 chars)
- `marked_read` - Entry IDs marked as read (present only if `--mark-read` used)
- `starred` - Entry IDs starred (present only if `--star` used)

## Workflow Example

1. Run digest to see candidates:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py digest --limit 50
```

2. Read excerpts, rank against your interests, decide which to read/star
3. Apply decisions in a single call:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py digest \
  --mark-read 1001 1002 1005 \
  --star 1003 1004
```
