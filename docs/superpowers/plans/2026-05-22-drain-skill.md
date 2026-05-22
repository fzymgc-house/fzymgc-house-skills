<!-- markdownlint-disable MD013 -->

# `/drain` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `dev-flow:subagent-driven-development` (recommended) or `dev-flow:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `/drain` slash command + `draining-beads` skill + `formula-drain.toml` bd formula that runs autonomous bead iteration via Claude Code's `/goal`, with a per-run drain bead carrying lessons / rejections / halt reasons.

**Architecture:** Three-piece structure inside the `dev-flow` plugin. The slash command (`commands/drain.md`) is the operator entry point and carries the iteration body that `/goal` re-fires each Stop. The skill (`skills/draining-beads/SKILL.md`) is the canonical reference for sentinel, halt, lessons, and edge cases. The formula (`.beads/formulas/formula-drain.toml`) scaffolds the per-run drain bead via `bd mol pour` with variable substitution. Lessons and rejection counts live as `bd note`s on the drain bead, eliminating the holomush self-evolving-prompt anti-pattern.

**Tech Stack:** Markdown (slash command + skill), TOML (bd formula), Bash (`/drain init` bootstrap + per-mode shell), `bd` CLI (issue tracker + `bd mol pour` + `bd config`), Claude Code 2.1.148+ `/goal` slash command + Stop hook, `jj` VCS (colocated; `jj st` for working-tree checks).

**Spec:** `docs/superpowers/specs/2026-05-22-drain-skill-design.md`
**Design bead:** `fhsk-a67`

---

## File structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `dev-flow/.beads/formulas/formula-drain.toml` | **Create** | Single-step bd formula that scaffolds the per-run drain bead; declares `type = "drain"` on its `[[steps]]` block; var-substitutes `{{mode}}` / `{{scope}}` / `{{started_at}}` into title, description, labels |
| `dev-flow/commands/drain.md` | **Create** | `/drain` slash command. Frontmatter declares `allowed-tools` patterns for `bd`, `jj`, and the `${CLAUDE_PLUGIN_ROOT}` formula copy. Body parses `$ARGUMENTS` into a mode (`init` / `epic` / `set` / `cascade` / `resume`) and dispatches. For drain modes, the body composes the per-iteration prompt and fires `/goal "<prompt>"`. |
| `dev-flow/skills/draining-beads/SKILL.md` | **Create** | Canonical reference. Required topics (ordering left to implementer): overview, when to use vs SDD/executing-plans, sentinel design (three modes), halt conditions (three structural), lessons mechanism (two-tier `bd note`), edge cases (Codex / context bloat / push timing / dolt crash / PushNotification fallback), references |
| `dev-flow/skills/subagent-driven-development/SKILL.md` | **Modify** | Add a short pointer (≤4 lines) in the "When to Use" / "Process Flow" area linking to `draining-beads` / `/drain` for autonomous runs |
| `dev-flow/skills/executing-plans/SKILL.md` | **Modify** | Same short pointer in its overview area |
| `dev-flow/AGENTS.md` | **Modify** | Mention `/drain` under "Dev-Flow Conventions" with one-paragraph summary; defer detail to skill |

**Not modified** (verified — these don't need touching):

- `dev-flow/plugin.json` — does not enumerate skills/commands; new files discovered automatically.
- `.claude-plugin/marketplace.json` — registers plugins, not their contents.
- `.agents/plugins/marketplace.json` — same; Codex wrappers symlink to source files.

---

## Conventions used in this plan

- **VCS:** this repo is jj-colocated (`jj root` succeeds). Use `jj describe -m "..."` to set a commit message; `jj new` to start the next change. **Do not use `git commit` or `git checkout` for mutations.** Read-only `git log` / `git diff` are fine. See `references/vcs-preamble.md` in this plugin for the full rule.
- **Conventional Commits:** `type(scope): description`. Scope here is `drain` (e.g., `feat(drain): ...`).
- **Bead model labels:** each task suggests a `model:*` label below (used by `subagent-driven-development` for dispatch). Defaults match Rule 5 (sonnet absent override).

---

### Task 1: Scaffold the bd formula

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Create: `dev-flow/.beads/formulas/formula-drain.toml`

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): add formula-drain.toml"`
  Expected: working copy switches to a fresh empty change.

