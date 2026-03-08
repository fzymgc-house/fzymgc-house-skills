#!/usr/bin/env bash
# WorktreeCreate hook: create worktrees in sibling directory
# Input: JSON on stdin with "name" field
# Output: print the worktree path to stdout (framework reads this)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.claude/hooks/worktree-helpers.sh
source "${SCRIPT_DIR}/worktree-helpers.sh"

INPUT=$(cat)
NAME=$(echo "$INPUT" | jq -r '.name // empty')

if [[ -z "$NAME" ]]; then
  echo "ERROR: no worktree name provided" >&2
  exit 1
fi

validate_safe_name "$NAME" "worktree name" || exit 1

REPO_ROOT=$(detect_repo_root) || exit 1
REPO_NAME=$(basename "$REPO_ROOT")

validate_safe_name "$REPO_NAME" "repository directory name" || exit 1

WORKTREE_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
WORKTREE_PATH="${WORKTREE_PARENT}/${NAME}"

cleanup_on_error() {
  rm -rf "$WORKTREE_PATH" 2>/dev/null || echo "WARNING: cleanup failed for '$WORKTREE_PATH'" >&2
  if [[ -d "$WORKTREE_PARENT" ]] && [[ -z "$(ls -A "$WORKTREE_PARENT")" ]]; then
    rmdir "$WORKTREE_PARENT" 2>/dev/null || echo "WARNING: failed to remove empty parent '$WORKTREE_PARENT'" >&2
  fi
}

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — verify jj is installed
  if ! command -v jj &>/dev/null; then
    echo "ERROR: .jj/ directory found but jj is not installed" >&2
    exit 1
  fi
  # Runtime version probe: jj is user-installed and can be updated
  # independently, so we check --name support on each invocation.
  # Note: there is a theoretical TOCTOU window between the --help probe
  # and the actual workspace add, but the practical risk of jj being
  # replaced between two calls in the same hook invocation is negligible.
  if ! jj_help=$(jj workspace add --help 2>&1); then
    echo "ERROR: jj failed to run: $(echo "${jj_help:0:200}" | tr -d '\033')" >&2
    exit 1
  fi
  if ! echo "$jj_help" | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported" >&2
    exit 1
  fi
  mkdir -p "$WORKTREE_PARENT" || {
    echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
    exit 1
  }
  # From here on, WORKTREE_PARENT exists — cleanup_on_error handles it
  if ! jj_out=$(cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}" 2>&1); then
    echo "ERROR: jj workspace add failed: $(echo "${jj_out:0:200}" | tr -d '\033')" >&2
    cleanup_on_error
    exit 1
  fi
else
  # Standard git worktree
  mkdir -p "$WORKTREE_PARENT" || {
    echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
    exit 1
  }
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $(echo "${git_err:0:200}" | tr -d '\033')" >&2
    cleanup_on_error
    exit 1
  fi
fi

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  if ! lh_err=$(cd "$WORKTREE_PATH" && lefthook install 2>&1); then
    echo "WARNING: lefthook install failed in worktree: $(echo "${lh_err:0:200}" | tr -d '\033')" >&2
  fi
fi

echo "$WORKTREE_PATH"
