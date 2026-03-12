#!/usr/bin/env bats

load helpers

setup() {
  export REPO_ROOT=$(mktemp -d)
  cd "$REPO_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
}

teardown() {
  cd /
  rm -rf "$REPO_ROOT" "${REPO_ROOT}_worktrees"
}

@test "rejects names with path traversal" {
  run bash -c 'echo "{\"name\": \"../evil\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects names with spaces" {
  run bash -c 'echo "{\"name\": \"has space\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects names with shell metacharacters" {
  run bash -c 'echo "{\"name\": \"evil;rm\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects dot name" {
  run bash -c 'echo "{\"name\": \".\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects dotdot name" {
  run bash -c 'echo "{\"name\": \"..\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "accepts valid alphanumeric name" {
  run bash -c 'echo "{\"name\": \"fix-worker-abc123\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/fix-worker-abc123"* ]]
  [ -d "${REPO_ROOT}_worktrees/fix-worker-abc123" ]
}

@test "git path: succeeds when CWD is a subdirectory of repo root" {
  mkdir -p "${REPO_ROOT}/src/subdir"
  run bash -c 'cd '"${REPO_ROOT}/src/subdir"' && echo "{\"name\": \"sub-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [ -d "${REPO_ROOT}_worktrees/sub-wt" ]
  # Clean up
  git -C "$REPO_ROOT" worktree remove "${REPO_ROOT}_worktrees/sub-wt" --force 2>/dev/null || true
  rm -rf "${REPO_ROOT}_worktrees/sub-wt"
}

@test "jj path: succeeds when CWD is a subdirectory of repo root" {
  setup_jj
  create_mock_jj
  mkdir -p "${REPO_ROOT}/src/subdir"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'cd '"${REPO_ROOT}/src/subdir"' && echo "{\"name\": \"sub-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/sub-jj-wt"* ]]
  # Clean up
  rm -rf "${REPO_ROOT}_worktrees/sub-jj-wt"
}

@test "rejects names with trailing dot" {
  run bash -c 'echo "{\"name\": \"agent-abc.\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects empty name" {
  run bash -c 'echo "{\"name\": \"\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
}

@test "rejects missing name key in JSON input" {
  run bash -c 'echo "{}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
}

@test "fails when not inside a git repo (git rev-parse failure)" {
  NON_GIT=$(mktemp -d)
  run bash -c 'cd '"$NON_GIT"' && echo "{\"name\": \"orphan-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"not inside a git/jj repository"* ]]
  rm -rf "$NON_GIT"
}

# --- detect_repo_root fallback tests ---

@test "detect_repo_root falls back to jj root when git rev-parse fails" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  # Use create_pure_jj_mock via temporary REPO_ROOT override so the bin dir
  # lands inside NON_GIT (which has no .git/ to back git rev-parse).
  ORIG_REPO_ROOT="$REPO_ROOT"
  REPO_ROOT="$NON_GIT"
  create_pure_jj_mock
  REPO_ROOT="$ORIG_REPO_ROOT"
  PATH="${NON_GIT}/bin:$PATH" JJ_REPO_ROOT="${NON_GIT}" run bash -c \
    'cd '"$NON_GIT"' && echo "{\"name\": \"jj-root-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/jj-root-test"* ]]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

# --- jj code path tests ---

setup_jj() {
  mkdir -p "${REPO_ROOT}/.jj"
}