- [ ] **Step 2: Write `dev-flow/.beads/formulas/formula-drain.toml`**

  ```toml
  formula = "formula-drain"
  version = 1
  description = """
  Single bead-iteration run driven by /goal. See dev-flow/skills/draining-beads/.

  Note conventions on the resulting drain bead:
    "lesson: <text>"           — observation worth carrying to next iteration
    "rejection: <id> N=<n>"    — accumulating rejection count (>=3 triggers halt)
    "halt: <reason>"           — orchestrator-driven early termination
    "result: <summary>"        — final state on /goal termination
  """

  [vars.mode]
  description = "Drain mode"
  required = true
  enum = ["epic", "set", "cascade"]

  [vars.scope]
  description = "Scope identifier (epic id, or space-separated bead ids)"
  required = true

  [vars.started_at]
  description = "ISO8601 timestamp of drain start"
  required = true

  [[steps]]
  id = "drain-root"
  type = "drain"
  title = "Drain: {{mode}} {{scope}}"
  description = "Audit-trail root for the {{mode}}-mode drain over {{scope}} started {{started_at}}."
  labels = ["drain:{{mode}}", "phase:run"]
  ```

- [ ] **Step 3: Stage the formula into `.beads/formulas/` for local validation**

  This step is local-validation only; the formula is committed in `dev-flow/.beads/formulas/`, but for `bd formula show` to find it we need the per-repo path too (because bd searches the active project's `.beads/formulas/`, not plugin dirs). The bootstrap copy in Task 3 makes this permanent; here we just stage temporarily.

  Run:

  ```bash
  mkdir -p .beads/formulas
  cp dev-flow/.beads/formulas/formula-drain.toml .beads/formulas/
  ```

  Expected: file copied; `ls .beads/formulas/formula-drain.toml` shows it.

- [ ] **Step 4: Validate the formula**

  Run: `bd formula show formula-drain`
  Expected: bd prints the formula structure (description, vars, steps); no parse errors.

  Run: `bd formula list | grep formula-drain`
  Expected: one line confirming the formula is discovered.

- [ ] **Step 5: Dry-run pour to confirm the formula can be instantiated**

  Run:

  ```bash
  bd mol pour formula-drain \
    --var mode=epic --var scope=fhsk-a67 --var started_at=2026-05-22T00:00:00Z \
    --dry-run
  ```

  Expected: bd prints what would be created (a single bead titled `Drain: epic fhsk-a67`, type `drain`, labels `drain:epic`, `phase:run`); does NOT create the bead.

- [ ] **Step 6: Clean up the staged validation copy**

  The staged copy at `.beads/formulas/formula-drain.toml` was for validation. The canonical copy lives in `dev-flow/.beads/formulas/`. Remove the staged copy to keep the working tree clean.

  Run: `rm .beads/formulas/formula-drain.toml`
  Expected: file removed. `jj st` shows only `A dev-flow/.beads/formulas/formula-drain.toml`.

- [ ] **Step 7: Describe the jj change**

  Run: `jj --no-pager describe -m "feat(drain): add formula-drain.toml for /drain bead scaffolding"`
  Expected: change has the commit message set.

---

### Task 2: Skeleton `/drain` slash command (frontmatter + dispatch stub)

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Create: `dev-flow/commands/drain.md`

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): scaffold /drain slash command"`
  Expected: fresh empty change at `@`.

- [ ] **Step 2: Write the frontmatter + usage stub**

  Write `dev-flow/commands/drain.md`:

  ````markdown
  ---
  description: Autonomous bead iteration via /goal. Modes: init, epic, set, cascade, resume.
  argument-hint: "init | epic <id> | set <id...> | cascade <id...> | resume <drain-id>"
  allowed-tools: ["Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd types:*)", "Bash(bd formula list:*)", "Bash(bd formula show:*)", "Bash(bd --json mol pour:*)", "Bash(bd mol pour:*)", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd ready:*)", "Bash(bd update:*)", "Bash(bd note:*)", "Bash(bd close:*)", "Bash(bd dep list:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.toml\" .beads/formulas/:*)", "Bash(jj st:*)", "Bash(jj root:*)", "Bash(git status:*)", "Bash(git rev-parse:*)", "Bash(date:*)"]
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

  Remaining mode bodies are filled in by Tasks 3–8 of `docs/superpowers/plans/2026-05-22-drain-skill.md`. This stub MUST refuse all modes other than usage until those tasks land.
  ````

- [ ] **Step 3: Validate the file**

  Run: `rumdl check dev-flow/commands/drain.md`
  Expected: no errors.

  Run (manual sanity): `head -5 dev-flow/commands/drain.md` shows the frontmatter `---` block.

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): scaffold /drain slash command (modes stubbed)"`

---

### Task 3: Implement `/drain init`

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Modify: `dev-flow/commands/drain.md` (extend the `init` mode body)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): implement /drain init"`

