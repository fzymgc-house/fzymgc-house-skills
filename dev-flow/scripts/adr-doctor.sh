#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Durable health check for docs/adr/. Originally lifted from holomush
# PR #3833 (scripts/adr-doctor.sh) and adapted for dev-flow:
#
#   - Generic bd-id pattern (any prefix-NNNN, not just holomush-XXXX).
#   - No hardcoded file counts; checks invariants instead of cardinality.
#   - --changed-only flag lints only paths passed as arguments
#     (used by lefthook pre-commit per the spec).
#   - SPEC path points at the dev-flow design doc.
#   - Agent & hook locations match the dev-flow plugin layout.
#
# Wired in two places:
#   - lefthook pre-commit (changed-files-only mode, perf-bounded)
#   - CI .github/workflows/check-skills.yml (full pass, no flag)
#
# Exit codes: 0 clean; 1 on any check failure; 2 on missing prerequisites.
#
# See docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
# § "ADR Capture Subsystem".

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ADR_DIR="$REPO_ROOT/docs/adr"

# Generic bd-id matcher: any-prefix-XXXX (alnum slug after first hyphen).
# Matches holomush-abc12, fzymgc-skills-001, fhsk-406, etc.
BD_ID_RE='[a-z][a-z0-9-]*-[a-z0-9]+'

explain=0
changed_only=0
declare -a CHANGED_FILES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --explain) explain=1; shift ;;
    --changed-only) changed_only=1; shift ;;
    *)
      if [ "$changed_only" = "1" ]; then
        CHANGED_FILES+=("$1")
      fi
      shift
      ;;
  esac
done

fail_count=0

note() {
  [ "$explain" = "1" ] && echo "→ $*" >&2
}

check_fail() {
  echo "FAIL: $*" >&2
  fail_count=$((fail_count + 1))
}

# Prerequisites.
command -v jq  >/dev/null || { echo "missing prerequisite: jq"  >&2; exit 2; }
[ -d "$ADR_DIR" ] || { echo "missing $ADR_DIR" >&2; exit 2; }

