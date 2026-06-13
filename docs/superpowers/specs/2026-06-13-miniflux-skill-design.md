# Miniflux RSS Feed Management & Curation Skill — Design

- **Design bead:** fhsk-8k8
- **Date:** 2026-06-13
- **Plugin:** `homelab`
- **Status:** Draft (pending design-reviewer)

## Problem

Managing and curating a personal RSS subscription set in Miniflux is manual
and tedious: subscribing/organizing feeds, working down the unread backlog,
filtering recurring noise, finding dead or stale feeds, and figuring out "what's
actually worth reading" all happen by hand in the web UI. There is no
agent-driven path to triage the backlog, generate a relevance-ranked digest, or
turn recurring noise into durable filters.

## Goal

A `homelab` skill that lets Claude manage and curate Miniflux feeds through the
official Miniflux Python client, covering four areas the user identified as
in-scope: **feed management**, **reading & triage**, **AI curation**, and
**health & maintenance**. Curation follows a **rules + reasoning** model and a
**digest is a core workflow**.

## Non-Goals

- Building or maintaining a standalone Miniflux MCP server.
- Replacing Miniflux's web UI for interactive reading.
- Multi-user / multi-instance administration (single self-hosted instance,
  single API token).
- Server provisioning/deployment of Miniflux itself (that is Terraform/cluster
  concern, not this skill).

## Grounding (Rule 7)

- **Prior art (probe):** Existing `homelab` skills (`grafana`, `terraform`) use
  a gateway-script pattern — a single Python CLI (`*_mcp.py`) wrapping an
  API/MCP server, with raw passthrough commands plus compound workflows exposed
  as flags, `--format yaml|json` output, and per-domain `references/*.md`. This
  skill mirrors that pattern **structurally** but differs at the implementation
  level: the existing scripts proxy an MCP server over `httpx`, whereas
  `miniflux_api.py` is a **direct wrapper over the official `miniflux` Python
  client** — no MCP intermediary. SKILL.md describes it as a direct-client
  wrapper, not an MCP gateway.
- **Library (context7 `/miniflux/python-client`, High reputation, 111
  snippets):** Official `miniflux` pip package. `Client(url, api_key)` exposes
  `create_feed` / `update_feed` / `delete_feed`, `get_feeds`, `get_entries`
  (filters: `status`, `starred`, `search`, `category_id`, `feed_id`, `after`,
  `before`, `limit`, `offset`, `order`, `direction`),
  `update_entries(entry_ids, status)` (bulk status),
  `mark_feed_entries_as_read(feed_id)`, `get_categories` / `create_category`,
  OPML `export_feeds()` / `import_feeds(opml)`, `refresh_feed` / `refresh_all`,
  `discover`. Built-in
  per-feed curation primitives: `blocklist_rules`, `keeplist_rules`,
  `scraper_rules`, `rewrite_rules` (settable via `create_feed`/`update_feed`).

## Architecture

### Layout

```text
homelab/skills/miniflux/
  SKILL.md                     # frontmatter + workflows + rules-vs-reasoning guidance
  scripts/miniflux_api.py      # uv PEP723; deps = ["miniflux", "pyyaml"]
  references/
    feeds.md       # feed + category CRUD, OPML import/export, discover
    entries.md     # entry filtering, reading, triage, bulk mark-read/star
    curation.md    # blocklist/keeplist/scraper/rewrite rules + suggest-rules flow
    digest.md      # digest/highlights workflow + ranking guidance
    health.md      # health audit (errored/disabled/stale feeds)
```

Conventions inherited from `grafana`/`terraform`:

- Shebang `#!/usr/bin/env -S uv run` with PEP 723 inline metadata
  (`requires-python = ">=3.11"`, `dependencies = ["miniflux", "pyyaml"]`).
- `--format yaml|json`, YAML default.
- Invoked via `${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py`.
- `allowed-tools` scoped to `Bash(uv:*)`, the script path, plus
  `Read`, `Grep`, `Glob`, `Search`.

