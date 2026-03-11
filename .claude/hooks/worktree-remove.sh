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
  _rp_out=$(realpath "$WORKTREE_PATH" 2>&1) || {
    echo "ERROR: realpath failed for '$(sanitize_for_output "$_ORIG_PATH")': $(sanitize_for_output "${_rp_out:0:500}")" >&2
    exit 1
  }
  WORKTREE_PATH="$_rp_out"
else
  # POSIX fallback: cd into the directory and capture pwd -P
  _cd_out=$({ cd "$_ORIG_PATH" && pwd -P; } 2>&1) || {
    echo "ERROR: could not canonicalize path '$(sanitize_for_output "$_ORIG_PATH")': $(sanitize_for_output "${_cd_out:0:500}")" >&2
    exit 1
  }
  WORKTREE_PATH="$_cd_out"
fi
# Defensive: unreachable if realpath/cd succeeded above, but guards against
# future refactoring that might skip the exit-on-failure branches.
if [[ -z "$WORKTREE_PATH" ]]; then
  echo "ERROR: could not resolve canonical path for '$(sanitize_for_output "$_ORIG_PATH")'" >&2
  exit 1
fi

# Validate basename — lenient on removal path: warn but allow non-conforming names
# so orphaned worktrees with unusual names can still be cleaned up.
WORKSPACE_NAME=$(basename "$WORKTREE_PATH")
if ! validate_safe_name "$WORKSPACE_NAME" "worktree name"; then
  echo "WARNING: worktree name '$(sanitize_for_output "$WORKSPACE_NAME")' contains unusual characters — proceeding with removal" >&2
fi

# Detect repo root — requires git rev-parse (.git/ directory). In colocated
# jj repos (.jj/ + .git/), this succeeds. Pure jj repos use jj root fallback
# in detect_repo_root.
# Fallback: when hook CWD is outside any repo (e.g. orphaned worktree cleanup),
# infer the repo root from the worktree path by stripping the last two path
# components (workspace name and _worktrees suffix).
_REPO_ROOT_INFERRED=false
_root_err_file=$(mktemp) || { echo 'ERROR: mktemp failed — cannot create temp file for error capture' >&2; exit 1; }
# _ws_list_err is intentionally initialized empty here rather than via mktemp:
#   1. It is only needed for jj repos (the mktemp happens inside the jj branch below).
#   2. The EXIT trap guard `[[ -n "${_ws_list_err:-}" ]]` safely skips cleanup when
#      _ws_list_err was never set (git-only path or skip_vcs_cleanup path).
#   3. This avoids allocating a temp file that is never used on the git-only path.
#   4. _ws_list_mktemp_ok is an explicit boolean tracking whether mktemp succeeded;
#      this avoids using an empty _ws_list_err as a sentinel for both "never used"
#      and "mktemp failed" states.
_ws_list_err=""
_ws_list_mktemp_ok=false
trap '[[ -n "${_root_err_file:-}" ]] && rm -f "$_root_err_file"; [[ -n "${_ws_list_err:-}" ]] && rm -f "$_ws_list_err"' EXIT
if ! REPO_ROOT=$(detect_repo_root 2>"$_root_err_file"); then
  _root_stderr=$(cat "$_root_err_file" 2>/dev/null)
  _worktrees_dir=$(dirname "$WORKTREE_PATH")
  _inferred_root=$(dirname "$_worktrees_dir")
  _inferred_name=$(basename "$_worktrees_dir")
  # _worktrees dir should end in _worktrees suffix
  if [[ "$_inferred_name" == *_worktrees ]]; then
    REPO_ROOT="${_inferred_root}/${_inferred_name%_worktrees}"
    _REPO_ROOT_INFERRED=true
    echo "WARNING: detect_repo_root failed — inferred repo root as '$(sanitize_for_output "$REPO_ROOT")' from worktree path (detect_repo_root: $(sanitize_for_output "${_root_stderr:0:500}"))" >&2
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
  _ep_out=$(realpath "$EXPECTED_PARENT" 2>&1) || { echo "ERROR: _worktrees parent directory '$(sanitize_for_output "$EXPECTED_PARENT")' does not exist but WORKTREE_PATH '$(sanitize_for_output "$WORKTREE_PATH")' does — inconsistent state: $(sanitize_for_output "${_ep_out:0:500}")" >&2; exit 1; }
  EXPECTED_PARENT="$_ep_out"
else
  _ep_out=$({ cd "$EXPECTED_PARENT" && pwd -P; } 2>&1) || { echo "ERROR: _worktrees parent directory '$(sanitize_for_output "$EXPECTED_PARENT")' does not exist but WORKTREE_PATH '$(sanitize_for_output "$WORKTREE_PATH")' does — inconsistent state: $(sanitize_for_output "${_ep_out:0:500}")" >&2; exit 1; }
  EXPECTED_PARENT="$_ep_out"
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
  if [[ ! -d "${REPO_ROOT}/.jj" ]] && [[ ! -d "${REPO_ROOT}/.git" ]]; then
    echo "WARNING: inferred repo root '$(sanitize_for_output "$REPO_ROOT")' has no .jj/ or .git/ — skipping VCS cleanup" >&2
    _skip_vcs_cleanup=true
  elif [[ ! -d "${REPO_ROOT}/.jj" ]] && ! git -C "$REPO_ROOT" rev-parse --git-dir &>/dev/null; then
    echo "WARNING: inferred repo root '$(sanitize_for_output "$REPO_ROOT")' has .git/ but git rev-parse failed — VCS state may be corrupt; skipping VCS cleanup" >&2
    _skip_vcs_cleanup=true
  fi
