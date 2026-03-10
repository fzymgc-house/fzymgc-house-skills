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
homelab/
  plugin.json         # Homelab plugin (grafana, terraform, skill-qa)
  skills/
    <skill-name>/
      SKILL.md        # Skill definition (required)
      scripts/        # Executable scripts (optional)
      references/     # Additional resources (optional)
pr-review/
  plugin.json         # PR review plugin (review-pr, address-findings, respond-to-comments)
  agents/             # True agents with isolation: worktree
    <agent-name>.md   # Agent definition (YAML frontmatter + system prompt)
  skills/
    <skill-name>/
      SKILL.md
      scripts/
      references/
jj/
  plugin.json         # jj (Jujutsu) VCS plugin
  skills/
    jujutsu/
      SKILL.md        # Core jj workflow guidance
      references/
        jj-git-interop.md
  commands/
    jj-init.md        # /jj-init slash command
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

Skills should be self-contained and focused on specific tasks related to either homelab infrastructure or PR review workflows.

## Available Skills

- **grafana** - Grafana, Loki, Prometheus operations (dashboards, logs, metrics, alerting, incidents, OnCall, profiling).
  Use Loki/Prometheus FIRST for logs/metrics instead of kubectl.
- **terraform** - Terraform Cloud operations (runs, workspaces, state management, registry documentation lookup)
- **respond-to-comments** (`pr-review` plugin) - GitHub PR review comment management (list, acknowledge, respond to feedback, full
  review-response workflows). Reads review findings from beads for context-aware responses.
- **address-findings** (`pr-review` plugin) - Processes review-pr findings by working through
  beads in the review epic. Dependency-aware fix loop with batch review gates.
- **review-pr** (`pr-review` plugin) - Comprehensive PR review using 9 specialized subagents (code quality, error handling, test coverage,
  type design, comments, security, API compatibility, spec compliance, code simplification).
  Findings persisted as beads for cross-session context. User-invoked via `/review-pr [aspects]`.
- **skill-qa** (`homelab` plugin) - Validates SKILL.md files against Claude Code best practices (Claude-only, auto-triggered during skill reviews)
- **jujutsu** (`jj` plugin) - Jujutsu (jj) VCS workflow guidance. Activates when `.jj/` exists in repo root
  or user mentions jj/jujutsu. Covers core concepts, bookmarks, workspaces, and git interop.

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

### Release Versioning

Versions are managed by release-please. Do NOT manually bump versions
in `marketplace.json`, `plugin.json`, or SKILL.md `metadata.version`
fields.

When adding or removing a skill, update both:

- `release-please-config.json` (add/remove package entry)
- `.release-please-manifest.json` (add/remove version entry)

CI will fail if skill directories and release-please config fall out
of sync.

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

### Worktree Layout

Agent worktrees are created in a **sibling directory** to avoid nesting
repos (which confuses LSP servers):

```text
<repo>/                    # main repo
<repo>_worktrees/          # worktree parent (sibling)
  fix-worker-abc/          # one worktree per agent invocation
  verification-runner-def/
```

WorktreeCreate/WorktreeRemove hooks in `.claude/settings.json` handle
this automatically. Do NOT manually create worktrees — always use the
hook system.

**VCS rule:** When jj is available (`jj root` succeeds), MUST use jj
commands for ALL VCS operations — commits, workspaces, rebases, status,
log, etc. This applies to colocated repos (both `.jj/` and `.git/`)
as well as pure jj repos. Never use mutating git commands (`git commit`,
`git worktree add`, `git checkout`, etc.) when jj is present.
Read-only git commands (`git log`, `git diff`, `git rev-parse`) and
`gh` CLI are safe in colocated repos.

**VCS-specific behavior:**

- **jj repos (including colocated)**: `jj workspace add` for worktrees,
  `jj rebase` + `jj bookmark set` for integration, `jj workspace forget`
  for cleanup. fix-worker reports `CHANGE_ID`.
- **git-only repos** (no `.jj/`): `git worktree add` for worktrees,
  `git cherry-pick` for integration, `git worktree remove` for cleanup.
  fix-worker reports `WORKTREE_BRANCH`.

### jj Operation Log Semantics

jj's op log only records **successful** operations (unlike git's reflog).
A failed `jj bookmark set` leaves no op-log entry — `jj undo` skips past
it to the previous successful op. Never "undo twice" to account for failures.

In jj, `@` is the working-copy commit (typically empty). Use `@-` (parent)
when verifying committed state (e.g., after `jj undo` or `jj commit`).

### Skill Invocation

Skills are **model-invoked** (Claude decides when to use them), not user-invoked slash commands.
The `description` field determines when Claude loads a skill. Make descriptions specific with trigger phrases.