@test "jj path: rejects when jj not installed" {
  setup_jj
  PATH="$_NO_JJ_PATH" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj is not installed"* ]]
  [[ "$output" == *"INFO: cleanup: .jj/ found but jj not installed — no workspace was registered, no cleanup needed"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: creates workspace with mock jj" {
  setup_jj
  create_mock_jj
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/test-jj-wt"* ]]
  [ -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: forwards --name flag to jj workspace add" {
  setup_jj
  create_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"named-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  # Verify the logged args contain --name worktree-named-wt
  [[ "$(cat "${REPO_ROOT}/jj-args.log")" == *"--name worktree-named-wt"* ]]
}

@test "jj path: workspace name with hyphens and underscores is preserved in --name arg" {
  # Verify names containing valid but potentially shell-significant characters
  # (consecutive hyphens, underscores) survive the jj invocation intact.
  # validate_safe_name allows [a-zA-Z0-9_.-] so "fix_worker--v2" is valid.
  setup_jj
  create_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"fix_worker--v2\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [ -d "${REPO_ROOT}_worktrees/fix_worker--v2" ]
  # The workspace name passed to jj must be exactly "worktree-fix_worker--v2"
  [[ "$(cat "${REPO_ROOT}/jj-args.log")" == *"--name worktree-fix_worker--v2"* ]]
}

@test "jj path: cleans up worktree and parent on workspace add failure" {
  setup_jj
  create_failing_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"fail-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/fail-wt" ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: cleans up mkdir-created directory and warns when workspace add creates dir then fails" {
  setup_jj
  # Mock jj: workspace add creates the directory (simulating partial jj
  # execution) then exits non-zero, workspace forget fails (workspace was
  # never registered), root delegates to git rev-parse.
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  # Simulate partial jj execution: directory created but workspace not registered
  shift 2
  for arg in "\$@"; do
    case "\$arg" in
      -*) ;;
      *) mkdir -p "\$arg"; break ;;
    esac
  done
  echo "Error: workspace add failed after creating directory" >&2
  exit 1
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  echo "Error: No workspace named '\$3'" >&2
  exit 1
fi
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"partial-add-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  # Worktree directory created by jj must be cleaned up
  [ ! -d "${REPO_ROOT}_worktrees/partial-add-wt" ]
  # Parent _worktrees directory must be cleaned up (empty after rm)
  [ ! -d "${REPO_ROOT}_worktrees" ]
  # WARNING about workspace forget failure must appear (workspace was never registered)
  [[ "$output" == *"WARNING: cleanup: jj workspace forget"* ]]
}

@test "jj path: cleanup_on_error always attempts jj workspace forget even when workspace add fails" {
  # After 04l.29, cleanup_on_error always calls jj workspace forget in jj repos,
  # regardless of WORKSPACE_CREATED. This covers the case where jj workspace add
  # partially registered the workspace before failing.
  setup_jj
  create_failing_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"no-forget-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/no-forget-wt" ]
  # forget MUST be called — cleanup_on_error always attempts it in jj repos
  [ -f "${REPO_ROOT}/forget-called.log" ]
}

@test "jj path: cleanup_on_error warns when jj workspace forget fails with WORKSPACE_CREATED=false" {
  # Exercises the WARNING (not ERROR) branch at worktree-create.sh line 48:
  # when jj workspace add fails (WORKSPACE_CREATED stays false) AND
  # jj workspace forget also fails, emit WARNING (not ERROR/CLEANUP_FAILED).
  setup_jj
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  echo "error: workspace add failed" >&2
  exit 1
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  echo "Error: No workspace named 'worktree-warn-forget-wt'" >&2
  exit 1
fi
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"warn-forget-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  # WARNING must appear (WORKSPACE_CREATED=false → not a data integrity error)
  [[ "$output" == *"WARNING: cleanup: jj workspace forget"* ]]
}

@test "jj path: cleanup_on_error calls jj workspace forget on post-add failure" {
  setup_jj
  create_logging_jj_mock
  # Patch worktree-create.sh: replace "trap - EXIT" with "false" to simulate
  # a failure after workspace add succeeds (WORKSPACE_CREATED=true).
  # Under set -e, "false" exits non-zero, firing the EXIT trap.
  # Copy into the same directory so BASH_SOURCE[0]-based source resolution
  # still finds worktree-helpers.sh.
  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"forget-wt\"}" | bash '"$patched"
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # cleanup_on_error should have called jj workspace forget with the workspace name
  [ -f "${REPO_ROOT}/forget-arg.log" ]
  [[ "$(cat "${REPO_ROOT}/forget-arg.log")" == "worktree-forget-wt" ]]
}

