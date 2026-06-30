# Agent Instructions

`AGENTS.md` is the shared source of truth for repository instructions in this
repo. Use it for Codex, Claude Code, and other agents. This file contains both
cross-platform rules and Claude-specific notes.

## Repository Purpose

This repository publishes four source plugins for the fzymgc-house skills
marketplace:

- `homelab` - infrastructure skills for Terraform and skill QA
- `jj` - Jujutsu workflow guidance
- `dev-flow` - development workflow skills forked from obra/superpowers, plus
  the PR review orchestrators (`review-pr`, `address-findings`,
  `respond-to-comments`) and review/fix/verification agents
- `tmux` - terminal-multiplexer usage skill

It also publishes a repo-local Codex compatibility layer:

- `.agents/plugins/marketplace.json` - Codex marketplace manifest
- `plugins/<name>/` - thin Codex wrapper plugins

Keep the real skill content in the source plugin directories (`homelab/`,
`jj/`, `dev-flow/`). The `plugins/` wrappers should point
back to those sources instead of copying them.

## Quick Start

There is no pre-commit hook manager — jj does not fire git hooks reliably. The
`Taskfile.yaml` is the single source of truth for quality gates, and CI runs the
same tasks.

```bash
task fmt    # auto-format markdown + Python before committing
task lint   # markdown, Python, JSON, evals, ADR gates
task test   # all harness-independent test suites
```

## Agent Docs

Read this file for all repo-wide rules and Claude-specific notes.

## Repository Structure

```text
.claude-plugin/
  marketplace.json      # Claude marketplace manifest
.agents/plugins/
  marketplace.json      # Codex marketplace manifest
plugins/
  <plugin-name>/
    .codex-plugin/
      plugin.json       # Codex wrapper manifest
    ...                 # Symlinks back to source plugin content
homelab/
  plugin.json
  skills/
jj/
  plugin.json
  commands/
  hooks/
  skills/
dev-flow/
  plugin.json
  agents/         # incl. review/fix/verification agents
  commands/
  evals/
  hooks/
  references/     # incl. code-slop, prose-slop, vcs preambles
  scripts/
  skills/         # incl. review-pr, address-findings, respond-to-comments
```

## Issue Tracking With bd

This project uses **bd (beads)** for all issue tracking. Do not use markdown
TODO lists or ad-hoc task tracking.

Start with:

```bash
bd onboard
bd ready
```

Quick reference:

```bash
bd ready                 # Find available work
bd show <id>             # View issue details
bd update <id> --claim   # Claim work atomically
bd close <id>            # Complete work
bd prime                 # Show current workflow guidance
bd dolt push             # Push bead history if a Dolt remote is configured
```

If bead synchronization matters, check whether a Dolt remote exists first:

```bash
bd dolt remote list
```

If no remote is configured, do not invent a sync step.

## Non-Interactive Shell Commands

Always use non-interactive flags with file operations to avoid hangs from
interactive aliases.

```bash
cp -f source dest
mv -f source dest
rm -f file
rm -rf directory
cp -rf source dest
scp -o BatchMode=yes ...
ssh -o BatchMode=yes ...
apt-get -y ...
HOMEBREW_NO_AUTO_UPDATE=1 brew ...
```

## Development Rules

### Commits

All commits must follow Conventional Commits:

```text
<type>(<scope>): <description>
```

Examples:

```text
feat(terraform): add workspace tag filtering
fix(review-pr): correct agent dispatch for security aspect
docs: update agent instructions
```

Conventional-commit validation runs in CI on the PR title
(`.github/workflows/commit-lint.yaml`); there is no local commit-msg hook
(jj does not fire git hooks reliably).

### Testing and Linting

Primary local checks — the same gates CI runs (see `.github/workflows/ci.yaml`):

```bash
task lint   # rumdl (curated set), ruff check + format, jq, evals schema, adr-doctor
task test   # pytest across all harness-independent suites
task fmt    # auto-fix markdown + Python formatting
```

The `Taskfile.yaml` `vars` block lists exactly which markdown, JSON, and test
paths are gated. Behavioral evals (`dev-flow/evals`, `jj/evals`) need the Claude
agent harness to execute, so they are schema-validated in `lint` but never run.

Run the underlying commands directly when touching only part of the repo, but
verify the relevant surface before claiming completion.

### Release Versioning

