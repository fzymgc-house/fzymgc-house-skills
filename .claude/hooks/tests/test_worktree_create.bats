#!/usr/bin/env bats

setup() {
  export REPO_ROOT=$(mktemp -d)
  cd "$REPO_ROOT"
  git init -q
  git commit --allow-empty -m "init" -q
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

# --- jj code path tests ---

setup_jj() {
  mkdir -p "${REPO_ROOT}/.jj"
}

@test "jj path: rejects when jj not installed" {
  setup_jj
  PATH="/usr/bin:/bin" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"jj is not installed"* ]]
}

@test "jj path: creates workspace with mock jj" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # Handle --help: return output that satisfies --name version guard
  if [[ "$3" == "--help" ]]; then
    echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
    echo "  --name <NAME>"
    exit 0
  fi
  mkdir -p "$3"
  exit 0
fi
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"test-jj-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/test-jj-wt"* ]]
}

@test "jj path: cleans up on jj workspace add failure" {
  setup_jj
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "  --name <NAME>"
  exit 0
fi
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"fail-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 1 ]
  [ ! -d "${REPO_ROOT}_worktrees/fail-wt" ]
}

@test "git path: cleans up empty parent on worktree add failure" {
  git branch "worktree/fail-test"
  run bash -c 'echo "{\"name\": \"fail-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  [ ! -d "${REPO_ROOT}_worktrees/fail-test" ]
}

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
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"test-wt\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"--name"* ]]
}

# --- lefthook integration tests ---

@test "runs lefthook install when lefthook.yml exists" {
  touch "${REPO_ROOT}/lefthook.yml"
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/lefthook" << 'MOCK'
#!/bin/bash
echo "lefthook-installed"
MOCK
  chmod +x "${REPO_ROOT}/bin/lefthook"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"name\": \"hook-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
  [[ "$output" == *"_worktrees/hook-test"* ]]
}

@test "skips lefthook install when lefthook.yml absent" {
  run bash -c 'echo "{\"name\": \"no-hook-test\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-create.sh'
  [ "$status" -eq 0 ]
}
