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

@test "git path: continues to rm-rf when both git worktree remove and prune fail" {
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
  [[ "$output" == *"stale metadata"* ]]
}

@test "cleans up empty parent directory after removal" {
  [ -d "${REPO_ROOT}_worktrees/test-wt" ]
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees" ]
}

@test "rejects path outside expected parent with exit 1" {
  mkdir -p /tmp/evil-test-dir
  run bash -c 'echo "{\"path\": \"/tmp/evil-test-dir\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"outside expected parent"* ]]
  rmdir /tmp/evil-test-dir 2>/dev/null || true
}

@test "exits cleanly for nonexistent path" {
  run bash -c 'echo "{\"path\": \"/nonexistent\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
}

@test "exits cleanly for empty path field" {
  run bash -c 'echo "{\"path\": \"\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"no path field"* ]]
}

@test "exits cleanly when path key is absent from input" {
  run bash -c 'echo "{}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"no path field"* ]]
}

@test "warns but proceeds for names with shell metacharacters" {
  evil_path="${REPO_ROOT}_worktrees/evil;rm"
  mkdir -p "$evil_path"
  run bash -c 'echo "{\"path\": \"'"$evil_path"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"unusual characters"* ]]
  [ ! -d "$evil_path" ]
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
  # Remove the git worktree from setup() so only test-jj-wt remains
  git -C "$REPO_ROOT" worktree remove --force "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
  rm -rf "${REPO_ROOT}_worktrees/test-wt" 2>/dev/null || true
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
  # Mock jj: root and workspace list succeed, but workspace forget fails
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "default: rlvkpntz abc12345 (empty) (no description set)"
  echo "worktree-test-jj-wt: kkmpptqz def45678 (empty) (no description set)"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  echo "Error: workspace forget failed for some reason" >&2
  exit 1
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
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

@test "errors when _worktrees parent dir does not exist" {
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
  # which doesn't exist — realpath should fail with exit 1 (inconsistent state)
  run bash -c 'echo "{\"path\": \"'"${ALT_ROOT}_other/some-worktree"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"inconsistent state"* ]]
  cd /
  rm -rf "$ALT_ROOT" "${ALT_ROOT}_other"
}

@test "infers repo root from worktree path when outside git repo" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}_worktrees/orphan-wt"
  run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/orphan-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"inferred repo root"* ]]
  [[ "$output" == *"skipping VCS cleanup"* ]]
  [ ! -d "${NON_GIT}_worktrees/orphan-wt" ]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

@test "inferred root with .jj/ but jj not installed: warns and still removes directory" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  mkdir -p "${NON_GIT}_worktrees/orphan-jj-wt"
  PATH="/usr/bin:/bin" run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/orphan-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"jj not installed"* ]]
  [ ! -d "${NON_GIT}_worktrees/orphan-jj-wt" ]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

@test "inferred root with .jj/ and jj installed: removes directory and calls workspace forget" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  mkdir -p "${NON_GIT}_worktrees/orphan-jj-wt"
  # Mock jj: 'root' returns NON_GIT, 'workspace forget' logs the workspace name
  mkdir -p "${NON_GIT}/bin"
  cat > "${NON_GIT}/bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${NON_GIT}"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "default: rlvkpntz abc12345 (empty) (no description set)"
  echo "worktree-orphan-jj-wt: kkmpptqz def45678 (empty) (no description set)"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  shift 2
  for arg in "\$@"; do
    case "\$arg" in
      -*) ;;
      worktree-*) echo "\$arg" > "${NON_GIT}/forget-arg.log"; exit 0 ;;
    esac
  done
  exit 1
fi
exit 1
MOCK
  chmod +x "${NON_GIT}/bin/jj"
  PATH="${NON_GIT}/bin:/usr/bin:/bin" run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/orphan-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  # No WARNING expected: mock jj root succeeds, so detect_repo_root finds the
  # repo directly (no inference fallback). The key assertions are: directory
  # removed + workspace forget called with the correct name.
  [ ! -d "${NON_GIT}_worktrees/orphan-jj-wt" ]
  [ -f "${NON_GIT}/forget-arg.log" ]
  [[ "$(cat "${NON_GIT}/forget-arg.log")" == "worktree-orphan-jj-wt" ]]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

