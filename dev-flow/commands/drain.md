---
description: Autonomous bead iteration via /goal. Modes: init, epic, set, cascade, resume.
argument-hint: "init | epic <id> | set <id...> | cascade <id...> | resume <drain-id>"
allowed-tools: ["Read", "Grep", "Glob", "Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd types:*)", "Bash(bd create:*)", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd ready:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd close:*)", "Bash(bd dep list:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(date:*)"]
---

# /drain

Autonomous bead-iteration harness. Drives `subagent-driven-development` across a queue of beads via Claude Code's built-in `/goal` Stop hook. See `dev-flow:draining-beads` for the canonical reference (sentinel design, halt conditions, lessons mechanism, edge cases).

Parse `$ARGUMENTS` as one of:

- `init` — Bootstrap this repo: register the `drain` custom type.
- `epic <epic-id>` — Drain all open beads under `<epic-id>`.
- `set <id1> <id2> ...` — Drain only the listed beads.
- `cascade <id1> <id2> ...` — Drain seeds + transitive dependents (via `bd dep list --direction=up`).
- `resume <drain-id>` — Resume a halted drain run (recovers `mode`/`scope` from drain bead's metadata fields `drain_mode`, `drain_scope`, `drain_started_at`).
- anything else / missing — Print this usage and exit.

## Init mode (`/drain init`)

Idempotent, per-repo bootstrap. Run once per repo before any drain mode.

Registering the `drain` custom type is the only bootstrap step: Phase B creates
the drain bead with `bd create --type drain`, which requires `drain` to be in
`types.custom` (an unregistered type makes `bd create` fail with
`invalid issue type: drain`). No formula file is needed — see ADR `fhsk-rqh`
(superseded) for why `bd mol pour` is not used.

Execute these shell commands in order, surfacing errors plainly:

```bash
# 1. Register the custom drain type idempotently
EXISTING=$(bd config get types.custom 2>/dev/null | sed -n 's/.*= "\(.*\)"$/\1/p')
if ! echo "$EXISTING" | tr ',' '\n' | grep -qw drain; then
  bd config set types.custom "${EXISTING:+$EXISTING,}drain"
fi

# 2. Sanity check: drain type registered
bd types | grep -q drain || { echo "drain type not registered" >&2; exit 1; }
echo "drain init complete."
```

## Epic mode (`/drain epic <epic-id>`)

Drains all open beads under the specified epic. Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) create** makes the audit-trail drain bead, **(C) sentinel** composes the natural-language condition, **(D)** emits the `/goal` worker condition for an operator/driver to submit.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
EPIC_ID="$1"  # the bead id passed to `/drain epic <id>`

# 1. Bootstrap verified (drain type registered; Phase B's bd create needs it)
bd types | grep -q drain \
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
# In jj-colocated and pure-jj repos, derive the branch from the working-copy
# bookmark; fall back to git rev-parse for git-only repos. An undetermined
# branch (pure-jj with no bookmarks set) skips the check explicitly.
if jj root >/dev/null 2>&1; then
  BRANCH=$(jj --no-pager log -r @ --no-graph -T 'bookmarks' 2>/dev/null \
    | tr ' ,' '\n' | grep -v '^$' | grep -v '@origin$' | head -1)
else
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
fi
case "$BRANCH" in
  main|master|HEAD)
    echo "Refuse to drain on $BRANCH. Switch to a feature branch first." >&2; exit 1 ;;
  "")
    : ;;  # No determinable branch (pure-jj repo with no bookmarks); skip check
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

