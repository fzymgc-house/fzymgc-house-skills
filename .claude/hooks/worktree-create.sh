#!/usr/bin/env bash
# WorktreeCreate hook: create worktrees in sibling directory
# Input: JSON on stdin with "name" field
# Output: print the worktree path to stdout (framework reads this)
set -euo pipefail

INPUT=$(cat)
NAME=$(echo "$INPUT" | jq -r '.name // empty')

if [[ -z "$NAME" ]]; then
  echo "ERROR: no worktree name provided" >&2
  exit 1
fi

# Reject names with path-traversal or shell metacharacters
if [[ "$NAME" =~ [^a-zA-Z0-9_.-] || "$NAME" == "." || "$NAME" == ".." || "$NAME" == *".."* ]]; then
  echo "ERROR: invalid worktree name '$NAME' (alphanumeric, dots, hyphens, underscores only)" >&2
  exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
WORKTREE_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${NAME}"

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  # Verify jj supports --name flag (added in 0.21)
  if ! jj workspace add --help 2>&1 | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported (need jj >= 0.21)" >&2
    exit 1
  fi
  mkdir -p "$WORKTREE_PARENT"
  if ! (cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}"); then
    echo "ERROR: jj workspace add failed" >&2
    [[ -d "$WORKTREE_PATH" ]] && rm -rf "$WORKTREE_PATH"
    [[ -d "$WORKTREE_PARENT" ]] && [[ -z "$(ls -A "$WORKTREE_PARENT")" ]] && rmdir "$WORKTREE_PARENT" 2>/dev/null
    exit 1
  fi
else
  # Standard git worktree
  mkdir -p "$WORKTREE_PARENT"
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $git_err" >&2
    exit 1
  fi
fi

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  (cd "$WORKTREE_PATH" && lefthook install 2>/dev/null) || true
fi

echo "$WORKTREE_PATH"
