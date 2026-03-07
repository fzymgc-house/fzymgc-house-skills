#!/usr/bin/env bash
# WorktreeRemove hook: remove worktrees from sibling directory
# Input: JSON on stdin with "path" field
set -euo pipefail

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.path // empty')

if [[ -z "$WORKTREE_PATH" || ! -d "$WORKTREE_PATH" ]]; then
  exit 0
fi

# Derive workspace name from path for jj
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")

# Detect repo root — try git first, fall back to path derivation
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$REPO_ROOT" ]]; then
  # Infer from worktree path: <root>_worktrees/<name> → <root>
  WORKTREE_PARENT=$(dirname "$WORKTREE_PATH")
  PARENT_BASE=$(basename "$WORKTREE_PARENT")
  REPO_ROOT="$(dirname "$WORKTREE_PARENT")/${PARENT_BASE%_worktrees}"
fi

# Validate path is inside the expected sibling directory
EXPECTED_PARENT="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")_worktrees"
case "$WORKTREE_PATH" in
  "$EXPECTED_PARENT"/*)  ;;  # safe — inside expected parent
  *)
    echo "ERROR: WORKTREE_PATH '$WORKTREE_PATH' is outside expected parent '$EXPECTED_PARENT'" >&2
    exit 1
    ;;
esac

if [[ -n "$REPO_ROOT" && -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — log errors instead of silently suppressing
  if ! (cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
    echo "WARNING: jj workspace forget failed for worktree-${WORKSPACE_NAME}" >&2
  fi
  rm -rf "$WORKTREE_PATH"
else
  # Standard git worktree cleanup
  git worktree remove --force "$WORKTREE_PATH" 2>/dev/null || true
fi

# Clean up empty parent directory
PARENT=$(dirname "$WORKTREE_PATH")
if [[ -d "$PARENT" ]] && [[ -z "$(ls -A "$PARENT")" ]]; then
  rmdir "$PARENT" 2>/dev/null || true
fi
