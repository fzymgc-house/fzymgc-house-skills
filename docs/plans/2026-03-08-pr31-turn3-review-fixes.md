# PR #31 Turn 3 Review Findings Fix Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all deduplicated findings from the PR #31 turn 3 review (1 critical, 5 important, 14 suggestions).

**Architecture:** Group fixes by file to minimize edit passes. Shell script fixes are testable via BATS. Some prior fixes from turn 1-2 already landed (commits `0cf11e1`..`168588d`) but several issues remain. This plan addresses the CURRENT state of each file.

**Tech Stack:** Bash, BATS, JSON, Markdown

---

## Task Dependency Graph

```text
Tasks 1-8 are independent → run in parallel
Task 9 depends on Task 6
Task 10 depends on Tasks 2 and 7
Task 11 has no deps (mechanical)
```

---

### Task 1: Fix `jj undo` factual error in address-findings SKILL.md [CRITICAL]

**Files:**

- Modify: `pr-review/skills/address-findings/SKILL.md:341-348`

The current text (lines 343-346) incorrectly claims that a failed `jj bookmark set` does NOT create an operation log entry, then says one `jj undo` reverts the rebase. The comment-analyzer found this is factually wrong — jj records ALL operations including failures. Two `jj undo` calls are needed.

**Step 1: Fix the bookmark failure recovery block**

Replace lines 341-348:

```markdown
   If bookmark set fails:

   1. Run `jj undo` to revert the rebase. (A failed `jj bookmark set`
      does not create an operation log entry — jj only records
      successful mutations — so `jj undo` targets the preceding
      rebase.)
   2. Verify: `jj log -r @ --no-graph -n 1` — confirm pre-rebase state.
   3. Mark FAILED, add bead comment, re-queue for next round.
```

With:

```markdown
   If bookmark set fails:

   1. Run `jj undo` twice — once to revert the failed `jj bookmark set`
      (jj records all operations, including failures), and once more
      to revert the preceding `jj rebase`:

      ```bash
      jj undo  # revert failed bookmark set
      jj undo  # revert rebase
      ```

   2. Verify: `jj log -r @ --no-graph -n 1` — confirm pre-rebase state.
   3. Mark FAILED, add bead comment, re-queue for next round.
```

**Step 2: Lint**

```bash
rumdl check pr-review/skills/address-findings/SKILL.md
```

**Step 3: Commit**

```bash
git add pr-review/skills/address-findings/SKILL.md
git commit -m "fix(address-findings): correct jj undo recovery for failed bookmark set

jj records all operations including failures, so two jj undo calls are
needed to fully revert a failed bookmark set after a rebase."
```

---

### Task 2: Fix orphan directory leak in worktree-create.sh [IMPORTANT]

**Files:**

- Modify: `.claude/hooks/worktree-create.sh:43-63`
- Modify: `.claude/hooks/tests/test_worktree_create.bats`

Current state: `mkdir -p "$WORKTREE_PARENT"` runs at line 43 BEFORE the jj
validation guards (lines 48-63). When jj is absent or too old, the guards
exit without calling `cleanup_on_error`, leaving an orphan directory.

**Step 1: Write failing tests**

Add to `test_worktree_create.bats`:

```bash
@test "jj path: cleans up WORKTREE_PARENT when jj not installed" {
  setup_jj
  PATH="/usr/bin:/bin" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj is not installed"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: cleans up WORKTREE_PARENT when jj version too old" {
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
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: cleans up WORKTREE_PARENT when jj --help fails" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"help-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "fails gracefully when mkdir -p fails" {
  READONLY_PARENT=$(mktemp -d)
  READONLY_REPO="${READONLY_PARENT}/test-repo"
  mkdir "$READONLY_REPO"
  cd "$READONLY_REPO"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  chmod 555 "$READONLY_PARENT"
  run bash -c 'echo "{\"name\": \"mkdir-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  chmod 755 "$READONLY_PARENT"
  cd /
  rm -rf "$READONLY_PARENT"
}
```

**Step 2: Run tests to verify they fail**

```bash
bats .claude/hooks/tests/test_worktree_create.bats
```

Expected: New cleanup assertion tests FAIL (orphan dir remains).

**Step 3: Move `mkdir -p` after jj validation guards**

Remove the `mkdir -p` block at lines 43-46. Add `mkdir -p` into each VCS
branch, after validation passes but before the actual workspace/worktree
command:

```bash
if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  if ! jj_help=$(jj workspace add --help 2>&1); then
    echo "ERROR: jj failed to run: ${jj_help:0:200}" >&2
    exit 1
  fi
  if ! echo "$jj_help" | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported" >&2
    exit 1
  fi
  mkdir -p "$WORKTREE_PARENT" || {
    echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
    exit 1
  }
  if ! jj_out=$(cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}" 2>&1); then
    echo "ERROR: jj workspace add failed: $jj_out" >&2
    cleanup_on_error
    exit 1
  fi
else
  # Standard git worktree
  mkdir -p "$WORKTREE_PARENT" || {
    echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
    exit 1
  }
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $git_err" >&2
    cleanup_on_error
    exit 1
  fi
fi
```

