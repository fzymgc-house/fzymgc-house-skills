# Entries Reference

## Get Entries

Retrieve entries with filtering and search:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py get-entries \
  --status unread \
  --limit 50 \
  --order published_at \
  --direction desc
```

### Filter Arguments

- `--status {read,unread,removed}` - Filter by entry status (optional)
- `--starred` / `--no-starred` - Filter by star status (optional)
- `--search <q>` - Full-text search query (optional)
- `--category N` - Filter by category ID (optional)
- `--feed N` - Filter by feed ID (optional)
- `--after <unix-ts>` - Entries after timestamp (optional)
- `--limit N` - Maximum results (default: 20)
- `--order` - Sort field, e.g. `published_at`, `created_at` (default: `published_at`)
- `--direction {asc,desc}` - Sort order (default: `desc`)

### Returns

```yaml
total: 342
entries:
  - id: 1001
    title: "Article Title"
    url: "https://example.com/article"
    status: "unread"
    starred: false
    published_at: "2026-06-13T08:00:00Z"
    feed: "Example Feed"
    category: "Technology"
  - id: 1002
    title: "Another Article"
    url: "https://example.com/another"
    status: "unread"
    starred: true
    published_at: "2026-06-13T07:58:20Z"
    feed: "Another Feed"
    category: "News"
```

Fields: `id`, `title`, `url`, `status`, `starred`, `published_at` (ISO 8601
string from the API), `feed` (feed title, not id), `category` (category title).

## Mark Entry Read

Mark an entry as read:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py mark-read 1001 1002 1003
```

Returns:

```yaml
marked_read:
  - 1001
  - 1002
  - 1003
```

## Toggle Star

Add or remove star from entry:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py toggle-star 1001
```

Returns:

```yaml
toggled_star: 1001
```
