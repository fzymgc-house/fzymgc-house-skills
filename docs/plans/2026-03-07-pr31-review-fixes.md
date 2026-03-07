# PR #31 Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 1 critical + 8 important + 8 suggestion findings from the PR #31 review.

**Architecture:** Fixes are grouped by file to minimize context switches. Shell script fixes come first (security/error handling), then documentation consistency fixes, then eval fixes.

**Tech Stack:** Bash shell scripts, Markdown (SKILL.md/agent .md files), JSON (evals)

---

## Task 1: Harden worktree-create.sh — input validation and jj guard

**Files:**

- Modify: `.claude/hooks/worktree-create.sh`

**Findings addressed:**

- [security/suggestion] NAME accepts path-traversal characters
- [errors/important] No guard for jj not installed when .jj/ detected

**Step 1: Add NAME validation after line 12**

Insert after the `NAME` empty check (line 10-13), before `REPO_ROOT`:

```bash
# Reject names with path-traversal or shell metacharacters
if [[ "$NAME" =~ [^a-zA-Z0-9_.-] || "$NAME" == *".."* ]]; then
  echo "ERROR: invalid worktree name '$NAME' (alphanumeric, dots, hyphens, underscores only)" >&2
  exit 1
fi
```

**Step 2: Add jj-not-installed guard inside the jj branch**

Replace the jj branch (line 22-25) with:

```bash
if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  (cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}")
else
```

**Step 3: Verify the script is syntactically valid**

Run: `bash -n .claude/hooks/worktree-create.sh`
Expected: no output (clean parse)

**Step 4: Commit**

```bash
git add .claude/hooks/worktree-create.sh
git commit -m "fix(hooks): add input validation and jj guard to worktree-create"
```

---

### Task 2: Harden worktree-remove.sh — path validation and error handling

**Files:**

- Modify: `.claude/hooks/worktree-remove.sh`

**Findings addressed:**

- [security/important] rm -rf on unvalidated caller-supplied path
- [errors/important] jj workspace forget silently suppressed
- [simplify/suggestion] git rev-parse dependency for REPO_ROOT

**Step 1: Add path validation after WORKTREE_PATH is read**

After line 7 (`WORKTREE_PATH=...`), before the `-z` check, add the
REPO_ROOT derivation and prefix guard. Replace lines 7-27 with:

```bash
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.path // empty')

if [[ -z "$WORKTREE_PATH" || ! -d "$WORKTREE_PATH" ]]; then
  exit 0
fi

# Derive workspace name from path for jj
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")

# Detect repo root — try git first, fall back to path derivation
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$REPO_ROOT" ]]; then
  # Infer from worktree path: <root>_worktrees/<name> → <root>
  WORKTREE_PARENT=$(dirname "$WORKTREE_PATH")
  PARENT_BASE=$(basename "$WORKTREE_PARENT")
  REPO_ROOT="$(dirname "$WORKTREE_PARENT")/${PARENT_BASE%_worktrees}"
fi

# Validate path is inside the expected sibling directory
EXPECTED_PARENT="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")_worktrees"
case "$WORKTREE_PATH" in
  "$EXPECTED_PARENT"/*)  ;;  # safe — inside expected parent
  *)
    echo "ERROR: WORKTREE_PATH '$WORKTREE_PATH' is outside expected parent '$EXPECTED_PARENT'" >&2
    exit 1
    ;;
esac

if [[ -n "$REPO_ROOT" && -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — log errors instead of silently suppressing
  if ! (cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
    echo "WARNING: jj workspace forget failed for worktree-${WORKSPACE_NAME}" >&2
  fi
  rm -rf "$WORKTREE_PATH"
else
  # Standard git worktree cleanup
  git worktree remove --force "$WORKTREE_PATH" 2>/dev/null || true
fi
```

**Step 2: Verify the script is syntactically valid**

Run: `bash -n .claude/hooks/worktree-remove.sh`
Expected: no output (clean parse)

**Step 3: Commit**

```bash
git add .claude/hooks/worktree-remove.sh
git commit -m "fix(hooks): add path validation and improve jj error handling in worktree-remove"
```

---

### Task 3: Fix jj-init --colocate flag

**Files:**

- Modify: `jj/commands/jj-init.md`

**Findings addressed:**

- [code/important] jj git init missing --colocate flag on jj 0.15+

**Step 1: Update the init command**

In `jj/commands/jj-init.md`, replace lines 26-32:

```markdown
3. **Initialize colocated repo** — Run:

   ```bash
   jj git init --colocate

```text
   ```

   The `--colocate` flag ensures jj shares the working copy with git
   (required on jj 0.15+; harmless on older versions).

