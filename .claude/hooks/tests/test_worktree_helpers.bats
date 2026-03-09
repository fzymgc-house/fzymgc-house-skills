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

@test "sanitize_for_output: strips newlines" {
  # Newline is 0x0A, within C0 range — must be stripped.
  input=$(printf 'line1\nline2')
  result=$(sanitize_for_output "$input")
  [[ "$result" != *$'\n'* ]]
  [ "$result" = "line1line2" ]
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