@test "jj path: cleanup_on_error warns when jj workspace forget fails on post-add failure" {
  setup_jj
  # Mock jj: workspace add succeeds, workspace forget FAILS with error message
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
${_MOCK_WORKSPACE_ADD_BODY}
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2; _mock_workspace_add "\$@"
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  echo "Error: No workspace named 'worktree-forget-fail-wt'" >&2
  exit 1
fi
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"

  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"forget-fail-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # WORKSPACE_CREATED=true (post-add failure) → ERROR severity, not WARNING
  [[ "$output" == *"ERROR: cleanup: jj workspace forget"* ]]
}

@test "jj path: cleanup_on_error errors jj-not-in-PATH after successful workspace add" {
  # Exercises the branch at cleanup_on_error line 36: command -v jj returns false
  # inside cleanup for a .jj/ repo after a successful workspace add
  # (WORKSPACE_CREATED=true).  The scenario: jj is present when workspace add
  # runs (so it succeeds), then disappears from PATH before the post-add step
  # triggers the EXIT trap.
  # When WORKSPACE_CREATED=true, the orphaned workspace is a data integrity
  # issue, so the message is escalated to ERROR and CLEANUP_FAILED is set.
  #
  # Strategy: use a custom mock jj that succeeds on workspace add, then patch
  # the script so that "trap - EXIT" is replaced with a PATH-clearing step
  # followed by false.  This fires cleanup_on_error with WORKSPACE_CREATED=true
  # and jj absent from PATH, exercising the else branch at line 44.
  setup_jj
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
${_MOCK_WORKSPACE_ADD_BODY}
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2; _mock_workspace_add "\$@"
fi
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"

  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  # Replace "trap - EXIT" with PATH-clearing then false so the EXIT trap fires
  # with jj no longer in PATH.  The mock jj dir is removed from PATH here so
  # cleanup_on_error sees command -v jj fail.
  sed "s|^trap - EXIT  # disarm after success\$|PATH=\"${_NO_JJ_PATH}\"; false|" \
    "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"jj-gone-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # Workspace directory created by mock jj must be cleaned up
  [ ! -d "${REPO_ROOT}_worktrees/jj-gone-wt" ]
  # ERROR about jj not installed must appear (WORKSPACE_CREATED=true makes this a data integrity issue)
  [[ "$output" == *"ERROR: cleanup: .jj/ found but jj not installed"* ]]
}

@test "jj path: fails gracefully when mkdir -p fails" {
  setup_jj
  create_mock_jj
  SANDBOX=$(mktemp -d)
  NESTED="${SANDBOX}/repos/myrepo"
  mkdir -p "$NESTED"
  cd "$NESTED"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  mkdir -p "${NESTED}/.jj"
  chmod a-w "${SANDBOX}/repos"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"mkdir-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  chmod a+w "${SANDBOX}/repos"
  rm -rf "$SANDBOX"
  [ "$status" -eq 1 ]
  [[ "$output" == *"failed to create worktree parent directory"* ]]
  [[ "$output" != *"jj workspace forget"* ]]
}

@test "git path: cleans up empty parent on worktree add failure" {
  git branch "worktree/fail-test"
  run bash -c 'echo "{\"name\": \"fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  [ ! -d "${REPO_ROOT}_worktrees/fail-test" ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "cleanup_on_error preserves parent directory when it contains other entries" {
  # Pre-populate the worktree parent with another entry so it is non-empty
  mkdir -p "${REPO_ROOT}_worktrees/other-wt"
  git branch "worktree/fail-test"
  run bash -c 'echo "{\"name\": \"fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  # failed worktree directory must be removed
  [ ! -d "${REPO_ROOT}_worktrees/fail-test" ]
  # parent must be preserved because other-wt still exists
  [ -d "${REPO_ROOT}_worktrees" ]
  [ -d "${REPO_ROOT}_worktrees/other-wt" ]
}

