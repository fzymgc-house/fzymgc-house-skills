# Curation Reference

## Per-Feed Rules

Miniflux applies regex-based content filtering per feed via two rule fields:

- **`blocklist_rules`** - Regex patterns matching entry titles/URLs to exclude (hide/remove)
- **`keeplist_rules`** - Regex patterns matching entry titles/URLs to always include (override blocklist)

Additional rule fields exist but are not first-class operations here:

- `scraper_rules` - HTML extraction patterns for content crawling
- `rewrite_rules` - URL rewrite patterns

### Rule Semantics

Rules are standard regex expressions applied to entry titles and URLs. Case-insensitive matching uses `(?i)` prefix:

```text
(?i)advertisement  # Case-insensitive: matches "Advertisement", "ADVERTISEMENT", etc.
spam|noise         # Alternation: matches either "spam" OR "noise"
^promoted          # Anchor: matches titles starting with "promoted"
```

Rules are written per-feed via the client. The `suggest-rules` command identifies
candidates; `apply-rule` persists them.

## Suggest Rules

Analyze recent entries in a feed to suggest blocklist/keeplist rules:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py suggest-rules \
  --feed 42 \
  --limit 20
```

### Arguments

- `--feed N` - Feed ID (required)
- `--limit N` - Number of recent entries to analyze (optional, default: 20)

### Returns

```yaml
feed_id: 42
feed_title: "Tech News Daily"
current:
  blocklist_rules: "(?i)advertisement|sponsored"
  keeplist_rules: "breaking"
recent_titles:
  - "New JavaScript Framework Released"
  - "Sponsored: Cloud Platform Review"
  - "Breaking: Security Vulnerability Disclosed"
  - "Advertisement: DevOps Tools"
  - "New Kubernetes Operator Available"
```

The response shows current rules (if any) and recent entry titles to help identify
patterns for new rules.

## Apply Rule

Persist a blocklist or keeplist rule to a feed:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py apply-rule \
  --feed 42 \
  --blocklist "(?i)advertisement|spam" \
  --keeplist "breaking|urgent"
```

### Arguments

- `--feed N` - Feed ID (required)
- `--blocklist '<regex>'` - Regex to add/update blocklist rule (optional)
- `--keeplist '<regex>'` - Regex to add/update keeplist rule (optional)
- At least one of `--blocklist` or `--keeplist` is required; omit one to leave unchanged

### Clear a Rule

Pass an empty string to clear a rule:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py apply-rule \
  --feed 42 \
  --blocklist ""
```

### Returns

```yaml
feed_id: 42
applied:
  blocklist_rules: "(?i)advertisement|spam"
  keeplist_rules: "breaking|urgent"
```

The response includes only the rules that were modified (not current rules for
unmodified fields).