Releases are managed by **release-please** (`.github/workflows/release.yaml`,
push-triggered on `main`). Merging conventional-commit PRs maintains a **release
PR** that bumps a single repo-wide version in `.release-please-manifest.json`,
the `$.version` of the source plugin manifests (`.claude-plugin/marketplace.json`,
`homelab/plugin.json`, `jj/plugin.json`, `dev-flow/plugin.json`) via the
`extra-files` in `release-please-config.json`, and `CHANGELOG.md`. Merging that
release PR creates the `vX.Y.Z` tag and the GitHub Release.

It is **one repo-wide version line** (a single `.` package). Claude Code and
Codex resolve installs by git commit SHA; the in-file `version` fields + tag are
the human-facing markers, kept in sync automatically by release-please — do not
bump them by hand.

There is no local release command and no `cog`. PR titles are validated as
conventional commits by the commit-lint workflow
(`.github/workflows/commit-lint.yaml`, `amannn/action-semantic-pull-request`) —
the same squash-merged titles release-please reads to compute the bump.

The release-please GitHub App (`RELEASE_PLEASE_APP_ID` /
`RELEASE_PLEASE_PRIVATE_KEY`, defined org-wide) performs the release-PR / tag /
Release writes and must be a bypass actor on the protect-`main` ruleset.

> See ADR `fhsk-dgo`, which supersedes `fhsk-toy` (tag-only cog, no commit to
> main) and `fhsk-7y4` (no in-file versions).

### MCP Servers

Repo-level MCP servers are declared in `.mcp.json`:

- `context7`
- `terraform`

Codex wrapper plugins may expose these via symlinks or manifest paths, but the
source configuration remains repo-rooted.

## Cross-Platform Guidance

### Claude and Codex

- Claude installs from `.claude-plugin/marketplace.json` and the source plugin
  directories.
- Codex uses `.agents/plugins/marketplace.json` and the thin wrappers in
  `plugins/`.
- Do not duplicate skill trees across the Claude and Codex layers.

### Agent Dispatch

Some workflows, especially the `dev-flow` review orchestrators, were authored
for Claude-style named subagents. In Codex, use the compatibility guidance in:

`dev-flow/skills/using-superpowers/references/codex-tools.md`

That guidance explains how to map named agent dispatch to `spawn_agent`
workflows while reusing the existing prompt files.

## Gotchas

### Worktree Layout

Agent worktrees use a sibling directory layout:

```text
<repo>/
<repo>_worktrees/
  <worktree-name>/
```

Do not manually invent nested worktree repos under the main checkout.

### jj Rule

When `jj root` succeeds, treat the repo as a jj repo even if `.git/` also
exists. Use jj for mutating VCS operations.

- Allowed git usage: read-only commands such as `git log`, `git diff`,
  `git rev-parse`
- Disallowed when jj is present: `git commit`, `git checkout`,
  `git worktree add`, `git merge`, `git push`

### Session Completion

Work is not complete until the relevant changes are committed and pushed.

Required sequence:

1. File follow-up beads for leftover work
2. Run quality gates for the changed surface
3. Update or close the related bead
4. Push Git or jj changes
5. If a Dolt remote is configured, run `bd dolt push`
6. Verify final state with `git status` or `jj st`
7. Hand off concise context for the next session

Never stop at "ready to push." Push the branch yourself when the workflow
expects it.

## Dev-Flow Conventions

For workflow-skill conventions covering spec/plan discipline, bead
lifecycle, model selection, and grounding tools, see
[`dev-flow/AGENTS.md`](dev-flow/AGENTS.md). Rules 1-7 there apply to
every `dev-flow` skill and review-gate agent.

## Claude-Specific Notes

### Claude Marketplace

Claude installs the source plugins from the repository marketplace rooted at:

```text
.claude-plugin/marketplace.json
```

The source plugin manifests live in:

- `homelab/plugin.json`
- `jj/plugin.json`
- `dev-flow/plugin.json`

### Claude Hook Behavior

Claude-specific hooks and settings live under `.claude/` when present.
Historically this repo has used Claude hooks for formatting and worktree
automation. If you are investigating Claude-only behavior, inspect:

- `.claude/settings.json`
- `.claude/hooks/`

These are Claude-specific implementation details, not the shared source of
truth for repo workflow rules.

### Claude-Specific Compatibility

Some older agent prompts and docs in this repo refer to `CLAUDE.md` for project
conventions. Keep this file present as a compatibility shim, but put general
repository rules in `AGENTS.md`.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses
`refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export.
See <https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md> for
details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:

   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```

5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
