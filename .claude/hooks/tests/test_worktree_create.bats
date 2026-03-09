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

@test "rejects names with trailing dot" {
  run bash -c 'echo "{\"name\": \"agent-abc.\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
}

@test "rejects empty name" {
  run bash -c 'echo "{\"name\": \"\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
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
    'cd '"$NON_GIT"' && echo "{\"name\": \"jj-root-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
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
  PATH="/usr/bin:/bin" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj is not installed"* ]]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: creates workspace with mock jj" {
  setup_jj
  create_mock_jj
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/test-jj-wt"* ]]
  [ -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: forwards --name flag to jj workspace add" {
  setup_jj
  create_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"named-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  # Verify the logged args contain --name worktree-named-wt
  [[ "$(cat "${REPO_ROOT}/jj-args.log")" == *"--name worktree-named-wt"* ]]
}

@test "jj path: cleans up worktree and parent on workspace add failure" {
  setup_jj
  create_failing_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"fail-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/fail-wt" ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: does NOT call jj workspace forget when workspace add fails (WORKSPACE_CREATED guard)" {
  setup_jj
  create_failing_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"no-forget-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/no-forget-wt" ]
  [ ! -f "${REPO_ROOT}/forget-called.log" ]
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
  patched="$BATS_TEST_DIRNAME/../worktree-create-test-patched.sh"
  sed 's/^trap - EXIT$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c \
    'echo "{\"name\": \"forget-wt\"}" | bash '"$patched"
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # cleanup_on_error should have called jj workspace forget with the workspace name
  [ -f "${REPO_ROOT}/forget-arg.log" ]
  [[ "$(cat "${REPO_ROOT}/forget-arg.log")" == "worktree-forget-wt" ]]
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
  patched="$BATS_TEST_DIRNAME/../worktree-create-test-patched.sh"
  sed 's/^trap - EXIT$/false/' "$BATS_TEST_DIRNAME/../worktree-create.sh" > "$patched"
  run bash -c \
    'echo "{\"name\": \"git-cleanup-wt\"}" | bash '"$patched"' 2>&1'
  rm -f "$patched"
  [ "$status" -ne 0 ]
  # cleanup_on_error should have removed the worktree directory
  [ ! -d "${REPO_ROOT}_worktrees/git-cleanup-wt" ]
  # Parent dir should also be cleaned up if empty
  [ ! -d "${REPO_ROOT}_worktrees" ]
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

@test "jj path: exits with error when jj workspace add --help fails" {
  setup_jj
  create_always_failing_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"name\": \"help-fail\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj failed to run"* ]]
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

@test "fails gracefully when mkdir -p fails" {
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
}

@test "git path: mkdir -p failure exits 1 with descriptive error message" {
  SANDBOX=$(mktemp -d)
  NESTED="${SANDBOX}/repos/myrepo"
  mkdir -p "$NESTED"
  cd "$NESTED"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  chmod a-w "${SANDBOX}/repos"
  run bash -c 'echo "{\"name\": \"mkdir-msg-git\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
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

# --- jj lifecycle tests ---

@test "git path: cleanup_on_error skips git worktree remove when WORKSPACE_CREATED is false" {
  # Fail git worktree add (branch already exists) so WORKSPACE_CREATED stays false.
  # Wrap git to log any 'worktree remove' calls; the guard must prevent them.
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/git" << MOCK
#!/bin/bash
if [[ "\$1" == "worktree" && "\$2" == "remove" ]]; then
  echo "worktree-remove-called" >> "${REPO_ROOT}/git-calls.log"
fi
exec $(which git) "\$@"
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
