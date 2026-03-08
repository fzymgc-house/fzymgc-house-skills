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
  # Parse args: find --name flag and destination path
  # Real invocation: jj workspace add <path> --name <name>
  shift 2  # drop "workspace" "add"
  dest_path=""
  has_name=false
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name) has_name=true; shift ;;
      -*) ;;
      *) dest_path="$1" ;;
    esac
    shift
  done
  if [[ "$has_name" == true && -n "$dest_path" ]]; then
    mkdir -p "$dest_path"
    exit 0
  fi
  echo "ERROR: --name flag or destination not passed to jj workspace add" >&2
  exit 1
fi
if [[ "$1" == "workspace" && "$2" == "forget" && "$3" == worktree-* ]]; then
  exit 0
fi
echo "ERROR: unexpected jj invocation: $*" >&2
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
