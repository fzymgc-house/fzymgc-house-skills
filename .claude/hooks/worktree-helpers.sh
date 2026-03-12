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
    echo "ERROR: $(sanitize_for_output "$label") must not be empty" >&2
    return 1
  fi
  if [[ "$name" =~ [^a-zA-Z0-9_.-] || "$name" == .* || "$name" == *".."* || "$name" == *. ]]; then
    local safe_name safe_label
    safe_name=$(sanitize_for_output "$name")
    safe_label=$(sanitize_for_output "$label")
    echo "ERROR: invalid ${safe_label} '${safe_name}' (alphanumeric, dots, hyphens, underscores only; no leading dot, trailing dot, or double-dot)" >&2
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
      echo "WARNING: ls failed on parent directory '$(sanitize_for_output "$parent")' — skipping rmdir" >&2
      return 0
    fi
    if [[ -z "$ls_out" ]]; then
      _rmdir_err=$(rmdir "$parent" 2>&1) || echo "WARNING: failed to remove empty parent '$(sanitize_for_output "$parent")': $(sanitize_for_output "${_rmdir_err:0:500}")" >&2
    fi
  fi
}

# Detect repo root. Supports colocated jj repos (have .git/) and falls back
# to 'jj root' when jj is in PATH.
detect_repo_root() {
  local root
  root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [[ -n "$root" && -d "$root" ]]; then
    printf '%s\n' "$root"
    return 0
  fi
  local jj_attempted=false
  local mktemp_failed=false
  local jj_out jj_err="(not run)" jj_rc=1
  # git rev-parse failed — try jj root for non-colocated repos
  if command -v jj &>/dev/null; then
    jj_attempted=true
    local _jj_err_file
    _jj_err_file=$(mktemp) || {
      echo "WARNING: mktemp failed — cannot capture jj stderr; skipping jj root check" >&2
      jj_attempted=false
      mktemp_failed=true
    }
    if [[ "$jj_attempted" == "true" ]]; then
      jj_rc=0
      jj_out=$(jj root 2>"$_jj_err_file") || jj_rc=$?
      jj_err=$(cat "$_jj_err_file")
      rm -f "$_jj_err_file"
      if [[ $jj_rc -eq 0 && -n "$jj_out" && -d "$jj_out" ]]; then
        printf '%s\n' "$jj_out"
        return 0
      fi
    fi
  fi
  if [[ "$jj_attempted" == "true" ]]; then
    if [[ $jj_rc -ne 0 ]]; then
      echo "ERROR: not inside a git/jj repository (git rev-parse and jj root both failed${jj_err:+; jj: $(sanitize_for_output "$jj_err")})" >&2
    elif [[ -z "$jj_out" ]]; then
      echo "ERROR: not inside a git/jj repository (git rev-parse failed; jj root returned empty output)" >&2
    else
      echo "ERROR: not inside a git/jj repository (git rev-parse failed; jj root returned '$(sanitize_for_output "$jj_out")' but directory does not exist)" >&2
    fi
  elif [[ "$mktemp_failed" == "true" ]]; then
    echo "ERROR: repository root detection failed — git rev-parse failed and jj root check could not run because mktemp failed (possible resource exhaustion). If this is a jj-only repo, ensure /tmp is writable and retry." >&2
  else
    echo "ERROR: not inside a git/jj repository (git rev-parse failed; jj not in PATH)" >&2
  fi
  return 1
}