@test "inferred root with .jj/ and jj installed: workspace forget called when detect_repo_root fails" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  mkdir -p "${NON_GIT}_worktrees/inferred-jj-wt"
  # Mock jj: 'root' exits 1 so detect_repo_root fails and triggers path inference;
  # 'workspace list' returns a line containing the workspace name;
  # 'workspace forget' logs the workspace name and exits 0.
  mkdir -p "${NON_GIT}/bin"
  cat > "${NON_GIT}/bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  exit 1
fi
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "worktree-inferred-jj-wt: kkmpptqz def45678 (empty) (no description set)"
  exit 0
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  shift 2
  for arg in "\$@"; do
    case "\$arg" in
      -*) ;;
      worktree-*) echo "\$arg" > "${NON_GIT}/forget-arg.log"; exit 0 ;;
    esac
  done
  exit 1
fi
exit 1
MOCK
  chmod +x "${NON_GIT}/bin/jj"
  # Run from /tmp so detect_repo_root fails (no git/jj repo in cwd)
  PATH="${NON_GIT}/bin:/usr/bin:/bin" run bash -c 'cd /tmp && echo "{\"path\": \"'"${NON_GIT}_worktrees/inferred-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"inferred repo root"* ]]
  [ ! -d "${NON_GIT}_worktrees/inferred-jj-wt" ]
  [ -f "${NON_GIT}/forget-arg.log" ]
  [[ "$(cat "${NON_GIT}/forget-arg.log")" == "worktree-inferred-jj-wt" ]]
  rm -rf "$NON_GIT" "${NON_GIT}_worktrees"
}

@test "errors when parent dir has no _worktrees suffix" {
  NON_GIT=$(mktemp -d)
  # Parent dir name does NOT end in _worktrees — fail-safe refuses removal
  mkdir -p "${NON_GIT}/random-dir/some-worktree"
  run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}/random-dir/some-worktree"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR"* ]]
  [[ "$output" == *"refusing removal for safety"* ]]
  # Directory must still exist (fail-safe did not remove it)
  [ -d "${NON_GIT}/random-dir/some-worktree" ]
  rm -rf "$NON_GIT"
}

@test "reports error when rm -rf fails to remove worktree directory" {
  # Make the worktree directory unremovable by removing write permission on parent
  [ -d "${REPO_ROOT}_worktrees/test-wt" ]
  chmod a-w "${REPO_ROOT}_worktrees"
  run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  chmod a+w "${REPO_ROOT}_worktrees"
  [ "$status" -eq 1 ]
  [[ "$output" == *"failed to remove worktree directory"* ]]
}

@test "jj path: reports error when rm -rf fails to remove worktree directory" {
  setup_jj_worktree
  create_mock_jj
  chmod a-w "${REPO_ROOT}_worktrees"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  chmod a+w "${REPO_ROOT}_worktrees"
  [ "$status" -eq 1 ]
  [[ "$output" == *"failed to remove worktree directory"* ]]
}

@test "jj path: warns and skips forget when jj workspace list fails" {
  setup_jj_worktree
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "Error: workspace list failed" >&2
  exit 1
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"jj workspace list failed"* ]]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "jj path: warns and skips forget when workspace not in list" {
  setup_jj_worktree
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "default: rlvkpntz abc12345 (empty) (no description set)"
  echo "worktree-other-wt: ssttuuvv xyz78901 (empty) (no description set)"
  exit 0
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"not found in jj workspace list"* ]]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
}

