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
  local _exit_code=$?
  local CLEANUP_FAILED=false
  if [[ ! -d "$REPO_ROOT" ]]; then
    echo "WARNING: cleanup: REPO_ROOT '$(sanitize_for_output "$REPO_ROOT")' missing — VCS workspace cleanup skipped" >&2
    echo "WARNING: cleanup: proceeding with directory removal despite missing REPO_ROOT" >&2
  elif [[ -d "${REPO_ROOT}/.jj" ]]; then
    # jj repo: check jj availability before attempting workspace forget
    if command -v jj &>/dev/null; then
      # Always attempt workspace forget — safe even if workspace wasn't fully
      # registered (jj workspace add may partially complete before failing).
      # Suppress errors since forget is best-effort here.
      if ! jj_err=$(cd "$REPO_ROOT" && jj workspace forget "worktree-${NAME}" 2>&1); then
        if [[ "$WORKSPACE_CREATED" == "true" ]]; then
          echo "ERROR: cleanup: jj workspace forget worktree-${NAME} failed — workspace metadata may be leaked: $(sanitize_for_output "${jj_err:0:500}")" >&2
          CLEANUP_FAILED=true
        else
          echo "WARNING: cleanup: jj workspace forget worktree-${NAME} failed (may not have been registered) — run manually if needed: $(sanitize_for_output "${jj_err:0:500}")" >&2
        fi
      fi
    else
      if [[ "$WORKSPACE_CREATED" == "true" ]]; then
        echo "ERROR: cleanup: .jj/ found but jj not installed — workspace 'worktree-${NAME}' was created and cannot be cleaned up; run 'jj workspace forget worktree-${NAME}' manually" >&2
        CLEANUP_FAILED=true
      else
        echo "INFO: cleanup: .jj/ found but jj not installed — no workspace was registered, no cleanup needed" >&2
      fi
    fi
  elif [[ "$WORKSPACE_CREATED" == "true" ]]; then
    # git repo: only remove worktree registration if it was actually created
    # (git worktree remove requires a registered worktree)
    if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
      echo "WARNING: cleanup: git worktree remove failed: $(sanitize_for_output "${git_err:0:500}")" >&2
      if ! prune_err=$(git worktree prune 2>&1); then
        echo "WARNING: cleanup: git worktree prune also failed: $(sanitize_for_output "${prune_err:0:500}") — stale metadata may remain" >&2
      fi
    fi
  else
    # Partial git worktree add may leave stale metadata in .git/worktrees/
    if ! prune_err=$(cd "$REPO_ROOT" && git worktree prune 2>&1); then
      echo "WARNING: cleanup: git worktree prune failed for partial create: $(sanitize_for_output "${prune_err:0:500}") — stale worktree metadata may remain" >&2
    fi
  fi
  if ! rm_err=$(rm -rf "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: cleanup failed for '$(sanitize_for_output "$WORKTREE_PATH")': $(sanitize_for_output "${rm_err:0:500}")" >&2
    CLEANUP_FAILED=true
  fi
  cleanup_empty_parent "$WORKTREE_PARENT"
  # Exit code promotion: only override when original operation succeeded (_exit_code==0).
  # When the original operation failed, preserve its exit code — cleanup failures are
  # always surfaced via WARNING/ERROR on stderr regardless of exit code.
  if [[ "$CLEANUP_FAILED" == "true" ]] && [[ $_exit_code -eq 0 ]]; then
    _exit_code=1
  fi
  exit $_exit_code
}
trap cleanup_on_error EXIT
if [[ -d "${REPO_ROOT}/.jj" ]] && ! command -v jj &>/dev/null; then
  echo "ERROR: .jj/ directory found but jj is not installed" >&2
  exit 1
fi

mkdir -p "$WORKTREE_PARENT" || {
  echo "ERROR: failed to create worktree parent directory '$WORKTREE_PARENT'" >&2
  exit 1
}

if [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace — jj availability already verified above
  if ! jj_out=$(cd "$REPO_ROOT" && jj workspace add "$WORKTREE_PATH" \
    --name "worktree-${NAME}" 2>&1); then
    if echo "$jj_out" | grep -qiF -- '--name' && \
       echo "$jj_out" | grep -qiE 'unexpected|unrecognized|unknown'; then
      echo "ERROR: jj version too old — 'jj workspace add --name' not supported (jj output: $(sanitize_for_output "${jj_out:0:200}")). Update jj." >&2
    else
      echo "ERROR: jj workspace add failed: $(sanitize_for_output "${jj_out:0:500}")" >&2
    fi
    exit 1
  fi
  WORKSPACE_CREATED=true
else
  # Standard git worktree
  if ! git_err=$(git worktree add "$WORKTREE_PATH" -b "worktree/${NAME}" HEAD 2>&1); then
    echo "ERROR: git worktree add failed: $(sanitize_for_output "${git_err:0:500}")" >&2
    exit 1
  fi
  WORKSPACE_CREATED=true
fi

# Install hooks in the new workspace (lefthook works in both VCS modes)
if [[ -f "${REPO_ROOT}/lefthook.yml" ]]; then
  if ! lh_err=$(cd "$WORKTREE_PATH" && lefthook install 2>&1); then
    echo "WARNING: lefthook install failed in worktree: $(sanitize_for_output "${lh_err:0:500}")" >&2
  fi
fi

trap - EXIT  # disarm after success

echo "$WORKTREE_PATH"
