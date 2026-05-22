---
description: ADR lifecycle operations. Modes: init, new, propose, update, supersede, addendum, accept, deprecate, render, migrate.
argument-hint: "init | new | propose | update <id> | supersede <old-id> | addendum <id> --text \"...\" | accept <id> | deprecate <id> --reason \"...\" | render <id> | migrate [--apply]"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Bash(bd:*)", "Bash(jq:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-adr.formula.toml\" .beads/formulas/:*)", "Bash(dev-flow/scripts/render-adr:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(date:*)"]
---

# /adr

ADR lifecycle operations. bd is the source of truth; this command mutates bd state and re-renders `docs/adr/<id>-<slug>.md` via `dev-flow/scripts/render-adr`. See `dev-flow:evolve-adr` for the canonical reference (capture-vs-propose distinction, status mechanics, migration).

Parse `$ARGUMENTS` as one of:

- `init` — Bootstrap this repo: copy `formula-adr.formula.toml` into `.beads/formulas/`. Idempotent.
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

Idempotent per-repo bootstrap. Run this once before any other `/adr` mode.

```bash
mkdir -p .beads/formulas
cp -n "${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-adr.formula.toml" .beads/formulas/
bd formula list | grep -q formula-adr \
  || { echo "formula-adr not visible to bd after copy" >&2; exit 1; }
echo "/adr init complete."
```

## New mode (/adr new)

Retrospective ADR documentation. Creates a bead via the formula and immediately closes it as Accepted.

1. Prompt operator (interactively via AskUserQuestion, or accept values from stdin/heredoc) for:
   title, context, decision, rationale, alternatives, consequences, deciders.
2. Pour the bead via formula:
   ```bash
   ID=$(bd --json mol pour formula-adr \
         --var title="$title" \
         --var context="$context" \
         --var decision="$decision" \
         --var rationale="$rationale" \
         --var alternatives="$alternatives" \
         --var consequences="$consequences" \
         --var deciders="$deciders" \
       | jq -r '.id')
   [ -n "$ID" ] && [ "$ID" != "null" ] \
     || { echo "/adr new: bd mol pour failed" >&2; exit 1; }
   ```
3. Close immediately (retrospective → Accepted):
   ```bash
   bd close "$ID" --reason="Accepted ADR filed via /adr new"
   ```
4. Render:
   ```bash
   dev-flow/scripts/render-adr "$ID"
   ```
5. Print: `Created and accepted ADR $ID → docs/adr/<rendered>.md`

## Propose mode (/adr propose)

Forward-looking ADR. Same flow as New EXCEPT skip Step 3 (no `bd close`). The bead stays in
`bd.status=open` so render-adr emits `Status: Proposed`.

1. Prompt operator (interactively via AskUserQuestion, or accept values from stdin/heredoc) for:
   title, context, decision, rationale, alternatives, consequences, deciders.
2. Pour the bead via formula:
   ```bash
   ID=$(bd --json mol pour formula-adr \
         --var title="$title" \
         --var context="$context" \
         --var decision="$decision" \
         --var rationale="$rationale" \
         --var alternatives="$alternatives" \
         --var consequences="$consequences" \
         --var deciders="$deciders" \
       | jq -r '.id')
   [ -n "$ID" ] && [ "$ID" != "null" ] \
     || { echo "/adr propose: bd mol pour failed" >&2; exit 1; }
   ```
3. Do NOT close the bead — leave it open (Proposed status).
4. Render:
   ```bash
   dev-flow/scripts/render-adr "$ID"
   ```
5. Print: `Proposed ADR $ID → docs/adr/<rendered>.md (run /adr accept $ID to finalize)`

## Render mode (/adr render <id>)

Re-render the ADR file from bd state. No bd mutation.

```bash
ID="$1"
bd show "$ID" --json >/dev/null 2>&1 \
  || { echo "Decision bead $ID not found." >&2; exit 1; }
dev-flow/scripts/render-adr "$ID"
```

## Update mode (/adr update <id>)

Edit an ADR's body or individual sections, then re-render.

1. `ID="$1"`; show current state for context:
   ```bash
   bd show "$ID" --json | jq '{title, description, metadata, status}'
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
   CURRENT=$(bd show "$ID" --json | jq -r '.description')
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
   dev-flow/scripts/render-adr "$ID"
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
dev-flow/scripts/render-adr "$ID"
echo "Addendum added to $ID and re-rendered."
```

## Accept mode (/adr accept <id>)

Close a Proposed ADR (bd status=open → closed). Re-renders the file so Status flips to Accepted.

```bash
ID="$1"
STATUS=$(bd show "$ID" --json | jq -r '.status')
[ "$STATUS" = "open" ] \
  || { echo "ADR $ID is not in Proposed state (bd status=$STATUS); cannot accept." >&2; exit 1; }
bd close "$ID" --reason="Accepted"
dev-flow/scripts/render-adr "$ID"
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

STATUS=$(bd show "$ID" --json | jq -r '.status')
[ "$STATUS" = "closed" ] \
  || { echo "ADR $ID must be Accepted (bd status=closed) before Deprecation. Current: $STATUS." >&2; exit 1; }

bd update "$ID" --add-label adr:deprecated
bd note "$ID" "deprecated: $REASON"
dev-flow/scripts/render-adr "$ID"
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
   STATUS=$(bd show "$OLD" --json | jq -r '.status')
   ```
   If `$STATUS != "closed"`, error: `"Cannot supersede a Proposed ADR; /adr accept $OLD first."`
3. Run the `/adr new` flow interactively (gather title + 5 sections + deciders) to create NEW:
   ```bash
   NEW=$(bd --json mol pour formula-adr \
         --var title="$title" \
         --var context="$context" \
         --var decision="$decision" \
         --var rationale="$rationale" \
         --var alternatives="$alternatives" \
         --var consequences="$consequences" \
         --var deciders="$deciders" \
       | jq -r '.id')
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
   dev-flow/scripts/render-adr "$OLD"   # status flips to Superseded by NEW
   dev-flow/scripts/render-adr "$NEW"   # References shows Supersedes: OLD
   ```
7. Print: `"Superseded $OLD with $NEW. Both ADRs re-rendered."`
