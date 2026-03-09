# Shared test helpers for worktree hook BATS tests

# Ensure MOCK_JJ_BIN_DIR is set and the directory exists.
_setup_mock_bin_dir() {
  MOCK_JJ_BIN_DIR="${REPO_ROOT}/bin"
  mkdir -p "$MOCK_JJ_BIN_DIR"
}

# Write a mock jj binary to MOCK_JJ_BIN_DIR.
# $1: shell snippet that implements the 'root' command response.
#     Examples:
#       'git rev-parse --show-toplevel 2>/dev/null; exit $?'   (colocated repo)
#       'echo "$JJ_REPO_ROOT"; exit 0'                         (pure jj repo)
_write_mock_jj() {
  local root_cmd="$1"
  cat > "${MOCK_JJ_BIN_DIR}/jj" << MOCK
#!/bin/bash
_mock_workspace_add() {
  if [[ "\$1" == "--help" ]]; then
    echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
    echo "  --name <NAME>"
    exit 0
  fi
  for arg in "\$@"; do
    case "\$arg" in
      -*) ;;
      *) mkdir -p "\$arg"; exit 0 ;;
    esac
  done
  exit 1
}
if [[ "\$1" == "workspace" && "\$2" == "add" ]]; then
  shift 2; _mock_workspace_add "\$@"
fi
if [[ "\$1" == "workspace" && "\$2" == "forget" && "\$3" == worktree-* ]]; then
  exit 0
fi
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
create_mock_jj() {
  _setup_mock_bin_dir
  _write_mock_jj 'git rev-parse --show-toplevel 2>/dev/null; exit $?'
}

# Create a mock jj whose --help output lacks --name (simulates old jj).
create_old_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "Usage: jj workspace add <path>"
  exit 0
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
create_logging_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
_mock_workspace_add() {
  if [[ "$1" == "--help" ]]; then
    echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
    echo "  --name <NAME>"
    exit 0
  fi
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      *) mkdir -p "$arg"; exit 0 ;;
    esac
  done
  exit 1
}
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  shift 2
  echo "$*" > "${REPO_ROOT}/jj-args.log"
  _mock_workspace_add "$@"
fi
if [[ "$1" == "workspace" && "$2" == "forget" ]]; then
  shift 2
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      worktree-*) echo "$arg" > "${REPO_ROOT}/forget-arg.log"; exit 0 ;;
    esac
  done
  exit 1
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
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

# Create a mock jj that responds to --help but fails on workspace add.
# Used for testing cleanup-on-failure paths.
create_failing_jj_mock() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
  echo "  --name <NAME>"
  exit 0
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
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
  echo "  --name <NAME>"
  exit 0
fi
if [[ "$1" == "workspace" && "$2" == "forget" ]]; then
  shift 2
  echo "$*" > "${REPO_ROOT}/forget-called.log"
  exit 0
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
}
