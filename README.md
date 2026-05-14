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

### pr-review

Automated PR review workflow using 12 specialized agents with git worktree isolation for parallel execution.

**Skills** (orchestrators):

| Skill | Description |
|-------|-------------|
| **review-pr** | Dispatches up to 9 review agents in parallel, persists findings as beads |
| **address-findings** | Fix loop with worktree-isolated fix-workers, merge protocol, and review gates |
| **respond-to-comments** | GitHub PR comment management with bead-aware context |

**Agents** (dispatched by orchestrator skills):

| Agent | Role |
|-------|------|
| code-reviewer | Project guideline compliance and bug detection |
| silent-failure-hunter | Error handling and silent failure auditing |
| pr-test-analyzer | Test coverage quality and gap analysis |
| type-design-analyzer | Type invariant strength and encapsulation |
| comment-analyzer | Code comment accuracy and maintainability |
| security-auditor | OWASP-based security vulnerability detection |
| api-contract-checker | Breaking changes and backward compatibility |
| spec-compliance | Alignment with design docs and ADRs |
| code-simplifier | Clarity and maintainability improvements |
| fix-worker | Implements fixes in isolated worktrees |
| review-gate | Validates fixes address their findings |
| verification-runner | Runs quality gates after fixes are applied |

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

## Installation

### Claude Code

Add the marketplace, then install plugins by name:

```bash
claude plugin marketplace add fzymgc-house/fzymgc-house-skills
claude plugin install homelab@fzymgc-house-skills
claude plugin install pr-review@fzymgc-house-skills
claude plugin install jj@fzymgc-house-skills
claude plugin install dev-flow@fzymgc-house-skills
```

### Codex

Use the repo-local Codex marketplace at
`.agents/plugins/marketplace.json`. The `plugins/` directory contains thin
Codex wrappers that symlink back to the existing `homelab/`, `pr-review/`,
`jj/`, and `dev-flow/` directories so the underlying SKILL.md content
remains single-source.

Current Codex limitation: named Claude plugin agents are not installed
natively. `pr-review` and some `dev-flow` workflows still work in Codex,
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
pr-review/
  plugin.json           # Plugin manifest
  agents/               # 12 agent definitions (YAML frontmatter + system prompt)
  skills/
    review-pr/          # Review orchestrator
    address-findings/   # Fix loop orchestrator
    respond-to-comments/  # PR comment management
jj/
  plugin.json           # Plugin manifest
  skills/
    jujutsu/            # Jujutsu workflow guidance
dev-flow/
  plugin.json           # Plugin manifest
  skills/
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

Versions are managed by [release-please](https://github.com/googleapis/release-please). Do not manually bump versions in `marketplace.json`, `plugin.json`, or SKILL.md files.

## License

Private repository for fzymgc-house infrastructure.
