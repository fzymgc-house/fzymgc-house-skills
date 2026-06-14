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