fi

jj_forget_failed=false
git_prune_failed=false
git_remove_failed=false
if [[ "$_skip_vcs_cleanup" == "true" ]]; then
  : # Skip VCS deregistration, proceed directly to directory removal below
elif [[ -d "${REPO_ROOT}/.jj" ]]; then
  # jj workspace cleanup — forget workspace metadata before removing directory.
  # Strategy: check `jj workspace list` first; only attempt forget if the
  # workspace is listed. If not listed, it is already gone — skip forget.
  # If workspace list itself fails, attempt forget as a fallback.
  _ws_list_err=$(mktemp 2>/dev/null) && _ws_list_mktemp_ok=true || true
  _attempt_forget=true
  if ! command -v jj &>/dev/null; then
    echo "WARNING: .jj/ found but jj not installed — workspace metadata not cleaned (run: jj workspace forget worktree-$(sanitize_for_output "$WORKSPACE_NAME") from $(sanitize_for_output "$REPO_ROOT") after reinstalling jj)" >&2
    _attempt_forget=false
    jj_forget_failed=true
    [[ -n "${_ws_list_err:-}" ]] && rm -f "$_ws_list_err" && _ws_list_err=''
  elif [[ "$_ws_list_mktemp_ok" == false ]]; then
    echo "WARNING: mktemp failed — skipping jj workspace list check, attempting forget directly for worktree-$(sanitize_for_output "$WORKSPACE_NAME") (if this fails, run: cd $(sanitize_for_output "$REPO_ROOT") && jj workspace forget worktree-$(sanitize_for_output "$WORKSPACE_NAME") to clean up)" >&2
    _attempt_forget=true
  elif ! _jj_ws_list=$(cd "$REPO_ROOT" && jj workspace list 2>"$_ws_list_err"); then
    _ws_err_msg=$(cat "$_ws_list_err" 2>/dev/null)
    rm -f "$_ws_list_err"; _ws_list_err=''
    echo "WARNING: jj workspace list failed: $(sanitize_for_output "${_ws_err_msg:-(no details)}") — attempting workspace forget anyway for worktree-$(sanitize_for_output "$WORKSPACE_NAME")" >&2
  else
    rm -f "$_ws_list_err"; _ws_list_err=''
    if ! grep -qF "worktree-${WORKSPACE_NAME}:" <<< "$_jj_ws_list"; then
      echo "INFO: workspace 'worktree-$(sanitize_for_output "$WORKSPACE_NAME")' not found in jj workspace list output — skipping forget" >&2
      _attempt_forget=false
    fi
  fi
  if [[ "$_attempt_forget" == true ]]; then
    if ! jj_err=$(cd "$REPO_ROOT" && jj workspace forget "worktree-${WORKSPACE_NAME}" 2>&1); then
      echo "ERROR: jj workspace forget failed for worktree-$(sanitize_for_output "$WORKSPACE_NAME"): $(sanitize_for_output "${jj_err:0:500}"); workspace directory will still be removed (run 'jj workspace forget worktree-$(sanitize_for_output "$WORKSPACE_NAME")' manually to clean up)" >&2
      jj_forget_failed=true
    fi
  fi
else
  # Standard git worktree cleanup — log errors instead of suppressing
  if ! git_err=$(git worktree remove --force "$WORKTREE_PATH" 2>&1); then
    echo "WARNING: git worktree remove failed for '$(sanitize_for_output "$WORKTREE_PATH")': $(sanitize_for_output "${git_err:0:500}")" >&2
    git_remove_failed=true
  fi
fi

# Always attempt directory removal, even when jj workspace forget failed above.
# This avoids compounding problems: a leaked workspace entry is recoverable
# via `jj workspace forget`, but an orphaned directory is harder to diagnose.
if ! rm_err=$(rm -rf "$WORKTREE_PATH" 2>&1); then
  echo "ERROR: failed to remove worktree directory '$(sanitize_for_output "$WORKTREE_PATH")': $(sanitize_for_output "${rm_err:0:500}")" >&2
  exit 1
fi
# If git worktree remove failed, prune now that the directory is gone so git
# can clean up the orphaned .git/worktrees/ metadata entry.
if ${git_remove_failed:-false}; then
  if ! prune_err=$(git worktree prune 2>&1); then
    echo "WARNING: git worktree prune also failed: $(sanitize_for_output "${prune_err:0:500}") — stale metadata may remain in .git/worktrees/" >&2
    git_prune_failed=true
  fi
fi
# Clean up empty parent directory
cleanup_empty_parent "$(dirname "$WORKTREE_PATH")"

rm -f "$_root_err_file"
[[ -n "${_ws_list_err:-}" ]] && rm -f "$_ws_list_err"
trap - EXIT
# Directory removal succeeded above. VCS metadata cleanup outcomes differ:
# - jj workspace forget failure: exit 1 so callers know the workspace metadata
#   was NOT cleaned up (a leaked jj workspace entry can cause confusion in jj repos).
# - git worktree prune failure: exit 0 (best-effort cleanup; stale .git/worktrees/
#   metadata is cosmetic and does not affect correctness).
if ${jj_forget_failed:-false}; then
  exit 1
fi
