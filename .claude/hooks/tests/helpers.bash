# Shared test helpers for worktree hook BATS tests

# Ensure MOCK_JJ_BIN_DIR is set and the directory exists.
_setup_mock_bin_dir() {
  MOCK_JJ_BIN_DIR="${REPO_ROOT}/bin"
  mkdir -p "$MOCK_JJ_BIN_DIR"
}

# Create a mock jj binary that handles common workspace operations.
# Uses REPO_ROOT (must be set before calling).
# Sets MOCK_JJ_BIN_DIR for PATH prepending.
create_mock_jj() {
  _setup_mock_bin_dir
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # --help probe for version guard
  if [[ "$3" == "--help" ]]; then
    echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
    echo "  --name <NAME>"
    exit 0
  fi
  # Find the destination path (first non-flag argument after "workspace add")
  shift 2
  for arg in "$@"; do
    case "$arg" in
      -*) ;;
      *) mkdir -p "$arg"; exit 0 ;;
    esac
  done
  exit 1
fi
if [[ "$1" == "workspace" && "$2" == "forget" && "$3" == worktree-* ]]; then
  exit 0
fi
if [[ "$1" == "root" ]]; then
  git rev-parse --show-toplevel 2>/dev/null
  exit $?
fi
echo "ERROR: unexpected jj invocation: $*" >&2
exit 1
MOCK
  chmod +x "${MOCK_JJ_BIN_DIR}/jj"
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
if [[ "$1" == "workspace" && "$2" == "add" && "$3" == "--help" ]]; then
  echo "  --name <NAME>"
  exit 0
fi
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  echo "$@" > "${REPO_ROOT}/jj-args.log"
  mkdir -p "$3"
  exit 0
fi
if [[ "$1" == "workspace" && "$2" == "forget" && "$3" == worktree-* ]]; then
  echo "$3" > "${REPO_ROOT}/forget-arg.log"
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
