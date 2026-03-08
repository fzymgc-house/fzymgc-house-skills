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
if [[ "$NAME" =~ [^a-zA-Z0-9_.-] || "$NAME" == .* || "$NAME" == *".."* ]]; then
  echo "ERROR: invalid worktree name '$NAME' (alphanumeric, dots, hyphens, underscores only; no leading dot)" >&2
  exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "ERROR: not inside a git/jj repository (git rev-parse failed)" >&2
  exit 1
}
REPO_NAME=$(basename "$REPO_ROOT")

# Validate repo directory name (same rules as worktree NAME)
if [[ "$REPO_NAME" =~ [^a-zA-Z0-9_.-] || "$REPO_NAME" == .* || "$REPO_NAME" == *".."* ]]; then
  echo "ERROR: repository directory name '$REPO_NAME' contains unsafe characters" >&2
  exit 1
fi

WORKTREE_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${NAME}"

cleanup_on_error() {
  rm -rf "$WORKTREE_PATH" 2>/dev/null || echo "WARNING: cleanup failed for '$WORKTREE_PATH'" >&2
  if [[ -d "$WORKTREE_PARENT" ]] && [[ -z "$(ls -A "$WORKTREE_PARENT")" ]]; then
    rmdir "$WORKTREE_PARENT" 2>/dev/null || echo "WARNING: failed to remove empty parent '$WORKTREE_PARENT'" >&2
  fi
}

mkdir -p "$WORKTREE_PARENT" || {
  echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
  exit 1
}

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  # Runtime version probe: jj is user-installed and can be updated
  # independently, so we check --name support on each invocation
  if ! jj_help=$(jj workspace add --help 2>&1); then
    echo "ERROR: jj failed to run: ${jj_help:0:200}" >&2
    exit 1
  fi
  if ! echo "$jj_help" | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported" >&2
    exit 1
  fi
  if ! jj_out=$(cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}" 2>&1); then
    echo "ERROR: jj workspace add failed: $jj_out" >&2
    cleanup_on_error
    exit 1
  fi
else
  # Standard git worktree
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $git_err" >&2
    cleanup_on_error
    exit 1
  fi
fi

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  if ! lh_err=$(cd "$WORKTREE_PATH" && lefthook install 2>&1); then
    echo "WARNING: lefthook install failed in worktree: $lh_err" >&2
  fi
fi

echo "$WORKTREE_PATH"
