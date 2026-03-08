#!/usr/bin/env bats

load helpers

setup() {
  export REPO_ROOT=$(mktemp -d)
  cd "$REPO_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
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

@test "git path: surfaces warning when git worktree remove fails" {
  git -C "$REPO_ROOT" worktree remove --force "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
  mkdir -p "${REPO_ROOT}_worktrees/test-wt"
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-wt" ]
  [[ "$output" == *"WARNING"* ]]
}

@test "git path: emits second warning when git worktree prune also fails" {
  # Remove the real worktree so we have a plain directory
  git -C "$REPO_ROOT" worktree remove --force "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
  mkdir -p "${REPO_ROOT}_worktrees/test-wt"
  # Mock git that delegates rev-parse to real git but fails worktree ops
  local real_git
  real_git="$(command -v git)"
  mkdir -p "${REPO_ROOT}/bin"
  # Write mock with real git path baked in (unquoted heredoc expands vars)
  cat > "${REPO_ROOT}/bin/git" <<GITEOF
#!/bin/bash
case "\$1:\$2" in
  rev-parse:*) exec ${real_git} "\$@" ;;
  worktree:remove) echo "mock remove failure" >&2; exit 1 ;;
  worktree:prune) echo "mock prune failure" >&2; exit 1 ;;
  *) exec ${real_git} "\$@" ;;
esac
GITEOF
  chmod +x "${REPO_ROOT}/bin/git"
  PATH="${REPO_ROOT}/bin:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-wt" ]
  [[ "$output" == *"git worktree remove failed"* ]]
  [[ "$output" == *"git worktree prune also failed"* ]]
}

@test "cleans up empty parent directory after removal" {
  [ -d "${REPO_ROOT}_worktrees/test-wt" ]
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
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

@test "rejects symlinked path resolving outside expected parent" {
  mkdir -p "${REPO_ROOT}_worktrees"
  ln -s /tmp "${REPO_ROOT}_worktrees/evil-link"
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/evil-link"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"outside expected parent"* ]]
  rm -f "${REPO_ROOT}_worktrees/evil-link"
  rmdir "${REPO_ROOT}_worktrees" 2>/dev/null || true
}

# --- jj code path tests ---

setup_jj_worktree() {
  mkdir -p "${REPO_ROOT}/.jj"
  mkdir -p "${REPO_ROOT}_worktrees/test-jj-wt"
}

@test "jj path: removes workspace directory" {
  setup_jj_worktree
  create_mock_jj
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: cleans up empty parent directory after removal" {
  setup_jj_worktree
  create_mock_jj
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "jj path: calls jj workspace forget with correct name" {
  setup_jj_worktree
  create_logging_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
  [[ "$(cat "${REPO_ROOT}/forget-arg.log")" == "worktree-test-jj-wt" ]]
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
  create_always_failing_jj_mock
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"jj workspace forget failed"* ]]
}

@test "rejects repo directory name with spaces" {
  UNSAFE_ROOT=$(mktemp -d)/repo\ with\ spaces
  mkdir -p "$UNSAFE_ROOT"
  cd "$UNSAFE_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  mkdir -p "${UNSAFE_ROOT}_worktrees/test-wt"
  run bash -c 'echo "{\"path\": \"'"${UNSAFE_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid repository directory name"* ]]
  cd /
  rm -rf "$(dirname "$UNSAFE_ROOT")" "${UNSAFE_ROOT}_worktrees"
}

@test "exits cleanly when _worktrees parent dir does not exist" {
  # Set up a repo whose _worktrees sibling doesn't exist, but the worktree
  # path is inside a differently-named parent that DOES exist.
  # This triggers the realpath failure on EXPECTED_PARENT.
  ALT_ROOT=$(mktemp -d)
  cd "$ALT_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  # Create a worktree dir under a different name (not ${REPO_NAME}_worktrees)
  mkdir -p "${ALT_ROOT}_other/some-worktree"
  # The script computes EXPECTED_PARENT as ${REPO_PARENT}/${REPO_NAME}_worktrees
  # which doesn't exist — realpath should fail gracefully
  run bash -c 'echo "{\"path\": \"'"${ALT_ROOT}_other/some-worktree"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  cd /
  rm -rf "$ALT_ROOT" "${ALT_ROOT}_other"
}

@test "fails when git rev-parse cannot determine repo root" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}_worktrees/orphan-wt"
  run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/orphan-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"could not determine repo root"* ]]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

@test "detect_repo_root falls back to jj root when git rev-parse fails" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  mkdir -p "${NON_GIT}_worktrees/jj-fallback-wt"
  # Mock jj that responds to 'root' with the directory path and handles 'workspace forget'
  mkdir -p "${NON_GIT}/bin"
  cat > "${NON_GIT}/bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${NON_GIT}"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  exit 0
fi
exit 1
MOCK
  chmod +x "${NON_GIT}/bin/jj"
  PATH="${NON_GIT}/bin:$PATH" run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/jj-fallback-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${NON_GIT}_worktrees/jj-fallback-wt" ]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}
