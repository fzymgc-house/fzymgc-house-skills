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
if [[ "$NAME" =~ [^a-zA-Z0-9_.-] || "$NAME" == *".."* ]]; then
  echo "ERROR: invalid worktree name '$NAME' (alphanumeric, dots, hyphens, underscores only)" >&2
  exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
WORKTREE_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${NAME}"

mkdir -p "$WORKTREE_PARENT"

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  (cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}")
else
  # Standard git worktree
  git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD

  # Install git hooks in the new worktree
  if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
    (cd "$WORKTREE_PATH" && lefthook install 2>/dev/null) || true
  fi
fi

echo "$WORKTREE_PATH"
