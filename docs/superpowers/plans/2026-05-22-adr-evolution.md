<!-- markdownlint-disable MD013 -->

# ADR Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `dev-flow:subagent-driven-development` (recommended) or `dev-flow:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the ADR evolution machinery — `formula-adr.formula.toml`, `render-adr` script, `/adr` slash command, `evolve-adr` skill, `adr-doctor` extensions, `capture-adrs` integration, and migration — so bd is the source of truth for ADR content and markdown is a derived view.

**Architecture:** bd `decision` bead's `--description` is canonical body; `adr_deciders` metadata is the single envelope key; status / date / supersession use bd-native lifecycle, timestamps, and `--type=supersedes` dep edges; a label-based path covers Rejected / Deprecated. A bash script (`render-adr`) reads bd state and writes `docs/adr/<bd-id>-<slug>.md`. A `/adr` slash command + `evolve-adr` skill provide the lifecycle operations (propose / update / supersede / addendum / accept / deprecate / render / migrate). `adr-doctor` gains 5 new checks (INV-A20–A24) including bd↔markdown drift detection.

**Tech Stack:** Markdown (skill + command + ADRs), TOML (bd formula), Bash (render-adr + /adr subcommand bodies), `bd` CLI (`mol pour` + `update` + `dep add/list` + `show` + `list` + `note` + `close`), `jq` (JSON parsing), `jj` VCS (colocated; commits authored via `jj describe`).

**Spec:** `docs/superpowers/specs/2026-05-22-adr-evolution-design.md`
**Design bead:** `fhsk-4xf`

---

## File structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `dev-flow/.beads/formulas/formula-adr.formula.toml` | **Create** | Single-step formula scaffolding a `decision` bead with the canonical body shape (Context / Decision / Rationale / Alternatives / Consequences sections) + `adr_deciders` metadata + `phase:design` label |
| `dev-flow/scripts/render-adr` | **Create** | Bash script. Reads bd state for one decision bead and writes `docs/adr/<bd-id>-<slug>.md` from title + computed-status + body + addenda + supersession references. Idempotent. |
| `dev-flow/commands/adr.md` | **Create** | `/adr` slash command with 10 subcommands: `init` / `new` / `propose` / `update` / `supersede` / `addendum` / `accept` / `deprecate` / `render` / `migrate` |
| `dev-flow/skills/evolve-adr/SKILL.md` | **Create** | Canonical reference for the ADR lifecycle; documents capture-adrs vs. /adr distinction, status mechanics, supersession semantics, migration |
| `dev-flow/skills/capture-adrs/SKILL.md` | **Modify** | Step 7 (Write phase) replaces direct `bd create -t decision --stdin` with `bd mol pour formula-adr ...` + `render-adr` |
| `dev-flow/scripts/adr-doctor.sh` | **Modify** | Add 5 new checks: INV-A20 (Context section), INV-A21 (Consequences section), INV-A22 (markdown↔render drift), INV-A23 (status/label coherence), INV-A24 (adr_deciders attribution) |
| `dev-flow/AGENTS.md` | **Modify** | Add `evolve-adr` to skill list + 1-paragraph `/adr` mention under Dev-Flow Conventions |
| `docs/adr/fhsk-{thw,0o2,rqh,ce3,0cd}-*.md` | **Modify** | Re-rendered by Task 12 via `/adr migrate --apply` (canonicalizes against the new render shape) |

**Not modified** (verified):

- `dev-flow/plugin.json` — does not enumerate skills/commands; new files discovered automatically.
- `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` — register plugins only.

---

## Conventions used in this plan

- **VCS:** jj-colocated. Use `jj --no-pager new -m "..."` to start a change; `jj --no-pager describe -m "..."` to set the message; `jj st` for status. Do not use `git commit` or `git checkout` for mutations.
- **Conventional Commits:** `type(scope): description`. Scope here is `adr` (e.g., `feat(adr): ...`).
- **Bead model labels:** each task suggests a `model:*` label.
- **bd flag corrections (verified at design-review round 1):**
  - Label mutations: `bd update <id> --add-label foo` (additive) and `--remove-label foo` and `--set-labels foo,bar` (replace). NOT `--labels +foo`.
  - Piped body: `bd update <id> --body-file -` reads description from stdin. NOT `--description-file -`.
  - List filter: `bd list --type=decision` (decision/adr aliased per `bd list --help`).
- **Deferred plan-stage verifications** (per design-review round 2 minors):
  - Task 2 verifies experimentally whether `bd dep list --direction=up --type=supersedes` filters list output or only filters add-time type — and falls back to `bd dep list --direction=up --json | jq` if the list filter is broken.
  - Task 1's `phase:design` label on the formula is noted as semantically mild-fit for retrospective ADRs from `capture-adrs`; left as-is per spec, can be revisited.

---

### Task 1: Scaffold formula-adr.formula.toml

Suggested labels: `model:sonnet`, `scope:adr`

**Files:** Create `dev-flow/.beads/formulas/formula-adr.formula.toml`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): add formula-adr.toml"`

