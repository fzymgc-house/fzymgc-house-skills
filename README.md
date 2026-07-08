# fzymgc-house-skills

A [Claude Code](https://claude.ai/code) plugin marketplace for the fzymgc-house
self-hosted cluster. It ships several plugins: homelab operations, jj
workflow guidance, a development-flow workflow suite (originally forked from
obra/superpowers, evolved independently), a tmux usage skill, and a grepping
search skill. The repo now also includes a repo-local Codex marketplace that
wraps the same skill content for Codex.

> **`memory-curator` has moved.** The memory plugin now lives in
> [seanb4t/engram](https://github.com/seanb4t/engram) as the `engram` bundled
> skill-plugin, co-located with the memory MCP server it drives. Install it via
> `/plugin marketplace add seanb4t/engram` → `/plugin install engram`. Its design
> history (spec/plan/ADRs) remains in this repo under `docs/`.

## Plugins

### homelab

Infrastructure skills for interacting with the homelab cluster.

| Skill | Description |
|-------|-------------|
| **terraform** | Terraform Cloud operations — runs, workspaces, state management, registry documentation |
| **skill-qa** | Validates SKILL.md files against Claude Code best practices |

### jj

Jujutsu workflow guidance for colocated and standalone repositories.

| Skill | Description |
|-------|-------------|
| **jujutsu** | Core jj workflows, git interop, bookmarks, and workspace guidance |

### dev-flow

Development workflow skills with git and jj support. Originally derived
from [obra/superpowers](https://github.com/obra/superpowers) v5.0.7 and
evolved independently for this repository (first-class jj support, bead
integration, ADR capture).

Highlights:

| Skill | Description |
|-------|-------------|
| **using-superpowers** | Entry skill that enforces skill discovery and platform adaptation |
| **brainstorming** | Design workflow before implementation |
| **writing-plans** / **executing-plans** | Plan-driven implementation workflow |
| **systematic-debugging** | Structured debugging workflow |
| **verification-before-completion** | Verification gate before claiming success |

See [`dev-flow/skills/`](dev-flow/skills/) for the complete skill
list — additional skills cover worktrees, parallel agents, code review,
TDD, and skill authoring.

#### PR review workflow

dev-flow also includes an automated PR review workflow using specialized
agents with worktree isolation for parallel execution.

| Skill | Description |
|-------|-------------|
| **review-pr** | Dispatches up to 10 review agents in parallel, persists findings as beads |
| **address-findings** | Fix loop with worktree-isolated fix-workers, merge protocol, and review gates |
| **respond-to-comments** | GitHub PR comment management with bead-aware context |

Review/fix agents (dispatched by the orchestrators): `code-reviewer`,
`silent-failure-hunter`, `pr-test-analyzer`, `type-design-analyzer`,
`comment-analyzer`, `security-auditor`, `api-contract-checker`,
`spec-compliance`, `code-simplifier`, `slop-hunter`, `fix-worker`,
`review-gate`, `verification-runner`.

### tmux

Terminal-multiplexer usage skill for scripting and agent automation.

| Skill | Description |
|-------|-------------|
| **tmux** | Spawn and drive tmux sessions, windows, and panes; capture pane output |

### grepping

Shell code/text search skill. Two advisory hooks nudge toward `rg` / `ast-grep`
over grep-family tools (PreToolUse) and flag common `rg` mistakes (PostToolUse).

| Skill | Description |
|-------|-------------|
| **grepping** | ripgrep (`rg`), ast-grep (`sg`), and grep-family → rg translation |

## Installation

### Claude Code

Add the marketplace, then install plugins by name:

```bash
claude plugin marketplace add fzymgc-house/fzymgc-house-skills
claude plugin install homelab@fzymgc-house-skills
claude plugin install jj@fzymgc-house-skills
claude plugin install dev-flow@fzymgc-house-skills
claude plugin install tmux@fzymgc-house-skills
claude plugin install grepping@fzymgc-house-skills
```

### Codex

Use the repo-local Codex marketplace at
`.agents/plugins/marketplace.json`. The `plugins/` directory contains thin
Codex wrappers that symlink back to the existing `homelab/`, `jj/`,
`dev-flow/`, `tmux/`, and `grepping/` directories so the underlying SKILL.md
content remains single-source.

Current Codex limitation: named Claude plugin agents are not installed
natively. The `dev-flow` review workflows still work in Codex,
but agent-dispatch steps must follow the compatibility guidance in
`dev-flow/skills/using-superpowers/references/codex-tools.md`.

## Development

### Prerequisites

- [Task](https://taskfile.dev/) (task runner — wraps the quality gates)
- [rumdl](https://github.com/rvben/rumdl) (markdown linting)
- [ruff](https://docs.astral.sh/ruff/) (Python linting/formatting)
- [uv](https://docs.astral.sh/uv/) (runs the Python test suites)

### Setup

```bash
git clone git@github.com:fzymgc-house/fzymgc-house-skills.git
cd fzymgc-house-skills

# There is no pre-commit hook manager — jj does not fire git hooks reliably.
# Run the gates manually (the same tasks CI runs):
task fmt    # auto-format markdown + Python before committing
task lint   # markdown, Python, JSON, evals, ADR gates
task test   # all harness-independent test suites
```

Repo-wide agent guidance lives in `AGENTS.md`. `CLAUDE.md` remains in the
repo as a Claude-specific addendum and compatibility shim.

### Repository Structure

```text
AGENTS.md
  ...                  # Canonical cross-platform agent instructions
CLAUDE.md
  ...                  # Claude-specific addendum and compatibility shim
.claude-plugin/
  marketplace.json      # Claude marketplace manifest listing the source plugins
.agents/plugins/
  marketplace.json      # Codex marketplace manifest listing wrapper plugins
plugins/
  <plugin-name>/
    .codex-plugin/plugin.json  # Codex wrapper manifest
    ...symlinks into source plugin content
homelab/
  plugin.json           # Plugin manifest
  skills/
    terraform/          # Terraform Cloud operations
    skill-qa/           # SKILL.md validation
jj/
  plugin.json           # Plugin manifest
  skills/
    jujutsu/            # Jujutsu workflow guidance
dev-flow/
  plugin.json           # Plugin manifest
  agents/               # workflow + review/fix/verification agents
  skills/
    review-pr/          # Review orchestrator
    address-findings/   # Fix loop orchestrator
    respond-to-comments/  # PR comment management
    ...                 # Workflow skills (originally from obra/superpowers v5.0.7)
tmux/
  plugin.json           # Plugin manifest
  skills/
    tmux/               # tmux usage skill
grepping/
  plugin.json           # Plugin manifest
  hooks/                # nudge-rg-over-grep, nudge-rg-failure (advisory)
  skills/
    grepping/           # rg / ast-grep / grep-family search skill
```

### Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/)
format, validated in CI by the commit-lint workflow
([`amannn/action-semantic-pull-request`](https://github.com/amannn/action-semantic-pull-request)).
The repo squash-merges, so the PR title is the commit that lands on `main`.

```text
feat(terraform): add workspace tag filtering
fix(review-pr): correct agent dispatch for security aspect
docs: update README
```

### Versioning

Releases are managed by [release-please](https://github.com/googleapis/release-please):
merging conventional-commit PRs maintains a release PR that bumps a single
repo-wide version (`.release-please-manifest.json`, the plugin/marketplace
`$.version` fields, and `CHANGELOG.md`); merging it cuts the `vX.Y.Z` tag and
GitHub Release. Claude Code and Codex resolve installs by git commit SHA — the
in-file `version` fields and tag are human-facing markers, kept in sync by
release-please. See the "Release Versioning" section in `AGENTS.md`.

## License

Private repository for fzymgc-house infrastructure.