- [ ] **Step 2: Replace the `init` placeholder in `dev-flow/commands/drain.md`**

  Locate the section that says `- init — Bootstrap this repo: ...`. Below the usage parse, add an `## Init mode` section with the bootstrap body:

  ````markdown
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
  cp -n "${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.toml" .beads/formulas/

  # 3. Sanity check: both assets present
  bd types | grep -q drain || { echo "drain type not registered" >&2; exit 1; }
  bd formula list | grep -q formula-drain || { echo "formula-drain not visible to bd" >&2; exit 1; }
  echo "drain init complete."
  ```

  `${CLAUDE_PLUGIN_ROOT}` resolves via the `allowed-tools` declaration (matches the ralph-loop / hookify slash-command pattern).
  ````

- [ ] **Step 3: Manually test the init body**

  In a scratch worktree (or a backup of `.beads/`), invoke `/drain init` and verify:

  ```bash
  bd config get types.custom
  ```

  Expected: includes `drain`.

  ```bash
  ls .beads/formulas/formula-drain.toml
  ```

  Expected: file present.

  Run `/drain init` again.
  Expected: idempotent — no duplicate type entries, no overwrite (`cp -n` skips if exists).

- [ ] **Step 4: Add idempotency assertion**

  After the success message, verify the second run produces the same output without errors. If you observe an error, the script is non-idempotent — root-cause it before committing.

- [ ] **Step 5: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): implement /drain init (idempotent bootstrap)"`

---

### Task 4: Implement `/drain epic <epic-id>`

Suggested labels: `model:opus`, `scope:drain`

This is the most complex task in the plan — it implements pre-flight, pour, sentinel composition, the `/goal` fire-and-track sequence, and the post-flight branches.

**Files:**

- Modify: `dev-flow/commands/drain.md` (add the `epic` mode body)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): implement /drain epic mode"`

- [ ] **Step 2: Add the `## Epic mode` section to `dev-flow/commands/drain.md`**

  Place it after the `## Init mode` section. The body has four phases.

  **Phase A: Pre-flight checks** (refuse early on bad state):

  ```bash
  EPIC_ID="$1"  # the bead id passed to `/drain epic <id>`

  # 1. Bootstrap verified
  bd types | grep -q drain && [ -f .beads/formulas/formula-drain.toml ] \
    || { echo "Run /drain init first." >&2; exit 1; }

  # (Spec pre-flight #2 — mode arg valid — is handled by Task 2's dispatch stub.)

  # 3. Scope validation: epic exists; has >=1 open child
  bd show "$EPIC_ID" --json >/dev/null 2>&1 \
    || { echo "Epic $EPIC_ID not found." >&2; exit 1; }
  OPEN_CHILDREN=$(bd list --parent "$EPIC_ID" --status=open --json | jq 'length')
  [ "$OPEN_CHILDREN" -gt 0 ] \
    || { echo "Epic $EPIC_ID has no open children — nothing to drain." >&2; exit 1; }

  # 4. Working tree clean (jj first if jj root succeeds; git status as fallback)
  if jj root >/dev/null 2>&1; then
    DIRTY=$(jj st --no-pager | grep -E "^(M|A|D|R)" | wc -l | tr -d ' ')
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

  # 6. Trust + hooks check — /goal silently no-ops in untrusted workspaces and
  #    fails with "hooks disabled" if disableAllHooks / allowManagedHooksOnly is set.
  #    Probe the writable settings files for the hooks-disable flags. The trust gate
  #    is not introspectable from shell — if you see "/goal is only available in
  #    trusted workspaces" when /goal fires, accept the trust dialog and re-run.
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

  Numbering matches the spec's 7-check pre-flight: #1 bootstrap, #2 mode arg (handled by Task 2's dispatch stub, not re-checked here), #3 scope, #4 working tree, #5 branch, #6 trust+hooks, #7 no overlap.

  **Phase B: Pour the drain bead + stash structured metadata**:

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

  **Phase C: Compose the `/goal` prompt and fire it.** The prompt body is the per-iteration text from Task 8 (referenced here as a placeholder; Task 8 fills in the actual prose):

  ```bash
  # SENTINEL: the natural-language condition the model evaluates each iteration
  SENTINEL="All beads under epic $EPIC_ID are closed."

  # The /goal prompt body is the 12-step iteration text — see Task 8 of the plan
  # for the exact prose. Task 8 fills in $PROMPT_BODY below.
  ```

  **Phase D: Tell Claude to fire `/goal`.** This is a literal slash-command invocation in the assistant's next action — not a Bash command:

  ```markdown
  After the shell commands above complete successfully, invoke:

      /goal <PROMPT_BODY>

  where `<PROMPT_BODY>` is composed per the "Iteration body" section below (filled in by Task 8). Pass `DRAIN_ID`, `EPIC_ID`, and `SENTINEL` as substituted values inside the prompt body.
  ```

- [ ] **Step 3: Manual test — pre-flight refusals**

  In a scratch state:

  - Run `/drain epic nonexistent-id` → expect "Epic nonexistent-id not found" exit 1.
  - Touch a file (`echo x >> README.md`), run `/drain epic <real-epic-id>` → expect "Working tree not clean" exit 1. Revert the touch.
  - Switch to `main` (`jj edit main`), run `/drain epic <real-epic-id>` → expect "Refuse to drain on main" exit 1.
  - Temporarily add `{"disableAllHooks": true}` to a copy of `.claude/settings.json` (back up the original first), run `/drain epic <real-epic-id>` → expect "Refusing: ... has hooks disabled" exit 1. Restore the original settings.

- [ ] **Step 4: Manual test — pour + metadata**

  Create a test epic (`bd create -t epic --title='Test drain epic'`) with one open child task.

  Run `/drain epic <test-epic-id>`.

  Expected:
  - A new drain bead is created (record its id from output).
  - `bd show <drain-id> --json | jq '.type'` returns `"drain"`.
  - `bd show <drain-id> --json | jq '.metadata.drain_mode, .metadata.drain_scope, .metadata.drain_started_at'` returns `"epic"`, `"<test-epic-id>"`, and an ISO timestamp.
  - `bd show <drain-id> --json | jq '.parent'` returns `<test-epic-id>`.
  - `bd show <drain-id> --json | jq '.status'` returns `"in_progress"`.

  Then `bd close <drain-id> --reason=test` to clean up; close the test epic too.

- [ ] **Step 5: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): implement /drain epic pre-flight, pour, and goal-fire scaffolding"`

  (Phase D's actual `/goal` prompt body lands in Task 8.)

---

### Task 5: Implement `/drain set <id1> <id2> ...`

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Modify: `dev-flow/commands/drain.md` (add `## Set mode` section)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): implement /drain set mode"`

