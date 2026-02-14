# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a Claude Code marketplace plugin repository containing skills for the fzymgc-house self-hosted cluster.
Skills are reusable prompts and workflows that extend Claude Code's capabilities.

## Quick Start

```bash
# Install git hooks (required before first commit)
lefthook install

# Verify hooks are installed
lefthook run pre-commit --all-files  # Run linters on all files
```

## Structure

```text
.claude-plugin/
  marketplace.json    # Plugin metadata (name, version, owner)
fzymgc-house/
  plugin.json         # Plugin definition
  skills/
    <skill-name>/
      SKILL.md        # Skill definition (required)
      scripts/        # Executable scripts (optional)
      references/     # Additional resources (optional)
```

## Creating Skills

Each skill is a directory containing at minimum a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: Brief description for skill discovery
---

# Skill content and instructions
```

Skills should be self-contained and focused on specific tasks related to the fzymgc-house infrastructure.

## Available Skills

- **grafana** - Grafana, Loki, Prometheus operations (dashboards, logs, metrics, alerting, incidents, OnCall, profiling).
  Use Loki/Prometheus FIRST for logs/metrics instead of kubectl.
- **terraform** - Terraform Cloud operations (runs, workspaces, state management, registry documentation lookup)
- **respond-to-pr-comments** - GitHub PR review comment management (list, acknowledge, respond to feedback, full review-response workflows)
- **skill-qa** - Validates SKILL.md files against Claude Code best practices (Claude-only, auto-triggered during skill reviews)

## Commit Workflow

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```text
<type>(<scope>): <description>

Examples:
  feat(skills): add new skill for X
  fix(grafana): correct API endpoint
  docs: update CLAUDE.md
```

Validation is enforced by `cog verify` in the commit-msg hook. Pre-commit hooks auto-format Python (ruff) and Markdown (rumdl).

## Development

### Testing Skills Locally

Skills are model-invoked (Claude decides when to use them based on the description). To test:

1. Install the plugin locally: `claude plugin install .`
2. Start a session: `claude`
3. Trigger the skill by asking Claude to perform the relevant task

### Validating SKILL.md Files

The `skill-qa` skill (Claude-only) validates SKILL.md files against best practices. Alternatively, check manually:

- `name`: lowercase, hyphens only, max 64 chars
- `description`: includes what the skill does AND when to use it
- Body: under 500 lines, concise, actionable commands

### Linting

Pre-commit hooks run automatically via lefthook:

```bash
# Python
ruff check --fix <file>
ruff format <file>

# Markdown
rumdl check <file>
rumdl fmt <file>
```

## MCP Servers

The following MCP servers are available in `.mcp.json`:

- **grafana** - HTTP MCP server for Grafana operations (<https://mcp.grafana.fzymgc.house/mcp>)
- **context7** - Live library documentation lookup (GitHub CLI, APIs)
- **terraform** - Terraform Cloud operations via Docker

Skills can invoke these servers on-demand without pre-loading tool definitions into context.

## Gotchas

### Auto-Formatting on Edit

PostToolUse hooks (`.claude/settings.json`) auto-format files after Edit/Write:

- **Python (.py)**: `ruff check --fix` + `ruff format`
- **Markdown (.md)**: `rumdl check --fix`

This prevents commit hook failures by fixing issues immediately.
If you see files change after editing, this is expected behavior.

### Skill Invocation

Skills are **model-invoked** (Claude decides when to use them), not user-invoked slash commands.
The `description` field determines when Claude loads a skill. Make descriptions specific with trigger phrases.
