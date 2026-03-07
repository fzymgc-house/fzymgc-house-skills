# PR #31 Review Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 30 deduplicated findings from the PR #31 review (epic `fzymgc-house-skills-g13`).

**Architecture:** Changes grouped by file/area to minimize context switches. Shell hook fixes first (critical path), then agent/skill doc fixes, then eval fixes, then test coverage. Each task is independently committable.

**Tech Stack:** Bash (shell hooks), Markdown (skills/agents), JSON (evals), BATS (tests)

**Findings map:** 38 raw → 8 closed (3 won't-fix, 5 duplicates) → 30 to fix across 10 tasks.

---

## Task 1: Fix worktree-remove.sh (Critical + Important)

**Closes:** g13.9, g13.14, g13.16, g13.11

**Files:**

- Modify: `.claude/hooks/worktree-remove.sh`
- Modify: `.claude/hooks/worktree-create.sh`

**Step 1: Add `command -v jj` guard to worktree-remove.sh (g13.9)**

In `.claude/hooks/worktree-remove.sh`, replace the jj branch (lines 39-44) with:

```bash
if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — verify jj is installed first
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed — cannot forget workspace" >&2
    # Still remove the directory since it's just a workspace copy
    rm -rf "$WORKTREE_PATH"
  elif ! (cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
    echo "WARNING: jj workspace forget failed for worktree-${WORKSPACE_NAME}" >&2
    rm -rf "$WORKTREE_PATH"
  else
    rm -rf "$WORKTREE_PATH"
  fi
```

Note: Unlike worktree-create (which must fail hard), worktree-remove should still clean up the directory even if jj is missing.

**Step 2: Add `.`/`..` rejection to WORKSPACE_NAME validation (g13.14)**

In `.claude/hooks/worktree-remove.sh`, line 18, extend the validation:

```bash
if [[ "$WORKSPACE_NAME" =~ [^a-zA-Z0-9_.-] || "$WORKSPACE_NAME" == "." || "$WORKSPACE_NAME" == ".." || "$WORKSPACE_NAME" == *".."* ]]; then
```

**Step 3: Fix stderr redirect for git worktree remove (g13.16)**

In `.claude/hooks/worktree-remove.sh`, line 47, capture stderr properly:

```bash
  if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: git worktree remove failed for '$WORKTREE_PATH': $git_err" >&2
```

**Step 4: Add cleanup on jj workspace add failure (g13.11)**

In `.claude/hooks/worktree-create.sh`, wrap the jj workspace add call:

```bash
  if ! (cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}"); then
    echo "ERROR: jj workspace add failed" >&2
    [[ -d "$WORKTREE_PATH" ]] && rm -rf "$WORKTREE_PATH"
    [[ -d "$WORKTREE_PARENT" ]] && [[ -z "$(ls -A "$WORKTREE_PARENT")" ]] && rmdir "$WORKTREE_PARENT" 2>/dev/null
    exit 1
  fi
```

**Step 5: Fix comment "git hooks" → "hooks" in jj branch (g13.27)**

In `.claude/hooks/worktree-create.sh`, line 37, change:

```bash
  # Install hooks in the new workspace (lefthook works via .git/ in colocated repos)
```

**Step 6: Extract shared lefthook install block (g13.7)**

Move the lefthook block after the if/else so it runs once:

```bash
if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace ...
else
  # git worktree ...
fi

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  (cd "$WORKTREE_PATH" && lefthook install 2>/dev/null) || true
fi
```

**Step 7: Run tests**

Run: `cd .claude/hooks && bats tests/test_worktree_create.bats tests/test_worktree_remove.bats`
Expected: All existing tests still pass.

**Step 8: Commit**

```bash
git add .claude/hooks/worktree-create.sh .claude/hooks/worktree-remove.sh
git commit -m "fix(hooks): harden worktree hooks for jj edge cases

- Add command -v jj guard to worktree-remove.sh (g13.9)
- Reject . and .. in workspace name validation (g13.14)
- Fix stderr handling for git worktree remove (g13.16)
- Clean up orphaned dirs on jj workspace add failure (g13.11)
- Fix comment and extract shared lefthook block (g13.27, g13.7)"
```

---

## Task 2: Fix agent Environment blocks (11 agents)

**Closes:** g13.17, g13.26, g13.13

**Files:**

- Modify: `pr-review/agents/api-contract-checker.md`
- Modify: `pr-review/agents/code-reviewer.md`
- Modify: `pr-review/agents/code-simplifier.md`
- Modify: `pr-review/agents/comment-analyzer.md`
- Modify: `pr-review/agents/fix-worker.md`
- Modify: `pr-review/agents/pr-test-analyzer.md`
- Modify: `pr-review/agents/review-gate.md` (check if it has the block)
- Modify: `pr-review/agents/security-auditor.md`
- Modify: `pr-review/agents/silent-failure-hunter.md`
- Modify: `pr-review/agents/spec-compliance.md`
- Modify: `pr-review/agents/type-design-analyzer.md`
- Modify: `pr-review/agents/verification-runner.md`

**Step 1: Define the corrected Environment block template**

Current (in all 11 worktree-isolated agents):

```markdown
1. **Detect VCS:** `test -d .jj && echo "jj" || echo "git"`
2. **Verify location:**
   - jj: Run `pwd` and `jj workspace root` — confirm you are in a workspace
   - git: Run `pwd` and `git branch --show-current` — verify you are on a `worktree/*` branch, NOT `main`
3. If anything looks wrong, STOP and report STATUS: FAIL
```

Replace with:

```markdown
1. **Detect VCS:** `test -d .jj && echo "jj" || echo "git"`
   - If neither `.jj/` nor `.git/` exists, STOP and report
     STATUS: FAILED — "No VCS detected (no .jj/ or .git/ directory)"
2. **Verify location:**
   - jj: Run `pwd` and `jj workspace list` — confirm your `pwd` appears
     in the workspace list (verifies workspace identity, not just path)
   - git: Run `pwd` and `git branch --show-current` — verify you are on
     a `worktree/*` branch, NOT `main`
3. If anything looks wrong, STOP and report STATUS: FAILED
```

Key changes:

- `jj workspace root` → `jj workspace list` (verifies identity)
- `STATUS: FAIL` → `STATUS: FAILED` (matches output spec enum)
- Added no-VCS diagnostic

**Step 2: Apply to all 11 worktree-isolated agents**

Skip review-gate (isolation: none, read-only, no Environment block).

**Step 3: Verify consistency**

```bash
grep -c "STATUS: FAILED" pr-review/agents/*.md
grep -c "STATUS: FAIL[^E]" pr-review/agents/*.md   # should be 0
grep -c "jj workspace list" pr-review/agents/*.md   # should be 11
grep -c "jj workspace root" pr-review/agents/*.md   # should be 0
```

**Step 4: Commit**

```bash
git add pr-review/agents/*.md
git commit -m "fix(agents): fix Environment block across all 11 agents

- Replace jj workspace root with jj workspace list (g13.17)
- Fix STATUS: FAIL → STATUS: FAILED to match output spec (g13.26)
- Add no-VCS diagnostic (g13.13)"
```

---

## Task 3: Fix documentation and comments

**Closes:** g13.18, g13.21, g13.23, g13.24, g13.32

**Files:**

- Modify: `jj/skills/jujutsu/references/jj-git-interop.md`
- Modify: `AGENTS.md`
- Modify: `pr-review/skills/address-findings/SKILL.md`
- Modify: `pr-review/skills/respond-to-comments/SKILL.md`
- Modify: `jj/skills/jujutsu/SKILL.md`

**Step 1: Fix jj-git-interop.md header/body contradiction (g13.18)**

Line 7: Change "Every `jj` command" to "Most `jj` commands":

```markdown
A colocated repo has both `.jj/` and `.git/` directories. Most `jj` commands automatically sync
state to the underlying git repo.
```

**Step 2: Fix AGENTS.md verify step (g13.21)**

Find the session completion / verify section. Add VCS branching so the verify step uses `jj st` in jj repos instead of `git status`.

**Step 3: Fix Phase 4b jj undo comment (g13.23)**

In `pr-review/skills/address-findings/SKILL.md`, line 333, replace:

```markdown
   If bookmark set fails, run `jj undo` to revert the rebase too.
```

With:

```markdown
   If bookmark set fails, run `jj undo` to revert the bookmark set,
   then run `jj undo` again to revert the rebase (each `jj undo`
   reverts only the most recent operation).
```

**Step 4: Fix respond-to-comments workspace guidance (g13.24)**

In `pr-review/skills/respond-to-comments/SKILL.md`, lines 145-151, replace the mixed `jj workspace list` / `jj workspace root` guidance with:

```markdown
   In jj repos, use `jj workspace list` to find existing workspaces
   and verify the current workspace by checking that `pwd` appears
   in the workspace list output.
```

**Step 5: Document `jj workspace list` in SKILL.md (g13.32)**

In `jj/skills/jujutsu/SKILL.md`, Workspaces section, add:

```markdown
- `jj workspace list` shows all workspaces and their working-copy paths
```

**Step 6: Commit**

```bash
git add jj/skills/jujutsu/references/jj-git-interop.md AGENTS.md \
  pr-review/skills/address-findings/SKILL.md \
  pr-review/skills/respond-to-comments/SKILL.md \
  jj/skills/jujutsu/SKILL.md
git commit -m "docs: fix jj documentation inaccuracies

- Fix jj-git-interop.md 'every' → 'most' (g13.18)
- Fix AGENTS.md verify step to be VCS-aware (g13.21)
- Fix Phase 4b jj undo semantics (g13.23)
- Fix respond-to-comments workspace guidance (g13.24)
- Document jj workspace list in jujutsu SKILL.md (g13.32)"
```

---

## Task 4: Fix skill orchestration issues

**Closes:** g13.36, g13.37, g13.15, g13.39

**Files:**

- Modify: `pr-review/skills/address-findings/SKILL.md`
- Modify: `pr-review/skills/review-pr/SKILL.md`

**Step 1: Add jj alternative for Phase 6 ship commit (g13.36)**

In `pr-review/skills/address-findings/SKILL.md`, line 415, replace:

```markdown
1. **Commit** using the `commit-commands:commit` skill.
```

With:

```markdown
1. **Commit** changes:
   - git repos: Use the `commit-commands:commit` skill.
   - jj repos: Run `jj commit -m "fix: address review findings for PR #<number>"`
```

**Step 2: Fix Phase 1 checkout verification (g13.37)**

In `pr-review/skills/address-findings/SKILL.md`, lines 77-87, make the checkout verification VCS-conditional (don't run `git branch --show-current` unconditionally before jj steps).

**Step 3: Add error handling for jj workspace forget (g13.15)**

In Phase 4b jj section (around line 336-339), add:

```markdown
   If `jj workspace forget` fails (e.g., workspace already forgotten
   or jj not installed), log a warning but proceed with directory
   cleanup. The directory removal is the critical step.
```

**Step 4: Normalize review-pr jj tool entries (g13.39)**

In `pr-review/skills/review-pr/SKILL.md`, replace the 8 granular `Bash(jj X)` entries (lines 26-33) with:

```yaml
  - "Bash(jj *)"
```

**Step 5: Commit**

```bash
git add pr-review/skills/address-findings/SKILL.md \
  pr-review/skills/review-pr/SKILL.md
git commit -m "fix(skills): fix skill orchestration for jj workflows

- Add jj commit alternative in Phase 6 ship (g13.36)
- Make Phase 1 checkout VCS-conditional (g13.37)
- Add error handling for jj workspace forget (g13.15)
- Normalize review-pr jj tool entries to wildcard (g13.39)"
```

---

## Task 5: Fix eval assertion schemas

**Closes:** g13.19, g13.20, g13.25

**Files:**

- Modify: `pr-review/evals/evals.json`
- Modify: `jj/evals/evals.json`

**Step 1: Fix B-JJ1 assertions in pr-review/evals/evals.json (g13.19)**

Replace (lines 253-261):

```json
"assertions": [
  {"type": "output_contains", "value": "jj rebase"},
  {"type": "output_not_contains", "value": "git cherry-pick"}
]
```

With:

```json
"assertions": [
  {
    "name": "uses-jj-rebase",
    "description": "Uses jj rebase for integration instead of cherry-pick",
    "type": "output_contains",
    "check": "jj rebase"
  },
  {
    "name": "no-git-cherry-pick",
    "description": "Does not use git cherry-pick in jj repos",
    "type": "output_not_contains",
    "check": "git cherry-pick"
  }
]
```

**Step 2: Fix B8 assertion in jj/evals/evals.json (g13.20)**

Replace (lines 174-177):

```json
"assertions": [
  {"type": "output_contains", "value": "test -d .jj"}
]
```

With:

```json
"assertions": [
  {
    "name": "references-vcs-detection",
    "description": "References the VCS detection preamble command",
    "type": "output_contains",
    "check": "test -d .jj"
  }
]
```

**Step 3: Add triggering assertions to pr-review evals (g13.25)**

For each of the 10 pr-review triggering evals (T1-T10), add the appropriate assertion matching the `expected_skill` field:

```json
"assertions": [{"type": "skill_triggered", "value": "<expected_skill>"}]
```

**Step 4: Verify schemas**

```bash
python3 -c "
import json
for f in ['jj/evals/evals.json', 'pr-review/evals/evals.json']:
    data = json.load(open(f))
    for e in data['evals']:
        for a in e.get('assertions', []):
            if e['type'] == 'behavioral' and 'check' not in a and 'value' in a:
                print(f'FAIL: {f} {e[\"id\"]} has value instead of check')
            if e['type'] == 'behavioral' and ('name' not in a or 'description' not in a):
                print(f'FAIL: {f} {e[\"id\"]} missing name/description')
    print(f'OK: {f}')
"
```

Expected: No FAIL lines.

**Step 5: Commit**

```bash
git add pr-review/evals/evals.json jj/evals/evals.json
git commit -m "fix(evals): normalize assertion schemas across all evals

- Fix B-JJ1 assertions to use {name, description, type, check} (g13.19)
- Fix B8 assertion to use correct behavioral schema (g13.20)
- Add triggering assertions to pr-review evals (g13.25)"
```

---

## Task 6: Extract shared VCS detection preamble

**Closes:** g13.3, g13.5

**Files:**

- Create: `pr-review/references/vcs-detection-preamble.md`
- Modify: `pr-review/agents/*.md` (11 agents)
- Modify: `pr-review/skills/address-findings/SKILL.md`
- Modify: `pr-review/skills/respond-to-comments/SKILL.md`
- Modify: `pr-review/skills/review-pr/SKILL.md`

**Step 1: Create shared VCS detection reference**

Create `pr-review/references/vcs-detection-preamble.md`:

```markdown
# VCS Detection Preamble

Standard startup procedure for agents and skills operating in
repositories that may use git or jj (Jujutsu).

## Steps

1. **Detect VCS:** `test -d .jj && echo "jj" || echo "git"`
   - If neither `.jj/` nor `.git/` exists, STOP and report
     STATUS: FAILED — "No VCS detected (no .jj/ or .git/ directory)"
2. **Verify location:**
   - jj: Run `pwd` and `jj workspace list` — confirm your `pwd` appears
     in the workspace list (verifies workspace identity, not just path)
   - git: Run `pwd` and `git branch --show-current` — verify you are on
     a `worktree/*` branch, NOT `main`
3. If anything looks wrong, STOP and report STATUS: FAILED

Use the detected VCS for all operations in this session. Consult
`pr-review/references/vcs-equivalence.md` for command equivalents.

## Path Rules

- Use ONLY relative paths for all file operations
- Do NOT `cd` outside your working directory
- Do NOT use absolute paths from diffs or PR metadata — translate them
  to relative paths within your worktree
```

**Step 2: Replace inline preambles in 11 agents with reference**

In each worktree-isolated agent, replace the Environment block content with:

```markdown
## Environment

You are running in an isolated worktree. Follow the startup procedure
in `pr-review/references/vcs-detection-preamble.md` to detect VCS
and verify your location before proceeding.
```

Keep any agent-specific constraints that differ from the shared preamble.

**Step 3: Replace inline VCS Detection in 3 skills (g13.5)**

In each skill's VCS Detection section, replace with:

```markdown
### VCS Detection

Follow the procedure in `pr-review/references/vcs-detection-preamble.md`.
```

**Step 4: Verify**

```bash
grep -r "jj workspace root" pr-review/   # should be 0
grep -r "vcs-detection-preamble" pr-review/   # should be 14+
```

**Step 5: Commit**

```bash
git add pr-review/references/vcs-detection-preamble.md \
  pr-review/agents/*.md pr-review/skills/*/SKILL.md
git commit -m "refactor(pr-review): extract shared VCS detection preamble

- Create pr-review/references/vcs-detection-preamble.md (g13.3)
- Replace inline preambles in 11 agents with reference
- Replace inline VCS Detection in 3 skills (g13.5)"
```

---

## Task 7: Add jj BATS test coverage

**Closes:** g13.1, g13.2, g13.4, g13.6

**Files:**

- Modify: `.claude/hooks/tests/test_worktree_create.bats`
- Modify: `.claude/hooks/tests/test_worktree_remove.bats`
- Modify: `pr-review/evals/evals.json`

**Step 1: Add jj path tests to test_worktree_create.bats (g13.1, g13.2)**

Add tests using a mock `jj` binary (jj may not be installed in CI):

```bash
# --- jj code path tests ---

setup_jj() {
  mkdir -p "${REPO_ROOT}/.jj"
}

@test "jj path: rejects when jj not installed" {
  setup_jj
  PATH="/usr/bin:/bin" run bash -c \
    'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj is not installed"* ]]
}

@test "jj path: creates workspace with mock jj" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  mkdir -p "$3"
  exit 0
fi
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/test-jj-wt"* ]]
}