- [ ] **Step 2: Add the `## Set mode` section**

  Mirror epic mode's structure, swapping the scope validation + sentinel:

  ```bash
  # SET-mode scope validation
  for id in "$@"; do
    bd show "$id" --json >/dev/null 2>&1 \
      || { echo "Bead $id not found." >&2; exit 1; }
    STATUS=$(bd show "$id" --json | jq -r '.status')
    [ "$STATUS" != "closed" ] \
      || { echo "Bead $id is already closed; remove from set." >&2; exit 1; }
  done

  SCOPE="$*"  # space-separated ids stored in metadata
  ```

  And the sentinel:

  ```bash
  SENTINEL="All of {$SCOPE} are closed."
  ```

  The pour / metadata / goal-fire phases are otherwise identical to epic mode, except **no parent linkage** (set mode doesn't have a single parent) — skip `bd update "$DRAIN_ID" --parent "$EPIC_ID"`.

- [ ] **Step 3: Manual test — set scope**

  Create three test task beads; pick two of them as the set.

  Run `/drain set <id1> <id2>`.

  Expected:
  - Drain bead created with `--var mode=set --var scope="<id1> <id2>"`.
  - `bd show <drain-id> --json | jq '.metadata.drain_scope'` returns `"<id1> <id2>"`.
  - `bd show <drain-id> --json | jq '.parent'` returns null (no parent).
  - The unused third bead is unaffected.

  Cleanup: `bd close <drain-id> --reason=test`; remove test beads.

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): implement /drain set mode"`

---

### Task 6: Implement `/drain cascade <id1> <id2> ...`

Suggested labels: `model:opus`, `scope:drain`

Cascade introduces the stateful working-set expansion. The iteration body (Task 8) will reference these helpers.

**Files:**

- Modify: `dev-flow/commands/drain.md` (add `## Cascade mode` section)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): implement /drain cascade mode"`

- [ ] **Step 2: Add the `## Cascade mode` section**

  Scope validation mirrors set mode. The sentinel is computed via a per-iteration helper (defined in Task 8) that maintains a working set:

  ```bash
  # Cascade-mode scope = seed ids; working set expands via bd dep list --direction=up
  for id in "$@"; do
    bd show "$id" --json >/dev/null 2>&1 \
      || { echo "Seed bead $id not found." >&2; exit 1; }
    STATUS=$(bd show "$id" --json | jq -r '.status')
    [ "$STATUS" != "closed" ] \
      || { echo "Seed bead $id is already closed; remove from set." >&2; exit 1; }
  done

  SCOPE="$*"  # space-separated seeds
  SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed."
  ```

  In the iteration body (filled by Task 8), the per-iteration helper resolves the working set by, for each closed seed/descendant, calling:

  ```bash
  bd dep list <closed-id> --direction=up --json | jq -r '.[].id'
  ```

  to add newly-revealed dependents to the working set. The helper terminates when no open beads remain in the working set AND no new dependents are added.