### Configuration

Resolution order:

1. Environment: `MINIFLUX_URL`, `MINIFLUX_API_KEY`.
2. Fallback config file: `~/.config/miniflux/config.yaml` (keys `url`,
   `api_key`). XDG `$XDG_CONFIG_HOME` honored if set.

The Miniflux client requires only `url` + `api_key`, so either source fully
configures it. Missing/incomplete config produces a clear actionable error
naming both the env vars and the config-file path.

Optional relevance profile: `~/.config/miniflux/interests.md` (or interests
stated in the session) informs digest ranking. Absent → Claude ranks from
session context alone.

### CLI surface

## Discovery

- `--list-commands`, `--help`

**Raw passthrough** (thin wrappers over client methods)

- `list-feeds`, `list-categories`, `get-feed <id>`
- `get-entries [--status --starred --search --category --feed --after --limit
  --order --direction]`
- `create-feed <url> [--category --crawler ...]`, `update-feed <id> [...]`,
  `delete-feed <id>`
- `mark-read <ids...>` (`update_entries(ids, "read")`), `toggle-star <id>`
  (`toggle_bookmark`; the client exposes a single toggle, not separate
  star/unstar)
- `refresh-feed <id>`, `refresh-all`
- `export-opml`, `import-opml <path>`
- `discover <url>`

## Compound workflows

- `digest [--category --since --limit]` → returns structured unread candidates
  (`id`, `title`, `feed`, `category`, `url`, `excerpt`, `published`) for Claude
  to rank + summarize; `--mark-read <ids>` / `--star <ids>` applies decisions
  after.
- `triage` → unread counts per feed/category (from `get_feed_counters()`); bulk
  mark-read by feed (`mark_feed_entries_as_read(feed_id)`) or category
  (`mark_category_entries_as_read(category_id)`).
- `health-audit` → feeds with `parsing_error_count > 0`, disabled feeds, and
  stale feeds. Staleness is computed client-side as the most recent entry
  `published_at` per feed (no native Miniflux staleness endpoint): a feed with
  no entry newer than N days is stale (N configurable, sensible default).
- `suggest-rules --feed <id>` → dumps recent entry titles for Claude to propose
  regex; `apply-rule --feed <id> --blocklist|--keeplist <regex>` writes it via
  `update_feed`.

## Curation Data Flow (rules + reasoning)

- **Digest (reasoning):** script fetches filtered unread → Claude ranks against
  interests + writes highlights → Claude optionally marks read / stars selected
  entries via the script.
- **Soft → hard handoff (rules):** when Claude spots recurring noise during
  triage/digest, it proposes a `blocklist_rules` / `keeplist_rules` regex; on
  user approval, `apply-rule` makes it a durable in-Miniflux filter so the noise
  is removed deterministically going forward.

This split keeps deterministic plumbing (multi-call orchestration, regex
application) in the script and judgment (relevance, digest prose, rule
proposals) in Claude.

## Error Handling

Centralized in the script:

- `miniflux.AccessUnauthorized` (typed subclass of `ClientError`) → message
  pointing at `MINIFLUX_API_KEY` / config `api_key`.
- Connection error → message pointing at `MINIFLUX_URL` / config `url`.
- Other `miniflux.ClientError` (e.g. `ResourceNotFound`) → surface the
  server-provided message verbatim.
- Non-zero exit codes on failure; no silent fallbacks.

## Testing

- `pytest` suite mocking `miniflux.Client` covering: config resolution
  (env vs. file vs. missing), command dispatch / argument parsing, output
  formatting (yaml/json), and error-path exit codes. No live instance required,
  so it runs under the repo's harness-independent `task test`.
- SKILL.md frontmatter validated by the existing `task lint` (rumdl + schema
  gates). Optional `skill-qa` pass on the finished SKILL.md.

## Open Questions

None outstanding; integration approach, auth, config source, curation model,
and digest scope were all decided during brainstorming.
