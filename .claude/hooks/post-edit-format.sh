#!/usr/bin/env bash
# PostToolUse hook: auto-format edited files
# Reads hook JSON from stdin, extracts file_path, runs appropriate formatter.
set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
  *.py)
    ruff check --fix --quiet "$FILE" 2>/dev/null || true
    ruff format --quiet "$FILE" 2>/dev/null || true
    ;;
  *.md)
    rumdl check --fix "$FILE" 2>/dev/null || true
    ;;
esac