@test "git path: cleanup_on_error removes worktree on post-add failure" {
  # Patch worktree-create.sh: replace "trap - EXIT" with "false" to simulate
  # a failure after worktree add succeeds (WORKSPACE_CREATED=true).
  # Copy into the same directory so BASH_SOURCE[0]-based source resolution
  # still finds worktree-helpers.sh.
  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  run bash -c \
    'echo "{\"name\": \"git-cleanup-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # cleanup_on_error should have removed the worktree directory
  [ ! -d "${REPO_ROOT}_worktrees/git-cleanup-wt" ]
  # Parent dir should also be cleaned up if empty
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "git path: cleanup_on_error warns when git worktree remove fails on post-add failure" {
  # Resolve real git path before creating mock to avoid PATH confusion
  local real_git
  real_git="$(command -v git)"

  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "${mock_bin}/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "remove" ]]; then
  echo "fatal: mock failure" >&2
  exit 1
fi
exec "${real_git}" "\$@"
MOCK
  chmod +x "${mock_bin}/git"

  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${mock_bin}:$PATH" run bash -c \
    'echo "{\"name\": \"git-fail-cleanup-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  rm -rf "$mock_bin"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WARNING: cleanup: git worktree remove failed"* ]]
}

@test "cleanup_on_error warns when rm -rf fails to remove worktree directory" {
  # Resolve real git path before creating mock to avoid PATH confusion.
  # macOS resolves symlinks in tmpdir paths (e.g. /var/... → /private/var/...)
  # so we can't match WORKTREE_PATH exactly; instead fail on any -rf invocation
  # inside the cleanup, which is the only rm -rf the cleanup function issues.
  local real_git
  real_git="$(command -v git)"
  local real_rm
  real_rm="$(command -v rm)"

  local mock_bin
  mock_bin=$(mktemp -d)

  # Mock rm: fail on -rf (the cleanup rm -rf call); delegate everything else.
  cat > "${mock_bin}/rm" << MOCK
#!/bin/bash
if [[ "\$1" == "-rf" ]]; then
  echo "rm: \$2: Operation not permitted" >&2
  exit 1
fi
exec "${real_rm}" "\$@"
MOCK
  chmod +x "${mock_bin}/rm"

  # Mock git: pass through all calls so worktree add succeeds, and succeed on
  # worktree remove so cleanup_on_error proceeds to the rm -rf step.
  cat > "${mock_bin}/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "remove" ]]; then
  exit 0
fi
exec "${real_git}" "\$@"
MOCK
  chmod +x "${mock_bin}/git"

  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${mock_bin}:$PATH" run bash -c \
    'echo "{\"name\": \"rm-fail-cleanup-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  rm -rf "$mock_bin"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WARNING: cleanup failed for"* ]]
}

@test "rejects repo directory name with spaces" {
  UNSAFE_ROOT=$(mktemp -d)/repo\ with\ spaces
  mkdir -p "$UNSAFE_ROOT"
  cd "$UNSAFE_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid repository directory name"* ]]
  cd /
  rm -rf "$(dirname "$UNSAFE_ROOT")"
}

@test "rejects dot-prefixed names" {
  run bash -c 'echo "{\"name\": \".hidden\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "jj path: rejects old jj without --name support" {
  setup_jj
  create_old_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: rejects old jj with 'unrecognized' error pattern" {
  setup_jj
  create_old_jj_unrecognized_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: rejects old jj with 'unknown' error pattern" {
  setup_jj
  create_old_jj_unknown_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: cleans up partial directory when old jj creates it before rejecting --name" {
  setup_jj
  # Mock jj that creates the target directory then rejects --name (simulates old jj
  # that partially executes workspace add before failing on the unknown flag).
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # Simulate old jj: create the target directory, then fail on --name
  mkdir -p "$3"
  echo "error: unexpected argument '--name' found" >&2
  exit 1
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
exit 0
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"partial-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
  # EXIT trap must clean up the partial directory created by the mock
  [ ! -d "${REPO_ROOT}_worktrees/partial-test" ]
}

