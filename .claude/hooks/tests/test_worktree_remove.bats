#!/usr/bin/env bats

setup() {
  export REPO_ROOT=$(mktemp -d)
  cd "$REPO_ROOT"
  git init -q
  git commit --allow-empty -m "init" -q
  mkdir -p "${REPO_ROOT}_worktrees/test-wt"
  git worktree add "${REPO_ROOT}_worktrees/test-wt" -b worktree/test-wt HEAD -q
}

teardown() {
  cd /
  git -C "$REPO_ROOT" worktree remove --force "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
  rm -rf "$REPO_ROOT" "${REPO_ROOT}_worktrees"
}

@test "removes valid worktree" {
  [ -d "${REPO_ROOT}_worktrees/test-wt" ]
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-wt" ]
}

@test "falls back to rm when git worktree remove fails" {
  # Create a plain directory (not a real worktree) to force git worktree remove failure
  git -C "$REPO_ROOT" worktree remove --force "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
  mkdir -p "${REPO_ROOT}_worktrees/test-wt"
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-wt" ]
}

@test "rejects path outside expected parent" {
  mkdir -p /tmp/evil-test-dir
  run bash -c 'echo "{\"path\": \"/tmp/evil-test-dir\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"outside expected parent"* || "$output" == *"invalid worktree name"* ]]
  rmdir /tmp/evil-test-dir 2>/dev/null || true
}

@test "exits cleanly for nonexistent path" {
  run bash -c 'echo "{\"path\": \"/nonexistent\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
}

@test "rejects names with shell metacharacters" {
  evil_path="${REPO_ROOT}_worktrees/evil;rm"
  mkdir -p "$evil_path"
  run bash -c 'echo "{\"path\": \"'"$evil_path"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid worktree name"* ]]
  rmdir "$evil_path" 2>/dev/null || true
}

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
if [[ "$1" == "workspace" && "$2" == "forget" && "$3" == worktree-* ]]; then exit 0; fi
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: warns but still removes directory when jj not installed" {
  setup_jj_worktree
  PATH="/usr/bin:/bin" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
  [[ "$output" == *"WARNING"* ]]
}

@test "jj path: handles workspace forget failure" {
  setup_jj_worktree
  mkdir -p "${REPO_ROOT}/bin"
  cat > "${REPO_ROOT}/bin/jj" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "${REPO_ROOT}/bin/jj"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}