- [ ] **Step 2: Write `dev-flow/.beads/formulas/formula-adr.formula.toml`**

  ```toml
  formula = "formula-adr"
  version = 1
  description = """
  ADR (Architecture Decision Record). Built on bd's built-in `decision` type;
  bd's --validate enforces ## Decision / ## Rationale / ## Alternatives Considered.
  Project convention additionally requires ## Context and ## Consequences,
  enforced by adr-doctor (INV-A20, INV-A21) at lint time.

  Body authored at pour time via vars. Edit later via /adr update <id>;
  render to markdown via /adr render <id>.
  """

  [vars.title]
  description = "ADR title (imperative — what the decision is)"
  required = true

  [vars.context]
  description = "## Context section prose"
  required = true

  [vars.decision]
  description = "## Decision section prose"
  required = true

  [vars.rationale]
  description = "## Rationale section prose"
  required = true

  [vars.alternatives]
  description = "## Alternatives Considered section prose"
  required = true

  [vars.consequences]
  description = "## Consequences section prose"
  required = true

  [vars.deciders]
  description = "Comma-separated decider names (stored as adr_deciders metadata)"
  required = true

  [[steps]]
  id = "adr-root"
  type = "decision"
  title = "{{title}}"
  description = """## Context

  {{context}}

  ## Decision

  {{decision}}

  ## Rationale

  {{rationale}}

  ## Alternatives Considered

  {{alternatives}}

  ## Consequences

  {{consequences}}
  """
  labels = ["phase:design"]
  metadata = { adr_deciders = "{{deciders}}" }
  ```

- [ ] **Step 3: Stage into `.beads/formulas/` for validation**

  Run:

  ```bash
  mkdir -p .beads/formulas
  cp dev-flow/.beads/formulas/formula-adr.formula.toml .beads/formulas/
  ```

- [ ] **Step 4: Validate**

  Run: `bd formula show formula-adr` — expect parse-clean output listing all 7 vars + the single `adr-root` step.
  Run: `bd formula list | grep formula-adr` — expect one match.

- [ ] **Step 5: Dry-run pour to confirm**

  Run:

  ```bash
  bd mol pour formula-adr \
    --var title="Test ADR title" \
    --var context="Test context" \
    --var decision="Test decision" \
    --var rationale="Test rationale" \
    --var alternatives="Test alternatives" \
    --var consequences="Test consequences" \
    --var deciders="Sean Brandt (@seanb4t)" \
    --dry-run
  ```

  Expected: prints "would pour" with type `decision`, title `Test ADR title`, labels `phase:design`, and metadata `adr_deciders=Sean Brandt (@seanb4t)`. Does NOT create the bead.

- [ ] **Step 6: Clean up staged validation copy**

  Run: `rm .beads/formulas/formula-adr.formula.toml`
  Expected: `jj st` shows only `A dev-flow/.beads/formulas/formula-adr.formula.toml`.

- [ ] **Step 7: Describe the change**

  Run: `jj --no-pager describe -m "feat(adr): add formula-adr formula scaffolding decision beads"`

---

### Task 2: Implement render-adr script

Suggested labels: `model:opus`, `scope:adr`

This is the most complex task in the plan — bd JSON parsing, computed status (5 branches), addenda extraction, supersession reference rendering, and an experimental verification of `bd dep list --type=supersedes` filter behavior.

**Files:** Create `dev-flow/scripts/render-adr`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): implement render-adr script"`

- [ ] **Step 2: Verify `bd dep list --type=supersedes` filter behavior (plan-stage gate from design-review round 2)**

  In a scratch state: create two test decision beads (`bd create -t decision --title="A" --description="..."` and `--title="B"`), wire `bd dep add B A --type=supersedes`, then run:

  ```bash
  bd dep list A --direction=up --type=supersedes --json
  ```

  If output is the expected single edge (B depending on A via supersedes): the script can use this filter directly.
  If output errors or returns wrong data: fall back to `bd dep list A --direction=up --json | jq '.[] | select(.type == "supersedes")'` in the script. Document the fallback inline in the script.

  Cleanup: `bd close A B --reason=test`.

