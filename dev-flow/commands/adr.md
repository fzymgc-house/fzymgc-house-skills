---
description: ADR lifecycle operations. Modes: init, new, propose, update, supersede, addendum, accept, deprecate, render, migrate.
argument-hint: "init | new | propose | update <id> | supersede <old-id> | addendum <id> --text \"...\" | accept <id> | deprecate <id> --reason \"...\" | render <id> | migrate [--apply]"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Bash(bd:*)", "Bash(jq:*)", "Bash(printf:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/render-adr:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(date:*)"]
---

# /adr

ADR lifecycle operations. bd is the source of truth; this command mutates bd state and re-renders `docs/adr/<id>-<slug>.md` via `${CLAUDE_PLUGIN_ROOT}/scripts/render-adr`. See `dev-flow:evolve-adr` for the canonical reference (capture-vs-propose distinction, status mechanics, migration).

Parse `$ARGUMENTS` as one of:

- `init` — No-op (retained for compatibility): `decision` is a built-in bd type and ADR bodies are composed inline, so no formula or type registration is needed.
- `new` — Retrospective documentation. Creates ADR + auto-closes (Accepted).
- `propose` — Forward-looking. Creates ADR (Proposed; bd status=open).
- `update <id>` — Edit an ADR's body or sections; re-render.
- `supersede <old-id>` — Create a new ADR that supersedes `<old-id>`; wire the dep edge; re-render both.
- `addendum <id> --text "..."` — Append clarification as a bd note; re-render.
- `accept <id>` — Close a Proposed ADR (status flips to Accepted); re-render.
- `deprecate <id> --reason "..."` — Add `adr:deprecated` label; re-render.
- `render <id>` — Re-render only; no bd mutation.
- `migrate [--apply]` — Backfill metadata + re-render legacy ADRs. Defaults to dry-run; `--apply` mutates.

## Init mode (/adr init)

No-op, retained for backward compatibility. `decision` is a built-in bd type
and `/adr new|propose|supersede` compose the ADR body inline with `bd create`,
so there is no formula file to copy and no custom type to register. See ADR
`fhsk-buu` for why `bd mol pour` is not used.

```bash
bd types | grep -qw decision \
  || { echo "bd 'decision' type unavailable; upgrade bd." >&2; exit 1; }
echo "/adr init: no bootstrap required (decision is a built-in type)."
```

## New mode (/adr new)

Retrospective ADR documentation. Creates a bead via the formula and immediately closes it as Accepted.

1. Prompt operator (interactively via AskUserQuestion, or accept values from stdin/heredoc) for:
   title, context, decision, rationale, alternatives, consequences, deciders.
2. Create the decision bead, composing the 5-section body inline. `decision` is
   a built-in bd type, so `bd create --type decision` stamps it correctly,
   returns a flat top-level `.id`, and sets `adr_deciders` metadata directly.
   `bd mol pour` is NOT used: bd's cook step downgrades the formula's
   `type = "decision"` step to `task`, leaves `adr_deciders` as a literal
   `{{deciders}}` (vars are not substituted in metadata), and emits a wrapper
   epic. See ADR `fhsk-buu`.
   ```bash
   ID=$(printf '## Context\n\n%s\n\n## Decision\n\n%s\n\n## Rationale\n\n%s\n\n## Alternatives Considered\n\n%s\n\n## Consequences\n\n%s\n' \
          "$context" "$decision" "$rationale" "$alternatives" "$consequences" \
        | bd create \
            --title "$title" \
            --type decision \
            --label phase:design \
            --metadata "$(jq -n --arg d "$deciders" '{adr_deciders:$d}')" \
            --stdin --json \
        | jq -r '.id')
   [ -n "$ID" ] && [ "$ID" != "null" ] \
     || { echo "/adr new: bd create -t decision failed" >&2; exit 1; }
   ```
3. Close immediately (retrospective → Accepted):
   ```bash
   bd close "$ID" --reason="Accepted ADR filed via /adr new"
   ```
4. Render:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
   ```
5. Print: `Created and accepted ADR $ID → docs/adr/<rendered>.md`

## Propose mode (/adr propose)

Forward-looking ADR. Same flow as New EXCEPT skip Step 3 (no `bd close`). The bead stays in
`bd.status=open` so render-adr emits `Status: Proposed`.

1. Prompt operator (interactively via AskUserQuestion, or accept values from stdin/heredoc) for:
   title, context, decision, rationale, alternatives, consequences, deciders.
2. Create the decision bead, composing the 5-section body inline (see New mode
   for why `bd create --type decision` is used instead of `bd mol pour`):
   ```bash
   ID=$(printf '## Context\n\n%s\n\n## Decision\n\n%s\n\n## Rationale\n\n%s\n\n## Alternatives Considered\n\n%s\n\n## Consequences\n\n%s\n' \
          "$context" "$decision" "$rationale" "$alternatives" "$consequences" \
        | bd create \
            --title "$title" \
            --type decision \
            --label phase:design \
            --metadata "$(jq -n --arg d "$deciders" '{adr_deciders:$d}')" \
            --stdin --json \
        | jq -r '.id')
   [ -n "$ID" ] && [ "$ID" != "null" ] \
     || { echo "/adr propose: bd create -t decision failed" >&2; exit 1; }
   ```
3. Do NOT close the bead — leave it open (Proposed status).
4. Render:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
   ```
5. Print: `Proposed ADR $ID → docs/adr/<rendered>.md (run /adr accept $ID to finalize)`

## Render mode (/adr render <id>)

Re-render the ADR file from bd state. No bd mutation.

```bash
ID="$1"
bd show "$ID" --json >/dev/null 2>&1 \
  || { echo "Decision bead $ID not found." >&2; exit 1; }
${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
```

## Update mode (/adr update <id>)

Edit an ADR's body or individual sections, then re-render.

1. `ID="$1"`; show current state for context:
   ```bash
   bd show "$ID" --json | jq '.[0] | {title, description, metadata, status}'
   ```

2. Interactive: AskUserQuestion which section to edit:
   - `## Context`
   - `## Decision`
   - `## Rationale`
   - `## Alternatives Considered`
   - `## Consequences`
   - `WHOLE BODY` (replace entire description)

3. Prompt for new prose for that section (or whole body).

4. Re-compose the description body. Read current body via:
   ```bash
   CURRENT=$(bd show "$ID" --json | jq -r '.[0].description')
   ```
   Then use awk anchored on `## <section>` headings to slice/replace cleanly:
   - Match the chosen `## <section>` heading.
   - Replace its content (lines until the next `## ` heading or EOF) with the new prose.
   - Preserve all OTHER sections verbatim.
   The whole-body case just uses the new prose directly (overwrites).

   ```bash
   # Replace the ## Context section content with $NEW_PROSE, preserving others:
   echo "$CURRENT" | awk -v new="$NEW_PROSE" '
     /^## Context$/ { print; print ""; print new; print ""; in_section=1; next }
     /^## / { in_section=0 }
     !in_section { print }
   '
   ```

5. Pipe the recomposed body to bd update:
   ```bash
   printf '%s' "$NEW_BODY" | bd update "$ID" --body-file -
   ```

6. Render:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
   ```

## Addendum mode (/adr addendum <id> --text "...")

Append a clarification note to an existing ADR and re-render.

```bash
ID="$1"; shift
TEXT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --text) TEXT="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$TEXT" ] || { echo "Usage: /adr addendum <id> --text \"<text>\"" >&2; exit 1; }
bd note "$ID" "addendum: $TEXT"
${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
echo "Addendum added to $ID and re-rendered."
```

## Accept mode (/adr accept <id>)

Close a Proposed ADR (bd status=open → closed). Re-renders the file so Status flips to Accepted.

```bash
ID="$1"
STATUS=$(bd show "$ID" --json | jq -r '.[0].status')
[ "$STATUS" = "open" ] \
  || { echo "ADR $ID is not in Proposed state (bd status=$STATUS); cannot accept." >&2; exit 1; }
bd close "$ID" --reason="Accepted"
${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
echo "ADR $ID accepted."
```

## Deprecate mode (/adr deprecate <id> --reason "...")

Mark an Accepted ADR as deprecated. Requires `--reason`; guards that the ADR is already Accepted
(bd status=closed) before mutating.

```bash
ID="$1"; shift
REASON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --reason) REASON="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$REASON" ] || { echo "Usage: /adr deprecate <id> --reason \"<why>\"" >&2; exit 1; }

