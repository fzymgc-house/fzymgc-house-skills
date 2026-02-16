---
name: review-pr
description: >-
  Comprehensive PR review using specialized subagents. Use when the user asks to
  "review this PR", "check my PR", "review code quality", "run PR review",
  "analyze this pull request", or invokes /review-pr. Launches targeted review
  agents for code quality, error handling, test coverage, type design, comments,
  security, API compatibility, spec compliance, and code simplification.
argument-hint: "PR# [aspects: all|code|errors|tests|types|comments|security|api|spec|simplify]"
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
  - "Bash(gh pr comment *)"
  - "Bash(gh api *)"
  - "Bash(bd create *)"
  - "Bash(bd list *)"
  - "Bash(bd update *)"
  - "Bash(bd show *)"
  - "Bash(bd dep *)"
  - "Bash(bd query *)"
  - "Bash(bd config *)"
metadata:
  author: fzymgc-house
  version: 0.3.0
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

- [ ] Determine scope (parse PR number + aspects, check for existing review bead)
- [ ] Select applicable agents based on changes and requested aspects
- [ ] Choose model per agent (sonnet default, opus for complex/security)
- [ ] Read agent prompts from `references/`
- [ ] Create PR review parent bead (or find existing for re-review)
- [ ] Launch subagents via Task tool (batched, max 3 concurrent)
- [ ] Aggregate results from beads into unified summary
- [ ] Offer to post findings as PR comment (confirm with user first)

## Workflow

### 0. Prerequisites

Verify `bd` is available: run `bd --version`. If it fails, stop and
tell the user: "beads CLI (`bd`) is required but not found. Install
beads and run `bd init` in the target project."

### 1. Determine Scope

Parse `$ARGUMENTS`:

- **First token**: PR number (required). Use for `gh pr view <number>`
  and `gh pr diff <number>` to get the review context.
- **Remaining tokens**: Requested aspects. If blank or `all`, run all.

Check for an existing PR review bead:

```bash
bd list --labels "pr-review,pr:<number>" --json
```

**First review** (no bead found): Create the PR review parent bead:

```bash
bd create "Review: PR #<number> — <title>" \
  --type task \
  --labels "pr-review,pr:<number>,turn:1" \
  --external-ref "https://github.com/{owner}/{repo}/pull/<number>" \
  --description "<PR body summary>" \
  --parent <epic-id> \
  --silent
```

The `--parent` flag is only included if an epic is found for this PR.

**Re-review** (bead found): This is turn N+1. Read the existing bead ID
and increment the turn label.

Gather PR context:

```bash
gh pr diff <number>                    # PR diff
gh pr view <number> --json title,body  # PR metadata
```

Optionally fetch GitHub review comments for supplementary context:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments
gh api repos/{owner}/{repo}/pulls/<number>/reviews
```

Beads are the primary source for prior findings; GitHub comments are
supplementary.

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

Use the `Task` tool to launch each selected agent. Each agent creates
finding beads directly via `bd create` and returns only a terse summary.

**Bead schema**: Each subagent creates finding beads with type, priority,
labels (`aspect:*`, `severity:*`, `turn:*`), external-ref (PR URL), and
description (full details + location + suggested fix).

Each Task call should:

1. Set the `model` parameter per the routing decision from step 3
2. Include the git diff or changed file contents as context
3. Include the full system prompt from the reference file
4. Pass `PARENT_BEAD_ID`, `ASPECT`, `TURN`, `PR_URL` variables
5. Instruct the agent to create beads directly and return a 2-3 line summary

**Batched parallel execution** (default for `all`): Launch agents in
batches of **at most 3 concurrent** Task tool calls per message. Wait for
each batch to complete before launching the next. Order batches by
priority — run `security` and `code` in the first batch when possible.

**Sequential execution**: When a specific aspect is requested alone, launch
one agent at a time for interactive review.

### 6. Aggregate Results

Query all findings from beads:

```bash
bd list --parent <parent-bead-id> --status open --json
```

Group findings by severity label. Compile the unified report and present
to the user:

```markdown
# PR Review Summary

## Critical Issues (must fix before merge)

- [aspect]: description [location]

## Important Issues (should fix)

- [aspect]: description [location]

## Suggestions (nice to have)

- [aspect]: description [location]

## Strengths

- [aspect]: description [location]

## Recommended Action

1. Fix critical issues first
2. Address important issues
3. Consider suggestions
4. Re-run review after fixes
```

The `aspect` label comes from the bead's `aspect:*` label. The `severity`
label determines which section each finding appears in.

### 7. Offer to Post Findings

After presenting the summary, ask the user whether to post the review
findings as a single comment on the PR. **Do NOT post without explicit
user confirmation.**

If confirmed, write the comment to a temp file and post:

```bash
gh pr comment <number> --body-file /tmp/pr-review-comment.md
```

Use this comment template:

````markdown
<!-- pr-review:<bead-id> -->
## <bead-id> — PR Review

`bd list --parent <bead-id> --status open`

N critical · N important · N suggestions

---

### Critical

**Finding title** `<finding-bead-id>`
Up to two lines of summary describing the issue,
its location, and the recommended fix.

### Important

**Finding title** `<finding-bead-id>`
Summary.

### Suggestions

**Finding title** `<finding-bead-id>`
Summary.
````

Every finding is listed. Each gets a bold title with bead ID, plus up to
2 lines of summary (max 3 lines total per finding). Grouped by severity.
The HTML comment marker `<!-- pr-review:<bead-id> -->` enables machine
detection of prior review comments.

## Usage Examples

```bash
# Full review of PR #123 (all aspects)
/review-pr 123

# Specific aspects
/review-pr 123 code errors
/review-pr 123 tests
/review-pr 123 simplify

# Security-focused review
/review-pr 123 security
```

## Tips

- Run before creating the PR, not after
- Address critical issues before lower priority
- Re-run targeted reviews after fixes to verify
- The `simplify` aspect works best after other issues are resolved