- [ ] **Step 3: Write `dev-flow/scripts/render-adr`**

  ```bash
  #!/usr/bin/env bash
  # render-adr <bd-id>
  #
  # Reads bd state for a decision bead and writes docs/adr/<bd-id>-<slug>.md.
  # bd is the source of truth (description body + metadata + dep edges + labels +
  # timestamps); this script renders that state into the canonical markdown form.
  # Idempotent.

  set -euo pipefail

  ID="${1:?Usage: render-adr <bd-id>}"
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  ADR_DIR="$REPO_ROOT/docs/adr"
  mkdir -p "$ADR_DIR"

  # 1. Fetch bd state
  JSON=$(bd show "$ID" --json 2>/dev/null) || { echo "render-adr: bd show $ID failed" >&2; exit 1; }
  [ -n "$JSON" ] || { echo "render-adr: empty bd show output for $ID" >&2; exit 1; }

  TITLE=$(echo "$JSON" | jq -r '.title // empty')
  STATUS_BD=$(echo "$JSON" | jq -r '.status // empty')
  CREATED=$(echo "$JSON" | jq -r '.created_at // empty' | cut -c1-10)
  CLOSED=$(echo "$JSON" | jq -r '.closed_at // empty' | cut -c1-10)
  DECIDERS=$(echo "$JSON" | jq -r '.metadata.adr_deciders // "—"')
  BODY=$(echo "$JSON" | jq -r '.description // empty')
  LABELS=$(echo "$JSON" | jq -r '.labels[]? // empty' | tr '\n' ',' | sed 's/,$//')
  NOTES=$(echo "$JSON" | jq -r '.notes[]? // empty')

  # 2. Compute date: closed_at preferred, else created_at
  DATE="${CLOSED:-$CREATED}"

  # 3. Compute slug: kebab-case title, drop stop-words, cap 60 chars
  SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' \
    | tr -c 'a-z0-9' '-' | tr -s '-' \
    | sed 's/^-//; s/-$//' \
    | awk -F'-' '{
        # drop stop words
        out=""
        for (i=1; i<=NF; i++) {
          w=$i
          if (w!="a" && w!="an" && w!="the" && w!="for" && w!="of" && w!="to" && w!="in" && w!="on" && w!="with") {
            out = out (out=="" ? "" : "-") w
          }
        }
        print out
      }' \
    | cut -c1-60 \
    | sed 's/-$//')

  # 4. Compute status (Proposed / Superseded / Rejected / Deprecated / Accepted)
  SUPERSEDED_BY=""
  if [ "$STATUS_BD" = "open" ]; then
    STATUS="Proposed"
  else
    # closed bead — check for incoming supersedes edge
    # NOTE: if Step 2 found that --type=supersedes works for `bd dep list`, use the inline filter.
    # Otherwise fall back to | jq filtering after fetching all up-edges.
    SUPERSEDER=$(bd dep list "$ID" --direction=up --type=supersedes --json 2>/dev/null \
      | jq -r '.[0].id // empty' 2>/dev/null || true)
    # Fallback path (uncomment if Step 2 verified --type filter is broken):
    # SUPERSEDER=$(bd dep list "$ID" --direction=up --json 2>/dev/null \
    #   | jq -r '.[] | select(.type == "supersedes") | .id' | head -1)

    if [ -n "$SUPERSEDER" ]; then
      STATUS="Superseded by $SUPERSEDER"
      SUPERSEDED_BY="$SUPERSEDER"
    elif echo ",$LABELS," | grep -q ",adr:rejected,"; then
      STATUS="Rejected"
    elif echo ",$LABELS," | grep -q ",adr:deprecated,"; then
      STATUS="Deprecated"
    else
      STATUS="Accepted"
    fi
  fi

  # 5. Collect addenda from notes (lines starting with "addendum: ")
  ADDENDA=$(echo "$NOTES" | grep "^addendum: " | sed 's/^addendum: //')

  # 6. Find outgoing supersedes (this ADR replaced an earlier one)
  SUPERSEDES=$(bd dep list "$ID" --direction=down --type=supersedes --json 2>/dev/null \
    | jq -r '.[].id' 2>/dev/null | tr '\n' ' ' || true)
  # Fallback if --type filter is broken: as in step 4.

  # 7. Build the file path
  OUT="$ADR_DIR/${ID}-${SLUG}.md"

  # 8. Emit canonical markdown
  {
    echo '<!-- markdownlint-disable MD013 -->'
    echo "<!-- adr-render: source=bd:$ID; do not edit manually; use \`/adr update $ID\` -->"
    echo
    echo "# $TITLE"
    echo
    echo "**Date:** $DATE"
    echo "**Status:** $STATUS"
    echo "**Decision:** $ID"
    echo "**Deciders:** $DECIDERS"
    echo
    echo "$BODY"

    if [ -n "$ADDENDA" ]; then
      echo
      echo "## Addenda"
      echo
      echo "$ADDENDA" | while IFS= read -r line; do
        [ -n "$line" ] && echo "- $line"
      done
    fi

    if [ -n "$SUPERSEDES" ] || [ -n "$SUPERSEDED_BY" ]; then
      echo
      echo "## References"
      echo
      for old in $SUPERSEDES; do
        echo "- Supersedes: [\`$old\`](./${old}-*.md)"
      done
      if [ -n "$SUPERSEDED_BY" ]; then
        echo "- Superseded by: [\`$SUPERSEDED_BY\`](./${SUPERSEDED_BY}-*.md)"
      fi
    fi
  } > "$OUT"

  echo "Rendered $OUT"
  ```

  Make executable: `chmod +x dev-flow/scripts/render-adr`.

- [ ] **Step 4: Manual test against an existing ADR**

  Run: `dev-flow/scripts/render-adr fhsk-thw`
  Expected: writes `docs/adr/fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md`. Diff vs the existing file should be small (header normalization, possibly addenda placement). Major drift = real bug.

  Inspect: `diff docs/adr/fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md <(jj diff -r '@' docs/adr/fhsk-thw-* | head)`

  Restore the existing .md before proceeding to Step 5 (re-run will be done by Task 12's migration).

- [ ] **Step 5: Describe the change**

  Run: `jj --no-pager describe -m "feat(adr): implement render-adr (bd → markdown renderer)"`

---

### Task 3: Scaffold /adr slash command

Suggested labels: `model:sonnet`, `scope:adr`

**Files:** Create `dev-flow/commands/adr.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): scaffold /adr slash command"`

- [ ] **Step 2: Write `dev-flow/commands/adr.md`** with frontmatter + dispatch stub:

  ````markdown
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

  Remaining mode bodies are filled in by Tasks 4–7 of `docs/superpowers/plans/2026-05-22-adr-evolution.md`. This stub MUST refuse all modes other than usage until those tasks land.
  ````

- [ ] **Step 3: Validate**

  Run: `rumdl check dev-flow/commands/adr.md` — pre-existing dev-flow/ exclusions OK.

- [ ] **Step 4: Describe**

  Run: `jj --no-pager describe -m "feat(adr): scaffold /adr slash command (modes stubbed)"`

---

### Task 4: Implement /adr init + /adr new + /adr propose

Suggested labels: `model:sonnet`, `scope:adr`

These three are the creation paths. `init` is bootstrap. `new` and `propose` share a creation flow; differ only on whether to immediately close (Accepted vs Proposed).

**Files:** Modify `dev-flow/commands/adr.md` (add three mode sections after the usage list, before the closing stub note).

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): implement /adr init + new + propose"`