STATUS=$(bd show "$ID" --json | jq -r '.[0].status')
[ "$STATUS" = "closed" ] \
  || { echo "ADR $ID must be Accepted (bd status=closed) before Deprecation. Current: $STATUS." >&2; exit 1; }

bd update "$ID" --add-label adr:deprecated
bd note "$ID" "deprecated: $REASON"
${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
echo "ADR $ID deprecated: $REASON"
```

## Supersede mode (/adr supersede <old-id>)

Create a new ADR that supersedes `<old-id>`. Wires the dependency edge, closes the new ADR as
Accepted, and re-renders both files so the old ADR shows "Superseded by NEW" and the new ADR shows
"Supersedes: OLD".

Operator steps (shell + interactive):

1. `OLD="$1"`
2. Verify `<old-id>` exists and is closed (Accepted):
   ```bash
   STATUS=$(bd show "$OLD" --json | jq -r '.[0].status')
   ```
   If `$STATUS != "closed"`, error: `"Cannot supersede a Proposed ADR; /adr accept $OLD first."`
3. Run the `/adr new` flow interactively (gather title + 5 sections + deciders) to create NEW
   (see New mode for why `bd create --type decision` is used instead of `bd mol pour`):
   ```bash
   NEW=$(printf '## Context\n\n%s\n\n## Decision\n\n%s\n\n## Rationale\n\n%s\n\n## Alternatives Considered\n\n%s\n\n## Consequences\n\n%s\n' \
          "$context" "$decision" "$rationale" "$alternatives" "$consequences" \
        | bd create \
            --title "$title" \
            --type decision \
            --label phase:design \
            --metadata "$(jq -n --arg d "$deciders" '{adr_deciders:$d}')" \
            --stdin --json \
        | jq -r '.id')
   [ -n "$NEW" ] && [ "$NEW" != "null" ] \
     || { echo "/adr supersede: bd create -t decision failed" >&2; exit 1; }
   ```
4. Wire the supersession edge:
   ```bash
   bd dep add "$NEW" "$OLD" --type=supersedes
   ```
5. Close the new ADR (Accepted):
   ```bash
   bd close "$NEW" --reason="Accepted (supersedes $OLD)"
   ```
6. Re-render BOTH markdown files:
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$OLD"   # status flips to Superseded by NEW
   ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$NEW"   # References shows Supersedes: OLD
   ```
7. Print: `"Superseded $OLD with $NEW. Both ADRs re-rendered."`

## Migrate mode (/adr migrate [--apply])

Backfill `adr_deciders` metadata on legacy decision beads and re-render their `.md` files.
Defaults to **dry-run** — surveys legacy ADRs and reports what would change without mutating bd
state. Pass `--apply` to actually perform the migrations.

Three legacy paths are handled:

- **(a) Already migrated** — bead's `metadata.adr_deciders` is set → skip.
- **(b) Legacy with .md file** — bead lacks `adr_deciders` metadata but a `docs/adr/<id>-*.md`
  exists. Extract the value from the `**Deciders:**` header line in the rendered file, backfill
  the metadata, and re-render so the file is sourced from bd going forward.
- **(c) Orphan (bd record, no .md)** — bead has no rendered file. `--apply` requires interactive
  `AskUserQuestion` to ask the operator for deciders. Per INV-A19, `AskUserQuestion` is only
  available in the **main session context**, so orphan-recovery under `--apply` **fails fast**
  in non-main contexts (Codex / subagent dispatch / autonomous loops). Re-run from a primary
  Claude Code session to recover orphans. This is v1-stub behavior; a follow-up will wire the
  interactive prompt path so orphan recovery completes end-to-end from a main session.

```bash
APPLY=0
for arg in "$@"; do
  [ "$arg" = "--apply" ] && APPLY=1
done

echo "/adr migrate: --apply=$APPLY"

ALREADY=0; MIGRATED=0; RECOVERED=0; FAILED=0
FAILED_IDS=""

# Iterate all decision beads (include closed via --all; accepted ADRs are closed beads).
for ID in $(bd list --all --type=decision --json | jq -r '.[].id'); do
  DECIDERS=$(bd show "$ID" --json | jq -r '.[0].metadata.adr_deciders // empty')
  if [ -n "$DECIDERS" ]; then
    ALREADY=$((ALREADY+1))
    continue
  fi

  # Legacy bead — look for corresponding .md
  MD=$(ls docs/adr/${ID}-*.md 2>/dev/null | head -1)
  if [ -n "$MD" ]; then
    EXTRACTED=$(grep '^\*\*Deciders:\*\*' "$MD" | head -1 | sed 's/^\*\*Deciders:\*\*[[:space:]]*//')
    if [ -n "$EXTRACTED" ]; then
      if [ "$APPLY" = "1" ]; then
        bd update "$ID" --set-metadata "adr_deciders=$EXTRACTED"
        ${CLAUDE_PLUGIN_ROOT}/scripts/render-adr "$ID"
        MIGRATED=$((MIGRATED+1))
        echo "MIGRATED: $ID (deciders='$EXTRACTED') + re-rendered"
      else
        echo "WOULD MIGRATE: $ID (deciders='$EXTRACTED') + would re-render"
        MIGRATED=$((MIGRATED+1))
      fi
    else
      FAILED=$((FAILED+1))
      FAILED_IDS="$FAILED_IDS $ID"
      echo "FAILED: $ID has .md but no extractable **Deciders:** line" >&2
    fi
  else
    # Orphan: bd record but no .md
    if [ "$APPLY" = "1" ]; then
      # Orphan-recovery requires AskUserQuestion (main session context per INV-A19).
      # Fail fast in non-main contexts (Codex / subagent dispatch).
      echo "ORPHAN: $ID — operator-prompt path needs main session context (AskUserQuestion). Skipping in this run; re-run from primary session to recover." >&2
      FAILED=$((FAILED+1))
      FAILED_IDS="$FAILED_IDS $ID"
    else
      echo "WOULD RECOVER: $ID (orphan; would prompt for deciders + render new .md)"
      RECOVERED=$((RECOVERED+1))
    fi
  fi
done

echo
echo "Migration report:"
echo "  Already migrated:    $ALREADY"
if [ "$APPLY" = "1" ]; then
  echo "  Newly migrated:      $MIGRATED"
  echo "  Newly recovered:     $RECOVERED"
else
  echo "  Will migrate:        $MIGRATED"
  echo "  Will recover:        $RECOVERED"
fi
echo "  Failed:              $FAILED"
[ -n "$FAILED_IDS" ] && echo "  Failed IDs:         $FAILED_IDS"

if [ "$APPLY" = "0" ] && [ $((MIGRATED + RECOVERED)) -gt 0 ]; then
  echo
  echo "Dry-run only. Re-run with --apply to perform the migrations."
fi
```