@test "jj path: exits with error when jj workspace add fails" {
  setup_jj
  create_always_failing_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"add-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj workspace add failed"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: pure jj repo (no .git) uses jj root fallback for repo root detection" {
  # Create a temp directory with only .jj/ — no git init, no .git/
  PURE_JJ=$(mktemp -d)
  mkdir -p "${PURE_JJ}/.jj"
  # create_pure_jj_mock writes to MOCK_JJ_BIN_DIR which defaults to REPO_ROOT/bin;
  # override REPO_ROOT temporarily so the bin dir is inside PURE_JJ.
  ORIG_REPO_ROOT="$REPO_ROOT"
  REPO_ROOT="$PURE_JJ"
  create_pure_jj_mock
  REPO_ROOT="$ORIG_REPO_ROOT"
  # Pass JJ_REPO_ROOT so the mock's 'root' command returns the pure-jj directory.
  PATH="${PURE_JJ}/bin:$PATH" JJ_REPO_ROOT="${PURE_JJ}" run bash -c \
    'cd '"$PURE_JJ"' && echo "{\"name\": \"pure-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/pure-jj-wt"* ]]
  [ -d "${PURE_JJ}_worktrees/pure-jj-wt" ]
  rm -rf "$PURE_JJ" "${PURE_JJ}_worktrees"
}

# --- lefthook integration tests ---
# Lefthook runs on shared post-VCS code (identical for git and jj paths),
# so these tests cover both code paths without duplication.

@test "runs lefthook install when lefthook.yml exists" {
  touch "${REPO_ROOT}/lefthook.yml"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/lefthook" << 'MOCK'
#!/bin/bash
touch ./lefthook-marker
MOCK
  chmod +x "${REPO_ROOT}/bin/lefthook"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"hook-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/hook-test"* ]]
  [ -f "${REPO_ROOT}_worktrees/hook-test/lefthook-marker" ]
}

@test "warns when lefthook install fails" {
  touch "${REPO_ROOT}/lefthook.yml"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/lefthook" << 'MOCK'
#!/bin/bash
echo "mock error" >&2
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/lefthook"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"lh-fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"_worktrees/lh-fail-test"* ]]
}

@test "skips lefthook install when lefthook.yml absent" {
  run bash -c 'echo "{\"name\": \"no-hook-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
}

@test "jj path: runs lefthook install after jj workspace add" {
  setup_jj
  create_mock_jj
  touch "${REPO_ROOT}/lefthook.yml"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/lefthook" << 'MOCK'
#!/bin/bash
touch ./lefthook-marker
MOCK
  chmod +x "${REPO_ROOT}/bin/lefthook"
  PATH="${MOCK_JJ_BIN_DIR}:${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"jj-hook-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/jj-hook-test"* ]]
  [ -f "${REPO_ROOT}_worktrees/jj-hook-test/lefthook-marker" ]
}

@test "jj path: warns when lefthook install fails" {
  setup_jj
  create_mock_jj
  touch "${REPO_ROOT}/lefthook.yml"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/lefthook" << 'MOCK'
#!/bin/bash
echo "mock error" >&2
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/lefthook"
  PATH="${MOCK_JJ_BIN_DIR}:${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"jj-lh-fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"_worktrees/jj-lh-fail-test"* ]]
}

@test "git path: fails gracefully when mkdir -p fails" {
  # Create a nested temp dir so we can chmod the parent
  SANDBOX=$(mktemp -d)
  NESTED="${SANDBOX}/repos/myrepo"
  mkdir -p "$NESTED"
  cd "$NESTED"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  # Make the repos/ dir read-only so mkdir -p for _worktrees sibling fails
  chmod a-w "${SANDBOX}/repos"
  run bash -c 'echo "{\"name\": \"mkdir-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  chmod a+w "${SANDBOX}/repos"
  rm -rf "$SANDBOX"
  [ "$status" -eq 1 ]
  [[ "$output" == *"failed to create worktree parent directory"* ]]
}

@test "jj path: mkdir -p failure exits 1 with descriptive error message" {
  SANDBOX=$(mktemp -d)
  NESTED="${SANDBOX}/repos/myrepo"
  mkdir -p "$NESTED"
  mkdir -p "${NESTED}/.jj"
  ORIG_REPO_ROOT="$REPO_ROOT"
  REPO_ROOT="$NESTED"
  create_mock_jj
  local JJ_BIN_DIR="$MOCK_JJ_BIN_DIR"
  REPO_ROOT="$ORIG_REPO_ROOT"
  cd "$NESTED"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  chmod a-w "${SANDBOX}/repos"
  PATH="${JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"mkdir-msg-jj\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  chmod a+w "${SANDBOX}/repos"
  rm -rf "$SANDBOX"
  [ "$status" -eq 1 ]
  [[ "$output" == *"failed to create worktree parent directory"* ]]
}