@test "jj path: cleans up on jj workspace add failure" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'echo "{\"name\": \"fail-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/fail-wt" ]
}
```

**Step 2: Add jj path tests to test_worktree_remove.bats (g13.4)**

```bash
# --- jj code path tests ---

setup_jj_worktree() {
  mkdir -p "${REPO_ROOT}/.jj"
  mkdir -p "${REPO_ROOT}_worktrees/test-jj-wt"
}

@test "jj path: removes workspace directory" {
  setup_jj_worktree
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "forget" ]]; then exit 0; fi
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: handles missing jj binary gracefully" {
  setup_jj_worktree
  PATH="/usr/bin:/bin" run bash -c \
    'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
  [[ "$output" == *"jj is not installed"* ]]
}

@test "jj path: handles workspace forget failure" {
  setup_jj_worktree
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}
```

**Step 3: Add fix-worker CHANGE_ID eval (g13.6)**

In `pr-review/evals/evals.json`, add:

```json
{
  "id": "B-JJ2",
  "type": "behavioral",
  "skill": "address-findings",
  "prompt": "fix-worker returned: STATUS: FIXED, VCS: jj, CHANGE_ID: abc123. Integrate this fix.",
  "expected_output": "Should use jj rebase and jj bookmark set with the CHANGE_ID",
  "assertions": [
    {
      "name": "uses-jj-rebase-with-change-id",
      "description": "Uses jj rebase with the reported CHANGE_ID",
      "type": "output_contains",
      "check": "jj rebase"
    },
    {
      "name": "uses-bookmark-set",
      "description": "Updates bookmark after rebase",
      "type": "output_contains",
      "check": "jj bookmark set"
    }
  ]
}
```

**Step 4: Run BATS tests**

Run: `cd .claude/hooks && bats tests/`
Expected: All tests pass.

**Step 5: Commit**

```bash
git add .claude/hooks/tests/test_worktree_create.bats \
  .claude/hooks/tests/test_worktree_remove.bats \
  pr-review/evals/evals.json
