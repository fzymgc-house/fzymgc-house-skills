# Shared test helpers for worktree hook BATS tests

# A PATH that preserves all tools (jq, git, etc.) but excludes jj.
# Used to simulate "jj not installed" without breaking other tools.
# On macOS (Homebrew), jj and jq share /opt/homebrew/bin — we can't just
# exclude that directory. Instead, filter PATH to drop dirs containing jj,
# and symlink needed tools (jq) from those dirs into a temp directory.
_NO_JJ_PATH=""
_NO_JJ_FILTERED_DIR=""
IFS=: read -ra _path_dirs <<< "$PATH"
for _dir in "${_path_dirs[@]}"; do
  if [[ ! -x "$_dir/jj" ]]; then
    _NO_JJ_PATH="${_NO_JJ_PATH:+$_NO_JJ_PATH:}$_dir"
  else
    # This dir has jj — create a filtered copy with other needed tools
    if [[ -z "$_NO_JJ_FILTERED_DIR" ]]; then
      _NO_JJ_FILTERED_DIR=$(mktemp -d)
    fi
    for _tool in "$_dir"/*; do
      [[ -x "$_tool" && "$(basename "$_tool")" != "jj" ]] && \
        ln -sf "$_tool" "$_NO_JJ_FILTERED_DIR/$(basename "$_tool")" 2>/dev/null || true
    done
    _NO_JJ_PATH="${_NO_JJ_PATH:+$_NO_JJ_PATH:}$_NO_JJ_FILTERED_DIR"
  fi
done
export _NO_JJ_PATH

# Ensure MOCK_JJ_BIN_DIR is set and the directory exists.
_setup_mock_bin_dir() {
  MOCK_JJ_BIN_DIR="${REPO_ROOT}/bin"
  mkdir -p "$MOCK_JJ_BIN_DIR"
}

# Shared _mock_workspace_add implementation used by both _write_mock_jj and
# create_logging_jj_mock. Interpolated into heredocs as ${_MOCK_WORKSPACE_ADD_BODY}.
_MOCK_WORKSPACE_ADD_BODY='
_mock_workspace_add() {
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      *) mkdir -p "$arg" && exit 0 ;;
    esac
  done
  exit 1
}'

# Write a mock jj binary to MOCK_JJ_BIN_DIR.
# $1: shell snippet that implements the 'root' command response.
#     Examples:
#       'git rev-parse --show-toplevel 2>/dev/null; exit $?'   (colocated repo)
#       'echo "$JJ_REPO_ROOT"; exit 0'                         (pure jj repo)
# $2: (optional) exact workspace name to accept for 'workspace forget'.
#     When provided, only that exact name succeeds; any other name exits 1.
#     When omitted, any worktree-* name succeeds (backward-compatible).
_write_mock_jj() {
  local root_cmd="$1"
  local expected_forget="${2:-}"
  local forget_check
  if [[ -n "$expected_forget" ]]; then
    forget_check="if [[ \"\$1\" == \"workspace\" && \"\$2\" == \"forget\" && \"\$3\" == \"${expected_forget}\" ]]; then
  exit 0
fi"
  else
    forget_check='if [[ "$1" == "workspace" && "$2" == "forget" && "$3" == worktree-* ]]; then
  exit 0
fi'
  fi
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
${_MOCK_WORKSPACE_ADD_BODY}
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2; _mock_workspace_add "\$@"
fi
# workspace list: dynamically list workspaces from _worktrees sibling directory
# so the workspace-exists check in worktree-remove.sh passes.
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "default: rlvkpntz abc12345 (empty) (no description set)"
  _repo=\$(pwd)
  _base=\$(basename "\$_repo")
  _parent=\$(dirname "\$_repo")
  _wt_dir="\${_parent}/\${_base}_worktrees"
  if [[ -d "\$_wt_dir" ]]; then
    for _d in "\$_wt_dir"/*/; do
      [[ -d "\$_d" ]] && echo "worktree-\$(basename "\$_d"): ssttuuvv xyz78901 (empty) (no description set)"
    done
  fi
  exit 0
fi
# workspace forget: production scripts always pass "worktree-${NAME}".
# The worktree-* pattern ensures the mock rejects unexpected workspace names
# with a clear error rather than falling through silently.
${forget_check}
if [[ "\$1" == "root" ]]; then
  ${root_cmd}
fi
echo "ERROR: unexpected jj invocation: \$*" >&2
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj binary that handles common workspace operations.
# Uses REPO_ROOT (must be set before calling).
# Sets MOCK_JJ_BIN_DIR for PATH prepending.
#
# NOTE: This mock delegates 'jj root' to 'git rev-parse --show-toplevel',
# making all tests using this mock implicitly colocated-repo tests.
# For pure-jj isolation tests (no .git/), use create_pure_jj_mock instead.
create_mock_jj() {
  _setup_mock_bin_dir
  _write_mock_jj 'git rev-parse --show-toplevel 2>/dev/null; exit $?'
}