# --- colocated jj+git repo tests ---

@test "colocated jj+git: creates workspace via jj path when both .jj and .git present" {
  setup_jj
  create_mock_jj
  # Both .jj/ and .git/ exist — script should take jj path
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"colo-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/colo-wt"* ]]
  [ -d "${REPO_ROOT}_worktrees/colo-wt" ]
}

@test "colocated jj+git: rejects repo directory name with spaces" {
  UNSAFE_ROOT=$(mktemp -d)/repo\ with\ spaces
  mkdir -p "$UNSAFE_ROOT"
  cd "$UNSAFE_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  mkdir -p .jj
  create_mock_jj
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid repository directory name"* ]]
  cd /
  rm -rf "$(dirname "$UNSAFE_ROOT")"
}

@test "git path: cleanup_on_error removes pre-existing worktree directory on collision" {
  # Pre-create the worktree path with a sentinel file so git worktree add fails.
  # cleanup_on_error must rm -rf the stale directory even though WORKSPACE_CREATED is false.
  mkdir -p "${REPO_ROOT}_worktrees/git-collision-wt"
  echo "stale" > "${REPO_ROOT}_worktrees/git-collision-wt/sentinel"
  run bash -c 'cd '"$REPO_ROOT"' && echo "{\"name\": \"git-collision-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  # git worktree add fails when target directory already exists
  [ "$status" -ne 0 ]
  # cleanup_on_error must remove the pre-existing directory
  [ ! -d "${REPO_ROOT}_worktrees/git-collision-wt" ]
}

@test "colocated jj+git: fails gracefully when worktree path already exists" {
  setup_jj
  # Create a custom mock jj that fails when the target directory already exists
  MOCK_JJ_BIN_DIR="${REPO_ROOT}/bin"
  mkdir -p "$MOCK_JJ_BIN_DIR"
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  shift 2
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      *)
        if [[ -d "$arg" ]]; then
          echo "error: Destination path already exists" >&2
          exit 1
        fi
        mkdir -p "$arg" && exit 0
        ;;
    esac
  done
  exit 1
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
echo "ERROR: unexpected jj invocation: $*" >&2
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  # Pre-create the worktree path with content so jj workspace add fails
  mkdir -p "${REPO_ROOT}_worktrees/preexist-wt"
  echo "stale" > "${REPO_ROOT}_worktrees/preexist-wt/stale-file"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"preexist-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  # Script should fail (jj workspace add fails on non-empty target)
  [ "$status" -ne 0 ]
  # cleanup_on_error must remove the pre-existing stale directory
  [ ! -d "${REPO_ROOT}_worktrees/preexist-wt" ]
}

# --- jj lifecycle tests ---

@test "git path: cleanup_on_error skips git worktree remove when WORKSPACE_CREATED is false" {
  # Fail git worktree add (branch already exists) so WORKSPACE_CREATED stays false.
  # Wrap git to log any 'worktree remove' calls; the guard must prevent them.
  local real_git
  real_git="$(command -v git)"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "remove" ]]; then
  echo "worktree-remove-called" >> "${REPO_ROOT}/git-calls.log"
fi
exec "${real_git}" "\$@"
MOCK
  chmod +x "${REPO_ROOT}/bin/git"
  # Create the branch so 'git worktree add -b worktree/guard-test' fails (branch exists)
  git branch "worktree/guard-test"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'cd '"$REPO_ROOT"' && echo "{\"name\": \"guard-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  # Directory must be cleaned up
  [ ! -d "${REPO_ROOT}_worktrees/guard-test" ]
  # git worktree remove must NOT have been called (WORKSPACE_CREATED was false)
  if [[ -f "${REPO_ROOT}/git-calls.log" ]]; then
    [[ "$(cat "${REPO_ROOT}/git-calls.log")" != *"worktree-remove-called"* ]]
  fi
}

