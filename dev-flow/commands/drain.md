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

## Set mode (`/drain set <id1> <id2> ...`)

Drains an explicit set of beads by id. Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) pour** creates the audit-trail drain bead, **(C) sentinel** composes the natural-language condition, **(D)** fires `/goal` with the iteration body from `dev-flow:draining-beads`.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
# 1. Bootstrap verified
bd types | grep -q drain && [ -f .beads/formulas/formula-drain.formula.toml ] \
  || { echo "Run /drain init first." >&2; exit 1; }

# (Spec pre-flight #2 — mode arg valid — is handled by the dispatch stub above.)

# 3. Scope validation: each id exists and is not already closed
for id in "$@"; do
  bd show "$id" --json >/dev/null 2>&1 \
    || { echo "Bead $id not found." >&2; exit 1; }
  STATUS=$(bd show "$id" --json | jq -r '.status')
  [ "$STATUS" != "closed" ] \
    || { echo "Bead $id is already closed; remove from set." >&2; exit 1; }
done
SCOPE="$*"

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
MODE=set
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

# Status transition (no parent linkage for set mode)
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for set: $SCOPE."
```

**Phase C — Compose the sentinel string**:

```bash
SENTINEL="All of {$SCOPE} are closed."
```

The full `/goal` prompt body (referenced as `<PROMPT_BODY>` in Phase D) lands in Task 8; for now Phase D is a directive placeholder.

**Phase D — Fire `/goal`** (literal slash-command invocation, NOT a Bash command):

After the shell commands above complete successfully, invoke:

    /goal <PROMPT_BODY>

where `<PROMPT_BODY>` is the per-iteration text from the "Iteration body" section below (filled in by Task 8). Substitute `$DRAIN_ID`, `$MODE`, `$SCOPE`, `$SENTINEL` at fire time.

## Cascade mode (`/drain cascade <id1> <id2> ...`)

Drains the listed seed beads plus their transitive dependents (via `bd dep list --direction=up`). Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) pour** creates the audit-trail drain bead, **(C) sentinel** composes the natural-language condition + describes the working-set expansion, **(D)** fires `/goal` with the iteration body from `dev-flow:draining-beads`.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
# 1. Bootstrap verified
bd types | grep -q drain && [ -f .beads/formulas/formula-drain.formula.toml ] \
  || { echo "Run /drain init first." >&2; exit 1; }

# (Spec pre-flight #2 — mode arg valid — is handled by the dispatch stub above.)

# 3. Scope validation: each seed exists and is not already closed
for id in "$@"; do
  bd show "$id" --json >/dev/null 2>&1 \
    || { echo "Bead $id not found." >&2; exit 1; }
  STATUS=$(bd show "$id" --json | jq -r '.status')
  [ "$STATUS" != "closed" ] \
    || { echo "Bead $id is already closed; remove from cascade seeds." >&2; exit 1; }
done
SCOPE="$*"

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
MODE=cascade
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

# Status transition (no parent linkage for cascade mode — no single parent)
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for cascade seeds: $SCOPE."
```

**Phase C — Compose the sentinel string**:

```bash
SCOPE="$*"  # space-separated seeds
SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed."
```

**Working-set expansion**: cascade mode does not pre-compute the full reachable set. Instead, the per-iteration helper (defined in Task 8) maintains a stateful working set that starts as `{$SCOPE}` and grows as beads close. After each close, the helper calls `bd dep list <closed-id> --direction=up --json | jq -r '.[].id'` to surface newly-revealed dependents and adds any not-yet-seen ids to the working set. The helper terminates when (a) no open beads remain in the working set AND (b) the most recent close revealed no new dependents — both conditions must hold simultaneously to declare the sentinel satisfied.

The full `/goal` prompt body (referenced as `<PROMPT_BODY>` in Phase D) lands in Task 8; for now Phase D is a directive placeholder.

**Phase D — Fire `/goal`** (literal slash-command invocation, NOT a Bash command):

After the shell commands above complete successfully, invoke:

    /goal <PROMPT_BODY>

where `<PROMPT_BODY>` is the per-iteration text from the "Iteration body" section below (filled in by Task 8). Substitute `$DRAIN_ID`, `$MODE`, `$SCOPE`, `$SENTINEL` at fire time. For cascade mode the iteration body must call the working-set helper described above so the cascade expands as dependents are revealed.

## Resume mode (`/drain resume <drain-id>`)

Resumes a halted drain run by recovering structured metadata from the drain bead and re-firing `/goal` with the same sentinel. The drain bead's existing notes (lessons, rejection counts, halt reasons) carry forward unchanged — the iteration body's halt-check on iteration 1 will see prior `rejection:` notes and trip immediately if any task is already past N=3.

