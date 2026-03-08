# Shared test helpers for worktree hook BATS tests

# Create a mock jj binary that handles common workspace operations.
# Uses REPO_ROOT (must be set before calling).
# Sets MOCK_JJ_BIN_DIR for PATH prepending.
create_mock_jj() {
  MOCK_JJ_BIN_DIR="${REPO_ROOT}/bin"
  mkdir -p "$MOCK_JJ_BIN_DIR"
  cat > "${MOCK_JJ_BIN_DIR}/jj" << 'MOCK'
#!/bin/bash
if [[ "$1" == "workspace" && "$2" == "add" ]]; then
  # --help probe for version guard
  if [[ "$3" == "--help" ]]; then
    echo "Usage: jj workspace add [OPTIONS] <DESTINATION>"
    echo "  --name <NAME>"
    exit 0
  fi
  # Require --name flag (matches real jj invocation)
  for arg in "$@"; do
    if [[ "$arg" == "--name" ]]; then
      # $3 is the destination path; create it
      mkdir -p "$3"
      exit 0
    fi
  done
  echo "ERROR: --name flag not passed to jj workspace add" >&2
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