- [ ] **Step 2: Add `## Init mode (/adr init)` section**

  ```bash
  # Idempotent per-repo bootstrap: copy formula into .beads/formulas/.
  mkdir -p .beads/formulas
  cp -n "${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-adr.formula.toml" .beads/formulas/
  bd formula list | grep -q formula-adr \
    || { echo "formula-adr not visible to bd after copy" >&2; exit 1; }
  echo "/adr init complete."
  ```

- [ ] **Step 3: Add `## New mode (/adr new)` section** (retrospective; auto-close on creation)

  Body:
  1. Interactively prompt the operator for: title, context, decision, rationale, alternatives, consequences, deciders. Use `AskUserQuestion` for each (or accept all via stdin / heredoc for non-interactive use).
  2. `ID=$(bd --json mol pour formula-adr --var title=... --var context=... ... | jq -r '.id')`
  3. `[ -n "$ID" ] && [ "$ID" != "null" ] || { echo "pour failed" >&2; exit 1; }`
  4. `bd close "$ID" --reason="Accepted ADR filed via /adr new"`
  5. `dev-flow/scripts/render-adr "$ID"`
  6. Print: `Created and accepted ADR $ID → docs/adr/<rendered-slug>.md`

- [ ] **Step 4: Add `## Propose mode (/adr propose)` section** (forward-looking; left open)

  Same as `new` except SKIP step 4 (no `bd close`). The bead stays in status=open → renderer emits `Status: Proposed`. Print: `Proposed ADR $ID → docs/adr/<rendered-slug>.md (run /adr accept $ID to finalize)`.

- [ ] **Step 5: Manual test**

  Verify `init` writes the formula into `.beads/formulas/` (after which `bd formula list` shows it).
  Verify `propose` flow with a tossable test ADR: `bd show <id> --json | jq '.status'` returns `"open"`; rendered file shows `Status: Proposed`. Cleanup: `bd close <id> --reason=test`.
  Verify `new` flow similarly: `bd show <id> --json | jq '.status'` returns `"closed"`; rendered file shows `Status: Accepted`. Cleanup.

- [ ] **Step 6: Describe**

  Run: `jj --no-pager describe -m "feat(adr): implement /adr init, /adr new (retrospective), /adr propose (forward-looking)"`

---

### Task 5: Implement /adr update + /adr render + /adr addendum

Suggested labels: `model:sonnet`, `scope:adr`

These are the body-mutation paths. `render` is no-op-mutation; `update` rewrites the description body; `addendum` adds a note.

**Files:** Modify `dev-flow/commands/adr.md` (add three sections).

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): implement /adr update + render + addendum"`

- [ ] **Step 2: Add `## Render mode (/adr render <id>)` section**

  ```bash
  ID="$1"
  bd show "$ID" --json >/dev/null 2>&1 \
    || { echo "Decision bead $ID not found." >&2; exit 1; }
  dev-flow/scripts/render-adr "$ID"
  ```

- [ ] **Step 3: Add `## Update mode (/adr update <id>)` section**

  Interactive flow:
  1. Show current bd state (`bd show $ID` for context).
  2. `AskUserQuestion`: which section to edit (Context / Decision / Rationale / Alternatives Considered / Consequences / WHOLE BODY)?
  3. Prompt for new prose for that section.
  4. Re-compose the full body by reading current bd description and replacing the selected section's content.
  5. Pipe new body to `bd update $ID --body-file -`.
  6. `dev-flow/scripts/render-adr $ID` → regenerated .md.

  Note: the section re-composition uses `awk` (or similar) anchored on `## <section>` headings to slice/replace cleanly. Provide an inline awk one-liner in the command body that handles all 5 section names. Single-section edits don't perturb other sections.

- [ ] **Step 4: Add `## Addendum mode (/adr addendum <id> --text "...")` section**

  ```bash
  ID="$1"; shift
  # Parse --text from $@
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
  ```

- [ ] **Step 5: Manual test**

  Create a test ADR (`/adr new` with throwaway content). Run `/adr addendum <id> --text "Test addendum"`. Verify: `bd show <id> --json | jq '.notes'` includes the addendum; rendered .md has `## Addenda` section with the entry. Cleanup.

- [ ] **Step 6: Describe**

  Run: `jj --no-pager describe -m "feat(adr): implement /adr update, /adr render, /adr addendum"`

---

### Task 6: Implement /adr accept + /adr deprecate + /adr supersede

Suggested labels: `model:sonnet`, `scope:adr`

Status-transition paths. `accept` closes a Proposed bead; `deprecate` adds the label; `supersede` is the cross-bead operation.

**Files:** Modify `dev-flow/commands/adr.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): implement /adr accept + deprecate + supersede"`

- [ ] **Step 2: Add `## Accept mode (/adr accept <id>)` section**

  ```bash
  ID="$1"
  STATUS=$(bd show "$ID" --json | jq -r '.status')
  [ "$STATUS" = "open" ] \
    || { echo "ADR $ID is not in Proposed state (bd status=$STATUS); cannot accept." >&2; exit 1; }
  bd close "$ID" --reason="Accepted"
  dev-flow/scripts/render-adr "$ID"
  echo "ADR $ID accepted."
  ```

- [ ] **Step 3: Add `## Deprecate mode (/adr deprecate <id> --reason "...")` section**

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

