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
  echo '{"warning":"no path field in WorktreeRemove input — skipping removal"}' >&2
  exit 0
fi

if [[ ! -d "$WORKTREE_PATH" ]]; then
  echo "{\"warning\":\"worktree directory already removed: $(sanitize_for_output "$WORKTREE_PATH")\"}" >&2
  exit 0
fi

# Canonicalize path to prevent traversal via ../ segments
_ORIG_PATH="$WORKTREE_PATH"
if command -v realpath &>/dev/null; then
  WORKTREE_PATH=$(realpath "$WORKTREE_PATH" 2>/dev/null) || {
    echo "ERROR: realpath failed for '$(sanitize_for_output "$_ORIG_PATH")'" >&2
    exit 1
  }
else
  # POSIX fallback: cd into the directory and capture pwd -P
  WORKTREE_PATH=$(cd "$_ORIG_PATH" 2>/dev/null && pwd -P) || {
    echo "ERROR: could not canonicalize path '$(sanitize_for_output "$_ORIG_PATH")'" >&2
    exit 1
  }
fi
if [[ -z "$WORKTREE_PATH" ]]; then
  echo "ERROR: could not resolve canonical path for '$(sanitize_for_output "$_ORIG_PATH")'" >&2
  exit 1
fi

# Validate basename — lenient on removal path: warn but allow non-conforming names
# so orphaned worktrees with unusual names can still be cleaned up.
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")
if ! validate_safe_name "$WORKSPACE_NAME" "worktree name" 2>/dev/null; then
  echo "WARNING: worktree name '$(sanitize_for_output "$WORKSPACE_NAME")' contains unusual characters — proceeding with removal" >&2
fi

# Detect repo root — requires git rev-parse (.git/ directory). In colocated
# jj repos (.jj/ + .git/), this succeeds. Pure jj repos use jj root fallback
# in detect_repo_root.
# Fallback: when hook CWD is outside any repo (e.g. orphaned worktree cleanup),
# infer the repo root from the worktree path by stripping the last two path
# components (workspace name and _worktrees suffix).
_REPO_ROOT_INFERRED=false
if ! REPO_ROOT=$(detect_repo_root 2>/dev/null); then
  _worktrees_dir=$(dirname "$WORKTREE_PATH")
  _inferred_root=$(dirname "$_worktrees_dir")
  _inferred_name=$(basename "$_worktrees_dir")
  # _worktrees dir should end in _worktrees suffix
  if [[ "$_inferred_name" == *_worktrees ]]; then
    REPO_ROOT="${_inferred_root}/${_inferred_name%_worktrees}"
    _REPO_ROOT_INFERRED=true
    echo "WARNING: detect_repo_root failed — inferred repo root as '$(sanitize_for_output "$REPO_ROOT")' from worktree path" >&2
  else
    echo "ERROR: could not determine repo root and path does not match expected _worktrees pattern — refusing removal for safety" >&2
    echo "Manual cleanup required: rm -rf '$(sanitize_for_output "$WORKTREE_PATH")'" >&2
    exit 1
  fi
fi

# Validate path is inside the expected sibling directory
REPO_NAME=$(basename "$REPO_ROOT")
validate_safe_name "$REPO_NAME" "repository directory name" || exit 1

EXPECTED_PARENT="$(dirname "$REPO_ROOT")/${REPO_NAME}_worktrees"
# Canonicalize to match WORKTREE_PATH (also canonicalized via realpath)
# If the _worktrees parent doesn't exist but WORKTREE_PATH exists, state is inconsistent
if command -v realpath &>/dev/null; then
  EXPECTED_PARENT=$(realpath "$EXPECTED_PARENT" 2>/dev/null) || { echo "ERROR: _worktrees parent directory '$(sanitize_for_output "$EXPECTED_PARENT")' does not exist but WORKTREE_PATH '$(sanitize_for_output "$WORKTREE_PATH")' does — inconsistent state" >&2; exit 1; }
else
  EXPECTED_PARENT=$(cd "$EXPECTED_PARENT" 2>/dev/null && pwd -P) || { echo "ERROR: _worktrees parent directory '$(sanitize_for_output "$EXPECTED_PARENT")' does not exist but WORKTREE_PATH '$(sanitize_for_output "$WORKTREE_PATH")' does — inconsistent state" >&2; exit 1; }
fi
case "$WORKTREE_PATH" in
  "$EXPECTED_PARENT"/*)  ;;  # safe — inside expected parent
  *)
    echo "ERROR: WORKTREE_PATH '$(sanitize_for_output "$WORKTREE_PATH")' is outside expected parent '$(sanitize_for_output "$EXPECTED_PARENT")' — refusing removal" >&2
    exit 1
    ;;
esac

# When repo root was inferred, verify it actually contains a repo before VCS cleanup.
# If neither .jj/ nor .git exists at the inferred root, skip VCS deregistration entirely.
_skip_vcs_cleanup=false
if [[ "$_REPO_ROOT_INFERRED" == "true" ]]; then
  if [[ ! -d "${REPO_ROOT}/.jj" ]] && ! git -C "$REPO_ROOT" rev-parse --git-dir &>/dev/null; then
    echo "WARNING: inferred repo root '$(sanitize_for_output "$REPO_ROOT")' has no .jj/ or .git — skipping VCS cleanup" >&2
    _skip_vcs_cleanup=true
  fi
fi

if [[ "$_skip_vcs_cleanup" == "true" ]]; then
  : # Skip VCS deregistration, proceed directly to directory removal below
elif [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — forget workspace metadata before removing directory
  if ! command -v jj &>/dev/null; then
    echo "WARNING: .jj/ found but jj not installed — workspace metadata not cleaned" >&2
  elif ! jj_err=$(cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
    echo "WARNING: jj workspace forget failed for worktree-$(sanitize_for_output "$WORKSPACE_NAME"): $(sanitize_for_output "${jj_err:0:200}") (run 'jj workspace forget worktree-$(sanitize_for_output "$WORKSPACE_NAME")' manually to clean up)" >&2
  fi
else
  # Standard git worktree cleanup — log errors instead of suppressing
  if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: git worktree remove failed for '$WORKTREE_PATH': $(sanitize_for_output "${git_err:0:200}")" >&2
    if ! prune_err=$(git worktree prune 2>&1); then
      echo "WARNING: git worktree prune also failed: $(sanitize_for_output "${prune_err:0:200}") — stale metadata may remain in .git/worktrees/" >&2
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
cleanup_empty_parent "$(dirname "$WORKTREE_PATH")"