# Create a mock jj that fails with "unexpected argument --name" (simulates old jj).
create_old_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # Detect --name flag: old jj doesn't support it
  for arg in "$@"; do
    if [[ "$arg" == "--name" ]]; then
      echo "error: unexpected argument '--name' found" >&2
      exit 1
    fi
  done
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj that fails with "unrecognized option --name" (simulates old jj).
create_old_jj_unrecognized_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # Detect --name flag: old jj doesn't support it
  for arg in "$@"; do
    if [[ "$arg" == "--name" ]]; then
      echo "error: unrecognized option '--name'" >&2
      exit 1
    fi
  done
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj that fails with "unknown argument --name" (simulates old jj).
create_old_jj_unknown_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # Detect --name flag: old jj doesn't support it
  for arg in "$@"; do
    if [[ "$arg" == "--name" ]]; then
      echo "error: unknown argument '--name'" >&2
      exit 1
    fi
  done
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj that always exits 1 (simulates broken jj install).
create_always_failing_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj that logs all workspace add args to $REPO_ROOT/jj-args.log.
# Used for verifying --name flag forwarding and other argument tests.
# $1: (optional) exact workspace name to accept for 'workspace forget'.
#     When provided, only that exact name succeeds and is logged to forget-arg.log.
#     When omitted, any worktree-* name succeeds (backward-compatible).
create_logging_jj_mock() {
  local expected_forget="${1:-}"
  local forget_check
  if [[ -n "$expected_forget" ]]; then
    forget_check="if [[ \"\$1\" == \"workspace\" && \"\$2\" == \"forget\" && \"\$3\" == \"${expected_forget}\" ]]; then
  echo \"${expected_forget}\" > \"\${REPO_ROOT}/forget-arg.log\"; exit 0
fi
if [[ \"\$1\" == \"workspace\" && \"\$2\" == \"forget\" ]]; then
  exit 1
fi"
  else
    forget_check='if [[ "$1" == "workspace" && "$2" == "forget" ]]; then
  shift 2
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      worktree-*) echo "$arg" > "${REPO_ROOT}/forget-arg.log"; exit 0 ;;
    esac
  done
  exit 1
fi'
  fi
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
${_MOCK_WORKSPACE_ADD_BODY}
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2
  echo "\$*" > "\${REPO_ROOT}/jj-args.log"
  _mock_workspace_add "\$@"
fi
# workspace list: dynamically list workspaces from _worktrees sibling directory
if [[ "\$1" == "workspace" && "\$2" == "list" ]]; then
  echo "default: rlvkpntz abc12345 (empty) (no description set)"
  _repo=\$(pwd)
  _base=\$(basename "\$_repo")
  _parent=\$(dirname "\$_repo")
  _wt_dir="\${_parent}/\${_base}_worktrees"
  if [[ -d "\$_wt_dir" ]]; then
    for _d in "\$_wt_dir"/*/; do
      [[ -d "\$_d" ]] && echo "worktree-\$(basename "\$_d"): ssttuuvv xyz78901 (empty) (no description set)"
    done
  fi
  exit 0
fi
# workspace forget: production scripts always pass "worktree-${NAME}".
# Non-worktree-* arguments are rejected (exit 1) to catch unexpected invocations.
${forget_check}
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj for a pure jj repo (no .git/).
# Unlike create_mock_jj, the 'root' command echoes JJ_REPO_ROOT directly
# instead of delegating to git rev-parse (which would fail without .git/).
# Requires JJ_REPO_ROOT to be set in the environment before calling this helper
# and before running the test binary.
create_pure_jj_mock() {
  _setup_mock_bin_dir
  _write_mock_jj 'echo "$JJ_REPO_ROOT"; exit 0'
}

# Create a mock jj that fails on workspace add.
# Used for testing cleanup-on-failure paths.
create_failing_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  echo "error: workspace add failed" >&2
  exit 1
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}

# Create a mock jj that fails on workspace add but logs workspace forget calls.
# Used to verify that cleanup_on_error invokes jj workspace forget.
# Writes the forgotten workspace name to $REPO_ROOT/forget-called.log.
create_failing_logging_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  echo "error: workspace add failed" >&2
  exit 1
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" ]]; then
  shift 2
  echo "\$*" > "${REPO_ROOT}/forget-called.log"
  exit 0
fi
if [[ "\$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit \$?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}
