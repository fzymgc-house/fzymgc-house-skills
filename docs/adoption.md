# Adoption Guide

This is the canonical guide for adopting `fzymgc-house-skills` plugins and
skills in another org repo. `README.md` carries only a short pointer to this
document — the full install paths, the complete skill discovery index, and
troubleshooting live here.

## Claude install path

Add the marketplace, then install plugins by name:

```bash
claude plugin marketplace add fzymgc-house/fzymgc-house-skills
claude plugin install homelab@fzymgc-house-skills
claude plugin install jj@fzymgc-house-skills
claude plugin install dev-flow@fzymgc-house-skills
claude plugin install tmux@fzymgc-house-skills
claude plugin install grepping@fzymgc-house-skills
```

Install only the plugins you need — each is independent.

## Codex install path

Codex uses the repo-local marketplace manifest at
`.agents/plugins/marketplace.json`. The `plugins/` directory contains thin
Codex wrapper plugins (`.codex-plugin/plugin.json` + symlinks) that point
back at the same `homelab/`, `jj/`, `dev-flow/`, `tmux/`, and `grepping/`
source directories used by the Claude marketplace, so skill content stays
single-source — no duplication between the Claude and Codex layers.

Point your Codex marketplace config at this repo's
`.agents/plugins/marketplace.json` and install wrapper plugins by name, the
same way you would with Claude's `claude plugin install`.

## Discovery index

Every shipped skill, by plugin. This table is the enforced discovery
contract: `tests/test_skill_catalog.py` enumerates `*/skills/*/SKILL.md` on
disk and fails CI if a skill is missing from this index (or from the README
catalog).

### homelab

| Skill | Description |
|-------|-------------|
| **terraform** | Terraform Cloud operations and registry documentation lookup — runs, workspaces, state management, provider docs |
| **skill-qa** | Validates SKILL.md files against Claude Code skill best practices |
| **miniflux** | Manage and curate a personal Miniflux RSS subscription set — feeds, reading/triage, AI curation, health |

### jj

| Skill | Description |
|-------|-------------|
| **jujutsu** | Jujutsu (jj) VCS workflow guidance — activates on any VCS operation when `jj root` succeeds or `.jj/` exists |

### dev-flow

| Skill | Description |
|-------|-------------|
| **using-superpowers** | Entry skill that enforces skill discovery and platform adaptation |
| **brainstorming** | Design workflow before implementation — explores intent, requirements, and design |
| **writing-plans** | Turn a spec/requirements into a multi-step implementation plan before touching code |
| **executing-plans** | Execute a written implementation plan in a separate session with review checkpoints |
| **systematic-debugging** | Structured debugging workflow for any bug, test failure, or unexpected behavior |
| **verification-before-completion** | Verification gate before claiming work is complete, fixed, or passing |
| **test-driven-development** | Write a failing test first, then minimal code to pass, then refactor |
| **subagent-driven-development** | Execute implementation plans with independent tasks dispatched to subagents in-session |
| **dispatching-parallel-agents** | Dispatch parallel subagents for 2+ independent tasks with no shared state or ordering dependency |
| **using-worktrees** | Ensure an isolated workspace exists (native tools or git/jj fallback) before implementation work |
| **using-git-worktrees** | Alias/redirect to `using-worktrees` |
| **finishing-a-development-branch** | Decide how to integrate completed work (git or jj) — merge, PR, or cleanup |
| **requesting-code-review** | Request code review before merging, verifying work meets requirements (git and jj) |
| **receiving-code-review** | Apply code review feedback with technical rigor and verification, not performative agreement |
| **review-pr** | Comprehensive PR review using specialized agents (code, errors, tests, types, security, spec compliance...) |
| **address-findings** | Process findings from `review-pr` by working through beads in the review epic |
| **respond-to-comments** | Manage GitHub PR review comments — list, respond to, or address reviewer feedback |
| **solving-a-bead** | Solve a specific bead/issue by ID — isolated workspace, problem/fix separation, TDD-driven solution |
| **plan-to-beads** | Materialize an implementation plan's task table into bd issues, dependency edges, and parent links |
| **bead-create-smart** | Create a tracked bd issue via structured flags for ad-hoc beads outside the plan-to-beads flow |
| **draining-beads** | Autonomously drain an epic/set/cascade of beads via Claude Code's `/goal`, paired with `/drain` |
| **drain-with-worker** | Launch an autonomous `/drain` worker in a detached cmux/tmux surface with a surface-aware watchdog |
| **handoff-prompt** | Generate a self-contained briefing prompt for a fresh agent session to pick up a bead's work |
| **capture-adrs** | Extract ADR-worthy decisions from a finalized spec/plan into docs/adr/ files and bd decision records |
| **evolve-adr** | Update, supersede, deprecate, or migrate an ADR; bd is the source of truth for ADR content |
| **writing-skills** | Create, edit, or verify skills before deployment |

Review/fix agents dispatched by the `review-pr` / `address-findings`
orchestrators (not directly invocable as skills): `code-reviewer`,
`silent-failure-hunter`, `pr-test-analyzer`, `type-design-analyzer`,
`comment-analyzer`, `security-auditor`, `api-contract-checker`,
`spec-compliance`, `code-simplifier`, `slop-hunter`, `fix-worker`,
`review-gate`, `verification-runner`.

### tmux

| Skill | Description |
|-------|-------------|
| **tmux** | Spawn and drive tmux sessions, windows, and panes; capture pane output; detection and lifecycle |

### grepping

| Skill | Description |
|-------|-------------|
| **grepping** | ripgrep (`rg`), ast-grep (`sg`), and grep-family → rg translation; two advisory hooks nudge toward `rg`/`ast-grep` and flag common `rg` mistakes |

## Troubleshooting

### Codex: named-agent dispatch is not native

Codex does not install named Claude plugin agents natively. The `dev-flow`
review workflows (`review-pr`, `address-findings`, `respond-to-comments`)
still work in Codex, but any step that dispatches a named agent (the `Task`
tool in Claude) must follow the compatibility guidance in
[`dev-flow/skills/using-superpowers/references/codex-tools.md`](../dev-flow/skills/using-superpowers/references/codex-tools.md),
which maps Claude's `Task`/`TodoWrite`/`Skill` tool calls to Codex's
`spawn_agent`/`wait_agent`/`close_agent`/`update_plan` equivalents. Dispatching
parallel agents in Codex additionally requires `multi_agent = true` under
`[features]` in `~/.codex/config.toml`.

### A skill is missing from this index or the README

That is a CI-caught bug, not a doc-maintenance task you need to do by hand:
`tests/test_skill_catalog.py` enumerates every `*/skills/*/SKILL.md` on disk
and fails `task test` if a skill dir is missing from either this index or the
README `## Plugins` catalog. If you add a skill and see this test fail, add
the missing `**<skill-name>**` row to both surfaces.
