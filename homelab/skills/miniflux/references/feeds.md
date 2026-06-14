# Feed Management Reference

## List Feeds

Retrieve all subscription feeds:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py list-feeds
```

Returns:

```yaml
- id: 1
  title: "Example Feed"
  feed_url: "https://example.com/feed.xml"
  category: "Technology"
  parsing_error_count: 0
  disabled: false
- id: 2
  title: "Another Feed"
  feed_url: "https://another.com/feed"
  category: null
  parsing_error_count: 0
  disabled: false
```

Fields: `id`, `title`, `feed_url`, `category` (string or null), `parsing_error_count`, `disabled`.

## List Categories

Retrieve all feed categories:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py list-categories
```

Returns:

```yaml
- id: 1
  title: "Technology"
- id: 2
  title: "News"
```

Fields: `id`, `title`.

## Get Feed

Fetch a single feed by id (raw Miniflux feed object, including
`blocklist_rules` / `keeplist_rules` / `scraper_rules` / `rewrite_rules`):

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py get-feed 42
```

Returns the raw feed object as Miniflux reports it (`id`, `title`, `feed_url`,
`category`, `parsing_error_count`, `disabled`, the per-feed rule fields, etc.).

## Subscribe to Feed

Create a new subscription:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py create-feed <url> --category 3 --crawler
```

Arguments:

- `<url>` - Feed URL (required)
- `--category N` - Category ID (optional)
- `--crawler` - Enable content crawler (optional)

Returns:

```yaml
created_feed_id: 42
```

## Update Feed

Update attributes of an existing feed:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py update-feed 42 --category 5 --crawler
```

Arguments:

- `<id>` - Feed ID (required)
- `--title TEXT` - Rename the feed (optional)
- `--category N` - Move to category ID (optional)
- `--crawler` / `--no-crawler` - Toggle the content crawler (optional)
- `--disabled` / `--no-disabled` - Disable or re-enable the feed (optional)

At least one attribute flag is required. Returns:

```yaml
updated_feed_id: 42
updated:
  category_id: 5
  crawler: true
```

## Unsubscribe from Feed

Remove a feed subscription:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py delete-feed 42
```

Returns:

```yaml
deleted_feed_id: 42
```

## Export OPML

Export subscriptions as OPML:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py export-opml
```

Returns:

```yaml
opml: "<?xml version=\"1.0\" encoding=\"UTF-8\"?><opml version=\"2.0\">...</opml>"
```

## Import OPML

Import subscriptions from OPML file:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py import-opml /path/to/subscriptions.opml
```

Returns:

```yaml
imported_from: /path/to/subscriptions.opml
```

## Discover Feeds at URL

Discover feeds available at a website:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py discover https://example.com
```

Returns raw list of discovered feeds:

```yaml
- url: "https://example.com/feed.xml"
  title: "Example Blog"
- url: "https://example.com/news.xml"
  title: "Example News"
```

## Refresh Feed

Fetch latest entries for a feed:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py refresh-feed 42
```

Returns:

```yaml
refreshed_feed_id: 42
```

## Refresh All Feeds

Fetch latest entries for all subscriptions:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py refresh-all
```

Returns:

```yaml
refreshed: "all"
```