- [ ] **Step 3: Manual test — cascade graph traversal**

  Create three beads: `A`, `B`, `C`. Add deps: `B` depends on `A`; `C` depends on `B` (via `bd dep add B A` and `bd dep add C B`).

  Run `/drain cascade A`.

  Expected:
  - Drain bead created with `--var mode=cascade --var scope=A`.
  - `bd dep list A --direction=up` lists `B`.
  - Initial working set after pour = `{A}`. As `A` closes, `B` joins; as `B` closes, `C` joins.

  Cleanup: close drain bead; remove test beads.

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): implement /drain cascade mode with working-set expansion"`

---

### Task 7: Implement `/drain resume <drain-id>`

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Modify: `dev-flow/commands/drain.md` (add `## Resume mode` section)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): implement /drain resume"`

- [ ] **Step 2: Add the `## Resume mode` section**

  ```bash
  DRAIN_ID="$1"

  # 1. Recover structured fields from drain bead metadata
  META=$(bd show "$DRAIN_ID" --json | jq '.metadata')
  MODE=$(echo "$META" | jq -r '.drain_mode')
  SCOPE=$(echo "$META" | jq -r '.drain_scope')
  STARTED_AT=$(echo "$META" | jq -r '.drain_started_at')

  [ -n "$MODE" ] && [ "$MODE" != "null" ] \
    || { echo "Drain bead $DRAIN_ID has no drain_mode metadata; cannot resume." >&2; exit 1; }

  # 2. Re-run pre-flight (Phase A from the original mode) against $SCOPE
  # (Run the mode-specific pre-flight; for epic, that's epic-mode Phase A; for set/cascade, theirs.)

  # 3. Recompose the same SENTINEL string the original run used
  case "$MODE" in
    epic)    SENTINEL="All beads under epic $SCOPE are closed." ;;
    set)     SENTINEL="All of {$SCOPE} are closed." ;;
    cascade) SENTINEL="All beads in the cascade-reachable set from {$SCOPE} are closed." ;;
  esac

  echo "Resuming drain $DRAIN_ID (mode=$MODE, scope=$SCOPE, started=$STARTED_AT)."
  ```

  Then fall through to the same `/goal <PROMPT_BODY>` invocation as the original mode. The drain bead's existing notes (lessons, rejection counts, halt reasons) carry forward unchanged — the iteration body's halt-check on iteration 1 will see prior `rejection:` notes and trip immediately if any task is already past N=3.

- [ ] **Step 3: Manual test — resume after halt**

  Set up: create a test epic with one open task. Run `/drain epic <epic-id>` → before /goal fires, manually `bd note <drain-id> "halt: test"` and `bd update <drain-id>` to simulate a halted run.

  Run `/drain resume <drain-id>`.

  Expected:
  - Recovered metadata fields shown in output.
  - Pre-flight runs against `<epic-id>` (mode=epic).
  - Same sentinel string composed.

  Cleanup: close drain; remove test epic.

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): implement /drain resume with metadata recovery"`

---

### Task 8: Compose the `/goal` Stop-hook prompt body (iteration body)

Suggested labels: `model:opus`, `scope:drain`

This task fills in the `<PROMPT_BODY>` referenced by Tasks 4–7. The prompt is the 12-step iteration body from the spec.

**Files:**

- Modify: `dev-flow/commands/drain.md` (add `## Iteration body (/goal Stop-hook prompt)` section)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): compose /goal Stop-hook iteration prompt"`

- [ ] **Step 2: Add the `## Iteration body (/goal Stop-hook prompt)` section**

  Insert the canonical 12-step iteration text. The prompt should be a single, self-contained natural-language description that references the drain bead by id and the sentinel by string:

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

  Then in Tasks 4, 5, 6, 7, replace the `<PROMPT_BODY>` placeholder with this text (with `$DRAIN_ID`, `$MODE`, `$SCOPE`, `$SENTINEL`, `$EPIC_ID` substituted at fire time).

- [ ] **Step 3: Validate the slash command file**

  Run: `rumdl check dev-flow/commands/drain.md`
  Expected: no errors.

  Run: `wc -l dev-flow/commands/drain.md`
  Expected: under ~500 lines (keep the file scannable).

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): compose 12-step /goal iteration prompt body"`