```bash
DRAIN_ID="$1"

# 1. Recover structured fields from drain bead metadata
META=$(bd show "$DRAIN_ID" --json | jq '.metadata')
MODE=$(echo "$META" | jq -r '.drain_mode')
SCOPE=$(echo "$META" | jq -r '.drain_scope')
STARTED_AT=$(echo "$META" | jq -r '.drain_started_at')

[ -n "$MODE" ] && [ "$MODE" != "null" ] \
  || { echo "Drain bead $DRAIN_ID has no drain_mode metadata; cannot resume." >&2; exit 1; }

# 2. Re-run pre-flight (Phase A from the original mode) against $SCOPE.
#    For epic mode, re-run epic-mode Phase A (with $SCOPE as $EPIC_ID).
#    For set/cascade modes, re-run their respective per-seed Phase A loops.
#    The specific Phase A pre-flight is invoked from the corresponding mode's section above.

# 3. Recompose the same SENTINEL string the original run used
case "$MODE" in
  epic)    SENTINEL="All beads under epic $SCOPE are closed." ;;
  set)     SENTINEL="All of {$SCOPE} are closed." ;;
  cascade) SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed." ;;
  *)       echo "Unknown drain_mode '$MODE' on $DRAIN_ID; cannot resume." >&2; exit 1 ;;
esac

echo "Resuming drain $DRAIN_ID (mode=$MODE, scope=$SCOPE, started=$STARTED_AT)."
```

After the shell commands above complete successfully, fall through to the same `/goal <PROMPT_BODY>` invocation as the original mode (Phase D directive). The iteration body in Task 8 handles all three modes via the `$MODE` substitution.

## Iteration body (`/goal` Stop-hook prompt)

The text below is the **canonical iteration body** referenced by the Phase D directives in epic/set/cascade/resume modes. Each Phase D substitutes `$DRAIN_ID`, `$MODE`, `$SCOPE`, `$SENTINEL`, and `$EPIC_ID` (when in epic mode) into this body and fires `/goal` with the result. `/goal` re-fires this prompt as a user message on each Stop event; each firing runs ONE bead per the steps below.

```text
You are in an autonomous drain run. Drain bead: $DRAIN_ID (mode=$MODE, scope=$SCOPE).
Sentinel: $SENTINEL

Each iteration of this Stop-hook prompt runs ONE bead. Execute these steps in order:

1. Check sentinel — run the mode-specific bd query (see dev-flow:draining-beads
   "Sentinel design" for the exact predicate). If met: emit a completion summary
   to the user, append `bd note $DRAIN_ID "result: complete; iterations=<N>, ..."`,
   run `bd close $DRAIN_ID --reason="drain completed cleanly"`, invoke
   dev-flow:finishing-a-development-branch, then exit (do NOT continue to step 2).

2. Check halt conditions — scan `bd show $DRAIN_ID --json | jq '.notes'` for any
   "rejection: <id> N=3+" line OR any prior "halt:" line. On match: append
   `bd note $DRAIN_ID "halt: <reason>"`, run `/goal clear`, send PushNotification,
   exit.

3. Read lessons — collect `bd show $DRAIN_ID --json | jq '.notes'` filtered to
   prefix "lesson:" (run-scoped). For epic mode, ALSO read `bd show $EPIC_ID --json | jq '.notes'`
   filtered to prefix "lesson:" (epic-scoped). Concatenate into a $LESSONS variable
   for step 7.

4. Pick next ready bead — `bd ready --json` filtered to in-scope (per mode).
   Deterministic order: lowest priority number, then alphabetic id. If filter
   empty but sentinel says not met → re-evaluate sentinel; if still not met,
   halt with "stalled queue" reason.

5. Atomic claim — `bd update <id> --claim`. On race (claim fails), skip step 6
   and restart iteration (re-fire of this prompt).

6. Load context — `bd show <id> --json` for description / acceptance / spec-id;
   if spec-id present, read the referenced spec/plan file for surrounding context.

7. Dispatch implementer subagent — per dev-flow:subagent-driven-development:
     subagent_type from bead's skills[] (heuristic; general-purpose fallback)
     model       from bead's model:* label (default sonnet per Rule 5)
     prompt      = bead description + acceptance criteria + spec excerpts + $LESSONS
   In jj repos (jj root succeeds): brief the subagent to run `jj --no-pager new`
   before any edits. In git repos: no-op.

8. Two-stage review — spec compliance reviewer (./spec-reviewer-prompt.md), then
   code quality reviewer (./code-quality-reviewer-prompt.md). On either failing,
   the implementer fixes and re-reviews.

9. On approval — `bd close <id> --reason="<one-line summary>"`. Append a bd note
   for any deviations or follow-ups discovered.

10. On rejection (review loops exhausted this iteration):
      bd update <id> --status=open
      bd note <id> "rejection round N: <reason>"
      bd note $DRAIN_ID "rejection: <id> N=<count>"
    Step 2 catches N>=3 on the NEXT iteration.

11. VCS verify — `jj st` (or `git status --porcelain`); confirm clean tree.
    If dirty: bd note $DRAIN_ID "halt: dirty-tree iter <N>"; halt.

12. Iteration ends. The /goal Stop hook re-fires this prompt → step 1.
```

The Phase D directives in epic/set/cascade/resume modes substitute the run-time values and pass the assembled string as `/goal`'s condition. See `dev-flow:draining-beads` for the full canonical reference (sentinel design, halt conditions, lessons mechanism, edge cases).

Remaining mode bodies are filled in by Tasks 3–8 of `docs/superpowers/plans/2026-05-22-drain-skill.md`. This stub MUST refuse all modes other than usage until those tasks land.