**Step 4: Run tests to verify all pass**

```bash
bats .claude/hooks/tests/test_worktree_create.bats
```

**Step 5: Commit**

```bash
git add .claude/hooks/worktree-create.sh .claude/hooks/tests/test_worktree_create.bats
git commit -m "fix(hooks): move mkdir after jj validation to prevent orphan directories

mkdir -p ran before jj installation/version checks, leaving an empty
_worktrees/ directory when jj was absent or too old. Move mkdir into
each VCS branch after validation passes."
```

---

### Task 3: Sanitize CI drift-check JSON keys [IMPORTANT]

**Files:**

- Modify: `.github/workflows/check-skills.yml:22-28`

**Step 1: Add key validation before shell expansion**

Insert after the `all_keys=` line (line 22):

```yaml
          configured=$(echo "$all_keys" | while read -r key; do
            # Validate key contains only safe path characters
            if [[ "$key" =~ [^a-zA-Z0-9_./-] ]]; then
              echo "::error::Unsafe character in release-please key: $key"
              exit 1
            fi
            case "$key" in
              */skills/*) echo "$key" ;;
              *) find "$key/skills" -name SKILL.md -exec dirname {} \; 2>/dev/null ;;
            esac
          done | sort -u)
```

**Step 2: Commit**

```bash
git add .github/workflows/check-skills.yml
git commit -m "fix(ci): sanitize release-please JSON keys before shell expansion

Validates that package keys contain only safe path characters before
passing to find, preventing potential command injection via crafted keys."
```

---

### Task 4: Add failure handling to jj-init command [IMPORTANT]

**Files:**

- Modify: `jj/commands/jj-init.md:29-36`

**Step 1: Add error guard after init**

Replace step 3 content (lines 29-36):

```markdown
3. **Initialize colocated repo** — Run:

   ```bash
   jj git init --colocate

```text
   ```

   The `--colocate` flag ensures jj shares the working copy with git.
   Always use `--colocate` when initializing in an existing git repo.

   **If the command fails**, report the error to the user and stop.
   Do NOT proceed to modify `.gitignore` or run verification steps.

```text

**Step 2: Lint**

```bash
rumdl check jj/commands/jj-init.md
```

**Step 3: Commit**

```bash
git add jj/commands/jj-init.md
git commit -m "fix(jj-init): add failure handling after jj git init --colocate

Prevents the agent from modifying .gitignore when init fails."
```

---

### Task 5: Add workspace name parsing guidance to VCS detection preamble [IMPORTANT]

**Files:**

- Modify: `pr-review/references/vcs-detection-preamble.md:12-16`

**Step 1: Clarify exact-match parsing**

Replace lines 12-17:

```markdown
   - jj: Run `jj workspace list`. Output shows one workspace per line:
     `<name>: <path>` with `(current)` marking the active workspace.
     Parse the current workspace name by finding the line containing
     `(current)` and extracting the name before the first `:` delimiter.
     Verify the extracted name starts with `worktree-`. If you
     are in the `default` workspace, STOP and report
     STATUS: FAILED -- "Operating in default workspace (main
     equivalent). Dispatch to a worktree workspace instead."
```

**Step 2: Commit**

```bash
git add pr-review/references/vcs-detection-preamble.md
git commit -m "fix(vcs-detection): add exact-match parsing for workspace names

Agents must parse the name before the colon delimiter to prevent
substring matching on workspace names."
```

---

### Task 6: Fix review-gate.md Environment section [IMPORTANT]

**Files:**

- Modify: `pr-review/agents/review-gate.md:19-24`

The Environment section implies the agent runs VCS detection commands.
In reality, the orchestrator provides the diff as input. The agent
doesn't need to detect VCS — it just needs to know the diff format.

**Step 1: Rewrite Environment section**

Replace lines 19-24:

```markdown
## Environment

On startup:

1. Note: You receive the VCS diff as input from the orchestrator — you do
   NOT need to run VCS commands to obtain it. The diff format may be
   either git-style or jj-style depending on the repository.
2. Consult `pr-review/references/vcs-equivalence.md` if you need to
   interpret jj-specific diff syntax.
```

**Step 2: Lint**

```bash
rumdl check pr-review/agents/review-gate.md
```

**Step 3: Commit**

```bash
git add pr-review/agents/review-gate.md
git commit -m "fix(review-gate): clarify that diff is received as input

The agent receives the diff from the orchestrator and does not need
to run VCS detection or diff commands."
```

---

### Task 7: Fix worktree-remove.sh error handling [SUGGESTIONS]

**Files:**

- Modify: `.claude/hooks/worktree-remove.sh:76,81`

**Step 1: Add error capture to `rm -rf` (line 76)**

Replace:

```bash
rm -rf "$WORKTREE_PATH"
```

With:

```bash
if ! rm -rf "$WORKTREE_PATH" 2>/dev/null; then
  echo "WARNING: failed to remove worktree directory '$WORKTREE_PATH'" >&2
fi
```

**Step 2: Add warning to `rmdir` failure (line 81)**

Replace:

```bash
  rmdir "$PARENT" 2>/dev/null || true