git commit -m "test(hooks): add jj code path coverage to BATS tests

- Add jj workspace create tests with mock jj binary (g13.1)
- Add jj-not-installed error path test (g13.2)
- Add jj workspace removal and cleanup tests (g13.4)
- Add fix-worker CHANGE_ID integration eval (g13.6)"
```

---

## Task 8: Add jj version guard to worktree-create.sh

**Closes:** g13.34

**Files:**

- Modify: `.claude/hooks/worktree-create.sh`
- Modify: `.claude/hooks/tests/test_worktree_create.bats`

**Step 1: Add jj version check**

After the `command -v jj` guard (line 30-33), add:

```bash
  # Verify jj supports --name flag (added in 0.21)
  if ! jj workspace add --help 2>&1 | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported (need jj >= 0.21)" >&2
    exit 1
  fi
```

**Step 2: Add BATS test**

```bash
@test "jj path: rejects old jj without --name support" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "Usage: jj workspace add <path>"
  exit 0
fi
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
}
```

**Step 3: Run tests**

Run: `cd .claude/hooks && bats tests/test_worktree_create.bats`

**Step 4: Commit**

```bash
git add .claude/hooks/worktree-create.sh .claude/hooks/tests/test_worktree_create.bats
git commit -m "fix(hooks): add jj version guard for --name flag support (g13.34)"
```

---

## Task 9: CI for BATS tests (follow-up issue)

**Closes:** g13.10

Out of scope for this PR. Create a follow-up issue:

```bash
bd create --title="Add BATS hook tests to CI pipeline" \
  --type=task --priority=3 \
  --description="BATS tests only run locally. Add CI job for .claude/hooks/tests/*.bats. Ref: g13.10" \
  --silent
