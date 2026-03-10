#!/usr/bin/env bats

# Tests for shared helpers in worktree-helpers.sh

load helpers

setup() {
  export REPO_ROOT=$(mktemp -d)
  # shellcheck source=.claude/hooks/worktree-helpers.sh
  source "${BATS_TEST_DIRNAME}/../worktree-helpers.sh"
}

teardown() {
  rm -rf "$REPO_ROOT"
}

# --- sanitize_for_output tests ---

@test "sanitize_for_output: passes normal text unchanged" {
  result=$(sanitize_for_output "hello world")
  [ "$result" = "hello world" ]
}

@test "sanitize_for_output: strips C0 control characters" {
  # Null bytes (\x00) cannot survive bash command substitution or argument
  # passing, so they are untestable here. Test other C0 control chars instead.
  input=$(printf 'he\x01ll\x1Fo')
  result=$(sanitize_for_output "$input")
  [ "$result" = "hello" ]
}

@test "sanitize_for_output: preserves newlines" {
  # Newlines (0x0A) are preserved for multi-line error readability.
  input=$(printf 'line1\nline2')
  result=$(sanitize_for_output "$input")
  [[ "$result" == *$'\n'* ]]
  [ "$result" = "$(printf 'line1\nline2')" ]
}

@test "sanitize_for_output: strips ESC byte from ANSI escape sequences" {
  # sanitize_for_output strips C0 controls (0x00-0x1F) including ESC (0x1B).
  # The printable remainder of an ANSI sequence ([31m) passes through.
  input=$(printf '\033[31mred text\033[0m')
  result=$(sanitize_for_output "$input")
  # ESC byte must be absent
  [[ "$result" != *$'\033'* ]]
  # Printable parts of the sequence survive (this is the defined behavior)
  [[ "$result" == *"red text"* ]]
}

@test "sanitize_for_output: strips DEL character (0x7F)" {
  input=$(printf 'hel\x7flo')
  result=$(sanitize_for_output "$input")
  [ "$result" = "hello" ]
}

@test "sanitize_for_output: preserves tab and carriage-return" {
  # Tab (0x09) and CR (0x0D) are excluded from the C0 strip range and must survive.
  input=$(printf 'col1\tcol2\r\n')
  result=$(sanitize_for_output "$input")
  [[ "$result" == *$'\t'* ]]
  [[ "$result" == *$'\r'* ]]
}

@test "sanitize_for_output: passes through alphanumeric and punctuation" {
  result=$(sanitize_for_output "abc-123_XYZ.test/path:value")
  [ "$result" = "abc-123_XYZ.test/path:value" ]
}

# --- validate_safe_name tests ---

@test "validate_safe_name: accepts valid alphanumeric-hyphen name" {
  run validate_safe_name "agent-abc123" "worktree name"
  [ "$status" -eq 0 ]
}

@test "validate_safe_name: rejects empty name" {
  run validate_safe_name "" "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"must not be empty"* ]]
}

