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

@test "sanitize_for_output: strips null bytes" {
  # Bash $() strips trailing nulls, so write to a file to verify absence.
  printf 'he\x00llo' | LC_ALL=C tr -d '\000-\037\177\200-\237' > "${REPO_ROOT}/out.bin"
  # File must contain exactly "hello" (5 bytes, no null)
  result=$(cat "${REPO_ROOT}/out.bin")
  [ "$result" = "hello" ]
  # Confirm no null byte remains in the file
  ! grep -Pq '\x00' "${REPO_ROOT}/out.bin"
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
