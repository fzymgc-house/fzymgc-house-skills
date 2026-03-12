#!/usr/bin/env bats

# Tests for shell fragments from jj/commands/jj-init.md

load helpers

# Scope: These tests cover the GITIGNORE_FRAGMENT (step 4 of jj-init.md).
# Steps 1-3 (prerequisite checks, already-initialized guard, jj git init)
# are markdown-defined agent instructions, not extractable shell fragments.
# They are covered by behavioral evals JJ-B-INIT1 through JJ-B-INIT4.

setup() {
  TEST_DIR=$(mktemp -d)
  cd "$TEST_DIR"
  git init --quiet .
}

teardown() {
  cd /
  rm -rf "$TEST_DIR"
}

# The gitignore fragment from jj-init.md step 4:
#   grep -qxF '.jj/' .gitignore 2>/dev/null || {
#     if ! append_err=$(echo '.jj/' >> .gitignore 2>&1); then
#       echo "Could not update .gitignore: $append_err"
#     fi
#   }
GITIGNORE_FRAGMENT='grep -qxF '"'"'.jj/'"'"' .gitignore 2>/dev/null || {
  if ! append_err=$({ echo '"'"'.jj/'"'"' >> .gitignore; } 2>&1); then
    echo "Could not update .gitignore: ${append_err:-permission denied}"
  fi
}'

@test "gitignore: adds .jj/ when no .gitignore exists" {
  run bash -c "$GITIGNORE_FRAGMENT"
  [ "$status" -eq 0 ]
  grep -qxF '.jj/' .gitignore
}

@test "gitignore: idempotent — does not duplicate .jj/ entry" {
  echo '.jj/' > .gitignore
  run bash -c "$GITIGNORE_FRAGMENT"
  [ "$status" -eq 0 ]
  count=$(grep -cxF '.jj/' .gitignore)
  [ "$count" -eq 1 ]
}

@test "gitignore: adds .jj/ when .gitignore exists but lacks entry" {
  echo '*.pyc' > .gitignore
  run bash -c "$GITIGNORE_FRAGMENT"
  [ "$status" -eq 0 ]
  grep -qxF '.jj/' .gitignore
  grep -qF '*.pyc' .gitignore
}

@test "gitignore: partial match .jj does not satisfy .jj/ check" {
  echo '.jj' > .gitignore
  run bash -c "$GITIGNORE_FRAGMENT"
  [ "$status" -eq 0 ]
  grep -qxF '.jj' .gitignore
  grep -qxF '.jj/' .gitignore
}

@test "gitignore: read-only .gitignore surfaces error" {
  echo '# existing' > .gitignore
  chmod a-w .gitignore
  run bash -c "$GITIGNORE_FRAGMENT"
  chmod u+w .gitignore
  [ "$status" -eq 0 ]
  [[ "$output" == *"Could not update .gitignore"* ]]
  # Verify .jj/ was not appended despite the error
  run grep -qF '.jj/' .gitignore
  [ "$status" -ne 0 ]
}

# The verification fragment from jj-init.md step 5:
#   Run jj st and jj log --no-graph -n 3; report error and advise user if either fails.
VERIFICATION_FRAGMENT='
jj_rc=0; jj_err=""
if ! jj_err=$(jj st 2>&1); then
  jj_rc=1
fi
if ! log_err=$(jj log --no-graph -n 3 2>&1); then
  jj_err="${jj_err:+$jj_err; }${log_err}"
  jj_rc=1
fi
if [ "$jj_rc" -ne 0 ]; then
  echo "WARNING: jj git init --colocate may have failed — jj status check returned an error: ${jj_err}. Run \`jj st\` manually to verify."
fi
exit $jj_rc
'

@test "verification: succeeds when jj st and jj log work" {
  MOCK_BIN="$TEST_DIR/mock_bin"
  mkdir -p "$MOCK_BIN"
  cat > "$MOCK_BIN/jj" << 'MOCK'
#!/bin/bash
exit 0
MOCK
  chmod +x "$MOCK_BIN/jj"
  run env PATH="$MOCK_BIN:$PATH" bash -c "$VERIFICATION_FRAGMENT"
  [ "$status" -eq 0 ]
  [[ "$output" != *"WARNING"* ]]
  [[ "$output" != *"jj git init --colocate may have failed"* ]]
}

@test "verification: reports error when jj st fails" {
  MOCK_BIN="$TEST_DIR/mock_bin"
  mkdir -p "$MOCK_BIN"
  cat > "$MOCK_BIN/jj" << 'MOCK'
#!/bin/bash
if [ "$1" = "st" ]; then
  echo "error: not in a jj repo" >&2
  exit 1
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/jj"
  run env PATH="$MOCK_BIN:$PATH" bash -c "$VERIFICATION_FRAGMENT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WARNING: jj git init --colocate may have failed"* ]]
}

@test "verification: reports error when jj log fails but jj st succeeds" {
  MOCK_BIN="$TEST_DIR/mock_bin"
  mkdir -p "$MOCK_BIN"
  cat > "$MOCK_BIN/jj" << 'MOCK'
#!/bin/bash
if [ "$1" = "log" ]; then
  echo "error: log command failed" >&2
  exit 1
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/jj"
  run env PATH="$MOCK_BIN:$PATH" bash -c "$VERIFICATION_FRAGMENT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"error: log command failed"* ]]
}

@test "verification: reports error when both jj st and jj log fail" {
  MOCK_BIN="$TEST_DIR/mock_bin"
  mkdir -p "$MOCK_BIN"
  cat > "$MOCK_BIN/jj" << 'MOCK'
#!/bin/bash
if [ "$1" = "st" ]; then
  echo "error: status check failed" >&2
  exit 1
fi
if [ "$1" = "log" ]; then
  echo "error: log check failed" >&2
  exit 1
fi
exit 0
MOCK
  chmod +x "$MOCK_BIN/jj"
  run env PATH="$MOCK_BIN:$PATH" bash -c "$VERIFICATION_FRAGMENT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"error: status check failed"* ]]
  [[ "$output" == *"error: log check failed"* ]]
  [[ "$output" == *"WARNING: jj git init --colocate may have failed"* ]]
}