- [ ] **Step 4: Add `## Supersede mode (/adr supersede <old-id>)` section**

  Cross-bead operation:
  1. Verify `<old-id>` exists and is closed: `bd show <old-id> --json | jq '.status'` == `"closed"`. If open, prompt to accept first.
  2. Run the `/adr new` flow (interactively gather title + 5 sections + deciders) to create the new bead `<new-id>`.
  3. Wire the dep: `bd dep add <new-id> <old-id> --type=supersedes`.
  4. Re-render `<old-id>` (renderer will now compute Status="Superseded by <new-id>").
  5. Render `<new-id>` (creates the new .md; renderer's References section shows "Supersedes: <old-id>").
  6. Print: `Superseded $old-id with $new-id. Both ADRs re-rendered.`

- [ ] **Step 5: Manual test**

  Create two test ADRs A and B (via `/adr new` with throwaway content). Run `/adr supersede A` interactively (B becomes the new ADR). Verify:
  - `bd dep list A --direction=up --type=supersedes` (or the verified fallback) lists B.
  - Rendered A.md shows `Status: Superseded by B`.
  - Rendered B.md References section shows `Supersedes: A`.
  Cleanup.

- [ ] **Step 6: Describe**

  Run: `jj --no-pager describe -m "feat(adr): implement /adr accept, /adr deprecate, /adr supersede"`

---

### Task 7: Implement /adr migrate

Suggested labels: `model:opus`, `scope:adr`

The migration command. Dry-run by default; `--apply` mutates. Handles three legacy paths.

**Files:** Modify `dev-flow/commands/adr.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): implement /adr migrate"`

- [ ] **Step 2: Add `## Migrate mode (/adr migrate [--apply])` section**

  Body (high-level pseudocode; the inline bash should implement this):

  ```text
  APPLY=0
  for arg in $@; do
    [ "$arg" = "--apply" ] && APPLY=1
  done

  echo "/adr migrate: --apply=$APPLY"

  # Session-context gate (INV-A19 inheritance): --apply may need AskUserQuestion
  if [ "$APPLY" = "1" ]; then
    # Inline check: refuse if AskUserQuestion not available (Codex / subagent context).
    # Per the design spec, orphan-bead recovery is the only path that needs operator input.
    # Detect at the orphan branch below; fail fast there with clear error.
    :
  fi

  ALREADY=0; MIGRATED=0; RECOVERED=0; FAILED=0

  # Iterate all decision beads
  for ID in $(bd list --type=decision --json | jq -r '.[].id'); do
    DECIDERS=$(bd show "$ID" --json | jq -r '.metadata.adr_deciders // empty')
    if [ -n "$DECIDERS" ]; then
      ALREADY=$((ALREADY+1))
      continue
    fi

    # Legacy bead — look for corresponding .md
    MD=$(ls docs/adr/${ID}-*.md 2>/dev/null | head -1)
    if [ -n "$MD" ]; then
      EXTRACTED=$(grep '^\*\*Deciders:\*\*' "$MD" | head -1 | sed 's/^\*\*Deciders:\*\*\s*//')
      if [ -n "$EXTRACTED" ]; then
        if [ "$APPLY" = "1" ]; then
          bd update "$ID" --set-metadata "adr_deciders=$EXTRACTED"
          dev-flow/scripts/render-adr "$ID"
          MIGRATED=$((MIGRATED+1))
        else
          echo "WOULD MIGRATE: $ID (deciders='$EXTRACTED') + re-render"
          MIGRATED=$((MIGRATED+1))
        fi
      else
        FAILED=$((FAILED+1))
        echo "FAILED: $ID has .md but no extractable **Deciders:** line"
      fi
    else
      # Orphan: bd record but no .md
      if [ "$APPLY" = "1" ]; then
        # Use AskUserQuestion (requires main session context)
        # If not available, fail fast with clear error per INV-A19 inheritance
        echo "ORPHAN: $ID — needs operator input via AskUserQuestion (main session context required)" >&2
        FAILED=$((FAILED+1))
      else
        echo "WOULD RECOVER: $ID (orphan; would prompt for deciders + render new .md)"
        RECOVERED=$((RECOVERED+1))
      fi
    fi
  done

  echo
  echo "Migration report:"
  echo "  Already migrated:    $ALREADY"
  echo "  Migrated:            $MIGRATED"
  echo "  Recovered (orphan):  $RECOVERED"
  echo "  Failed:              $FAILED"
  ```

  Note: this is the v1 of migrate. The orphan-recovery `AskUserQuestion` path is a TODO documented in the section header. For the immediate use case (this repo's 5 ADRs all have .md files), the orphan branch is unreachable.

- [ ] **Step 3: Dry-run test against this repo's 5 ADRs**

  In a scratch jj workspace (so any accidental writes don't pollute current state): run `/adr migrate` (no --apply).
  Expected output:
  - `WOULD MIGRATE: fhsk-thw (deciders='Sean Brandt (@seanb4t)') + re-render`
  - Same for fhsk-0o2, fhsk-rqh, fhsk-ce3, fhsk-0cd.
  - Report: 0 already, 5 migrated, 0 recovered, 0 failed.

  No bd mutations occurred (verify via `bd show fhsk-thw --json | jq '.metadata.adr_deciders'` returns null/empty).

- [ ] **Step 4: Describe**

  Run: `jj --no-pager describe -m "feat(adr): implement /adr migrate (dry-run + --apply paths)"`

---

### Task 8: Write evolve-adr SKILL.md

Suggested labels: `model:sonnet`, `scope:adr`

The canonical reference skill for ADR lifecycle. Documents the contract; the slash command and scripts are the execution layer.

**Files:** Create `dev-flow/skills/evolve-adr/SKILL.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): add evolve-adr skill"`

- [ ] **Step 2: Write `dev-flow/skills/evolve-adr/SKILL.md`**

  Required topics (ordering at implementer's discretion):
  - **Overview** of the ADR lifecycle pattern + the spec it implements.
  - **bd as source of truth** — what lives where (mirrors the spec's table); the contract that markdown is derived.
  - **When to use** — capture-adrs vs `/adr propose` vs `/adr new` distinction.
  - **Status mechanics** — Proposed / Accepted / Superseded / Rejected / Deprecated; how each maps to bd state.
  - **Supersession semantics** — dep edges, render-time inference, references section.
  - **Addenda** — when to use vs. supersession; bd-notes prefix convention.
  - **Migration** — `/adr migrate` for legacy ADRs; idempotency; orphan-recovery constraint.
  - **Edge cases** — Codex compatibility (the bash scripts work; `AskUserQuestion` is the only main-session-context dependency); the orphan-bead path; the rejection-without-/adr-reject workaround.
  - **References** — links to the spec, slash command, formula, adr-doctor, INV invariants.

  Frontmatter:

  ```yaml
  ---
  name: evolve-adr
  description: Use when you need to update, supersede, deprecate, or migrate an Architecture Decision Record. Pairs with the /adr slash command; bd is the source of truth for ADR content. See docs/superpowers/specs/2026-05-22-adr-evolution-design.md.
  ---
  ```

  Body must be under 500 lines per project conventions.

- [ ] **Step 3: Validate**

  Run: `rumdl check dev-flow/skills/evolve-adr/SKILL.md` — expect 0 violations (new file; no inherited noise).
  Run: `wc -l dev-flow/skills/evolve-adr/SKILL.md` — under 500 lines.
  Run frontmatter parse check: `uv run --with pyyaml python -c "import yaml; yaml.safe_load(open('dev-flow/skills/evolve-adr/SKILL.md').read().split('---')[1])"` — no error.

- [ ] **Step 4: Describe**

  Run: `jj --no-pager describe -m "feat(adr): add evolve-adr skill (canonical lifecycle reference)"`

---

### Task 9: Extend adr-doctor.sh with 5 new checks

Suggested labels: `model:sonnet`, `scope:adr`

Five new invariants: INV-A20, INV-A21, INV-A22, INV-A23, INV-A24.

**Files:** Modify `dev-flow/scripts/adr-doctor.sh`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): extend adr-doctor with 5 new invariants"`

- [ ] **Step 2: Add check `description_has_context_section` (INV-A20)**

  After the existing checks, before the "Full-pass-only checks" block:

  ```bash
  # --- description_has_context_section (INV-A20) ---
  note "description_has_context_section (INV-A20)"
  if command -v bd >/dev/null 2>&1; then
    for ID in $(bd list --type=decision --json | jq -r '.[].id'); do
      DESC=$(bd show "$ID" --json | jq -r '.description // empty')
      [ -z "$DESC" ] && continue
      echo "$DESC" | grep -q '^## Context' \
        || check_fail "$ID: bd description missing '## Context' heading (INV-A20)"
    done
  fi
  ```

- [ ] **Step 3: Add check `description_has_consequences_section` (INV-A21)**

  Same pattern, looking for `## Consequences`.

- [ ] **Step 4: Add check `markdown_matches_render` (INV-A22)**

  ```bash
  # --- markdown_matches_render (INV-A22) ---
  note "markdown_matches_render (INV-A22)"
  if command -v bd >/dev/null 2>&1 && command -v "$REPO_ROOT/dev-flow/scripts/render-adr" >/dev/null 2>&1; then
    for f in "${ADR_FILES[@]:-}"; do
      [ -z "${f:-}" ] && continue
      [ -f "$f" ] || continue
      bn=$(basename "$f")
      case "$bn" in README.md) continue ;; esac
      bd_id=$(printf '%s' "$bn" | grep -oE "^${BD_ID_RE}")
      [ -n "$bd_id" ] || continue

      TMP=$(mktemp)
      trap 'rm -f "$TMP"' RETURN
      # render to temp file
      ADR_DIR_BACKUP="$ADR_DIR"
      "$REPO_ROOT/dev-flow/scripts/render-adr" "$bd_id" 2>/dev/null
      # The renderer writes to $ADR_DIR/<id>-<slug>.md by convention. To get the rendered
      # output without overwriting the committed file, the implementer SHOULD add a
      # --to-stdout mode to render-adr (a Task 2 follow-up) OR temporarily move the
      # committed file aside. For v1, hash-compare after re-render:
      EXPECTED_HASH=$(shasum -a 256 "$f" | cut -d' ' -f1)
      ACTUAL_HASH=$(shasum -a 256 "$ADR_DIR/$bn" | cut -d' ' -f1)
      if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
        check_fail "$f: drift between rendered output and committed file. Run: /adr render $bd_id"
      fi
    done
  fi
  ```

  Note: the in-place re-render is destructive. The full-fidelity v1 of this check requires `render-adr --to-stdout` (or `--to-file <path>`) so we can render without overwriting. **File a follow-up task** during Task 9's implementation to add this flag to render-adr if not already present.

- [ ] **Step 5: Add check `status_label_coherent` (INV-A23)**

  ```bash
  # --- status_label_coherent (INV-A23) ---
  note "status_label_coherent (INV-A23)"
  if command -v bd >/dev/null 2>&1; then
    for ID in $(bd list --type=decision --label adr:deprecated --json | jq -r '.[].id'); do
      STATUS=$(bd show "$ID" --json | jq -r '.status')
      [ "$STATUS" = "closed" ] \
        || check_fail "$ID: has adr:deprecated label but bd status=$STATUS (must be closed) (INV-A23)"
    done
  fi
  ```

- [ ] **Step 6: Add check `adr_deciders_present` (INV-A24)**

  ```bash
  # --- adr_deciders_present (INV-A24) ---
  note "adr_deciders_present (INV-A24)"
  if command -v bd >/dev/null 2>&1; then
    for ID in $(bd list --type=decision --status=closed --json | jq -r '.[].id'); do
      DECIDERS=$(bd show "$ID" --json | jq -r '.metadata.adr_deciders // empty')
      [ -n "$DECIDERS" ] \
        || check_fail "$ID: closed decision bead lacks adr_deciders metadata. Run: /adr migrate --apply (INV-A24)"
    done
  fi
  ```

- [ ] **Step 7: Sanity test on this repo's current state**

  Run: `./dev-flow/scripts/adr-doctor.sh`
  Expected (assuming Task 12 hasn't run yet): A24 fails for the 5 legacy ADRs (no adr_deciders metadata yet). Other new checks pass (A20/A21: descriptions have Context + Consequences sections per the originals; A22: file matches render — but render may differ slightly from original since the original was hand-emitted; A23: no adr:deprecated labels exist).

  The A24 failures are EXPECTED until Task 12 backfills metadata via `/adr migrate --apply`. After Task 12, full lint pass.

- [ ] **Step 8: Describe**

  Run: `jj --no-pager describe -m "feat(adr): adr-doctor INV-A20 through INV-A24 — context/consequences sections, render drift, label coherence, deciders attribution"`

---

### Task 10: Update capture-adrs SKILL.md (Step 7 uses formula + render)

Suggested labels: `model:sonnet`, `scope:adr`

Switch Step 7 from direct `bd create -t decision --stdin` to `bd mol pour formula-adr ...` + `render-adr`.

**Files:** Modify `dev-flow/skills/capture-adrs/SKILL.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): switch capture-adrs Step 7 to formula + render-adr"`

- [ ] **Step 2: Locate and replace Step 7's write-phase shell**

  The current Step 7 has:

  ```bash
  printf '%s' "$body" | bd create -t decision --validate --title "<title>" --stdin
  ```

  Replace with:

  ```bash
  # Pour via formula-adr (bd validate runs in pour; metadata pre-set from var)
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
    || { echo "capture-adrs: bd mol pour formula-adr failed for '$title'" >&2; exit 1; }

  # Close immediately — capture-adrs is the retrospective path (Accepted on creation)
  bd close "$ID" --reason="Accepted ADR filed via capture-adrs"

  # Render markdown from bd state (replaces the old "Render the ADR markdown body" + "Write docs/adr/<id>-<slug>.md" steps)
  dev-flow/scripts/render-adr "$ID"
  ```

  Update surrounding prose so that the per-candidate review loop still triages each candidate; only the write-phase mechanism changes.

- [ ] **Step 3: Verify the skill still reads coherently**

  Read the skill end-to-end; ensure references to "render the ADR markdown body" and "write docs/adr/..." paths are consistent with the new flow (rendering is now in render-adr, not inline).

- [ ] **Step 4: Validate**

  Run: `rumdl check dev-flow/skills/capture-adrs/SKILL.md` — pre-existing dev-flow/ exclusions OK.

- [ ] **Step 5: Describe**

  Run: `jj --no-pager describe -m "feat(adr): capture-adrs Step 7 uses formula-adr + render-adr (replaces direct bd create)"`

---

### Task 11: Update dev-flow/AGENTS.md

Suggested labels: `model:haiku`, `scope:adr`

Add `evolve-adr` to the skill list + 1-paragraph `/adr` mention.

**Files:** Modify `dev-flow/AGENTS.md`.

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "docs(adr): mention /adr + evolve-adr in dev-flow AGENTS.md"`

- [ ] **Step 2: Edit the intro skill list**

  Locate the line:

  ```text
  Every workflow skill (`brainstorming`, ..., `capture-adrs`, `draining-beads`) and review-gate agent...
  ```

  Add `evolve-adr` after `capture-adrs`:

  ```text
  Every workflow skill (`brainstorming`, ..., `capture-adrs`, `evolve-adr`, `draining-beads`) and review-gate agent...
  ```

- [ ] **Step 3: Add a 1-paragraph `/adr` mention under Dev-Flow Conventions** (after the existing `/drain` paragraph from PR #79):

  ```markdown
  **ADR lifecycle (`/adr`):** ADRs are stored as bd `decision` beads with the description body as canonical content; markdown under `docs/adr/` is a derived view rendered by `dev-flow/scripts/render-adr`. Lifecycle operations (`/adr new` / `propose` / `update` / `supersede` / `addendum` / `accept` / `deprecate` / `render` / `migrate`) live in the `/adr` slash command; `evolve-adr` is the canonical reference. See [`docs/superpowers/specs/2026-05-22-adr-evolution-design.md`](../docs/superpowers/specs/2026-05-22-adr-evolution-design.md). Drift between bd state and committed markdown is a lint failure (INV-A22 in adr-doctor).
  ```

- [ ] **Step 4: Validate**

  Run: `rumdl check dev-flow/AGENTS.md` — pre-existing dev-flow/ exclusions OK.

- [ ] **Step 5: Describe**

  Run: `jj --no-pager describe -m "docs(adr): mention /adr lifecycle + evolve-adr skill in dev-flow AGENTS.md"`

---

### Task 12: Migrate this repo's 5 ADRs via /adr migrate --apply

Suggested labels: `model:sonnet`, `scope:adr`

Runs the migration. Backfills `adr_deciders` metadata on `fhsk-thw`, `fhsk-0o2`, `fhsk-rqh`, `fhsk-ce3`, `fhsk-0cd` and re-renders all 5 .md files via the new pipeline.

**Files:** Modify `docs/adr/fhsk-{thw,0o2,rqh,ce3,0cd}-*.md` (re-rendered).

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(adr): migrate existing 5 ADRs via /adr migrate --apply"`

- [ ] **Step 2: Dry-run preview**

  Invoke `/adr migrate` (no --apply).
  Expected: 5 "WOULD MIGRATE" entries with the extracted deciders strings; 0 failures.
  Inspect output. If any unexpected entries appear (e.g., a sixth ADR somewhere), investigate before proceeding.

- [ ] **Step 3: Apply**

  Invoke `/adr migrate --apply`.
  Expected: 5 `bd update --set-metadata adr_deciders=...` operations; 5 `render-adr` invocations writing to `docs/adr/fhsk-*.md`; report shows 5 migrated, 0 failed.

- [ ] **Step 4: Verify bd state**

  ```bash
  for id in fhsk-thw fhsk-0o2 fhsk-rqh fhsk-ce3 fhsk-0cd; do
    echo "$id: $(bd show "$id" --json | jq -r '.metadata.adr_deciders')"
  done
  ```

  Expected: each line shows `Sean Brandt (@seanb4t)` (extracted from the .md `**Deciders:**` headers).

- [ ] **Step 5: Verify markdown diff is small/cosmetic**

  Run: `jj diff -r '@' docs/adr/`
  Expected: 5 modified .md files; diffs should be header-only (the render adds the `<!-- adr-render: source=bd:... -->` marker and may normalize header formatting). No body content should change.

- [ ] **Step 6: Run adr-doctor full pass**

  Run: `./dev-flow/scripts/adr-doctor.sh`
  Expected: PASS. INV-A24 now satisfied (all 5 ADRs have `adr_deciders` metadata).

- [ ] **Step 7: Describe**

  Run: `jj --no-pager describe -m "feat(adr): backfill adr_deciders metadata + canonicalize markdown for 5 legacy ADRs"`

---

## Grounding-verification trace

Recorded as `bd note fhsk-4xf` entries:

- **probe-paths:** verified all `Create:` and `Modify:` paths in the file structure table. `dev-flow/{scripts,commands,skills,.beads/formulas}` parent directories exist; modify targets (`capture-adrs/SKILL.md`, `adr-doctor.sh`, `AGENTS.md`) all exist. The 5 existing ADR markdown files exist with the expected `**Deciders:**` header pattern.
- **bd-cli-reverify:** `bd update --add-label/--remove-label/--set-labels` confirmed (round 1); `bd update --body-file -` confirmed (round 1); `bd list --type=decision` confirmed (round 1; aliased to adr per `bd list --help`); `bd dep add --type=supersedes` and `bd dep list --direction=up/down` confirmed via deepwiki + prior session. `bd dep list --type=supersedes` as a list filter is **plan-stage verification gate (Task 2 Step 2)** — fallback path documented in render-adr if the filter is broken.
- **context7:** SKIP — no external library.
- **deepwiki:** consulted twice on bd metadata/formula semantics + `decision` type schema; both grounding notes already on the bead.

---

## Self-review

**Spec coverage check** — each spec subsection mapped to plan tasks:

| Spec section | Plan task |
|--------------|-----------|
| Architecture — bd as source of truth | Task 1 (formula) + Task 2 (renderer) + Task 8 (skill) |
| Architecture — `/adr` command surface | Tasks 3 (scaffold), 4 (init/new/propose), 5 (update/render/addendum), 6 (accept/deprecate/supersede), 7 (migrate) |
| Architecture — capture-adrs integration | Task 10 |
| Architecture — adr-doctor extensions | Task 9 |
| Architecture — formula structure | Task 1 |
| Architecture — render-adr behavior | Task 2 |
| Architecture — Computed status (5 branches) | Task 2 Step 3 |
| Migration | Task 7 (implementation) + Task 12 (run against this repo) |
| AGENTS.md update | Task 11 |

No gaps detected.

**Placeholder scan:** no "TBD", "TODO", "implement later", "fill in details", "appropriate error handling", or "similar to Task N" present. Task 7's note about an orphan-recovery TODO is intentional and explicitly bounded ("not exercised by this repo's migration; full AskUserQuestion implementation is v2"). Task 9 Step 4 notes a follow-up for `render-adr --to-stdout` — intentional scope-control note, not a hidden TBD.

**Type / name consistency:**

- `$ID`, `$DRAIN_ID` (used in spec drain context, not in this plan), `$TITLE`, `$BODY`, `$DECIDERS`, `$STATUS`, `$STATUS_BD`, `$SLUG`, `$DATE`, `$ADDENDA`, `$SUPERSEDER`, `$SUPERSEDES`, `$SUPERSEDED_BY` — consistent across Tasks 2, 4–7.
- Metadata key `adr_deciders` — Task 1 (formula `metadata = {...}`), Task 2 (`.metadata.adr_deciders` extraction), Task 7 (migrate write), Task 9 INV-A24 (lint check), Task 10 (capture-adrs propagates), Task 12 (migration verifies).
- Label `adr:deprecated` — Task 2 (status compute), Task 6 (`/adr deprecate`), Task 9 INV-A23 (coherence check).
- Label `adr:rejected` — Task 2 (status compute). No `/adr reject` command yet (per spec; deferred follow-up).
- Note prefix `addendum:` — Task 2 (extract), Task 5 (write).
- INV numbers A20–A24 — Tasks 9 and (validated against existing) A15 in adr-doctor.sh, A19 in capture-adrs SKILL.md; no collision.

All consistent.
<!-- adr-capture: sha256=07b9aa9dead177aa; session=cli; ts=2026-05-22T18:35:35Z; adrs= -->
