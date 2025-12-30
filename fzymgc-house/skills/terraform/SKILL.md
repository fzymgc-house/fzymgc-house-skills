---
name: terraform
description: |
  Terraform Cloud operations and registry documentation lookup.
  Watch runs, view plan/apply logs, check workspace status, look up provider docs.
  Invokes Terraform MCP server on-demand without loading tool definitions into context.
---

# Terraform Operations

## Gateway Script

All operations MUST use the gateway script at `${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py`.

### Configuration

The following environment variable MUST be set:
- `TFE_TOKEN` - HCP Terraform API token (create at https://app.terraform.io/app/settings/tokens)

The following environment variable is required for workspace/run operations:
- `TFE_ORG` - Default organization name (required for: workspace-status, list-runs, watch-run, run-outputs)

The following environment variable MAY be set:
- `TFE_ADDRESS` - TFC/TFE URL (default: https://app.terraform.io)

Note: Provider documentation commands (provider-docs, list-providers) do not require TFE_ORG.

## Quick Reference

| Task | Command |
|------|---------|
| View completed run | `run-details <run-id>` |
| Watch in-progress run | `watch-run <run-id>` |
| Watch latest run | `watch-run --workspace <name>` |
| List runs | `list-runs <workspace>` |
| Workspace status | `workspace-status [name]` |
| View terraform outputs | `run-outputs --workspace <name>` |
| Provider docs | `provider-docs aws --resource lambda_function` |
| List providers | `list-providers --search cloud` |

## TFC Operations

### run-details

View details and formatted logs for a completed run. Parses JSON logs into human-readable format, reducing token usage by ~70%.

```bash
# View completed run with formatted logs
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py run-details run-abc123
```

Output includes:
- Run status and commit message
- Resource change summary (+add ~change -destroy)
- Formatted plan output (errors, warnings, change summary)
- Formatted apply output (for successful runs)

Errors are displayed as:
```
ERROR: Reference to undeclared resource
  File: main.tf:32:20
  Detail: A managed resource "aws_instance" "web" has not been declared...
```

### watch-run

Monitor an in-progress run with live status updates. For completed runs, use `run-details` instead.

```bash
# Watch specific run (will suggest run-details if already complete)
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py watch-run run-abc123

# Watch latest run for workspace
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py watch-run --workspace my-workspace

# Include raw logs when complete (prefer run-details for formatted output)
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py watch-run --workspace my-workspace --logs
```

Options:
- `--workspace`, `-w` - Watch latest run for workspace
- `--logs`, `-l` - Show raw plan/apply logs when run completes
- `--interval`, `-i` - Poll interval in seconds (default: 5)
- `--timeout`, `-t` - Maximum wait time in seconds (default: 3600)

Behavior:
- If run is already complete, suggests using `run-details` instead
- Polls status at regular intervals for in-progress runs
- Displays status changes with timestamps
- Shows plan summary (resource additions/changes/destructions)
- Exits with code 0 for success states, 1 for failure states

### workspace-status

Show workspace overview or detailed info.

```bash
# List all workspaces
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py workspace-status

# Single workspace detail
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py workspace-status my-workspace
```

### list-runs

List recent runs for a workspace.

```bash
# Recent runs
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-runs my-workspace

# With limit
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-runs my-workspace --limit 20

# Filter by status
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-runs my-workspace --status errored
```

### run-outputs

View terraform outputs from a run.

```bash
# From specific run
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py run-outputs run-abc123

# From latest successful run
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py run-outputs --workspace my-workspace
```

## Documentation Lookup

### provider-docs

Look up provider resource documentation.

```bash
# Provider overview
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py provider-docs aws

# Specific resource
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py provider-docs aws --resource lambda_function

# Data source
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py provider-docs aws --data-source ami

# List available resources
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py provider-docs aws --list-resources
```

### list-providers

Search for providers.

```bash
# Search
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-providers --search cloud

# By namespace
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-providers --namespace cloudflare
```

## Output Options

```bash
--format yaml    # YAML output (default)
--format json    # Compact JSON
--format compact # Minimal output
```

## Tool Discovery

When unsure about MCP tool parameters:

```bash
# List all available tools
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py list-tools

# Get tool schema
${CLAUDE_PLUGIN_ROOT}/skills/terraform/scripts/terraform_mcp.py describe <tool_name>
```

## Best Practices

- SHOULD use `run-details <run-id>` for viewing completed runs (formatted output, reduced tokens)
- SHOULD use `watch-run --workspace <name>` for monitoring in-progress runs
- SHOULD use `workspace-status` to get an overview before investigating runs
- MUST NOT use raw MCP tools directly when a workflow exists
- SHOULD prefer `run-details` over `watch-run --logs` for completed runs

## Domain References

Load these as needed for detailed operations:
- [workspaces.md](references/workspaces.md) - Workspace management details
- [runs.md](references/runs.md) - Run status and lifecycle
- [providers.md](references/providers.md) - Provider documentation lookup
