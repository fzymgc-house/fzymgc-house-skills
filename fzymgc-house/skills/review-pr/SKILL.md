---
name: review-pr
description: >-
  Comprehensive PR review using specialized subagents. Use when the user asks to
  "review this PR", "check my PR", "review code quality", "run PR review",
  "analyze this pull request", or invokes /review-pr. Launches targeted review
  agents for code quality, error handling, test coverage, type design, comments,
  security, API compatibility, spec compliance, and code simplification.
argument-hint: "[aspects: all|code|errors|tests|types|comments|security|api|spec|simplify]"
allowed-tools:
  - Task
  - Read
  - Grep
  - Glob
  - "Bash(git diff *)"
  - "Bash(git log *)"
  - "Bash(git status)"
  - "Bash(git status *)"
  - "Bash(git show *)"
  - "Bash(git branch *)"
  - "Bash(git branch)"
  - "Bash(git worktree list)"
  - "Bash(git worktree list *)"
  - "Bash(git ls-files *)"
  - "Bash(git rev-parse *)"
  - "Bash(git merge-base *)"
  - "Bash(gh pr view *)"
  - "Bash(gh pr diff *)"
  - "Bash(gh pr list *)"
  - "Bash(gh pr checks *)"
metadata:
  author: fzymgc-house
  version: 0.1.0
  based-on: >-
    anthropics/claude-plugins-official pr-review-toolkit
    (https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit)
    — original 6 agents adapted from plugin format to skill references,
    plus 3 new agents (security-auditor, api-contract-checker, spec-compliance)
---

# Comprehensive PR Review

Launch specialized review subagents against the current branch's changes.
Each subagent focuses on one dimension of code quality and returns an
independent report. Results are aggregated into a prioritized action plan.

## Review Aspects

| Aspect | Subagent | Focus |
|--------|----------|-------|
| `code` | code-reviewer | Project guidelines, bugs, CLAUDE.md compliance |
| `errors` | silent-failure-hunter | Silent failures, catch blocks, error logging |
| `tests` | pr-test-analyzer | Test coverage quality, critical gaps |
| `types` | type-design-analyzer | Type encapsulation, invariants |
| `comments` | comment-analyzer | Comment accuracy, documentation rot |
| `security` | security-auditor | OWASP, secrets, auth, injection, IaC perms |
| `api` | api-contract-checker | Breaking changes, backward compat, schemas |
| `spec` | spec-compliance | Design doc/ADR/requirements alignment |
| `simplify` | code-simplifier | Clarity, redundancy, maintainability |

Default: `all` (run every applicable aspect).

## Quick Checklist

- [ ] Determine scope (parse arguments, gather git diff)
- [ ] Select applicable agents based on changes and requested aspects
- [ ] Choose model per agent (sonnet default, opus for complex/security)
- [ ] Read agent prompts from `references/`
- [ ] Launch subagents via Task tool (parallel for `all`, sequential for single)
- [ ] Aggregate results from `$REVIEW_DIR/*.md` into unified summary, then clean up

## Workflow

### 1. Determine Scope

Parse `$ARGUMENTS` for requested aspects. If blank or `all`, run all aspects.

Create an isolated temp directory for this review session:

```bash
REVIEW_DIR=$(mktemp -d /tmp/review-pr-XXXXXXXX)
```

All agents write their reports into this directory. Pass the full
`$REVIEW_DIR` path to each subagent.

Gather context:

```bash
git diff --name-only          # changed files
git diff --stat               # change summary
gh pr view --json title,body  # PR metadata (if PR exists)
```

### 2. Select Applicable Agents

Based on changes and requested aspects:

- **Always applicable**: `code` (general quality)
- **If test files changed or `tests` requested**: `tests`
- **If comments/docstrings added or `comments` requested**: `comments`
- **If error handling changed or `errors` requested**: `errors`
- **If types added/modified or `types` requested**: `types`
- **Always applicable**: `security` (security audit)
- **If public interfaces changed or `api` requested**: `api`
- **If spec/design docs exist or `spec` requested**: `spec`
- **After other reviews pass or `simplify` requested**: `simplify`

When `all` is requested, run every agent regardless of file heuristics.

### 3. Choose Model Per Agent

Assess the diff to assign `sonnet` or `opus` to each subagent via the
Task tool's `model` parameter.

**Use `opus` when any of these apply:**

- Diff exceeds ~300 lines changed
- Security-sensitive code (auth, crypto, permissions, secrets)
- Complex type design or architectural changes
- Multiple languages or cross-cutting concerns

**Use `sonnet` (default) otherwise** — faster and sufficient for
straightforward reviews.

| Agent | Default | Upgrade to opus when |
|-------|---------|----------------------|
| code-reviewer | sonnet | Large diff, security code |
| silent-failure-hunter | sonnet | Complex error flows, auth code |
| pr-test-analyzer | sonnet | Large test surface, async code |
| type-design-analyzer | opus | Always — nuanced reasoning |
| comment-analyzer | sonnet | Rarely needs opus |
| security-auditor | opus | Always — security requires rigor |
| api-contract-checker | sonnet | Many public interfaces changed |
| spec-compliance | sonnet | 2+ design docs found, or architectural changes |
| code-simplifier | sonnet | Rarely needs opus |

### 4. Load Agent Prompts

Read the system prompt for each selected agent from `references/`:

- `references/agent-code-reviewer.md`
- `references/agent-silent-failure-hunter.md`
- `references/agent-pr-test-analyzer.md`
- `references/agent-type-design-analyzer.md`
- `references/agent-comment-analyzer.md`
- `references/agent-security-auditor.md`
- `references/agent-api-contract-checker.md`
- `references/agent-spec-compliance.md`
- `references/agent-code-simplifier.md`

### 5. Launch Subagents

Use the `Task` tool to launch each selected agent. Each agent writes its
detailed report to a temp file and returns only a terse summary.

**Output convention**: `$REVIEW_DIR/<aspect>.md`
(e.g. `$REVIEW_DIR/code.md`, `$REVIEW_DIR/errors.md`)

Each Task call should:

1. Set the `model` parameter per the routing decision from step 3
2. Include the git diff or changed file contents as context
3. Include the full system prompt from the reference file
4. Instruct the agent to write detailed findings to `$REVIEW_DIR/<aspect>.md`
5. Instruct the agent to return only a 2-3 line summary (issue counts + critical items)

**Parallel execution** (default for `all`): Launch all agents simultaneously
using multiple Task tool calls in a single message.

**Sequential execution**: When a specific aspect is requested alone, launch
one agent at a time for interactive review.

### 6. Aggregate Results

Read the report files from `$REVIEW_DIR/*.md` to compile the unified report.
Delete the temp directory after aggregation: `rm -rf $REVIEW_DIR`.

```markdown
# PR Review Summary

## Critical Issues (must fix before merge)

- [agent]: Issue description [file:line]

## Important Issues (should fix)

- [agent]: Issue description [file:line]

## Suggestions (nice to have)

- [agent]: Suggestion [file:line]

## Strengths

- What's well-done in this PR

## Recommended Action

1. Fix critical issues first
2. Address important issues
3. Consider suggestions
4. Re-run review after fixes
```

## Usage Examples

```bash
# Full review (all aspects)
/review-pr

# Specific aspects
/review-pr code errors
/review-pr tests
/review-pr simplify

# Review with PR number context
/review-pr all
```

## Tips

- Run before creating the PR, not after
- Address critical issues before lower priority
- Re-run targeted reviews after fixes to verify
- The `simplify` aspect works best after other issues are resolved
