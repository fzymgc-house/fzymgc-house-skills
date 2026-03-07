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

# Detect VCS from the main repo root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)

if [[ -n "$REPO_ROOT" && -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup
  (cd "$REPO_ROOT" && jj workspace forget \
    "worktree-${WORKSPACE_NAME}") 2>/dev/null || true
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
