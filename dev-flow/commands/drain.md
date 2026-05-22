---
description: Autonomous bead iteration via /goal. Modes: init, epic, set, cascade, resume.
argument-hint: "init | epic <id> | set <id...> | cascade <id...> | resume <drain-id>"
allowed-tools: ["Read", "Grep", "Glob", "Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd types:*)", "Bash(bd formula list:*)", "Bash(bd formula show:*)", "Bash(bd --json mol pour:*)", "Bash(bd mol pour:*)", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd ready:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd close:*)", "Bash(bd dep list:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.formula.toml\" .beads/formulas/:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(date:*)"]
---

# /drain

Autonomous bead-iteration harness. Drives `subagent-driven-development` across a queue of beads via Claude Code's built-in `/goal` Stop hook. See `dev-flow:draining-beads` for the canonical reference (sentinel design, halt conditions, lessons mechanism, edge cases).

Parse `$ARGUMENTS` as one of:

- `init` — Bootstrap this repo: register `drain` custom type; copy formula into `.beads/formulas/`.
- `epic <epic-id>` — Drain all open beads under `<epic-id>`.
- `set <id1> <id2> ...` — Drain only the listed beads.
- `cascade <id1> <id2> ...` — Drain seeds + transitive dependents (via `bd dep list --direction=up`).
- `resume <drain-id>` — Resume a halted drain run (recovers `mode`/`scope` from drain bead's metadata fields `drain_mode`, `drain_scope`, `drain_started_at`).
- anything else / missing — Print this usage and exit.

## Init mode (`/drain init`)

Idempotent, per-repo bootstrap. Run once per repo before any drain mode.

Execute these shell commands in order, surfacing errors plainly:

```bash
# 1. Register the custom drain type idempotently
EXISTING=$(bd config get types.custom 2>/dev/null | sed -n 's/.*= "\(.*\)"$/\1/p')
if ! echo "$EXISTING" | tr ',' '\n' | grep -qw drain; then
  bd config set types.custom "${EXISTING:+$EXISTING,}drain"
fi

# 2. Copy formula into the active repo's .beads/formulas/ (bd searches there, not plugin dirs)
mkdir -p .beads/formulas
cp -n "${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.formula.toml" .beads/formulas/

# 3. Sanity check: both assets present
bd types | grep -q drain || { echo "drain type not registered" >&2; exit 1; }
bd formula list | grep -q formula-drain || { echo "formula-drain not visible to bd" >&2; exit 1; }
echo "drain init complete."
```

`${CLAUDE_PLUGIN_ROOT}` resolves via the `allowed-tools` declaration (matches the ralph-loop / hookify slash-command pattern).

## Epic mode (`/drain epic <epic-id>`)

Drains all open beads under the specified epic. Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) pour** creates the audit-trail drain bead, **(C) sentinel** composes the natural-language condition, **(D)** fires `/goal` with the iteration body from `dev-flow:draining-beads`.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
EPIC_ID="$1"  # the bead id passed to `/drain epic <id>`

# 1. Bootstrap verified
bd types | grep -q drain && [ -f .beads/formulas/formula-drain.formula.toml ] \
  || { echo "Run /drain init first." >&2; exit 1; }

# (Spec pre-flight #2 — mode arg valid — is handled by the dispatch stub above.)

# 3. Scope validation: epic exists; has >=1 open child
bd show "$EPIC_ID" --json >/dev/null 2>&1 \
  || { echo "Epic $EPIC_ID not found." >&2; exit 1; }
OPEN_CHILDREN=$(bd list --parent "$EPIC_ID" --status=open --json | jq 'length')
[ "$OPEN_CHILDREN" -gt 0 ] \
  || { echo "Epic $EPIC_ID has no open children — nothing to drain." >&2; exit 1; }

# 4. Working tree clean (jj first if jj root succeeds; git status as fallback)
if jj root >/dev/null 2>&1; then
  DIRTY=$(jj --no-pager st | grep -E "^(M|A|D|R)" | wc -l | tr -d ' ')
else
  DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
fi
[ "$DIRTY" = "0" ] \
  || { echo "Working tree not clean ($DIRTY changes). Commit or discard before draining." >&2; exit 1; }

# 5. Branch safety (refuse main / master)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
case "$BRANCH" in
  main|master|HEAD) echo "Refuse to drain on $BRANCH. Switch to a feature branch first." >&2; exit 1 ;;
esac

# 6. Trust + hooks check
for settings_file in .claude/settings.json "$HOME/.claude/settings.json"; do
  if [ -f "$settings_file" ]; then
    if jq -e '.disableAllHooks == true or .allowManagedHooksOnly == true' "$settings_file" >/dev/null 2>&1; then
      echo "Refusing: $settings_file has hooks disabled (disableAllHooks or allowManagedHooksOnly). /goal requires hooks enabled." >&2
      exit 1
    fi
  fi
done

# 7. No overlapping drain (label-based; --type fallback per spec)
OVERLAP=$(bd list --label-pattern 'drain:*' --status=in_progress --json | jq -r '.[] | .id' | tr '\n' ' ')
[ -z "$OVERLAP" ] \
  || { echo "Refusing: drain(s) already in_progress: $OVERLAP" >&2; exit 1; }
```

Pre-flight numbering matches the spec's canonical 7-check sequence: #1 bootstrap, #2 mode-arg (handled in the dispatch stub above), #3 scope, #4 working tree, #5 branch, #6 trust+hooks, #7 no overlap.

**Phase B — Pour the drain bead + stash structured metadata**:

```bash
MODE=epic
SCOPE="$EPIC_ID"
STARTED_AT=$(date -u +%FT%TZ)

DRAIN_ID=$(bd --json mol pour formula-drain \
  --var mode="$MODE" --var scope="$SCOPE" --var started_at="$STARTED_AT" \
  | jq -r '.id')

# Defense-in-depth: confirm the bead landed as type=drain (auto-registration is invisible)
ACTUAL_TYPE=$(bd show "$DRAIN_ID" --json | jq -r '.type')
[ "$ACTUAL_TYPE" = "drain" ] \
  || { echo "Drain bead $DRAIN_ID landed as type=$ACTUAL_TYPE (expected drain); aborting." >&2; exit 1; }

# Structured metadata for resume
bd update "$DRAIN_ID" \
  --set-metadata "drain_mode=$MODE" \
  --set-metadata "drain_scope=$SCOPE" \
  --set-metadata "drain_started_at=$STARTED_AT"

# Parent linkage (epic mode only) and status transition
bd update "$DRAIN_ID" --parent "$EPIC_ID"
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for epic $EPIC_ID."
```

**Phase C — Compose the sentinel string**:

```bash
SENTINEL="All beads under epic $EPIC_ID are closed."
```

The full `/goal` prompt body (referenced as `<PROMPT_BODY>` in Phase D) lands in Task 8; for now Phase D is a directive placeholder.

**Phase D — Fire `/goal`** (literal slash-command invocation, NOT a Bash command):

After the shell commands above complete successfully, invoke:

    /goal <PROMPT_BODY>

where `<PROMPT_BODY>` is the per-iteration text from the "Iteration body" section below (filled in by Task 8). Substitute `$DRAIN_ID`, `$EPIC_ID`, `$MODE`, `$SCOPE`, `$SENTINEL` at fire time.

Remaining mode bodies are filled in by Tasks 3–8 of `docs/superpowers/plans/2026-05-22-drain-skill.md`. This stub MUST refuse all modes other than usage until those tasks land.