```text

**Step 2: Commit**

```bash
git add jj/commands/jj-init.md
git commit -m "fix(jj): add --colocate flag to jj git init command"
```

---

### Task 4: Fix eval B3 bookmark assertion

**Files:**

- Modify: `jj/evals/evals.json`

**Findings addressed:**

- [tests/critical] B3 assertion uses literal "-b OR --bookmark" which never matches

**Step 1: Fix the assertion**

Replace the `specifies-bookmark` assertion (lines 100-104). The
`output_contains` type matches a literal string, so `"-b OR --bookmark"`
will never match. Split into a single `-b` check (the short form is what
the skill teaches):

```json
        {
          "name": "specifies-bookmark",
          "description": "Includes -b flag for bookmark",
          "type": "output_contains",
          "check": "-b "
        }
```

Note the trailing space after `-b` to avoid false matches on other
flags.

**Step 2: Commit**

```bash
git add jj/evals/evals.json
git commit -m "fix(jj): fix eval B3 bookmark assertion to use literal -b flag"
```

---

### Task 5: Fix address-findings collect-results step (CHANGE_ID gap)

**Files:**

- Modify: `pr-review/skills/address-findings/SKILL.md:268-269`

**Findings addressed:**

- [comments/important] Collect results step omits CHANGE_ID for jj repos
- [code/important] Phase 4c review-gate prompt uses git-specific diff

**Step 1: Fix collect-results step**

Replace line 268-269:

```markdown
5. **Collect results** from each agent: STATUS, FILES_CHANGED,
   DESCRIPTION, WORKTREE_BRANCH (git) or CHANGE_ID (jj).
```

**Step 2: Fix Phase 4c review-gate prompt template**

Read lines 339-351 of address-findings/SKILL.md. The prompt template
says `<git diff of cherry-picked changes>`. Update to be VCS-agnostic:

```markdown
### Phase 4c: Review Gate

Dispatch a review-gate agent to validate fixes:

```text
subagent_type: "review-gate"
model: sonnet
prompt: |
  FINDING_IDS: <comma-separated>
  Review the following changes against the original findings.
  <VCS diff of integrated changes>
  Return per-finding: PASS | FAIL: <reason>
```
```


```text

**Step 3: Commit**

```bash
git add pr-review/skills/address-findings/SKILL.md
git commit -m "fix(pr-review): add CHANGE_ID to collect-results and fix Phase 4c VCS reference"
```

---

### Task 6: Fix agent vcs-equivalence.md reference path

**Files:**

- Modify: all 11 worktree-isolated agent .md files in `pr-review/agents/`

**Findings addressed:**

- [spec/important] Agents reference `references/vcs-equivalence.md` — path won't resolve from worktree CWD

**Step 1: Understand the issue**

Agents run in worktrees rooted at the repo root. The file is at
`pr-review/references/vcs-equivalence.md`. The current reference says
`references/vcs-equivalence.md` which would only resolve if CWD is
`pr-review/`.

However, agent .md files are loaded by the Claude Code framework — the
`references/` path is a *documentation reference for the agent to
read*, not a runtime file path. The agent is told to "Consult
`references/vcs-equivalence.md`" but its actual CWD is the repo root.

Fix by using the full relative path from repo root.

**Step 2: Update all 11 agents**

For each of these files, change `references/vcs-equivalence.md` to
`pr-review/references/vcs-equivalence.md`:

- `pr-review/agents/code-reviewer.md`
- `pr-review/agents/silent-failure-hunter.md`
- `pr-review/agents/pr-test-analyzer.md`
- `pr-review/agents/type-design-analyzer.md`
- `pr-review/agents/comment-analyzer.md`
- `pr-review/agents/security-auditor.md`
- `pr-review/agents/api-contract-checker.md`
- `pr-review/agents/spec-compliance.md`
- `pr-review/agents/code-simplifier.md`
- `pr-review/agents/fix-worker.md`
- `pr-review/agents/verification-runner.md`

Each file has one occurrence on line 29:

```text
`references/vcs-equivalence.md` → `pr-review/references/vcs-equivalence.md`
```

**Step 3: Commit**

```bash
git add pr-review/agents/*.md
git commit -m "fix(pr-review): use full relative path for vcs-equivalence.md in agents"
```

---

### Task 7: Fix review-gate.md — VCS-agnostic diff reference

**Files:**

- Modify: `pr-review/agents/review-gate.md:50`

**Findings addressed:**

- [spec/suggestion] review-gate Process still says "git diff"

**Step 1: Update line 50**

Change:

```text
2. Examine the git diff for changes related to that finding
```

To:

```text
2. Examine the VCS diff for changes related to that finding
```

**Step 2: Commit**

```bash
git add pr-review/agents/review-gate.md
git commit -m "fix(pr-review): use VCS-agnostic language in review-gate process"
```

---

### Task 8: Fix fix-worker output — add VCS discriminator field

**Files:**

- Modify: `pr-review/agents/fix-worker.md:92-101`

**Findings addressed:**

- [api/important] fix-worker output has no VCS discriminator field

**Step 1: Update the output template**

Replace lines 92-101:

