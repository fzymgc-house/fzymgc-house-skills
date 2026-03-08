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
  # Mock jj that responds to 'root' with the directory path
  mkdir -p "${NON_GIT}/bin"
  cat > "${NON_GIT}/bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${NON_GIT}"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "add" && "\$3" == "--help" ]]; then
  echo "  --name <NAME>"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2
  for arg in "\$@"; do
    case "\$arg" in
      -*) ;;
      *) mkdir -p "\$arg"; exit 0 ;;
    esac
  done
fi
exit 1
MOCK
  chmod +x "${NON_GIT}/bin/jj"
  PATH="${NON_GIT}/bin:$PATH" run bash -c 'cd '"$NON_GIT"' && echo "{\"name\": \"jj-root-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
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
  # Mock that logs all args so we can verify --name was passed
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "  --name <NAME>"
  exit 0
fi
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  echo "$@" > "${REPO_ROOT}/jj-args.log"
  mkdir -p "$3"
  exit 0
fi
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"named-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
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

@test "git path: cleans up empty parent on worktree add failure" {
  git branch "worktree/fail-test"
  run bash -c 'echo "{\"name\": \"fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  [ ! -d "${REPO_ROOT}_worktrees/fail-test" ]
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
