#!/usr/bin/env bats

# Tests for shell fragments from jj/commands/jj-init.md

load helpers

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
  if ! append_err=$(echo '"'"'.jj/'"'"' >> .gitignore 2>&1); then
    echo "Could not update .gitignore: $append_err"
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
