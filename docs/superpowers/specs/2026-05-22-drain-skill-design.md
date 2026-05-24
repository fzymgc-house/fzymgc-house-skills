<!-- markdownlint-disable MD013 -->

# `dev-flow`: `/drain` Slash Command + `draining-beads` Skill

**Date:** 2026-05-22
**Status:** Proposed
**Deciders:** Sean Brandt (`@seanb4t`)
**Supersedes:** —
**Bead:** [fhsk-a67](../../../README.md) — *Design: /loop vs /goal for bead iteration in dev-flow*

## Overview

`dev-flow` gains a first-class autonomous bead-iteration harness in three pieces:

1. **`/drain` slash command** — operator-facing entry point for autonomous epic / set / cascade drains. Pre-flight-checks the workspace, pours a per-run *drain bead* via a versioned formula, and fires Claude Code's built-in `/goal` with a curated Stop-hook prompt body that embeds the iteration logic.
2. **`draining-beads` skill** — the canonical reference for sentinel design, halt conditions, lesson semantics, and drain-bead audit conventions. Documents the harness pattern as a discoverable dev-flow skill.
3. **`formula-drain.toml` bd formula** — version-controlled scaffolding for the drain bead. Single-step formula; var-substituted title / description / labels; persistent (`liquid`) phase. Lives in the plugin and is copied into the active repo's `.beads/formulas/` by `/drain init`.