# Resolve the set of ADR files to inspect.
declare -a ADR_FILES=()
if [ "$changed_only" = "1" ]; then
  for f in "${CHANGED_FILES[@]:-}"; do
    [ -z "$f" ] && continue
    case "$f" in
      */docs/adr/*.md|docs/adr/*.md) ;;
      *) continue ;;
    esac
    [ -f "$f" ] || continue
    ADR_FILES+=("$f")
  done
else
  while IFS= read -r f; do
    ADR_FILES+=("$f")
  done < <(find "$ADR_DIR" -maxdepth 1 -type f -name '*.md')
fi

# --- readme_present (INV-A12) ---
note "readme_present (INV-A12)"
if [ ! -f "$ADR_DIR/README.md" ]; then
  check_fail "missing $ADR_DIR/README.md"
fi

# --- readme_has_index_sentinels (INV-A12) ---
note "readme_has_index_sentinels (INV-A12)"
if [ -f "$ADR_DIR/README.md" ]; then
  if ! grep -qF '<!-- BEGIN INDEX -->' "$ADR_DIR/README.md"; then
    check_fail "$ADR_DIR/README.md: missing <!-- BEGIN INDEX --> sentinel"
  fi
  if ! grep -qF '<!-- END INDEX -->' "$ADR_DIR/README.md"; then
    check_fail "$ADR_DIR/README.md: missing <!-- END INDEX --> sentinel"
  fi
fi

# --- no_legacy_subdir (INV-A12) ---
# dev-flow has no legacy migration; the legacy/ subdir must never exist.
note "no_legacy_subdir (INV-A12)"
if [ -d "$ADR_DIR/legacy" ]; then
  check_fail "$ADR_DIR/legacy must not exist (dev-flow has no legacy ADR migration)"
fi

# --- file_has_decision_header (INV-A4, INV-A5) ---
# Every <bd-id>-<slug>.md must contain a **Decision:** <bd-id> line matching its filename.
note "file_has_decision_header (INV-A4, INV-A5)"
for f in "${ADR_FILES[@]:-}"; do
  [ -z "${f:-}" ] && continue
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  case "$bn" in
    README.md) continue ;;
  esac
  # Skip files that don't look like bd-id-slug at all (defensive).
  if ! printf '%s' "$bn" | grep -qE "^${BD_ID_RE}-[a-z0-9-]+\.md$"; then
    continue
  fi
  bd_id_from_filename=$(printf '%s' "$bn" | grep -oE "^${BD_ID_RE}")
  decision_line=$(grep -E "^\*\*Decision:\*\*\s+${BD_ID_RE}" "$f" | head -1)
  if [ -z "$decision_line" ]; then
    check_fail "$f: missing **Decision:** <bd-id> header"
    continue
  fi
  decision_id=$(printf '%s' "$decision_line" | grep -oE "${BD_ID_RE}" | head -1)
  if [ "$decision_id" != "$bd_id_from_filename" ]; then
    check_fail "$f: **Decision:** $decision_id does not match filename bd-id $bd_id_from_filename"
    continue
  fi
  # If bd is available, verify the record exists.
  if command -v bd >/dev/null 2>&1; then
    if ! bd show "$decision_id" >/dev/null 2>&1; then
      check_fail "$f: bd show $decision_id failed (record missing)"
    fi
  fi
done

# --- file_has_validator_sections (INV-A4) ---
note "file_has_validator_sections (INV-A4)"
for f in "${ADR_FILES[@]:-}"; do
  [ -z "${f:-}" ] && continue
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  case "$bn" in
    README.md) continue ;;
  esac
  if ! printf '%s' "$bn" | grep -qE "^${BD_ID_RE}-[a-z0-9-]+\.md$"; then
    continue
  fi
  for hdr in '## Decision' '## Rationale' '## Alternatives Considered'; do
    if ! grep -qF "$hdr" "$f"; then
      check_fail "$f: missing $hdr header"
    fi
  done
done

# Full-pass-only checks (skip when --changed-only is set, since they look
# at fixtures outside the staged file set).
if [ "$changed_only" = "0" ]; then
  # --- agent_frontmatter (INV-A14, INV-A15) ---
  note "agent_frontmatter (INV-A14, INV-A15)"
  AGENT="$REPO_ROOT/dev-flow/agents/adr-extractor.md"
  if [ ! -f "$AGENT" ]; then
    check_fail "agent file missing: $AGENT"
  else
    fm=$(awk '/^---$/{c++; next} c==1' "$AGENT")
    if ! printf '%s\n' "$fm" | grep -qE '^model:\s+sonnet\s*$'; then
      check_fail "$AGENT: model must be sonnet"
    fi
    if printf '%s\n' "$fm" | grep -qE '^\s+-\s+(Write|Edit|NotebookEdit)\s*$'; then
      check_fail "$AGENT: tools list MUST NOT include Write/Edit/NotebookEdit"
    fi
  fi

  # --- hook_executable ---
  note "hook_executable"
  HOOK="$REPO_ROOT/dev-flow/hooks/nudge-adr-capture"
  if [ ! -x "$HOOK" ]; then
    check_fail "$HOOK: not executable"
  fi
  if command -v shellcheck >/dev/null 2>&1; then
    if ! shellcheck "$HOOK" >/dev/null 2>&1; then
      check_fail "$HOOK: shellcheck failed"
    fi
  fi

  # --- forbid_skill_commits (INV-A2) ---
  note "forbid_skill_commits (INV-A2)"
  SKILL="$REPO_ROOT/dev-flow/skills/capture-adrs/SKILL.md"
  if [ -f "$SKILL" ]; then
    # shellcheck disable=SC2016  # literal regex; intentional single-quoted
    if grep -qE '(^\s*\$\s*(jj commit|jj describe|git commit|git add)|^\s*`(jj commit|jj describe|git commit|git add)`)' "$SKILL"; then
      check_fail "$SKILL: contains a commit/describe command — skill MUST NOT commit"
    fi
  fi

  # --- supersession_edges (INV-A13) ---
  note "supersession_edges (INV-A13)"
  if command -v bd >/dev/null 2>&1; then
    for f in "$ADR_DIR"/*.md; do
      [ -f "$f" ] || continue
      bn=$(basename "$f")
      [ "$bn" = "README.md" ] && continue
      status=$(grep -E "^\*\*Status:\*\*\s+Superseded by\s+${BD_ID_RE}" "$f" | head -1 || true)
      [ -n "$status" ] || continue
      this_id=$(grep -oE "^\*\*Decision:\*\*\s+${BD_ID_RE}" "$f" | grep -oE "${BD_ID_RE}" | head -1)
      superseder=$(printf '%s' "$status" | grep -oE "${BD_ID_RE}" | head -1)
      if ! bd dep list "$superseder" 2>/dev/null | grep -q "$this_id.*via supersedes"; then
        check_fail "$f: Status says superseded by $superseder, but bd dep edge missing"
      fi
    done
  fi
fi

if [ "$fail_count" -gt 0 ]; then
  echo "$fail_count check(s) failed." >&2
  exit 1
fi
echo "adr-doctor: all checks passed."
exit 0