@test "validate_safe_name: rejects leading-dot name" {
  run validate_safe_name ".hidden" "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects trailing-dot name" {
  run validate_safe_name "agent." "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects dotdot component" {
  run validate_safe_name "a..b" "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects name with space" {
  run validate_safe_name "has space" "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects name with shell metacharacter" {
  run validate_safe_name "evil;rm" "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: accepts name with dots and underscores" {
  run validate_safe_name "fix.worker_v2" "worktree name"
  [ "$status" -eq 0 ]
}

@test "validate_safe_name: rejects name with embedded newline" {
  run validate_safe_name $'test\nname' "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects name with embedded tab" {
  run validate_safe_name $'test\tname' "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: rejects name with C0 control character" {
  run validate_safe_name $'test\x01name' "worktree name"
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
}

@test "validate_safe_name: sanitizes control characters in label when name is invalid" {
  run validate_safe_name "bad name" $'wt\x07label'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
  # Raw BEL character must not appear in output
  [[ ! "$output" =~ $'\x07' ]]
}

@test "validate_safe_name: sanitizes control characters in both name and label output" {
  run validate_safe_name $'bad\x01name' $'wt\x02label'
  [ "$status" -eq 1 ]
  [[ "$output" == *"invalid"* ]]
  # Neither raw SOH nor raw STX should appear in output
  [[ ! "$output" =~ $'\x01' ]]
  [[ ! "$output" =~ $'\x02' ]]
}

# --- cleanup_empty_parent tests ---

@test "cleanup_empty_parent: removes empty directory" {
  local empty_dir="${REPO_ROOT}/empty-parent"
  mkdir -p "$empty_dir"
  cleanup_empty_parent "$empty_dir"
  [ ! -d "$empty_dir" ]
}

@test "cleanup_empty_parent: leaves non-empty directory" {
  local nonempty_dir="${REPO_ROOT}/nonempty-parent"
  mkdir -p "${nonempty_dir}/child"
  cleanup_empty_parent "$nonempty_dir"
  [ -d "$nonempty_dir" ]
  [ -d "${nonempty_dir}/child" ]
}

@test "cleanup_empty_parent: no-ops when directory does not exist" {
  run cleanup_empty_parent "${REPO_ROOT}/nonexistent-parent"
  [ "$status" -eq 0 ]
}

@test "cleanup_empty_parent: warns when ls fails (permission error)" {
  local unreadable_dir="${REPO_ROOT}/unreadable-parent"
  mkdir -p "$unreadable_dir"
  chmod a-rx "$unreadable_dir"
  # bats-core 1.5+ captures both stdout and stderr in $output by default
  run cleanup_empty_parent "$unreadable_dir"
  chmod a+rx "$unreadable_dir"
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
}

@test "cleanup_empty_parent warns when rmdir fails (permission error)" {
  local parent="$BATS_TEST_TMPDIR/rmdir-test-parent"
  local child="$parent/empty-child"
  mkdir -p "$child"
  # Remove write permission so rmdir fails
  chmod a-w "$parent"
  run cleanup_empty_parent "$child"
  chmod u+w "$parent"  # restore for cleanup
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"failed to remove empty parent"* ]]
}

# --- detect_repo_root tests ---

@test "detect_repo_root: falls through to error when jj root returns a file path (non-directory)" {
  local non_git_dir="${REPO_ROOT}/no-git"
  mkdir -p "${non_git_dir}/bin"
  # Create a mock jj whose 'root' command returns a regular file path, not a directory.
  local fake_file="${non_git_dir}/not-a-dir"
  touch "$fake_file"
  cat > "${non_git_dir}/bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${fake_file}"
  exit 0
fi
exit 1
MOCK
  chmod +x "${non_git_dir}/bin/jj"
  # Run detect_repo_root from a directory that has no .git ancestor so that
  # git rev-parse fails, forcing the jj fallback path. Use env -i to avoid
  # inheriting git environment variables that could interfere.
  run env -i HOME="$HOME" PATH="${non_git_dir}/bin:/usr/bin:/bin" \
    bash -c 'cd '"$non_git_dir"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -ne 0 ]
  [[ "$output" == *"ERROR"* ]]
}

@test "detect_repo_root: errors when git fails and jj is not in PATH" {
  local non_git_dir="${REPO_ROOT}/no-git-no-jj"
  mkdir -p "${non_git_dir}"
  # Run detect_repo_root with a PATH that excludes jj entirely
  # and from a directory with no .git ancestor
  run env -i HOME="$HOME" PATH="/usr/bin:/bin" \
    bash -c 'cd '"$non_git_dir"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -ne 0 ]
  [[ "$output" == *"ERROR"* ]]
}

@test "detect_repo_root: jj root returning non-existent directory falls through to error" {
  # Create a mock jj that outputs a non-existent directory path
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "$mock_bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then
  echo "/tmp/nonexistent_repo_path_$$"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"

  local non_git_dir
  non_git_dir=$(mktemp -d)
  # Run from a non-git directory with mock jj returning non-existent path
  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$non_git_dir"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -ne 0 ]
  [[ "$output" == *"not inside a git/jj repository"* ]]
  rm -rf "$non_git_dir" "$mock_bin"
}

@test "detect_repo_root: git rev-parse takes priority over jj root" {
  # Set up a git repo
  local git_repo
  git_repo=$(mktemp -d)
  # Canonicalize to handle macOS /var -> /private/var symlink
  git_repo=$(cd "$git_repo" && pwd -P)
  git -C "$git_repo" init -q
  git -C "$git_repo" -c commit.gpgsign=false commit --allow-empty -m "init" -q

  # Mock jj to return a different path
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "$mock_bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then
  echo "/tmp/jj_different_root_$$"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"

  # git rev-parse should win since it's checked first
  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$git_repo"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -eq 0 ]
  [[ "$output" == "$git_repo" ]]
  rm -rf "$git_repo" "$mock_bin"
}

@test "detect_repo_root: succeeds via jj root when git rev-parse fails" {
  local jj_repo
  jj_repo=$(mktemp -d)
  # Canonicalize to handle macOS /var -> /private/var symlink
  jj_repo=$(cd "$jj_repo" && pwd -P)
  mkdir -p "${jj_repo}/.jj"
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "${mock_bin}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${jj_repo}"
  exit 0
fi
exit 1
MOCK
  chmod +x "${mock_bin}/jj"
  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$jj_repo"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -eq 0 ]
  [[ "$output" == "$jj_repo" ]]
  rm -rf "$jj_repo" "$mock_bin"
}

@test "detect_repo_root: sanitize_for_output strips control chars from jj error output" {
  # Create a mock jj that writes control characters to stderr and exits 1
  # (detect_repo_root captures stderr via temp file into jj_err)
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "$mock_bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then
  printf 'path\x01with\x1B[31mcontrols\x1B[0m' >&2
  exit 1
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"

  local non_git_dir
  non_git_dir=$(mktemp -d)
  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$non_git_dir"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  [ "$status" -ne 0 ]
  # jj output was included in the error message
  [[ "$output" == *"jj:"* ]]
  # no raw C0 control characters
  [[ "$output" != *$'\x01'* ]]
  # no ESC bytes
  [[ "$output" != *$'\x1B'* ]]
  rm -rf "$non_git_dir" "$mock_bin"
}

@test "detect_repo_root: emits WARNING when mktemp fails and jj is in PATH" {
  # Scenario: non-git directory, jj is available, but mktemp fails.
  # The function should emit the WARNING and handle gracefully (no crash/unbound var).
  # It cannot succeed without stderr capture for jj, so returns non-zero.
  local non_git_dir
  non_git_dir=$(mktemp -d)
  non_git_dir=$(cd "$non_git_dir" && pwd -P)

  local mock_bin
  mock_bin=$(mktemp -d)

  # mktemp mock: always fails
  cat > "$mock_bin/mktemp" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$mock_bin/mktemp"

  # jj mock: would succeed if called, but mktemp failure skips the call
  cat > "$mock_bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${non_git_dir}"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"

  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$non_git_dir"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  rm -rf "$non_git_dir" "$mock_bin"
  # Function should emit WARNING about mktemp failure
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"mktemp failed"* ]]
  # Error must not falsely claim jj is not in PATH (it is — mktemp failed, not PATH)
  [[ "$output" != *"jj not in PATH"* ]]
  # Function exits non-zero (jj root was skipped; git also unavailable here)
  [ "$status" -ne 0 ]
}

@test "detect_repo_root: succeeds via git even when jj mktemp would fail" {
  # Scenario: git repo + jj in PATH + mktemp fails.
  # git rev-parse succeeds BEFORE mktemp is called, so WARNING is never emitted.
  local git_repo
  git_repo=$(mktemp -d)
  git_repo=$(cd "$git_repo" && pwd -P)
  git -C "$git_repo" init -q
  git -C "$git_repo" -c commit.gpgsign=false commit --allow-empty -m "init" -q

  local mock_bin
  mock_bin=$(mktemp -d)

  # mktemp mock: always fails (but never reached since git succeeds first)
  cat > "$mock_bin/mktemp" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "$mock_bin/mktemp"

  # jj mock: present in PATH to show git takes priority
  cat > "$mock_bin/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "root" ]]; then
  echo "${git_repo}"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"

  run env -i HOME="$HOME" PATH="${mock_bin}:/usr/bin:/bin" \
    bash -c 'cd '"$git_repo"' && source "'"${BATS_TEST_DIRNAME}"'/../worktree-helpers.sh" && detect_repo_root'
  rm -rf "$git_repo" "$mock_bin"
  [ "$status" -eq 0 ]
  [[ "$output" == "$git_repo" ]]
  # No WARNING — mktemp was never reached because git succeeded first
  [[ "$output" != *"WARNING"* ]]
}

@test "VCS detection preamble: outputs none when neither jj nor git is available" {
  local empty_dir
  empty_dir=$(mktemp -d)
  run bash -c 'export PATH=/usr/sbin:/sbin; cd '"$empty_dir"' && if jj root >/dev/null 2>&1; then echo "jj"; elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; else echo "none"; fi'
  rm -rf "$empty_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "none" ]
}

@test "VCS detection preamble: outputs jj when jj root succeeds" {
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "$mock_bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then
  echo "/some/repo"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"
  local test_dir
  test_dir=$(mktemp -d)
  run bash -c 'export PATH='"$mock_bin"':/usr/sbin:/sbin; cd '"$test_dir"' && if jj root >/dev/null 2>&1; then echo "jj"; elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; else echo "none"; fi'
  rm -rf "$mock_bin" "$test_dir"
  [ "$status" -eq 0 ]
  [ "$output" = "jj" ]
}

@test "VCS detection preamble: outputs git when jj absent and git rev-parse succeeds" {
  local git_repo
  git_repo=$(mktemp -d)
  git -C "$git_repo" init -q
  git -C "$git_repo" -c commit.gpgsign=false commit --allow-empty -m "init" -q
  # Use a PATH without jj so only git is available
  run bash -c 'export PATH=/usr/bin:/bin; cd '"$git_repo"' && if jj root >/dev/null 2>&1; then echo "jj"; elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; else echo "none"; fi'
  rm -rf "$git_repo"
  [ "$status" -eq 0 ]
  [ "$output" = "git" ]
}

@test "VCS detection preamble: outputs jj when both jj and git would succeed (jj takes precedence)" {
  local mock_bin
  mock_bin=$(mktemp -d)
  cat > "$mock_bin/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "root" ]]; then
  echo "/some/colocated-repo"
  exit 0
fi
exit 1
MOCK
  chmod +x "$mock_bin/jj"
  # Create a real git repo to ensure git rev-parse also succeeds
  local git_repo
  git_repo=$(mktemp -d)
  git -C "$git_repo" init -q
  git -C "$git_repo" -c commit.gpgsign=false commit --allow-empty -m "init" -q
  run bash -c 'export PATH='"$mock_bin"':/usr/bin:/bin; cd '"$git_repo"' && if jj root >/dev/null 2>&1; then echo "jj"; elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; else echo "none"; fi'
  rm -rf "$mock_bin" "$git_repo"
  [ "$status" -eq 0 ]
  [ "$output" = "jj" ]
}
