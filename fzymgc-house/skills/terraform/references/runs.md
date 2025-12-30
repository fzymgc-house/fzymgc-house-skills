# Run Operations Reference

## Run Status Lifecycle

```
pending → planning → planned → [cost_estimating →] [policy_checking →] confirmed → applying → applied
                  ↓                                                              ↓
              errored                                                        errored
                  ↓                                                              ↓
              discarded                                                      discarded
```

## Terminal States

| Status | Exit Code | Description |
|--------|-----------|-------------|
| `applied` | 0 | Successfully applied |
| `planned_and_finished` | 0 | Plan-only run completed |
| `errored` | 1 | Run failed |
| `discarded` | 1 | Run was discarded |
| `canceled` | 1 | Run was canceled |

## Run Fields

| Field | Description |
|-------|-------------|
| `id` | Run ID (run-xxx) |
| `status` | Current status |
| `message` | Commit message or description |
| `resource-additions` | Resources to add |
| `resource-changes` | Resources to change |
| `resource-destructions` | Resources to destroy |
| `created-at` | Run creation time |

## Underlying MCP Tools

- `list_runs` - List runs for workspace
- `get_run_details` - Get detailed run info

## Direct HCP API

For log streaming, the skill uses direct HCP Terraform API:
- `GET /api/v2/plans/:id` - Get plan with log URL
- `GET /api/v2/applies/:id` - Get apply with log URL