@test "infers repo root when jj root returns empty in pure-jj repo" {
  NON_GIT=$(mktemp -d)
  mkdir -p "${NON_GIT}/.jj"
  mkdir -p "${NON_GIT}_worktrees/orphan-jj-wt"
  # Mock jj that is installed but returns empty for 'root'
  mkdir -p "${NON_GIT}/bin"
  cat > "${NON_GIT}/bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then echo ""; exit 0; fi
if [[ "$1" == "workspace" && "$2" == "forget" ]]; then exit 0; fi
exit 1
MOCK
  chmod +x "${NON_GIT}/bin/jj"
  PATH="${NON_GIT}/bin:/usr/bin:/bin" run bash -c 'cd '"$NON_GIT"' && echo "{\"path\": \"'"${NON_GIT}_worktrees/orphan-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"inferred repo root"* ]]
  [ ! -d "${NON_GIT}_worktrees/orphan-jj-wt" ]
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

# --- colocated jj+git repo tests ---

@test "colocated jj+git: removes workspace via jj path when both .jj and .git present" {
  setup_jj_worktree
  create_logging_jj_mock
  # Both .jj/ and .git/ exist — script should take jj path and call jj workspace forget
  PATH="${MOCK_JJ_BIN_DIR}:$PATH" run bash -c 'echo "{\"path\": \"'"${REPO_ROOT}_worktrees/test-jj-wt"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh'
  [ "$status" -eq 0 ]
  [ ! -d "${REPO_ROOT}_worktrees/test-jj-wt" ]
  # Verify jj workspace forget was called (not git worktree remove)
  [ -f "${REPO_ROOT}/forget-arg.log" ]
  [[ "$(cat "${REPO_ROOT}/forget-arg.log")" == "worktree-test-jj-wt" ]]
}

@test "POSIX fallback: removes worktree when realpath unavailable" {
  # This test exercises the cd+pwd-P fallback paths (lines 30-36 and 81-83
  # of worktree-remove.sh) that run when realpath is not in PATH.
  # On ubuntu-latest (CI), realpath is always present in /usr/bin, so the test
  # self-skips there. Run manually on a POSIX-minimal system to verify coverage.
  command -v realpath &>/dev/null && skip "realpath is available — POSIX fallback cannot be tested on this system"

  ALT_ROOT=$(mktemp -d)
  cd "$ALT_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  mkdir -p "${ALT_ROOT}_worktrees/posix-test"
  git worktree add "${ALT_ROOT}_worktrees/posix-test" -b worktree/posix-test HEAD -q

  run bash -c 'echo "{\"path\": \"'"${ALT_ROOT}_worktrees/posix-test"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${ALT_ROOT}_worktrees/posix-test" ]

  cd /
  rm -rf "$ALT_ROOT" "${ALT_ROOT}_worktrees"
}

@test "POSIX fallback: removes worktree when realpath absent from PATH" {
  # Build a curated PATH that excludes realpath to exercise the POSIX
  # fallback (cd + pwd -P) on systems where realpath is normally available.
  local clean_bin
  clean_bin=$(mktemp -d)
  local cmd cmd_path
  for cmd in bash git rm rmdir ls dirname basename cat mkdir chmod jq tr mktemp; do
    cmd_path=$(command -v "$cmd" 2>/dev/null) || continue
    ln -sf "$cmd_path" "$clean_bin/$cmd"
  done
  # Verify realpath is NOT in clean_bin
  [[ ! -x "$clean_bin/realpath" ]]

  ALT_ROOT=$(mktemp -d)
  cd "$ALT_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  mkdir -p "${ALT_ROOT}_worktrees/posix-mock-test"
  git worktree add "${ALT_ROOT}_worktrees/posix-mock-test" -b worktree/posix-mock-test HEAD -q

  PATH="$clean_bin" run bash -c \
    'echo "{\"path\": \"'"${ALT_ROOT}_worktrees/posix-mock-test"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 0 ]
  [ ! -d "${ALT_ROOT}_worktrees/posix-mock-test" ]

  cd /
  rm -rf "$ALT_ROOT" "${ALT_ROOT}_worktrees" "$clean_bin"
}

@test "POSIX fallback: errors when _worktrees parent dir does not exist" {
  # Combine the POSIX fallback path (no realpath) with the missing EXPECTED_PARENT
  # condition, so that the cd+pwd -P branch on line 87 of worktree-remove.sh is
  # exercised and produces the "inconsistent state" error.
  local clean_bin
  clean_bin=$(mktemp -d)
  local cmd cmd_path
  for cmd in bash git rm rmdir ls dirname basename cat mkdir chmod jq tr mktemp; do
    cmd_path=$(command -v "$cmd" 2>/dev/null) || continue
    ln -sf "$cmd_path" "$clean_bin/$cmd"
  done
  # Verify realpath is NOT in clean_bin
  [[ ! -x "$clean_bin/realpath" ]]

  ALT_ROOT=$(mktemp -d)
  cd "$ALT_ROOT"
  git init -q
  git -c commit.gpgsign=false commit --allow-empty -m "init" -q
  # Place the worktree dir under a differently-named parent — NOT ${REPO_NAME}_worktrees
  mkdir -p "${ALT_ROOT}_other/some-worktree"

  PATH="$clean_bin" run bash -c \
    'echo "{\"path\": \"'"${ALT_ROOT}_other/some-worktree"'\"}" | bash '"$BATS_TEST_DIRNAME"'/../worktree-remove.sh 2>&1'
  [ "$status" -eq 1 ]
  [[ "$output" == *"inconsistent state"* ]]

  cd /
  rm -rf "$ALT_ROOT" "${ALT_ROOT}_other" "$clean_bin"
}