@test "git path: cleanup_on_error calls git worktree prune on partial add (WORKSPACE_CREATED=false)" {
  # Mock git: make 'worktree add' fail so WORKSPACE_CREATED stays false,
  # log 'worktree prune' calls, and pass everything else to the real git.
  local real_git
  real_git="$(command -v git)"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "add" ]]; then
  echo "mock: worktree add failed" >&2
  exit 1
fi
if [[ "\$1" == "worktree" && "\$2" == "prune" ]]; then
  echo "worktree-prune-called" >> "${REPO_ROOT}/git-calls.log"
fi
exec "${real_git}" "\$@"
MOCK
  chmod +x "${REPO_ROOT}/bin/git"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'cd '"$REPO_ROOT"' && echo "{\"name\": \"prune-partial-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  # git worktree prune must have been called for the partial add cleanup path
  [ -f "${REPO_ROOT}/git-calls.log" ]
  [[ "$(cat "${REPO_ROOT}/git-calls.log")" == *"worktree-prune-called"* ]]
}

@test "git path: cleanup_on_error warns when git worktree prune fails on partial add" {
  # Mock git: make both 'worktree add' and 'worktree prune' fail to exercise
  # the warning branch at lines 64-65 of worktree-create.sh.
  local real_git
  real_git="$(command -v git)"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "add" ]]; then
  echo "mock: worktree add failed" >&2
  exit 1
fi
if [[ "\$1" == "worktree" && "\$2" == "prune" ]]; then
  echo "mock: prune failed" >&2
  exit 1
fi
exec "${real_git}" "\$@"
MOCK
  chmod +x "${REPO_ROOT}/bin/git"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c \
    'cd '"$REPO_ROOT"' && echo "{\"name\": \"prune-fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"WARNING: cleanup: git worktree prune failed for partial create"* ]]
}

@test "cleanup_on_error warns and skips VCS cleanup when REPO_ROOT is missing" {
  # Patch worktree-create.sh: remove REPO_ROOT then trigger failure so cleanup
  # fires with a missing REPO_ROOT directory, exercising lines 32-33.
  # We replace "trap - EXIT" with a two-line snippet that deletes REPO_ROOT
  # first, then exits non-zero to fire the EXIT trap.
  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's|^trap - EXIT  # disarm after success$|rm -rf "$REPO_ROOT"; false|' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  run bash -c \
    'echo "{\"name\": \"missing-root-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WARNING: cleanup: REPO_ROOT"*"missing — VCS workspace cleanup skipped"* ]]
}

@test "jj path: cleanup_on_error warns and skips VCS cleanup when REPO_ROOT is missing" {
  # Same patch strategy as the git variant: replace "trap - EXIT" with a two-line
  # snippet that deletes REPO_ROOT first, then exits non-zero to fire the EXIT trap.
  # With setup_jj active, .jj/ exists inside REPO_ROOT, but because the REPO_ROOT
  # missing check is first in cleanup_on_error, the same WARNING fires.
  setup_jj
  create_logging_jj_mock
  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's|^trap - EXIT  # disarm after success$|rm -rf "$REPO_ROOT"; false|' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"missing-root-jj-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WARNING: cleanup: REPO_ROOT"*"missing — VCS workspace cleanup skipped"* ]]
}

