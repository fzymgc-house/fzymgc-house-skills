#!/usr/bin/env bash
# Shared helpers for worktree-create.sh and worktree-remove.sh

validate_safe_name() {
  local name="$1" label="$2"
  if [[ "$name" =~ [^a-zA-Z0-9_.-] || "$name" == .* || "$name" == *".."* || "$name" == *. ]]; then
    echo "ERROR: invalid ${label} '${name}' (alphanumeric, dots, hyphens, underscores only; no leading dot)" >&2
    return 1
  fi
}

# Detect repo root. Supports colocated jj repos (have .git/) and falls back
# to 'jj root' for non-colocated repos when .jj/ exists.
detect_repo_root() {
  if git rev-parse --show-toplevel 2>/dev/null; then
    return 0
  fi
  # git rev-parse failed — try jj root for non-colocated repos
  if command -v jj &>/dev/null && jj root 2>/dev/null; then
    return 0
  fi
  echo "ERROR: not inside a git/jj repository (git rev-parse and jj root both failed)" >&2
  return 1
}
