#!/usr/bin/env bats

# Lint test: all pr-review agents that run VCS operations must reference the
# VCS detection preamble (pr-review/references/vcs-detection-preamble.md).
# Agents reference it by including its path in their instructions.
#
# review-gate.md is intentionally excluded: it is a read-only agent with no
# worktree isolation that receives a pre-built VCS diff as input and never
# runs VCS commands directly.

# Note: this test is a textual presence check only — it verifies that agents
# include a reference to the VCS detection preamble in their source. Runtime
# invocation and correct branching behavior are covered by behavioral evals
# (B-FW1, B-VCS-GIT1).
@test "all pr-review agents (except review-gate) reference VCS detection preamble" {
  local repo_root
  repo_root="$(cd "$BATS_TEST_DIRNAME/../../.." && pwd)"

  local agents_dir="$repo_root/pr-review/agents"
  [ -d "$agents_dir" ] || {
    echo "agents dir not found: $agents_dir" >&2
    return 1
  }

  local missing=()
  local agent_file
  while IFS= read -r agent_file; do
    # review-gate is read-only and receives a pre-built diff; no VCS commands needed
    [[ "$(basename "$agent_file")" == "review-gate.md" ]] && continue
    if ! grep -q "vcs-detection-preamble" "$agent_file"; then
      missing+=("$agent_file")
    fi
  done < <(find "$agents_dir" -maxdepth 1 -name "*.md" | sort)

  if [ "${#missing[@]}" -gt 0 ]; then
    echo "The following pr-review agents are missing the VCS detection preamble reference (grep: 'vcs-detection-preamble'):" >&2
    for f in "${missing[@]}"; do
      echo "  $f" >&2
    done
    return 1
  fi
}

@test "all pr-review skills reference VCS detection preamble" {
  local repo_root
  repo_root="$(cd "$BATS_TEST_DIRNAME/../../.." && pwd)"

  local skills_dir="$repo_root/pr-review/skills"
  [ -d "$skills_dir" ] || {
    echo "skills dir not found: $skills_dir" >&2
    return 1
  }

  local missing=()
  local skill_file
  while IFS= read -r skill_file; do
    if ! grep -q "vcs-detection-preamble" "$skill_file"; then
      missing+=("$skill_file")
    fi
  done < <(find "$skills_dir" -name "SKILL.md" | sort)

  if [ "${#missing[@]}" -gt 0 ]; then
    echo "The following pr-review skills are missing the VCS detection preamble reference (grep: 'vcs-detection-preamble'):" >&2
    for f in "${missing[@]}"; do
      echo "  $f" >&2
    done
    return 1
  fi
}
