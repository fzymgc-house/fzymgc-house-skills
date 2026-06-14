---
name: miniflux
description: |
  Manage and curate a personal Miniflux RSS subscription set: feed management,
  reading & triage, AI curation, and health/maintenance. Wraps the official
  `miniflux` Python client via a uv-run gateway script (no MCP server required).
  Use when working with: (1) Feeds - subscribe/unsubscribe, organize into
  categories, OPML import/export, discover feeds at a URL; (2) Reading & triage -
  list/search unread entries, mark read, toggle stars, bulk-process the backlog;
  (3) Curation - generate a relevance-ranked digest of what's worth reading, and
  turn recurring noise into durable blocklist/keeplist regex rules; (4) Health -
  find errored, disabled, or stale feeds. This is a direct-client wrapper, not an
  MCP gateway.
allowed-tools:
  - "Bash(uv:*)"
  - "Bash(${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py:*)"
  - Read
  - Grep
  - Glob
  - Search
metadata:
  author: fzymgc-house
---

# Miniflux Operations

## Prerequisites

Set `MINIFLUX_URL` and `MINIFLUX_API_KEY`, or create
`~/.config/miniflux/config.yaml` with `url:` and `api_key:` keys. Create an API
key in Miniflux under Settings → API Keys.

Optional: `~/.config/miniflux/interests.md` describes your reading interests; the
digest workflow uses it to rank entries when present.

## Gateway Script

All operations run through
`${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py`.

```bash
# Discovery
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py --list-commands
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py <command> --help

# Examples
.../miniflux_api.py list-feeds
.../miniflux_api.py get-entries --status unread --limit 50
.../miniflux_api.py digest --category 3 --limit 50
.../miniflux_api.py triage
.../miniflux_api.py health-audit --stale-days 45
.../miniflux_api.py suggest-rules --feed 42
```

`--format yaml` (default) or `--format json` on any command.

## Curation: rules + reasoning

Miniflux applies per-feed `blocklist_rules` / `keeplist_rules` (regex over entry
titles/URLs) deterministically on its side. Claude supplies judgment:

1. **Digest (reasoning):** run `digest`, rank candidates against the user's
   interests, write highlights, then apply decisions with
   `digest --mark-read <ids> --star <ids>` (or the `mark-read` / `toggle-star`
   commands).
2. **Soft → hard handoff (rules):** when you notice recurring noise, run
   `suggest-rules --feed <id>`, propose a regex, get user approval, then make it
   durable with `apply-rule --feed <id> --blocklist '<regex>'`.

See `references/` for per-domain detail: `feeds.md`, `entries.md`,
`curation.md`, `digest.md`, `health.md`.