`/drain` replaces an ad-hoc holomush-era pattern that wrapped `/loop autonomous` with a ~1500-word self-evolving prompt. That pattern emerged because the model reached for `/loop` (visible in dev-flow's skill list) before Claude Code's native `/goal` (built into the harness in `2.1.148`). The current design eliminates the prompt-drift problem by routing lessons through `bd` notes on the drain bead instead of the prompt body, and adopts `/goal` natively so per-iteration prompt cost is amortized inside one session.

`/loop autonomous` is **not** referenced as a drain alternative — it has no legitimate niche for bead iteration. `/loop`'s real purpose (polling external state on a timer) is distinct and unchanged. See [References](#references) for the grounding that established this.

## Goals

- Encode `/goal`-driven bead iteration as the canonical autonomous-drain mechanism in `dev-flow`.
- Make every drain run discoverable, auditable, and resumable via a per-run drain bead in `bd`.
- Eliminate the holomush "self-evolving prompt" anti-pattern by storing run-level lessons in `bd` notes rather than the prompt body.
- Keep the surface area additive — `subagent-driven-development` and `executing-plans` gain a one-line pointer; no other dev-flow skill changes.
- Bootstrap is explicit (`/drain init`) and per-repo; nothing mutates `.beads/` without operator action.

## Non-goals

- Replacing `subagent-driven-development`. `/drain` reuses its 12-step per-iteration body (the two-stage review + atomic claim + label-driven model selection). The drain skill orchestrates; the SDD skill implements.
- Cross-platform parity. `/goal` is Claude Code-only (verified via binary strings; requires trusted workspace + hooks enabled). Codex / other harness users get a manual fallback recipe; no automation.
- Per-iteration audit beads (wisp children of the drain bead). Considered and deferred — drain-bead notes are sufficient v1 audit.
- Compressing closed drains via `bd mol squash`. Future hygiene; not v1.
- Touching `/loop autonomous`. The skill stays as-is for its actual purpose (timer-based external-state polling).

## Architecture

### Three-piece structure

```text
dev-flow/
├── .beads/formulas/
│   └── formula-drain.toml             # versioned bd formula, single step
├── commands/
│   └── drain.md                       # slash command frontmatter + body
└── skills/
    └── draining-beads/
        └── SKILL.md                   # canonical pattern reference
```

The slash command **carries the `/goal` Stop-hook prompt body** (the iteration logic). The skill is **read by the orchestrator** when the iteration body says "see skill for halt-condition semantics" — it is not invoked per iteration. The formula carries **only the drain bead's scaffolding** (title, description, labels) — not the iteration body.

This split is load-bearing: putting the iteration body in the formula would force a per-iteration formula read; putting it in the skill would force a per-iteration `Skill` tool call; embedding it in the `/goal` prompt body keeps it inside the cached session prompt.

### Invocation surface

```text
/drain init                          # one-shot bootstrap (register type, copy formula)
/drain epic <epic-id>                # mode A: all ready beads under epic
/drain set <id1> <id2> ...           # mode B: only these beads
/drain cascade <id1> <id2> ...       # mode C: seeds + transitive dependents
/drain resume <drain-id>             # resume a halted run
```

Mode keywords (`init` / `epic` / `set` / `cascade` / `resume`) are explicit. Missing or invalid: print usage; exit non-zero; do not fire `/goal`.

### Sentinel design (what makes `/goal` terminate cleanly)

`/goal`'s `condition` is natural-language evaluated by the model each Stop-hook iteration (the harness owns the Stop hook; the model owns `met` detection and sets a sentinel attachment — confirmed via binary strings in `2.1.148`). Phrasing the condition as a checkable predicate the model can verify with one `bd` query:

| Mode | Sentinel string | Verification query |
|------|-----------------|---------------------|
| `epic <id>` | `All beads under epic <id> are closed.` | `bd list --status=open --parent <id> --json \| jq 'length == 0'` |
| `set <ids…>` | `All of {<id1>, …} are closed.` | `for id in $SEED; do bd show $id --json \| jq -e '.status == "closed"'; done` |
| `cascade <ids…>` | `All beads in the cascade-reachable set from {seeds} are closed.` | Stateful per-iteration: maintain working set seeded by `$SEEDS`; expand via `bd dep list <id> --direction=up` (returns dependents, i.e., issues that depend on `<id>`) after each close; query is "any open bead in working_set?" |

### Halt conditions (orchestrator-driven early termination)

Three structural halts cause the iteration body to **explicitly clear `/goal`** and surface via `PushNotification` rather than waiting for the sentinel:

| # | Trigger | Bead-side bookkeeping |
|---|---------|------------------------|
| 1 | `BLOCKED` status from implementer subagent | `bd note <task-id> "BLOCKED iter N: <reason>"`; `bd note <drain-id> "halt: blocked on <task-id>; reason=<short>"` |
| 2 | ≥3 rejection rounds on a single task | `bd note <task-id> "rejection round N: <reason>"`; `bd note <drain-id> "rejection: <task-id> N=3"`; halt-check fires on next iteration |
| 3 | VCS / harness failure (push fails, dirty tree across iterations, `bd dolt` unreachable) | `bd note <drain-id> "halt: vcs-failure; detail=<short>"` |

On halt: `goal_status.met=false`; the drain bead stays `--status=in_progress` for resume. On clean sentinel: `bd note <drain-id> "result: complete; iterations=<N>, duration=<ms>, tokens=<n>"`; `bd close <drain-id>`.

### Per-iteration body (the `/goal` Stop-hook prompt)

Each iteration runs the following 12-step body, embedded verbatim in `commands/drain.md`. Steps are kept tight to amortize per-iteration token cost across the cached session.

```text
1.  Check sentinel — run mode-appropriate bd query.
    If met: emit completion summary; invoke finishing-a-development-branch; exit.

2.  Check halt conditions — scan drain bead's notes for "rejection: ... N=3+" lines
    OR check for any "halt:" note (idempotency on re-entry).
    On halt-triggered exit: see post-flight.

3.  Read lessons — bd notes <drain-id> + bd notes <epic-id-if-epic-mode>
    filtered to prefix "lesson: ". Collect text for subagent prompt injection.

4.  Pick next ready bead — bd ready --json filtered to in-scope.
    Deterministic order: lowest priority number, then alphabetic id.
    If filter returns empty but sentinel says not met → re-evaluate sentinel;
    if still not met → halt with "stalled queue" reason.

5.  Atomic claim — bd update <id> --claim. On race: skip step 6, restart iteration.

6.  Load context — bd show <id> for description / acceptance / --spec-id;
    if spec-id present, read the referenced spec/plan file.

7.  Dispatch implementer subagent (per existing subagent-driven-development):
      subagent_type from bead's skills[] (heuristic; general-purpose fallback)
      model       from bead's model:* label (default sonnet per Rule 5)
      prompt      = bead description + acceptance criteria + spec excerpts + lessons[]
    In jj repos (jj root succeeds): brief the subagent to run `jj --no-pager new`
    before any edits, so each task lands in its own change rather than squashing
    into the previous task's commit. In git repos: no-op (each task lands on the
    current branch tip as a separate commit).

8.  Two-stage review (existing pattern):
      Spec compliance reviewer → on fail, implementer fixes, re-review
      Code quality reviewer    → on fail, implementer fixes, re-review

9.  On approval — bd close <id> --reason="<one-line summary>". Append bd note
    for any deviations or follow-ups discovered.

10. On rejection (review loops exhausted this iteration):
      bd update <id> --status=open  (release the claim)
      bd note <id> "rejection round N: <reason>"
      bd note <drain-id> "rejection: <id> N=<count>"
      Step 2's halt check catches N≥3 on next iteration.

11. VCS verify — jj st (or git status --porcelain); confirm clean tree.
    If dirty: bd note <drain-id> "halt: dirty-tree iter N"; halt.

12. Iteration ends. /goal Stop hook re-fires this prompt → step 1.
```

### Lessons mechanism (two-tier)

| Scope | Storage | Lifetime | Written by |
|-------|---------|----------|------------|
| **Run-scoped** | `bd note <drain-id> "lesson: <text>"` | Closes with the drain bead | Orchestrator, on observation |
| **Epic-scoped** | `bd note <epic-id> "lesson: <text>"` | Persists across all future runs against this epic | Orchestrator (elevation) OR operator (manual) |

Step 3 reads both on each iteration. The orchestrator elevates a lesson by writing it to the epic bead when it judges the lesson generalizable beyond the current run.

This replaces the holomush hand-edited prompt drift with a structured, queryable lesson log.

### Drain bead (custom `drain` type) + `formula-drain.toml`

Each `/drain` invocation pours one bead via:

```bash
# Note: --json is a bd *global* flag (per `bd --help`), inherited by all
# subcommands including `bd mol pour`, even though it does not appear in
# `bd mol pour --help`'s local-flag listing. The current legacy envelope
# returns a flat object with `.id` at the top level; bd v2.0 will move to
# `.data.id` (set BD_JSON_ENVELOPE=1 to opt in early). Revisit this jq path
# if the team upgrades bd past v2.0.
DRAIN_ID=$(bd --json mol pour formula-drain \
  --var mode="$MODE" --var scope="$SCOPE" --var started_at="$(date -u +%FT%TZ)" \
  | jq -r '.id')

# Stash structured fields so /drain resume can recover mode + scope reliably,
# rather than parsing them out of the description prose.
bd update "$DRAIN_ID" \
  --set-metadata "drain_mode=$MODE" \
  --set-metadata "drain_scope=$SCOPE" \
  --set-metadata "drain_started_at=$(date -u +%FT%TZ)"

# Epic mode only: link drain bead as a child of the epic via the parent relation
# (NOT bd dep add — that is for blocking deps. Parent-child uses --parent.)
[ "$MODE" = "epic" ] && bd update "$DRAIN_ID" --parent "$SCOPE"

bd update "$DRAIN_ID" --status=in_progress
```

The formula:

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

**Bead-type assignment** is set by the `type = "drain"` field inside the `[[steps]]` block (confirmed via deepwiki — the per-step `type` field maps to the spawned bead's `IssueType`).

**Behavior when `drain` is not pre-registered** (confirmed against `gastownhall/beads`):

- `bd mol pour`'s `cloneSubgraph` invokes `ensureSubgraphCustomTypes`, which auto-registers any non-built-in type it encounters in the subgraph by calling `EnsureCustomTypeInTx` and syncing the `custom_types` table.
- The cook-phase `stepTypeToIssueType` defaults unrecognized type strings to `TypeTask` for the in-memory enum, but the original step type string is preserved and used by the auto-registration step so the resulting bead carries the correct custom type.
- Net effect: pour will NOT error if `drain` is not pre-registered. The bead lands as type `drain` either way.

**So `/drain init` is operator-visibility-and-predictability, not a hard correctness gate.** Explicit registration ensures:

1. `bd types` lists `drain` before the first run (visibility for operators inspecting bd config).
2. The formula file is in `.beads/formulas/` (so `bd formula list` shows it; without this, pour would still need the file present).
3. No surprise auto-registration mutates `types.custom` mid-run.

**Defense-in-depth verification after pour**, since the auto-registration path is invisible:

```bash
ACTUAL_TYPE=$(bd show "$DRAIN_ID" --json | jq -r '.type')
[ "$ACTUAL_TYPE" = "drain" ] || {
  echo "Drain bead $DRAIN_ID landed as type=$ACTUAL_TYPE (expected drain); aborting." >&2
  exit 1
}
```

### Bootstrap — `/drain init`

Per-repo, idempotent, run once. The slash command's frontmatter declares the plugin-root-aware `cp` invocation in `allowed-tools` so `${CLAUDE_PLUGIN_ROOT}` resolves in the Bash subshell:

```yaml
---
description: Bootstrap the drain harness in this repo
allowed-tools: ["Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd types:*)", "Bash(bd formula list:*)", "Bash(mkdir -p .beads/formulas:*)", "Bash(cp -n \"${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.toml\" .beads/formulas/:*)"]
---
```

The body:

```bash
# 1. Register custom type idempotently
EXISTING=$(bd config get types.custom 2>/dev/null | sed -n 's/.*= "\(.*\)"$/\1/p')
echo "$EXISTING" | tr ',' '\n' | grep -qw drain \
  || bd config set types.custom "${EXISTING:+$EXISTING,}drain"

# 2. Copy formula into .beads/formulas/ (idempotent via cp -n)
mkdir -p .beads/formulas
cp -n "${CLAUDE_PLUGIN_ROOT}/.beads/formulas/formula-drain.toml" .beads/formulas/

# 3. Sanity check
bd types | grep -q drain && bd formula list | grep -q formula-drain
```

**Why `${CLAUDE_PLUGIN_ROOT}` with braces is load-bearing:** Claude Code expands `${CLAUDE_PLUGIN_ROOT}` only when (a) it appears inside an `allowed-tools` pattern AND (b) the Bash body uses the brace form `${CLAUDE_PLUGIN_ROOT}` (not bare `$CLAUDE_PLUGIN_ROOT`). Confirmed against existing plugins (`claude-plugins-official/ralph-loop`, `hookify`).

**Codex compatibility:** Codex's equivalent variable (if any) is harness-specific; if `${CLAUDE_PLUGIN_ROOT}` is empty in the Bash subshell, the `cp` resolves to a wrong path and silently no-ops. The skill documents a manual fallback for non-Claude-Code harnesses (operator copies the formula by hand).

Subsequent `/drain` invocations call into a read-only version of `/drain init`'s checks as pre-flight; missing assets produce `run /drain init first` and exit non-zero. Pre-flight does not mutate.

### Pre-flight (per-invocation, runs before `/goal` fires)

```text
1. Bootstrap verified — drain type registered + formula present.
   On miss: print "run /drain init"; exit. No mutation.
2. Mode arg valid — init | epic | set | cascade | resume.
3. Scope validation:
     epic mode    — bd show <epic-id> succeeds; has ≥1 open child.
     set mode     — each id resolves; none already closed.
     cascade mode — each seed resolves; none already closed.
4. Working tree clean — jj st (or git status --porcelain) empty.
5. Branch safety — refuse main/master.
6. Trust + hooks — both required for /goal. Fail with clear message if absent.
7. No overlapping drain — refuse **only when an in_progress drain's scope intersects this run's scope**, so drains of disjoint chains run concurrently. Enumerate active drains by type, then compare each one's `drain_scope` metadata token-by-token against this run's scope:

   ```bash
   bd list --type=drain --status=in_progress --json
   ```

   `--type=drain` filters reliably once the custom type is registered (guaranteed by pre-flight #1; verified against bd v1.0.4 — `bd list --type=drain` returns only drain beads, not the full list). Do **not** use `--label-pattern` or `--label-regex`: both are silently ignored by `bd list` in bd ≤1.0.4 (a pattern matching nothing returns *every* issue), so the original `--label-pattern 'drain:*'` query false-positived on any unrelated in_progress bead and refused every drain (see fhsk-4ut). Scope tokens are the epic id (epic mode) or the space-separated bead ids (set/cascade mode); two drains overlap iff they share a token. The per-iteration atomic `bd update <id> --claim` (step 5) is the backstop for the rare epic-parent-vs-child-in-a-set case that token intersection does not catch. Resume excludes the drain bead being resumed from this scan (it is already in_progress).

```text

### Post-flight (on `/goal` termination)

**Clean sentinel:**

```text
bd note <drain-id> "result: complete; iterations=<N>, duration=<ms>, tokens=<n>"
bd close <drain-id> --reason="drain completed cleanly"
Invoke dev-flow:finishing-a-development-branch
PushNotification "Drain <drain-id> complete (<N> beads closed)"
```

**Halt:**

```text
bd note <drain-id> "halt: <reason>; last-bead=<id>; iterations=<N>"
/goal clear  (explicit)
Leave drain bead --status=in_progress  (resumable)
PushNotification "Drain <drain-id> HALTED: <reason>"
Exit; operator triages via bd show <drain-id>
```

**Resume (`/drain resume <drain-id>`):** recovers `mode` and `scope` from the drain bead's structured metadata fields (`drain_mode`, `drain_scope`, `drain_started_at`) set at pour time — not by parsing the description prose. The recovery query is:

```bash
META=$(bd show "$DRAIN_ID" --json | jq '.metadata')
MODE=$(echo "$META" | jq -r '.drain_mode')
SCOPE=$(echo "$META" | jq -r '.drain_scope')
```

Resume then runs pre-flight steps 1–7 against the recovered scope and re-fires `/goal` with the same condition. Drain-bead notes carry forward; circuit breakers see prior rejection counts on iteration 1.

### Edge cases documented in the skill

| Case | Handling |
|------|----------|
| Codex compatibility | Skill intro notes `/goal` is Claude Code-only; Codex users get a manual loop recipe. |
| Context bloat | Skill recommends `/compact` when iteration count > ~30 OR tokens > 70% limit. `/goal` survives `/compact` (Stop hook, not prompt-bound). |
| Pushing commits | Subagents commit but do not push. Orchestrator pushes only at clean-sentinel via `finishing-a-development-branch`. On halt, operator pushes manually after triage. |
| Drain bead vs epic bead status | Orthogonal. Epic closes via `finishing-a-development-branch`; drain closes per its own lifecycle. |
| `bd dolt` server crashes mid-drain | Falls under halt #3 (VCS / harness failure). Drain bead stays in_progress; operator restarts server and `/drain resume`s. |
| PushNotification unavailable | Fall back to final-turn message text. |

## Files added / changed

### Added

| Path | Purpose |
|------|---------|
| `dev-flow/.beads/formulas/formula-drain.toml` | bd formula scaffolding the drain bead |
| `dev-flow/commands/drain.md` | `/drain` slash command (init / epic / set / cascade / resume) |
| `dev-flow/skills/draining-beads/SKILL.md` | Canonical pattern reference. Must cover (ordering left to the implementer): **Overview** of the harness; **When to use** (vs. `subagent-driven-development` and `executing-plans`); **Sentinel design** restating the three modes' sentinels; **Halt conditions** restating the three structural halts; **Lessons mechanism** restating the two-tier `bd note` convention; **Edge cases** — Codex fallback, context bloat, push timing, dolt-server crash, PushNotification unavailable; **References** linking back to this spec and companion specs. Skill body cites this spec as source of truth; skill content is reference, not duplicated specification. |

### Changed (additive only)

| Path | Change |
|------|--------|
| `dev-flow/skills/subagent-driven-development/SKILL.md` | Add a 3-line pointer in the "When to Use" section to `/drain` / `draining-beads` for autonomous runs |
| `dev-flow/skills/executing-plans/SKILL.md` | Add the same 3-line pointer |
| `dev-flow/plugin.json` | Register the new skill + command (if explicit registration is required by the marketplace; otherwise no change) |
| `dev-flow/AGENTS.md` | Mention the `/drain` workflow under "Dev-Flow Conventions"; defer halt-condition detail to the skill |
| `.claude-plugin/marketplace.json` | Surface the new skill + command in the Claude marketplace listing (if needed) |
| `.agents/plugins/marketplace.json` | Same for Codex marketplace listing (with the Codex-fallback note) |

## Testing strategy

| Layer | Test |
|-------|------|
| Formula validity | `bd formula show formula-drain` succeeds; `bd mol pour formula-drain --var mode=epic --var scope=fhsk-test --var started_at=2026-05-22T00:00:00Z --dry-run` returns a valid bead spec (the `--dry-run` flag is confirmed in `bd mol pour --help`) |
| `/drain init` idempotency | Run twice; second run no-ops; `bd types` shows `drain`; formula present |
| Pre-flight refusals | Dirty tree → refuse. main branch → refuse. Unknown mode → usage. Missing init → "run /drain init" |
| Drain bead lifecycle | `/drain epic` pours bead; `/goal` fires; on clean sentinel bead closes; on halt bead stays in_progress |
| Resume | After halt, `/drain resume <id>` re-fires `/goal` with original scope; iteration 1 sees prior rejection counts |
| Cross-platform | Manual: confirm Codex users see clear "not supported here" message; manual loop recipe usable |

## Open questions / future work

- **Per-iteration wisp children** — deferred. If drain-bead-notes audit proves too coarse, add a sub-formula `formula-drain-iter` whose wisps become children of the drain bead.
- **Squash old closed drains** — `bd mol squash` recipe for >30-day-old closed drains. Not v1.
- **Multi-repo drains** — current design is single-repo. If a drain spans repos, the operator runs separate `/drain` invocations; cross-repo coordination is out of scope.

## References

### Grounding traces (recorded as bd notes on fhsk-a67)

- **Holomush transcript `f3a83fe5`** (2026-05-22) — 26 `/loop autonomous` invocations + 248 bd ops; established the prompt-drift anti-pattern and the bead-queue runner pattern.
- **Claude Code binary** (`/Users/sean/.local/share/claude/versions/2.1.148`) — strings extraction confirmed `/goal` semantics: Stop-hook registration, `activeGoal` state, `goal_status` attachment, `met`/`sentinel` flags, trust + hooks gates.
- **DeepWiki `gastownhall/beads`** — custom types via `bd config set types.custom`; formula schema (top-level `formula`/`version`/`type`/`description` + `[vars]` + `[[steps]]`); `IssueType.IsValidWithCustom`; mol primitives (`pour` / `wisp` / `bond` / `squash` / `burn` / `distill`).
- **Reference formula** — `/Users/sean/gascity/.beads/formulas/mol-witness-patrol.formula.toml` — exemplar single-bead-formula carrying workflow content in step descriptions.
- **Dev-flow internal** — `subagent-driven-development/SKILL.md` (336 lines), `executing-plans/SKILL.md` (90 lines) — confirmed both drive bead iteration but lack an autonomy harness.

### Related specs

- `2026-05-14-dev-flow-beads-integration-design.md` — beads-first execution discipline; `plan-to-beads` materialization; this spec builds on its bd-as-source-of-truth premise.

### Rule references

- **Rule 5** (model selection per bead via `model:*` label) — defaults applied in step 7.
- **Rule 6** (design-bead lifecycle) — fhsk-a67 carries this spec's grounding traces.
- **Rule 7** (grounding before design) — probe + deepwiki + binary-strings recorded; context7 skipped (no external library).
<!-- adr-capture: sha256=4810ac56f4ddc90c; session=cli; ts=2026-05-22T12:43:01Z; adrs=fhsk-thw,fhsk-0o2,fhsk-rqh,fhsk-ce3,fhsk-0cd -->