```

With:

```bash
  rmdir "$PARENT" 2>/dev/null || echo "WARNING: failed to remove empty parent '$PARENT'" >&2
```

**Step 3: Run tests**

```bash
bats .claude/hooks/tests/test_worktree_remove.bats
```

**Step 4: Commit**

```bash
git add .claude/hooks/worktree-remove.sh
git commit -m "fix(hooks): add error warnings to worktree-remove.sh cleanup

Consistent with worktree-create.sh warning pattern instead of silently
ignoring rm -rf and rmdir failures."
```

---

### Task 8: Fix eval skill_name and release-please config [SUGGESTIONS]

**Files:**

- Modify: `jj/evals/evals.json:2`
- Verify: `release-please-config.json` (run drift-check locally)

**Step 1: Fix eval skill_name**

In `jj/evals/evals.json` line 2, change:

```json
  "skill_name": "jj",
```

To:

```json
  "skill_name": "jujutsu",
```

The SKILL.md frontmatter declares `name: jujutsu`.

**Step 2: Verify release-please drift-check**

```bash
actual=$(find homelab/skills pr-review/skills jj/skills -name SKILL.md -exec dirname {} \; 2>/dev/null | sort)
all_keys=$(jq -r '.packages | keys[] | select(. != ".")' release-please-config.json)
configured=$(echo "$all_keys" | while read -r key; do
  case "$key" in
    */skills/*) echo "$key" ;;
    *) find "$key/skills" -name SKILL.md -exec dirname {} \; 2>/dev/null ;;
  esac
done | sort -u)
diff <(echo "$actual") <(echo "$configured")
```

If it passes, no change needed. If it fails, fix the key.

**Step 3: Commit**

```bash
git add jj/evals/evals.json
git commit -m "fix(evals): correct skill_name to match SKILL.md frontmatter

evals.json had skill_name 'jj' but the skill is registered as 'jujutsu'."
```

---

### Task 9: Normalize review-gate.md VCS detection [SUGGESTION]

**Depends on:** Task 6

After Task 6 rewrites the Environment section, verify that no inline
VCS detection (`test -d .jj`) remains. If Task 6's rewrite already
removes it, this is a no-op.

**Step 1: Verify review-gate.md**

Read the file and confirm inline detection is gone.

**Step 2: Commit (only if changes needed)**

```bash
git add pr-review/agents/review-gate.md
git commit -m "fix(review-gate): remove inline VCS detection"
```

---

### Task 10: Extract duplicated name-validation regex [SUGGESTION]

**Depends on:** Tasks 2 and 7 (both modify the same scripts)

**Files:**

- Modify: `.claude/hooks/worktree-create.sh`
- Modify: `.claude/hooks/worktree-remove.sh`

**Step 1: Add `validate_safe_name()` helper to both scripts**

Add after `set -euo pipefail`:

```bash
validate_safe_name() {
  local name="$1" label="$2"
  if [[ "$name" =~ [^a-zA-Z0-9_.-] || "$name" == .* || "$name" == *".."* ]]; then
    echo "ERROR: ${label} '${name}' contains unsafe characters (alphanumeric, dots, hyphens, underscores only; no leading dot)" >&2
    return 1
  fi
}
```

**Step 2: Replace inline checks**

In `worktree-create.sh`, replace both inline regex checks with:

```bash
validate_safe_name "$NAME" "worktree name" || exit 1
validate_safe_name "$REPO_NAME" "repository directory name" || exit 1
```

Same pattern in `worktree-remove.sh` for WORKSPACE_NAME and REPO_NAME.

**Step 3: Run all tests**

```bash
bats .claude/hooks/tests/
```

**Step 4: Commit**

```bash
git add .claude/hooks/worktree-create.sh .claude/hooks/worktree-remove.sh
git commit -m "refactor(hooks): extract validate_safe_name to DRY up regex

Replaces 4 verbatim copies of the same name-validation pattern."
```

---

### Task 11: Remaining low-risk suggestions

These items are either deferred or require minimal changes:

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | `actions/checkout@v4` not SHA-pinned | **Defer** — mutable tags standard for GH Actions; Dependabot handles updates |
| 2 | `.beads/README.md` curl-pipe-bash unpinned URL | **Defer** — file is auto-generated by `bd init`, edits will be overwritten |
| 3 | VCS "none" STOP is prose only | **Defer** — shell enforcement in a reference doc adds complexity for no gain |
| 4 | Missing negative eval for jj | **Defer** — T5 already covers generic-commit non-triggering case |
| 5 | CI dead-code branch for plugin-level keys | **Defer** — harmless future-proofing |

No code changes needed. Close these as deferred/by-design.

---

## Execution Summary

| Batch | Tasks | Files touched |
|-------|-------|---------------|
| Parallel batch 1 | 1, 2, 3, 4, 5, 6, 7, 8 | All independent files |
| Sequential | 9 (after 6), 10 (after 2+7) | review-gate.md, both hook scripts |
| Triage | 11 | None (close as deferred) |

**Total commits:** 10 (one per task, excluding no-ops and deferrals)
