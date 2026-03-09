#!/usr/bin/env bash
# Shared helpers for worktree-create.sh and worktree-remove.sh

sanitize_for_output() {
  # Strip C0 control chars (0x00-0x1F) except \t (009), \n (012), \r (015),
  # plus DEL (0x7F) and C1 control chars (0x80-0x9F).
  # Preserving \t, \n, \r allows multi-line error messages to remain readable.
  local input="$1"
  printf '%s' "$input" | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177\200-\237'
}

validate_safe_name() {
  local name="$1" label="$2"
  if [[ -z "$name" ]]; then
    echo "ERROR: ${label} must not be empty" >&2
    return 1
  fi
  if [[ "$name" =~ [^a-zA-Z0-9_.-] || "$name" == .* || "$name" == *".."* || "$name" == *. ]]; then
    local safe_name safe_label
    safe_name=$(sanitize_for_output "$name")
    safe_label=$(sanitize_for_output "$label")
    echo "ERROR: invalid ${safe_label} '${safe_name}' (alphanumeric, dots, hyphens, underscores only; no leading dot)" >&2
    return 1
  fi
}

# Remove parent directory if it exists and is empty. Safe to call even if the
# directory does not exist.
cleanup_empty_parent() {
  local parent="$1"
  if [[ -d "$parent" ]]; then
    local ls_out
    local _rmdir_err
    if ! ls_out=$(ls -A "$parent" 2>/dev/null); then
      echo "WARNING: ls failed on parent directory '$parent' — skipping rmdir" >&2
      return 0
    fi
    if [[ -z "$ls_out" ]]; then
      _rmdir_err=$(rmdir "$parent" 2>&1) || echo "WARNING: failed to remove empty parent '$(sanitize_for_output "$parent")': $(sanitize_for_output "${_rmdir_err:0:200}")" >&2
    fi
  fi
}

# Detect repo root. Supports colocated jj repos (have .git/) and falls back
# to 'jj root' for non-colocated repos when .jj/ exists.
detect_repo_root() {
  local root
  root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [[ -n "$root" && -d "$root" ]]; then
    printf '%s\n' "$root"
    return 0
  fi
  # git rev-parse failed — try jj root for non-colocated repos
  if command -v jj &>/dev/null; then
    local jj_out jj_rc=0
    jj_out=$(jj root 2>&1) || jj_rc=$?
    if [[ $jj_rc -eq 0 && -n "$jj_out" && -d "$jj_out" ]]; then
      printf '%s\n' "$jj_out"
      return 0
    fi
  fi
  echo "ERROR: not inside a git/jj repository (git rev-parse and jj root both failed${jj_out:+; jj: $(sanitize_for_output "$jj_out")})" >&2
  return 1
}