bd close fzymgc-house-skills-g13.10 --reason="Deferred to follow-up issue — out of scope for PR #31 review fixes"
```

---

## Task 10: Close remaining informational findings

**Closes:** g13.22

```bash
bd close fzymgc-house-skills-g13.22 --reason="Won't fix — VCS: field is informational/debug aid. Orchestrator uses CHANGE_ID vs WORKTREE_BRANCH presence to determine integration method."
```

---

## Execution Order

| Order | Task | Findings | Risk | Deps |
|-------|------|----------|------|------|
| 1 | Task 1: worktree hook fixes | g13.9,14,16,11,27,7 | High | None |
| 2 | Task 8: jj version guard | g13.34 | High | Task 1 |
| 3 | Task 2: agent Environment blocks | g13.17,26,13 | Medium | None |
| 4 | Task 3: documentation fixes | g13.18,21,23,24,32 | Low | None |
| 5 | Task 4: skill orchestration | g13.36,37,15,39 | Medium | None |
| 6 | Task 5: eval schemas | g13.19,20,25 | Low | None |
| 7 | Task 6: extract shared preamble | g13.3,5 | Medium | Task 2 |
| 8 | Task 7: BATS test coverage | g13.1,2,4,6 | Low | Task 1 |
| 9 | Task 9: CI follow-up | g13.10 | N/A | None |
| 10 | Task 10: close g13.22 | g13.22 | N/A | None |

**Parallelizable pairs:**

- Tasks 2 + 3 (agents + docs — no file overlap)
- Tasks 4 + 5 (skills + evals — minimal overlap, address-findings touched in both but different sections)

## Final Verification

```bash
bd list --parent fzymgc-house-skills-g13 --status open --json
# Expected: []

bd stats
git push
```