---

### Task 9: Write `draining-beads` SKILL.md

Suggested labels: `model:sonnet`, `scope:drain`

**Files:**

- Create: `dev-flow/skills/draining-beads/SKILL.md`

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): add draining-beads skill"`

- [ ] **Step 2: Write `dev-flow/skills/draining-beads/SKILL.md`**

  The SKILL.md MUST cover these topics (ordering left to implementer):

  - **Overview** of the harness and the spec it implements (`docs/superpowers/specs/2026-05-22-drain-skill-design.md`).
  - **When to use** vs. `subagent-driven-development` (which is the inner mechanism) and `executing-plans` (which is the single-session serial alternative).
  - **Sentinel design** — restate the three modes' sentinels (epic / set / cascade) with their verification queries.
  - **Halt conditions** — restate the three structural halts (BLOCKED, ≥3 rejections, VCS failure) with their bd-side bookkeeping.
  - **Lessons mechanism** — restate the two-tier `bd note "lesson: ..."` convention (run-scoped on drain bead, epic-scoped on epic bead).
  - **Edge cases** — Codex fallback (manual loop recipe), context bloat (`/compact` recommendation), push timing (subagents commit but don't push; orchestrator pushes at clean sentinel), dolt-server crash (halt #3 path), PushNotification unavailable (final-turn message fallback).
  - **References** — link to the spec, companion specs, and rules 1 / 5 / 6 / 7 from `dev-flow/AGENTS.md`.

  The skill body cites the spec as source of truth for any contract change; it is reference, not duplicated specification.

  Begin the file with the standard frontmatter:

  ```yaml
  ---
  name: draining-beads
  description: Use when you have an epic / set / cascade of beads to drain autonomously via Claude Code's /goal. Pairs with the /drain slash command. Requires Claude Code 2.1.148+ with hooks enabled.
  ---
  ```

  Skill body must be under 500 lines per the project's skill QA conventions.

- [ ] **Step 3: Validate the skill**

  Run: `rumdl check dev-flow/skills/draining-beads/SKILL.md`
  Expected: no errors.

  Run: `wc -l dev-flow/skills/draining-beads/SKILL.md`
  Expected: under 500 lines.

  Run: `uv run --with pyyaml python -c "import yaml,sys; yaml.safe_load(open('dev-flow/skills/draining-beads/SKILL.md').read().split('---')[1])"`
  Expected: frontmatter parses without error.

- [ ] **Step 4: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): add draining-beads skill (canonical reference)"`

---

### Task 10: Add cross-references to existing skills

Suggested labels: `model:haiku`, `scope:drain`

**Files:**