```markdown
```text
STATUS: FIXED | PARTIAL | FAILED
FINDING: <bead-id>
FILES_CHANGED: <file1>, <file2>, ...
DESCRIPTION: <one-line summary of what was changed>
VCS: git | jj
WORKTREE_BRANCH: <branch name>  (git repos only)
CHANGE_ID: <change-id>          (jj repos only)
```
```

Report `VCS: git` or `VCS: jj` based on the detected VCS, plus the
matching identifier field.

```text

**Step 2: Commit**

```bash
git add pr-review/agents/fix-worker.md
git commit -m "fix(pr-review): add VCS discriminator field to fix-worker output contract"
```

---

### Task 9: Reduce review-pr SKILL.md VCS cheat-sheet duplication

**Files:**

- Modify: `pr-review/skills/review-pr/SKILL.md:67-69`

**Findings addressed:**

- [simplify/suggestion] Inline VCS cheat-sheet partially duplicates vcs-equivalence.md

**Step 1: Replace the inline cheat-sheet**

Replace lines 67-69 with a reference-only approach:

```markdown
In jj repos, consult `pr-review/references/vcs-equivalence.md` for
command equivalents. Key: use `jj` commands for all VCS operations,
`gh` CLI for GitHub operations regardless of VCS.
```

**Step 2: Commit**

```bash
git add pr-review/skills/review-pr/SKILL.md
git commit -m "fix(pr-review): deduplicate VCS cheat-sheet in review-pr skill"
```

---

### Task 10: Update CLAUDE.md Worktree Layout gotcha

**Files:**

- Modify: `CLAUDE.md:164-179`

**Findings addressed:**

- [spec/suggestion] CLAUDE.md Worktree Layout omits jj-specific details

**Step 1: Expand the Worktree Layout section**

Replace lines 164-179:

```markdown
### Worktree Layout

Agent worktrees are created in a **sibling directory** to avoid nesting
repos (which confuses LSP servers):

```text
<repo>/                    # main repo
<repo>_worktrees/          # worktree parent (sibling)
  fix-worker-abc/          # one worktree per agent invocation
  verification-runner-def/
```
```

WorktreeCreate/WorktreeRemove hooks in `.claude/settings.json` handle
this automatically. In jj repos, hooks use `jj workspace add/forget`
instead of `git worktree add/remove`. Do NOT manually create worktrees
inside `.claude/worktrees/`.

**VCS-specific behavior:**

- **git**: fix-worker reports `WORKTREE_BRANCH`; orchestrator uses cherry-pick to integrate
- **jj**: fix-worker reports `CHANGE_ID`; orchestrator uses `jj rebase` to integrate (no cherry-pick)

```text

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: expand CLAUDE.md worktree layout with jj-specific details"
```

---

### Task 11: Add missing eval coverage (suggestion-level)

**Files:**

- Modify: `jj/evals/evals.json`

**Findings addressed:**

- [tests/important] No evals for jj-not-installed or workspace collision edge cases
- [tests/suggestion] Missing /jj-init edge case evals

**Step 1: Add new behavioral evals**

Add these after B5 in the evals array:

```json
    {
      "id": "B6",
      "type": "behavioral",
      "skill": "jujutsu",
      "prompt": "create a jj workspace with the same name as an existing one (in a jj repo)",
      "expected_output": "Should detect the naming collision and either use a unique name or report the conflict",
      "assertions": [
        {
          "name": "handles-collision",
          "description": "Handles workspace name collision gracefully",
          "type": "manual",
          "check": "Verify the agent detects or handles workspace name collision"
        }
      ]
    },
    {
      "id": "B7",
      "type": "behavioral",
      "skill": "jujutsu",
      "prompt": "initialize jj in this repo (repo already has .jj/ directory)",
      "expected_output": "Should detect existing .jj/ and inform user that jj is already initialized",
      "assertions": [
        {
          "name": "detects-existing",
          "description": "Detects existing jj initialization",
          "type": "output_contains",
          "check": "already"
        }
      ]
    }
```

**Step 2: Commit**

```bash
git add jj/evals/evals.json
git commit -m "test(jj): add evals for workspace collision and already-initialized edge cases"
```

---

### Task 12: Final verification

**Step 1: Run markdown linter on all changed files**

```bash
rumdl check .claude/hooks/worktree-create.sh .claude/hooks/worktree-remove.sh
rumdl check jj/commands/jj-init.md
rumdl check pr-review/agents/*.md
rumdl check pr-review/skills/address-findings/SKILL.md
rumdl check pr-review/skills/review-pr/SKILL.md
rumdl check CLAUDE.md
```

**Step 2: Validate JSON**

```bash
python3 -m json.tool jj/evals/evals.json > /dev/null
```

**Step 3: Validate shell scripts**

```bash
bash -n .claude/hooks/worktree-create.sh
bash -n .claude/hooks/worktree-remove.sh
```

**Step 4: Run lefthook pre-commit on all changed files**

```bash
lefthook run pre-commit --all-files
```

Expected: all checks pass.
