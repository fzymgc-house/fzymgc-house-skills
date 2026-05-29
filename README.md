# fzymgc-house-skills

A [Claude Code](https://claude.ai/code) plugin marketplace for the fzymgc-house
self-hosted cluster. It currently ships four plugins: homelab operations,
automated PR review, jj workflow guidance, and a development-flow workflow
suite (originally forked from obra/superpowers, evolved independently). The
repo now also includes a repo-local Codex marketplace that wraps the same
skill content for Codex.

## Plugins

### homelab

Infrastructure skills for interacting with the homelab cluster.

| Skill | Description |
|-------|-------------|
| **grafana** | Grafana, Loki, and Prometheus operations — dashboards, logs, metrics, alerting, incidents, OnCall, profiling |
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

## Installation

### Claude Code

Add the marketplace, then install plugins by name:

```bash
claude plugin marketplace add fzymgc-house/fzymgc-house-skills
claude plugin install homelab@fzymgc-house-skills
claude plugin install jj@fzymgc-house-skills
claude plugin install dev-flow@fzymgc-house-skills
```

### Codex

Use the repo-local Codex marketplace at
`.agents/plugins/marketplace.json`. The `plugins/` directory contains thin
Codex wrappers that symlink back to the existing `homelab/`, `jj/`, and
`dev-flow/` directories so the underlying SKILL.md content remains
single-source.

Current Codex limitation: named Claude plugin agents are not installed
natively. The `dev-flow` review workflows still work in Codex,
but agent-dispatch steps must follow the compatibility guidance in
`dev-flow/skills/using-superpowers/references/codex-tools.md`.

## Development

### Prerequisites

- [lefthook](https://github.com/evilmartians/lefthook) (git hooks)
- [rumdl](https://github.com/rvben/rumdl) (markdown linting)
- [cocogitto](https://docs.cocogitto.io/) (conventional commit validation)
- [ruff](https://docs.astral.sh/ruff/) (Python linting/formatting)

### Setup

```bash
git clone git@github.com:fzymgc-house/fzymgc-house-skills.git
cd fzymgc-house-skills
lefthook install
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
    grafana/            # Grafana/Loki/Prometheus operations
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
```

### Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) format. This is enforced by a commit-msg hook via cocogitto.

```text
feat(grafana): add incident management support
fix(review-pr): correct agent dispatch for security aspect
docs: update README
```

### Versioning

Releases are cut with [cocogitto](https://docs.cocogitto.io/) (`cog`),
tag-only: a single repo-wide `vX.Y.Z` git tag plus a GitHub Release, derived
from conventional commits. There are no in-file version numbers — plugins are
versioned by git commit SHA. Cut a release with `task release:cut`. See the
"Release Versioning" section in `AGENTS.md`.

## License

Private repository for fzymgc-house infrastructure.