- Modify: `dev-flow/skills/subagent-driven-development/SKILL.md`
- Modify: `dev-flow/skills/executing-plans/SKILL.md`

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "feat(drain): cross-reference draining-beads from SDD and executing-plans"`

- [ ] **Step 2: Edit `dev-flow/skills/subagent-driven-development/SKILL.md`**

  Find the "Continuous execution:" paragraph (around line 14) and add this paragraph immediately after it:

  ```markdown
  **Autonomous epic drain:** For a long-running, hands-off drain of an epic
  or seed set, pair this skill with `dev-flow:draining-beads` (operator
  entry: `/drain epic <id>` / `/drain set <id...>` / `/drain cascade <id...>`).
  The drain skill harnesses this one with Claude Code's `/goal` Stop hook so
  the orchestrator stays running until the sentinel is met or a halt
  condition fires. Requires Claude Code 2.1.148+ with hooks enabled.
  ```

- [ ] **Step 3: Edit `dev-flow/skills/executing-plans/SKILL.md`**

  Find the "Tell your human partner that Superpowers..." paragraph (the "Note:" block under Overview) and add this paragraph immediately after it:

  ```markdown
  **Autonomous mode alternative:** If your platform supports `/goal` and your
  work is shaped as an epic / set / cascade of beads, consider
  `dev-flow:draining-beads` (operator entry: `/drain <mode> <scope>`). It
  drains autonomously via the Stop hook without a human in the loop between
  beads.
  ```

- [ ] **Step 4: Validate**

  Run: `rumdl check dev-flow/skills/subagent-driven-development/SKILL.md dev-flow/skills/executing-plans/SKILL.md`
  Expected: no errors.

- [ ] **Step 5: Describe the change**

  Run: `jj --no-pager describe -m "feat(drain): cross-reference draining-beads from SDD + executing-plans"`

---

### Task 11: Update `dev-flow/AGENTS.md`

Suggested labels: `model:haiku`, `scope:drain`

**Files:**

- Modify: `dev-flow/AGENTS.md` (add `/drain` mention under Dev-Flow Conventions)

**Steps:**

- [ ] **Step 1: Start a new jj change**

  Run: `jj --no-pager new -m "docs(drain): mention /drain in dev-flow AGENTS.md"`

- [ ] **Step 2: Read the current `dev-flow/AGENTS.md`**

  Run: `head -60 dev-flow/AGENTS.md`
  Locate the "Dev-Flow Conventions" section (or the section that lists the workflow skills).

- [ ] **Step 3: Add a `/drain` paragraph at the appropriate location**

  Insert this paragraph in the conventions list (preserving the existing list style):

  ```markdown
  - **`/drain` autonomous bead iteration.** For epic / set / cascade drains
    that should run hands-off, use `/drain <mode> <scope>` (after a one-time
    `/drain init`). Wraps `subagent-driven-development` in a `/goal` Stop
    hook; lessons and rejection counts accumulate on a per-run drain bead.
    See `dev-flow/skills/draining-beads/SKILL.md` for the canonical pattern.
  ```

- [ ] **Step 4: Validate**

  Run: `rumdl check dev-flow/AGENTS.md`
  Expected: no errors.

- [ ] **Step 5: Describe the change**

  Run: `jj --no-pager describe -m "docs(drain): mention /drain in dev-flow AGENTS.md conventions"`

---

### Task 12: End-to-end smoke test

Suggested labels: `model:sonnet`, `scope:drain`

This task does not modify files. It runs a real `/drain` against a synthetic epic to confirm the pieces wire correctly.

**Files:**

- None modified. This is a manual verification task.

**Steps:**

- [ ] **Step 1: Create a synthetic epic + 2 child task beads in an isolated jj workspace**

  Isolate the test so its beads don't pollute the working repo's bd database. Create a sibling jj workspace that gets its own beads checkout:

  ```bash
  jj workspace add ../fzymgc-house-skills_worktrees/drain-e2e-test
  cd ../fzymgc-house-skills_worktrees/drain-e2e-test

  # The sibling workspace shares the same bd dolt server / db, so test beads
  # are still visible globally. Label them clearly for cleanup at Step 5.
  EPIC=$(bd --json create -t epic --title="Drain E2E test epic" --labels="test:drain-e2e" | jq -r '.id')
  TASK1=$(bd --json create -t task --title="E2E task 1" --parent "$EPIC" --labels="test:drain-e2e" --description="Trivial: write a marker file e2e-marker-1." | jq -r '.id')
  TASK2=$(bd --json create -t task --title="E2E task 2" --parent "$EPIC" --labels="test:drain-e2e" --description="Trivial: write a marker file e2e-marker-2." | jq -r '.id')
  echo "Epic=$EPIC Task1=$TASK1 Task2=$TASK2"
  ```

  Note: bd's Dolt backend is shared across jj workspaces, so the test beads are visible in the parent repo's bd queries too. The `test:drain-e2e` label is the cleanup discriminator used at Step 5.

- [ ] **Step 2: Run `/drain init`** (if not already done)

  Verify: `bd types | grep drain && bd formula list | grep formula-drain`.

- [ ] **Step 3: Run `/drain epic $EPIC`**

  Observe Claude's output:
  - Pre-flight passes.
  - Drain bead created (note the id).
  - `/goal` fires with the sentinel string.
  - Iteration 1 picks `TASK1` or `TASK2` (whichever sorts first), claims, dispatches subagent, closes.
  - Iteration 2 picks the other, repeats.
  - Iteration 3 sees both closed → sentinel met → drain bead closes cleanly.

- [ ] **Step 4: Verify final state**

  ```bash
  bd show $EPIC --json | jq '.status'
  # Expect: depending on finishing-a-development-branch behavior, either "open" (epic stays open if not auto-closed)
  # or "closed" (if the post-flight closed it). Spec is silent; either is acceptable.

  bd show "$DRAIN_ID" --json | jq '{status,notes}'
  # Expect: status="closed"; notes include "result: complete; iterations=2 ..."

  bd show $TASK1 --json | jq '.status'
  bd show $TASK2 --json | jq '.status'
  # Both: "closed"

  ls e2e-marker-1 e2e-marker-2
  # Both files exist
  ```

- [ ] **Step 5: Cleanup**

  ```bash
  # Remove marker files (in the isolated workspace)
  rm -f e2e-marker-1 e2e-marker-2

  # Close any remaining open test beads by label
  bd list --label-any test:drain-e2e --status=open --json | jq -r '.[].id' | \
    xargs -I {} bd close {} --reason="E2E test complete" 2>/dev/null || true
  bd list --label-any test:drain-e2e --status=in_progress --json | jq -r '.[].id' | \
    xargs -I {} bd close {} --reason="E2E test complete" 2>/dev/null || true

  # Forget the isolated workspace
  cd -  # back to the primary workspace
  jj workspace forget drain-e2e-test
  rm -rf ../fzymgc-house-skills_worktrees/drain-e2e-test
  ```

  Cleanup is best-effort; orphaned test beads (filtered by `test:drain-e2e` label) do not block the plan from being declared complete and can be cleaned later with the same bd query.

- [ ] **Step 6: No commit needed** — this task is verification only.

---

## Grounding-verification trace

Recorded as `bd note fhsk-a67` entries after the plan was drafted:

- **probe-paths:** verified all `Create:` and `Modify:` paths in the file structure table; new-create paths land in directories that already exist (`dev-flow/.beads/formulas/` is new, created by Task 1 alongside its file; `dev-flow/commands/`, `dev-flow/skills/`, `dev-flow/AGENTS.md` all exist).
- **bd-cli-reverify:** `bd config get/set types.custom`, `bd types`, `bd formula list/show`, `bd mol pour --dry-run`, `bd --json mol pour ...`, `bd update --set-metadata KEY=VALUE`, `bd update --parent`, `bd update --status=in_progress`, `bd list --label-pattern`, `bd list --parent`, `bd dep list --direction=up`, `bd ready --json` — all verified against `bd --help` output and deepwiki `gastownhall/beads` in the spec phase. No re-verify needed for plan stage.
- **context7:** SKIP — no external library; bd is local CLI; `/goal` semantics covered via spec's binary-strings extraction.
- **deepwiki re-check:** SKIP — same reason; spec phase exhausted the relevant deepwiki questions (custom types / formulas / molecule lifecycle / auto-registration behavior).

---

## Self-review

**Spec coverage check** — each numbered/lettered spec subsection mapped to a task:

| Spec section | Plan task |
|--------------|-----------|
| Three-piece structure (formula / command / skill) | Tasks 1, 2–8, 9 |
| Invocation surface (init / epic / set / cascade / resume) | Tasks 3, 4, 5, 6, 7 |
| Sentinel design (3 modes) | Tasks 4, 5, 6 (Phase A of each); restated in Task 8 prompt |
| Halt conditions (3 structural) | Task 8 step 2 |
| Per-iteration body (12 steps) | Task 8 |
| Lessons mechanism (2-tier) | Task 8 step 3; documented in Task 9 |
| Drain bead + formula | Task 1 + Task 4 Phase B |
| Bootstrap (`/drain init`) | Task 3 |
| Pre-flight (7 checks per spec) | Task 4 Phase A covers #1, #3, #4, #5, #6, #7 (mirrored in Tasks 5, 6, 7); #2 (mode arg valid) handled by Task 2's dispatch stub |
| Post-flight (clean / halt) | Task 8 steps 1, 2 |
| Edge cases (6) | Task 9 (skill body) |
| Files added / changed | Tasks 1–11 |
| Testing strategy | Task 12 + individual task verification |
| Open question: per-iteration wisps | Out of scope; spec says deferred |

No gaps detected.

**Placeholder scan:** no "TBD", "TODO", "implement later", "fill in details", "appropriate error handling", "similar to Task N" present. Task 4 Phase D contains `<PROMPT_BODY>` as a literal placeholder — but it is explicitly resolved by Task 8, which is the next task and references back. Acceptable per plan style.

**Type / name consistency:**

- `$DRAIN_ID`, `$MODE`, `$SCOPE`, `$SENTINEL`, `$EPIC_ID`, `$STARTED_AT` — consistent across Tasks 4–8.
- Metadata keys `drain_mode`, `drain_scope`, `drain_started_at` — written in Task 4 Phase B; read in Task 7 Step 2.
- Note prefixes `lesson:`, `rejection:`, `halt:`, `result:` — declared in Task 1 formula description; used in Task 8 steps 2, 3, 9, 10.
- Custom type name `drain` — set in Task 1 formula; registered in Task 3; verified in Task 4 Phase B; used in Tasks 4–7 sentinels.

All consistent.
<!-- adr-capture: sha256=a1fc103dbb485fde; session=cli; ts=2026-05-22T12:43:01Z; adrs=fhsk-thw,fhsk-0o2,fhsk-rqh,fhsk-ce3,fhsk-0cd -->
