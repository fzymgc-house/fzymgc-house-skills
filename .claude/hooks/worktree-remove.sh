#!/usr/bin/env bash
# WorktreeRemove hook: remove worktrees from sibling directory
# Input: JSON on stdin with "path" field
set -euo pipefail

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.path // empty')

if [[ -z "$WORKTREE_PATH" || ! -d "$WORKTREE_PATH" ]]; then
  exit 0
fi

# Canonicalize path to prevent traversal via ../ segments
WORKTREE_PATH=$(realpath "$WORKTREE_PATH")

# Validate basename has safe characters only (matches worktree-create.sh)
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")
if [[ "$WORKSPACE_NAME" =~ [^a-zA-Z0-9_.-] || "$WORKSPACE_NAME" == .* || "$WORKSPACE_NAME" == *".."* ]]; then
  echo "ERROR: invalid worktree name '$WORKSPACE_NAME' (alphanumeric, dots, hyphens, underscores only)" >&2
  exit 1
fi

# Detect repo root — git rev-parse works in colocated jj repos (.git/ present)
# Non-colocated jj repos are out of scope (see CLAUDE.md: "colocated repos")
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "ERROR: could not determine repo root (git rev-parse failed)" >&2
  exit 1
}

# Validate path is inside the expected sibling directory
EXPECTED_PARENT="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")_worktrees"
case "$WORKTREE_PATH" in
  "$EXPECTED_PARENT"/*)  ;;  # safe — inside expected parent
  *)
    echo "ERROR: WORKTREE_PATH '$WORKTREE_PATH' is outside expected parent '$EXPECTED_PARENT'" >&2
    exit 1
    ;;
esac

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — forget workspace metadata before removing directory
  if ! command -v jj &>/dev/null; then
    echo "WARNING: .jj/ found but jj not installed — workspace metadata not cleaned" >&2
  elif ! jj_err=$(cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
    echo "WARNING: jj workspace forget failed for worktree-${WORKSPACE_NAME}: $jj_err" >&2
  fi
else
  # Standard git worktree cleanup — log errors instead of suppressing
  if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: git worktree remove failed for '$WORKTREE_PATH': $git_err" >&2
    git worktree prune 2>/dev/null || true
  fi
fi

# Always remove directory (git worktree remove already did this on success;
# rm -rf on an already-removed path is a no-op)
rm -rf "$WORKTREE_PATH"

# Clean up empty parent directory
PARENT=$(dirname "$WORKTREE_PATH")
if [[ -d "$PARENT" ]] && [[ -z "$(ls -A "$PARENT")" ]]; then
  rmdir "$PARENT" 2>/dev/null || true
fi