@test "CLEANUP_FAILED promotes exit code from 0 to 1 when rm -rf fails after successful workspace add" {
  # Verify the exit-code promotion at lines 79-81 of worktree-create.sh:
  #   if [[ "$CLEANUP_FAILED" == "true" ]] && [[ $_exit_code -eq 0 ]]; then
  #     _exit_code=1
  #   fi
  # Scenario: workspace add succeeds (so _exit_code=0 when EXIT trap fires),
  # but rm -rf in cleanup_on_error fails (setting CLEANUP_FAILED=true).
  # The exit code must be promoted from 0 to 1.
  setup_jj
  create_mock_jj

  # Resolve real rm before creating mock bin
  local real_rm
  real_rm="$(command -v rm)"

  local mock_bin
  mock_bin=$(mktemp -d)

  # Mock rm: fail on -rf (cleanup's rm -rf call); delegate everything else.
  cat > "${mock_bin}/rm" << MOCK
#!/bin/bash
if [[ "\$1" == "-rf" ]]; then
  echo "rm: \$2: Operation not permitted" >&2
  exit 1
fi
exec "${real_rm}" "\$@"
MOCK
  chmod +x "${mock_bin}/rm"

  # Patch the script: replace "trap - EXIT" with "exit 0" so the EXIT trap
  # fires with _exit_code=0 (workspace add succeeded), then rm -rf fails
  # (CLEANUP_FAILED=true), triggering the promotion to exit code 1.
  local patched
  patched=$(mktemp "$BATS_TEST_TMPDIR/worktree-create-${BATS_TEST_NUMBER}-XXXXXX.sh")
  ln -sf "$BATS_TEST_DIRNAME/../worktree-helpers.sh" "$BATS_TEST_TMPDIR/worktree-helpers.sh"
  trap 'rm -f "$patched"' RETURN
  sed 's/^trap - EXIT  # disarm after success$/exit 0/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:${mock_bin}:$PATH" run bash -c \
    'echo "{\"name\": \"promote-exit-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  rm -rf "$mock_bin"
  # Exit code must be 1 (promoted from 0 due to CLEANUP_FAILED=true)
  [ "$status" -eq 1 ]
  [[ "$output" == *"WARNING: cleanup failed for"* ]]
}

@test "jj path: cleanup preserves non-zero exit code when both workspace add and rm -rf fail" {
  # Exercises the exit-code preservation logic at lines 79-84 of worktree-create.sh:
  #   if [[ "$CLEANUP_FAILED" == "true" ]] && [[ $_exit_code -eq 0 ]]; then
  #     _exit_code=1
  #   fi
  # When workspace add FAILS (_exit_code != 0) and rm -rf also fails
  # (CLEANUP_FAILED=true), the exit code must NOT be promoted — the original
  # non-zero exit code from workspace add is preserved.
  setup_jj
  create_failing_jj_mock

  # Resolve real rm before creating mock bin
  local real_rm
  real_rm="$(command -v rm)"

  local mock_bin
  mock_bin=$(mktemp -d)

  # Mock rm: fail on -rf (the cleanup rm -rf call); delegate everything else.
  cat > "${mock_bin}/rm" << MOCK
#!/bin/bash
if [[ "\$1" == "-rf" ]]; then
  echo "rm: \$2: Operation not permitted" >&2
  exit 1
fi
exec "${real_rm}" "\$@"
MOCK
  chmod +x "${mock_bin}/rm"

  PATH="${MOCK_JJ_BIN_DIR}:${mock_bin}:$PATH" run bash -c \
    'echo "{\"name\": \"jj-add-rm-fail-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  rm -rf "$mock_bin"
  # Exit code must be non-zero (from workspace add failure — NOT promoted)
  [ "$status" -ne 0 ]
  # WARNING about cleanup failure must appear on stderr
  [[ "$output" == *"WARNING: cleanup failed for"* ]]
}

@test "git path: create-then-remove lifecycle uses consistent branch names" {
  # Create
  run bash -c 'echo "{\"name\": \"git-lifecycle-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [ -d "${REPO_ROOT}_worktrees/git-lifecycle-wt" ]
  # Verify git worktree was created with expected branch
  git worktree list | grep -q "git-lifecycle-wt"
  # Remove
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/git-lifecycle-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/git-lifecycle-wt" ]
  # Verify git worktree list no longer shows it
  ! git worktree list | grep -q "git-lifecycle-wt"
}

@test "jj path: create-then-remove lifecycle uses consistent workspace names" {
  setup_jj
  create_logging_jj_mock
  # Create
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"lifecycle-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [ -d "${REPO_ROOT}_worktrees/lifecycle-wt" ]
  # Verify --name worktree-lifecycle-wt was passed to jj workspace add
  [[ "$(cat "${REPO_ROOT}/jj-args.log")" == *"--name worktree-lifecycle-wt"* ]]
  # Remove
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/lifecycle-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/lifecycle-wt" ]
  # Verify jj workspace forget was called with the same workspace name
  [ -f "${REPO_ROOT}/forget-arg.log" ]
  [[ "$(cat "${REPO_ROOT}/forget-arg.log")" == "worktree-lifecycle-wt" ]]
}
