# Health Audit Reference

## Feed Health

Audit subscription health to identify broken, disabled, or stale feeds:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py health-audit \
  --stale-days 45
```

### Arguments

- `--stale-days N` - Threshold days for "stale" classification (default: 30)

### Returns

```yaml
errored:
  - id: 12
    title: "Broken Feed"
    errors: 5
  - id: 18
    title: "Another Broken Source"
    errors: 2
disabled:
  - id: 25
    title: "Disabled Feed (Manual)"
  - id: 31
    title: "Another Disabled Feed"
stale:
  - id: 5
    title: "Inactive Blog"
    latest_entry: "2023-01-01T00:00:00Z"
  - id: 9
    title: "Dormant Newsletter"
    latest_entry: null
stale_days: 45
```

### Interpretation

- **Errored** - Feed has parsing errors (`parsing_error_count > 0`). May need
  unsubscription or feed URL change.
- **Disabled** - Feed is disabled (manually disabled in Miniflux). Not also
  reported in stale; check if you want to re-enable or delete.
- **Stale** - No entry published in the last `--stale-days` (staleness computed
  from the latest entry's `published_at` timestamp per feed). A feed with no
  entries shows `latest_entry: null` and counts as stale.
- **stale_days** - The threshold (days) used for this audit.

## Cleanup Workflow

1. Run health audit:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py health-audit
```

2. Decide actions:
   - **Errored feeds** - Try refreshing the feed or unsubscribe if persistently broken
   - **Disabled feeds** - Delete or re-enable based on your needs
   - **Stale feeds** - Unsubscribe from inactive sources or adjust stale threshold

3. Unsubscribe from unwanted feeds:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py delete-feed 12
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py delete-feed 25
```

4. Re-run health audit to verify cleanup.
