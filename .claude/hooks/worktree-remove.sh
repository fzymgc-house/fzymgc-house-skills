#!/usr/bin/env bash
# WorktreeRemove hook: remove worktrees from sibling directory
# Input: JSON on stdin with "path" field
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.claude/hooks/worktree-helpers.sh
source "${SCRIPT_DIR}/worktree-helpers.sh"

INPUT=$(cat)
WORKTREE_PATH=$(echo "$INPUT" | jq -r '.path // empty')

if [[ -z "$WORKTREE_PATH" ]]; then
  exit 0
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo '{"warning":"worktree directory already removed: '"$(sanitize_for_output "$WORKTREE_PATH")"'"}' >&2
  exit 0
fi

# Canonicalize path to prevent traversal via ../ segments
_ORIG_PATH="$WORKTREE_PATH"
WORKTREE_PATH=$(realpath "$WORKTREE_PATH" 2>/dev/null) || {
  echo "ERROR: realpath failed for '$(sanitize_for_output "$_ORIG_PATH")'" >&2
  exit 1
}
if [[ -z "$WORKTREE_PATH" ]]; then
  echo "ERROR: realpath returned empty result for '$(sanitize_for_output "$_ORIG_PATH")'" >&2
  exit 1
fi

# Validate basename has safe characters only (matches worktree-create.sh)
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")
validate_safe_name "$WORKSPACE_NAME" "worktree name" || exit 1

# Detect repo root — works with both .git/ (via git rev-parse) and .jj/
# (via jj root fallback). Handles git repos, colocated jj repos, and
# non-colocated jj repos.
REPO_ROOT=$(detect_repo_root) || {
  echo "ERROR: could not determine repo root" >&2
  exit 1
}

# Validate path is inside the expected sibling directory
REPO_NAME=$(basename "$REPO_ROOT")
validate_safe_name "$REPO_NAME" "repository directory name" || exit 1

EXPECTED_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
# Canonicalize to match WORKTREE_PATH (also canonicalized via realpath)
# If the _worktrees parent doesn't exist, worktree is already gone — exit cleanly
if ! EXPECTED_PARENT=$(realpath "$EXPECTED_PARENT" 2>/dev/null); then
  exit 0
fi
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
    echo "WARNING: jj workspace forget failed for worktree-${WORKSPACE_NAME}: $(sanitize_for_output "${jj_err:0:200}") (run 'jj workspace forget worktree-${WORKSPACE_NAME}' manually to clean up)" >&2
  fi
else
  # Standard git worktree cleanup — log errors instead of suppressing
  if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: git worktree remove failed for '$WORKTREE_PATH': $(sanitize_for_output "${git_err:0:200}")" >&2
    if ! prune_err=$(git worktree prune 2>&1); then
      echo "WARNING: git worktree prune also failed: $(sanitize_for_output "${prune_err:0:200}")" >&2
    fi
  fi
fi

# Always attempt directory removal. rm -rf exits 0 if path doesn't exist,
# so this is safe even when git worktree remove already cleaned up.
if ! rm -rf "$WORKTREE_PATH"; then
  echo "ERROR: failed to remove worktree directory '$WORKTREE_PATH'" >&2
  exit 1
fi

# Clean up empty parent directory
PARENT=$(dirname "$WORKTREE_PATH")
if [[ -d "$PARENT" ]] && [[ -z "$(ls -A "$PARENT")" ]]; then
  rmdir "$PARENT" 2>/dev/null || echo "WARNING: failed to remove empty parent '$PARENT'" >&2
fi
