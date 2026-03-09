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

WORKSPACE_CREATED=false

cleanup_on_error() {
  # Only deregister VCS workspace/worktree metadata if the workspace was actually created.
  # Without this guard the trap fires on early failures (e.g. mkdir) before any VCS
  # registration has occurred, causing spurious jj/git errors.
  if [[ "$WORKSPACE_CREATED" == "true" ]]; then
    if [[ -d "${REPO_ROOT}/.jj" ]] && command -v jj &>/dev/null; then
      # jj repo: forget workspace metadata (prevents orphaned metadata)
      if ! jj_err=$(cd "$REPO_ROOT" && jj workspace forget "worktree-${NAME}" 2>&1); then
        echo "WARNING: cleanup: jj workspace forget worktree-${NAME} failed — run manually if needed: $(sanitize_for_output "${jj_err:0:200}")" >&2
      fi
    else
      # git repo: remove worktree registration from .git/worktrees/ (prevents stale metadata)
      if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
        echo "WARNING: cleanup: git worktree remove failed — run 'git worktree prune' manually if needed: $(sanitize_for_output "${git_err:0:200}")" >&2
      fi
    fi
  fi
  if ! rm_err=$(rm -rf "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: cleanup failed for '$(sanitize_for_output "$WORKTREE_PATH")': $(sanitize_for_output "${rm_err:0:200}")" >&2
  fi
  cleanup_empty_parent "$WORKTREE_PARENT"
}
trap cleanup_on_error EXIT

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
  # Runtime capability probe: jj is user-managed and may not be in PATH
  # or may predate --name support. Check before each workspace creation.
  # Note: there is a theoretical TOCTOU window between the --help probe
  # and the actual workspace add, but the practical risk of jj being
  # replaced between two calls in the same hook invocation is negligible.
  if ! jj_help=$(jj workspace add --help 2>&1); then
    echo "ERROR: jj failed to run: $(sanitize_for_output "${jj_help:0:200}")" >&2
    exit 1
  fi
  if ! echo "$jj_help" | grep -q -- '--name'; then
    echo "ERROR: jj version too old — 'jj workspace add --name' not supported" >&2
    exit 1
  fi
  if ! jj_out=$(cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}" 2>&1); then
    echo "ERROR: jj workspace add failed: $(sanitize_for_output "${jj_out:0:200}")" >&2
    exit 1
  fi
  WORKSPACE_CREATED=true
else
  # Standard git worktree
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $(sanitize_for_output "${git_err:0:200}")" >&2
    exit 1
  fi
  WORKSPACE_CREATED=true
fi

trap - EXIT

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  if ! lh_err=$(cd "$WORKTREE_PATH" && lefthook install 2>&1); then
    echo "WARNING: lefthook install failed in worktree: $(sanitize_for_output "${lh_err:0:200}")" >&2
  fi
fi

echo "$WORKTREE_PATH"