# 7. No overlapping drain — refuse only when an in_progress drain's scope
#    intersects THIS run's scope, so drains of disjoint chains run concurrently.
#    Filter with --type=drain: pre-flight #1 guarantees the type is registered,
#    and --type filters reliably. Do NOT use --label-pattern / --label-regex —
#    both are silently ignored by `bd list` (bd <=1.0.4) and return every
#    in_progress bead, false-positiving on unrelated work (see fhsk-4ut).
NEW_SCOPE="${SCOPE:-$EPIC_ID}"  # set/cascade: $SCOPE ("$*"); epic: $EPIC_ID
OVERLAP=""
for did in $(bd list --type=drain --status=in_progress --json | jq -r '.[].id'); do
  [ "$did" = "${DRAIN_ID:-}" ] && continue  # resume: skip the drain being resumed (unset in fresh runs)
  DSCOPE=$(bd show "$did" --json | jq -r '.[0].metadata.drain_scope // empty')
  for have in $DSCOPE; do
    for want in $NEW_SCOPE; do
      [ "$have" = "$want" ] && OVERLAP="$OVERLAP $did"
    done
  done
done
OVERLAP=$(printf '%s' "$OVERLAP" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
[ -z "$OVERLAP" ] \
  || { echo "Refusing: in_progress drain(s) overlap this scope: $OVERLAP" >&2; exit 1; }
```

Pre-flight numbering matches the spec's canonical 7-check sequence: #1 bootstrap, #2 mode-arg (handled in the dispatch stub above), #3 scope, #4 working tree, #5 branch, #6 trust+hooks, #7 no overlap.

**Phase B — Create the drain bead + stash structured metadata**:

```bash
MODE=epic
SCOPE="$EPIC_ID"
STARTED_AT=$(date -u +%FT%TZ)
WORKSPACE=$(jj root 2>/dev/null || git rev-parse --show-toplevel)  # absolute jj workspace root

# Create the typed audit-trail drain bead directly. `bd create --type drain`
# honors types.custom (pre-flight #1 guarantees `drain` is registered), stamps
# the real label, creates exactly one bead, and returns a flat top-level `.id`.
# `bd mol pour` is NOT used: bd's cook step downgrades custom step types to
# `task` (cmd/bd/cook.go stepTypeToIssueType) and never substitutes vars in
# labels, so a poured drain bead lands as type=task with a literal
# `drain:{{mode}}` label and an orphan wrapper epic. See ADR fhsk-rqh (superseded).
DRAIN_ID=$(bd create \
  --title "Drain: $MODE $SCOPE" \
  --description "Audit-trail root for the $MODE-mode drain over $SCOPE started $STARTED_AT." \
  --type drain \
  --label phase:run --label "drain:$MODE" \
  --json | jq -r '.id')
[ -n "$DRAIN_ID" ] && [ "$DRAIN_ID" != "null" ] \
  || { echo "bd create --type drain failed (drain type unregistered or create error)." >&2; exit 1; }

# Structured metadata for resume
bd update "$DRAIN_ID" \
  --set-metadata "drain_mode=$MODE" \
  --set-metadata "drain_scope=$SCOPE" \
  --set-metadata "drain_started_at=$STARTED_AT" \
  --set-metadata "drain_workspace=$WORKSPACE"

# Parent linkage (epic mode only) and status transition
bd update "$DRAIN_ID" --parent "$EPIC_ID"
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for epic $EPIC_ID."
```

**Phase C — Compose the sentinel string**:

```bash
SENTINEL="All beads under epic $EPIC_ID are closed."
bd update "$DRAIN_ID" --set-metadata "drain_sentinel=$SENTINEL"
```

**Phase D — Emit the `/goal` condition** (the command does NOT run `/goal`;
`/goal` is a user-only built-in):

Print the **Worker condition** (see that section) with `<DRAIN_ID>` and
`<SENTINEL>` substituted, prefixed with: "Launch a fresh `claude` worker in this
workspace and submit the following as its first input (do not run it here):".
Then stop — do not attempt to invoke `/goal`.

## Set mode (`/drain set <id1> <id2> ...`)

Drains an explicit set of beads by id. Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) create** makes the audit-trail drain bead, **(C) sentinel** composes the natural-language condition, **(D)** emits the `/goal` worker condition for an operator/driver to submit.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
# 1. Bootstrap verified (drain type registered; Phase B's bd create needs it)
bd types | grep -q drain \
  || { echo "Run /drain init first." >&2; exit 1; }

# (Spec pre-flight #2 — mode arg valid — is handled by the dispatch stub above.)

# 3. Scope validation: each id exists and is not already closed
for id in "$@"; do
  bd show "$id" --json >/dev/null 2>&1 \
    || { echo "Bead $id not found." >&2; exit 1; }
  STATUS=$(bd show "$id" --json | jq -r '.[0].status')
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
# In jj-colocated and pure-jj repos, derive the branch from the working-copy
# bookmark; fall back to git rev-parse for git-only repos. An undetermined
# branch (pure-jj with no bookmarks set) skips the check explicitly.
if jj root >/dev/null 2>&1; then
  BRANCH=$(jj --no-pager log -r @ --no-graph -T 'bookmarks' 2>/dev/null \
    | tr ' ,' '\n' | grep -v '^$' | grep -v '@origin$' | head -1)
else
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
fi
case "$BRANCH" in
  main|master|HEAD)
    echo "Refuse to drain on $BRANCH. Switch to a feature branch first." >&2; exit 1 ;;
  "")
    : ;;  # No determinable branch (pure-jj repo with no bookmarks); skip check
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

# 7. No overlapping drain — refuse only when an in_progress drain's scope
#    intersects THIS run's scope, so drains of disjoint chains run concurrently.
#    Filter with --type=drain: pre-flight #1 guarantees the type is registered,
#    and --type filters reliably. Do NOT use --label-pattern / --label-regex —
#    both are silently ignored by `bd list` (bd <=1.0.4) and return every
#    in_progress bead, false-positiving on unrelated work (see fhsk-4ut).
NEW_SCOPE="${SCOPE:-$EPIC_ID}"  # set/cascade: $SCOPE ("$*"); epic: $EPIC_ID
OVERLAP=""
for did in $(bd list --type=drain --status=in_progress --json | jq -r '.[].id'); do
  [ "$did" = "${DRAIN_ID:-}" ] && continue  # resume: skip the drain being resumed (unset in fresh runs)
  DSCOPE=$(bd show "$did" --json | jq -r '.[0].metadata.drain_scope // empty')
  for have in $DSCOPE; do
    for want in $NEW_SCOPE; do
      [ "$have" = "$want" ] && OVERLAP="$OVERLAP $did"
    done
  done
done
OVERLAP=$(printf '%s' "$OVERLAP" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
[ -z "$OVERLAP" ] \
  || { echo "Refusing: in_progress drain(s) overlap this scope: $OVERLAP" >&2; exit 1; }
```

Pre-flight numbering matches the spec's canonical 7-check sequence: #1 bootstrap, #2 mode-arg (handled in the dispatch stub above), #3 scope, #4 working tree, #5 branch, #6 trust+hooks, #7 no overlap.

**Phase B — Create the drain bead + stash structured metadata**:

```bash
MODE=set
STARTED_AT=$(date -u +%FT%TZ)
WORKSPACE=$(jj root 2>/dev/null || git rev-parse --show-toplevel)  # absolute jj workspace root

# Create the typed audit-trail drain bead directly (see epic-mode Phase B for
# why `bd create --type drain` is used instead of `bd mol pour`).
DRAIN_ID=$(bd create \
  --title "Drain: $MODE $SCOPE" \
  --description "Audit-trail root for the $MODE-mode drain over $SCOPE started $STARTED_AT." \
  --type drain \
  --label phase:run --label "drain:$MODE" \
  --json | jq -r '.id')
[ -n "$DRAIN_ID" ] && [ "$DRAIN_ID" != "null" ] \
  || { echo "bd create --type drain failed (drain type unregistered or create error)." >&2; exit 1; }

# Structured metadata for resume
bd update "$DRAIN_ID" \
  --set-metadata "drain_mode=$MODE" \
  --set-metadata "drain_scope=$SCOPE" \
  --set-metadata "drain_started_at=$STARTED_AT" \
  --set-metadata "drain_workspace=$WORKSPACE"

# Status transition (no parent linkage for set mode)
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for set: $SCOPE."
```

**Phase C — Compose the sentinel string**:

```bash
SENTINEL="All of {$SCOPE} are closed."
bd update "$DRAIN_ID" --set-metadata "drain_sentinel=$SENTINEL"
```

**Phase D — Emit the `/goal` condition** (the command does NOT run `/goal`;
`/goal` is a user-only built-in):

Print the **Worker condition** (see that section) with `<DRAIN_ID>` and
`<SENTINEL>` substituted, prefixed with: "Launch a fresh `claude` worker in this
workspace and submit the following as its first input (do not run it here):".
Then stop — do not attempt to invoke `/goal`.

## Cascade mode (`/drain cascade <id1> <id2> ...`)

Drains the listed seed beads plus their transitive dependents (via `bd dep list --direction=up`). Runs four phases:
**(A) pre-flight** refuses on bad state, **(B) create** makes the audit-trail drain bead, **(C) sentinel** composes the natural-language condition + describes the working-set expansion, **(D)** emits the `/goal` worker condition for an operator/driver to submit.

**Phase A — Pre-flight checks** (refuse early on bad state):

```bash
# 1. Bootstrap verified (drain type registered; Phase B's bd create needs it)
bd types | grep -q drain \
  || { echo "Run /drain init first." >&2; exit 1; }

# (Spec pre-flight #2 — mode arg valid — is handled by the dispatch stub above.)

# 3. Scope validation: each seed exists and is not already closed
for id in "$@"; do
  bd show "$id" --json >/dev/null 2>&1 \
    || { echo "Bead $id not found." >&2; exit 1; }
  STATUS=$(bd show "$id" --json | jq -r '.[0].status')
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
# In jj-colocated and pure-jj repos, derive the branch from the working-copy
# bookmark; fall back to git rev-parse for git-only repos. An undetermined
# branch (pure-jj with no bookmarks set) skips the check explicitly.
if jj root >/dev/null 2>&1; then
  BRANCH=$(jj --no-pager log -r @ --no-graph -T 'bookmarks' 2>/dev/null \
    | tr ' ,' '\n' | grep -v '^$' | grep -v '@origin$' | head -1)
else
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
fi
case "$BRANCH" in
  main|master|HEAD)
    echo "Refuse to drain on $BRANCH. Switch to a feature branch first." >&2; exit 1 ;;
  "")
    : ;;  # No determinable branch (pure-jj repo with no bookmarks); skip check
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

# 7. No overlapping drain — refuse only when an in_progress drain's scope
#    intersects THIS run's scope, so drains of disjoint chains run concurrently.
#    Filter with --type=drain: pre-flight #1 guarantees the type is registered,
#    and --type filters reliably. Do NOT use --label-pattern / --label-regex —
#    both are silently ignored by `bd list` (bd <=1.0.4) and return every
#    in_progress bead, false-positiving on unrelated work (see fhsk-4ut).
NEW_SCOPE="${SCOPE:-$EPIC_ID}"  # set/cascade: $SCOPE ("$*"); epic: $EPIC_ID
OVERLAP=""
for did in $(bd list --type=drain --status=in_progress --json | jq -r '.[].id'); do
  [ "$did" = "${DRAIN_ID:-}" ] && continue  # resume: skip the drain being resumed (unset in fresh runs)
  DSCOPE=$(bd show "$did" --json | jq -r '.[0].metadata.drain_scope // empty')
  for have in $DSCOPE; do
    for want in $NEW_SCOPE; do
      [ "$have" = "$want" ] && OVERLAP="$OVERLAP $did"
    done
  done
done
OVERLAP=$(printf '%s' "$OVERLAP" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
[ -z "$OVERLAP" ] \
  || { echo "Refusing: in_progress drain(s) overlap this scope: $OVERLAP" >&2; exit 1; }
```

Pre-flight numbering matches the spec's canonical 7-check sequence: #1 bootstrap, #2 mode-arg (handled in the dispatch stub above), #3 scope, #4 working tree, #5 branch, #6 trust+hooks, #7 no overlap.

**Phase B — Create the drain bead + stash structured metadata**:

```bash
MODE=cascade
STARTED_AT=$(date -u +%FT%TZ)
WORKSPACE=$(jj root 2>/dev/null || git rev-parse --show-toplevel)  # absolute jj workspace root

# Create the typed audit-trail drain bead directly (see epic-mode Phase B for
# why `bd create --type drain` is used instead of `bd mol pour`).
DRAIN_ID=$(bd create \
  --title "Drain: $MODE $SCOPE" \
  --description "Audit-trail root for the $MODE-mode drain over $SCOPE started $STARTED_AT." \
  --type drain \
  --label phase:run --label "drain:$MODE" \
  --json | jq -r '.id')
[ -n "$DRAIN_ID" ] && [ "$DRAIN_ID" != "null" ] \
  || { echo "bd create --type drain failed (drain type unregistered or create error)." >&2; exit 1; }

# Structured metadata for resume
bd update "$DRAIN_ID" \
  --set-metadata "drain_mode=$MODE" \
  --set-metadata "drain_scope=$SCOPE" \
  --set-metadata "drain_started_at=$STARTED_AT" \
  --set-metadata "drain_workspace=$WORKSPACE"

# Status transition (no parent linkage for cascade mode — no single parent)
bd update "$DRAIN_ID" --status=in_progress

echo "Drain bead $DRAIN_ID created for cascade seeds: $SCOPE."
```

**Phase C — Compose the sentinel string**:

```bash
SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed."
bd update "$DRAIN_ID" --set-metadata "drain_sentinel=$SENTINEL"
```

(`$SCOPE` was set to `"$*"` in Phase A; reusing here.)

The iteration body (see "Iteration body" section below) maintains the working-set state in cascade mode: Step 4's cascade branch starts with the seeds from `$SCOPE`, expands via `bd dep list <closed-id> --direction=up` after each close, and terminates when both no open beads remain in the working set and the most recent close revealed no new dependents.

**Phase D — Emit the `/goal` condition** (the command does NOT run `/goal`;
`/goal` is a user-only built-in):

Print the **Worker condition** (see that section) with `<DRAIN_ID>` and
`<SENTINEL>` substituted, prefixed with: "Launch a fresh `claude` worker in this
workspace and submit the following as its first input (do not run it here):".
Then stop — do not attempt to invoke `/goal`.

## Resume mode (`/drain resume <drain-id>`)

Resumes a halted drain run by recovering structured metadata from the drain bead and re-firing `/goal` with the same sentinel. The drain bead's existing notes (lessons, rejection counts, halt reasons) carry forward unchanged — the iteration body's halt-check on iteration 1 will see prior `rejection:` notes and trip immediately if any task is already past N=3.

```bash
DRAIN_ID="$1"

# 1. Recover structured fields from drain bead metadata
META=$(bd show "$DRAIN_ID" --json | jq '.[0].metadata')
MODE=$(echo "$META" | jq -r '.drain_mode')
SCOPE=$(echo "$META" | jq -r '.drain_scope')
STARTED_AT=$(echo "$META" | jq -r '.drain_started_at')
WORKSPACE=$(echo "$META" | jq -r '.drain_workspace // empty')
SENTINEL=$(echo "$META" | jq -r '.drain_sentinel // empty')

[ -n "$MODE" ] && [ "$MODE" != "null" ] \
  || { echo "Drain bead $DRAIN_ID has no drain_mode metadata; cannot resume." >&2; exit 1; }
[ -n "$SCOPE" ] && [ "$SCOPE" != "null" ] \
  || { echo "Drain bead $DRAIN_ID has no drain_scope metadata; cannot resume." >&2; exit 1; }
[ -n "$STARTED_AT" ] && [ "$STARTED_AT" != "null" ] \
  || { echo "Drain bead $DRAIN_ID has no drain_started_at metadata; cannot resume." >&2; exit 1; }

# 2. Re-run the mode-specific Phase A pre-flight against the recovered $SCOPE.
#    The pre-flight body is in the corresponding mode's section above — there is
#    no shared function (slash-command Bash runs each block standalone). The
#    invoking model MUST copy-paste the appropriate Phase A block here:
#      - $MODE == epic     → copy Epic mode Phase A (with $SCOPE bound to $EPIC_ID)
#      - $MODE == set      → copy Set mode Phase A (the per-seed loop over $SCOPE words)
#      - $MODE == cascade  → copy Cascade mode Phase A (the per-seed loop over $SCOPE words)
#    Then continue to step 3.

# 3. Sentinel: prefer the stamped drain_sentinel; recompose only if absent (older beads)
if [ -z "$SENTINEL" ]; then
  case "$MODE" in
    epic)    SENTINEL="All beads under epic $SCOPE are closed." ;;
    set)     SENTINEL="All of {$SCOPE} are closed." ;;
    cascade) SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed." ;;
    *)       echo "Unknown drain_mode '$MODE' on $DRAIN_ID; cannot resume." >&2; exit 1 ;;
  esac
fi

echo "Resuming drain $DRAIN_ID (mode=$MODE, scope=$SCOPE, started=$STARTED_AT)."
```

After the shell commands above complete successfully, fall through to **Phase D — Emit the `/goal` condition**, which emits the Worker condition for the recovered `$MODE`/`$SCOPE`/`$SENTINEL` (the operator/driver submits it to a worker).

## Worker condition (the `/goal` payload)

Phases D above **emit** this condition for an operator (or a cmux/tmux / Agent
SDK driver) to submit as a worker's `/goal` turn. The skill never fires `/goal`
— see `dev-flow:draining-beads` "Using `/goal` correctly". Substitute
`<DRAIN_ID>` and `<SENTINEL>`; submit the result verbatim:

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Execute exactly ONE ready bead this
turn following the protocol, then stop. Goal met when: <SENTINEL>.
```

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

2. Check halt conditions — scan `bd show $DRAIN_ID --json | jq -r '.[0].notes'` for any
   "rejection: <id> N=3+" line OR any prior "halt:" line. On match: append
   `bd note $DRAIN_ID "halt: <reason>"`, run `/goal clear`, send PushNotification,
   exit.

3. Read lessons — collect `bd show $DRAIN_ID --json | jq -r '.[0].notes'` filtered to
   prefix "lesson:" (run-scoped). For epic mode, ALSO read `bd show $EPIC_ID --json | jq -r '.[0].notes'`
   filtered to prefix "lesson:" (epic-scoped). Concatenate into a $LESSONS variable
   for step 7.

4. Pick next ready bead — `bd ready --json` filtered to in-scope per mode:
     - epic mode: `bd ready --parent "$EPIC_ID" --json`
       (descendants of the epic that are currently ready). Use the native
       `--parent` flag, NOT a jq filter on `.parent`: `bd ready` JSON has no
       `.parent` field (it is always null), so `select(.parent == ...)` matches
       nothing and the queue looks permanently empty. The flag matches the
       sentinel's `bd list --parent` idiom and is verified to filter (a
       nonexistent parent returns zero rows, not all).
     - set mode: `bd ready --json | jq '[.[] | select(.id == ("'"$SCOPE"' " | split(" ")[]))]'`
       (only the explicit seed ids).
     - cascade mode: maintain a working set in this session (initially the seeds
       from `$SCOPE`). After each bead closes in step 9, expand the working set
       via `bd dep list <closed-id> --direction=up --json | jq -r '.[].id'`
       (newly-revealed dependents) and add any ids not already in the set.
       Filter `bd ready` to ids currently in the working set.
   Deterministic order across all modes: lowest priority number, then alphabetic id.
   If filter empty but sentinel says not met → re-evaluate sentinel (in cascade
   mode, this means the working set has no open beads AND the last close added
   no new dependents); if still not met, halt with "stalled queue" reason.

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
