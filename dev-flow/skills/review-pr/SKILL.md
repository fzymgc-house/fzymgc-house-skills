---
name: review-pr
description: >-
  Comprehensive PR review using specialized agents. Use when the user asks to
  "review this PR", "check my PR", "review code quality", "run PR review",
  "analyze this pull request", or invokes /review-pr. Launches targeted review
  agents for code quality, error handling, test coverage, type design, comments,
  security, API compatibility, spec compliance, and code simplification.
argument-hint: "PR# [aspects: all|code|errors|tests|types|comments|security|api|spec|simplify|slop]"
allowed-tools:
  - Task
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
  - "Bash(test *)"
  - "Bash(jj st *)"
  - "Bash(jj log *)"
  - "Bash(jj diff *)"
  - "Bash(jj show *)"
  - "Bash(jj file list *)"
  - "Bash(jj root)"
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
---

# Comprehensive PR Review

## Contents

- [VCS Detection](#vcs-detection)
- [Review Aspects](#review-aspects)
- [Workflow](#workflow)

## VCS Detection

Follow the procedure in `dev-flow/references/vcs-preamble.md` to
detect git vs jj and verify your location. Use `gh` CLI for GitHub
operations regardless of VCS.

Orchestrate specialized review agents against a PR's changes. Each agent
runs as an independent Task with its own system prompt, tools, and
isolation. Results are aggregated into a prioritized action plan.

## Review Aspects

| Aspect | Agent | Focus |
|--------|-------|-------|
| `code` | code-reviewer | Project guidelines, bugs, CLAUDE.md compliance |
| `errors` | silent-failure-hunter | Silent failures, catch blocks, error logging |
| `tests` | pr-test-analyzer | Test coverage quality, critical gaps |
| `types` | type-design-analyzer | Type encapsulation, invariants |
| `comments` | comment-analyzer | Comment accuracy, documentation rot |
| `security` | security-auditor | OWASP, secrets, auth, injection, IaC perms |
| `api` | api-contract-checker | Breaking changes, backward compat, schemas |
| `spec` | spec-compliance | Design doc/ADR/requirements alignment |
| `simplify` | code-simplifier | Clarity, redundancy, maintainability |
| `slop` | slop-hunter | AI-authorship tells in code and prose |

Default: `all` (run every applicable aspect).

## Workflow

### 1. Parse Input

Extract from `$ARGUMENTS`:

- **First token**: PR number (required).
- **Remaining tokens**: Requested aspects. If blank or `all`, run all applicable.

### 2. Check for Existing Review

```bash
bd list --label "pr-review,pr:<number>" --json
```

- **No bead found**: This is a first review (turn 1).
- **Open bead found**: This is turn N+1. Read the existing bead ID and
  increment the turn label.
- **Bead found but closed**: a prior review already reached PASS (or the PR
  merged) and the epic was reconciled. Start a fresh review — treat as turn 1
  and create a new epic in Step 6.

### 3. Gather PR Context

```bash
gh pr view <number> --json state,title,body
```

If this fails with a 404 or "not found" error, stop and tell the user:
"PR #N not found. Verify the number and try again."

If `state` is `MERGED` or `CLOSED`, do not review. Reconcile any open review
epic for this PR (close it per Step 12) and stop — there is nothing to gate on
a PR that has already left the review stage.

Then fetch the diff and changed file list:

```bash
gh pr diff <number>                  # full patch diff
gh pr diff <number> --name-only      # changed file names only
```

**`gh pr diff` only supports these flags:** `--color`, `--name-only`,
`--patch`, `--web`. There is NO `--stat` flag -- do not use it.
Use `--name-only` to get the list of changed files, or parse the
full diff output. For additions/deletions counts, use
`gh pr view <number> --json additions,deletions,changedFiles`.

Optionally fetch GitHub review comments for supplementary context:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments
```

### 4. Select Applicable Agents

| Condition | Agents |
|-----------|--------|
| Always | `code`, `security` |
| Test files changed OR `tests` requested | `tests` |
| Error handling changed OR `errors` requested | `errors` |
| Comments/docstrings added OR `comments` requested | `comments` |
| Types added/modified OR `types` requested | `types` |
| Public interfaces changed OR `api` requested | `api` |
| Spec/design docs exist OR `spec` requested | `spec` |
| After other reviews OR `simplify` requested | `simplify` |
| Code or prose added OR `slop` requested | `slop` |

When `all` is requested, run every agent regardless of file heuristics.

### 5. Model Escalation

Default: `sonnet`. Escalate to `opus` only when:

- The task is vague or under-specified with no clear precedent
- Novel architectural reasoning is required
- Crypto protocol design or complex threat modeling

| Agent | Default | Escalate to opus when |
|-------|---------|----------------------|
| code-reviewer | sonnet | Large diff (300+ lines) AND security code |
| silent-failure-hunter | sonnet | Complex error flows across many modules |
| pr-test-analyzer | sonnet | Rarely |
| type-design-analyzer | sonnet | Novel/ambiguous type design, no precedent |
| comment-analyzer | sonnet | Rarely |
| security-auditor | sonnet | Crypto, auth protocol, threat modeling |
| api-contract-checker | sonnet | Rarely |
| spec-compliance | sonnet | Vague spec with significant arch changes |
| code-simplifier | sonnet | Rarely |
| slop-hunter | sonnet | Rarely |

### 6. Create or Reuse Parent Bead

**First review**: Create the PR review parent epic bead:

```bash
bd create "Review: PR #<number> — <title>" \
  --type epic \
  --labels "pr-review,pr:<number>,turn:1" \
  --external-ref "https://github.com/{owner}/{repo}/pull/<number>" \
  --description "<PR body summary>" \
  --silent
```

**Re-review**: Use the existing bead ID and increment the turn label.

### 7. Launch Review Agents

Use the Task tool to dispatch each selected agent. Agents have their
own system prompts and tool definitions — do NOT construct inline
prompts or read reference files.

Each Task call:

- `subagent_type`: the agent name (e.g., `code-reviewer`, `security-auditor`)
- `model`: `sonnet` or `opus` per step 5
- `prompt`: Include the PR diff, plus these variables:
  `PARENT_BEAD_ID`, `TURN`, `PR_URL`, `ASPECT`. For the `slop-hunter` agent
  also pass `ACTIVE_ASPECTS`: the comma-separated aspect keys of all selected
  agents for this run (the left-column keys from step 4, e.g.
  `code,errors,comments,simplify`), excluding `slop` itself. It drives the
  agent's Rule B deferral.

**Batching**: Launch at most 3 concurrent Task calls per message.
Run `security` + `code` in the first batch. Wait for each batch to
complete before launching the next. `slop` depends on no other agent's
output; run it in the second batch.

**Sequential mode**: When a single aspect is requested, launch one
agent at a time for interactive review.

### 8. Aggregate Findings

```bash
bd list --parent <parent-bead-id> --status open --json
```

Group findings by their `severity:*` label. Then compute the **review verdict**
from the count of open must-fix findings (critical + important):

```bash
bd list --parent <parent-bead-id> --status open --json \
  | jq '[.[] | select(.labels[]? == "severity:critical"
                   or .labels[]? == "severity:important")] | length'
```

Deferred findings never appear in this count: when `/address-findings` defers a
finding it **closes** the finding in favour of an out-of-epic follow-up bead, so
it leaves the open set entirely.

- **0** → verdict is **✅ PASS** (`suggestion`-severity findings MAY remain open).
- **> 0** → verdict is **❌ CHANGES REQUESTED**.

### 9. Present Summary

Lead with the verdict line, then the findings grouped by severity:

```markdown
## Verdict: ✅ PASS   <!-- or: ❌ CHANGES REQUESTED -->

N critical · N important · N suggestions

## Critical Issues (must fix before merge)

- [aspect]: description [location]

## Important Issues (should fix)

- [aspect]: description [location]

## Suggestions (nice to have)

- [aspect]: description [location]

## Strengths

- [aspect]: description
```

### 10. Offer to Post

Ask the user whether to post findings as a PR comment. **Do NOT post
without explicit confirmation.**

If confirmed, write to a temp file and post:

```bash
gh pr comment <number> --body-file /tmp/pr-review-comment.md
```

Comment template:

````markdown
<!-- pr-review:<bead-id> -->
## <bead-id> — PR Review

N critical · N important · N suggestions

---

### Critical

**Finding title** `<finding-bead-id>`
Summary (2-3 lines max per finding).

### Important

**Finding title** `<finding-bead-id>`
Summary.

### Suggestions

**Finding title** `<finding-bead-id>`
Summary.
````

### 11. Report Verdict and Next Step

Report the verdict computed in Step 8 (open critical + important count):

- **❌ CHANGES REQUESTED** (count > 0): "❌ CHANGES REQUESTED — N must-fix
  finding(s). Run `/address-findings <number>` to resolve them with isolated
  fix-workers and review gates, then re-run `/review-pr <number>`."
- **✅ PASS** (count == 0): "✅ PASS — no open critical or important findings."
  If `suggestion`-severity findings remain, add "N suggestion(s) remain
  (optional)." Then **close the review epic** per Step 12.

This verdict is the gate consumed by `finishing-a-development-branch` Option 2:
that skill loops review → `/address-findings` → re-review until the verdict is
PASS before treating the PR as complete. Do not run `/address-findings`
automatically from here — report the verdict and let the caller drive the loop.

### 12. Close the Review Epic (on PASS or merged/closed PR)

The review epic is a transient tracker. Once the review is complete it MUST be
closed, or it orphans open in bd after the work is done. "Complete" means
either: the Step 11 verdict is ✅ PASS, or Step 3 found the PR already
`MERGED`/`CLOSED`.

1. Confirm the epic has no open children (deferred findings were already closed
   into out-of-epic follow-up beads by `/address-findings`, so they do not
   appear):

   ```bash
   bd list --parent <parent-bead-id> --status open --json | jq 'length'   # expect 0
   ```

   If this is > 0, the verdict is not PASS — do NOT close the epic; return to
   the fix loop instead.

2. Close the epic:

   ```bash
   # On PASS:
   bd close <parent-bead-id> --reason="Review complete — PASS (turn <N>)"
   # On a merged/closed PR (Step 3):
   bd close <parent-bead-id> --reason="PR #<number> merged/closed; review epic reconciled"
   ```

`finishing-a-development-branch` Step 5.5 also reconciles this epic at
integration time; both paths are idempotent — closing an already-closed epic is
a no-op.
