<!-- markdownlint-disable MD013 -->

# `dev-flow`: Beads Integration + Superpowers Fork Independence

**Date:** 2026-05-14
**Status:** Proposed
**Deciders:** Sean Brandt (`@seanb4t`)
**Supersedes:** —

## Overview

This spec defines a substantial restructuring of the development-workflow plugin in this repository:

1. **Fork independence.** The vendored `superpowers/` plugin (currently a sync-tracked fork of `obra/superpowers v5.1.0`) is rebranded to `dev-flow` and gains independence — upstream becomes inspiration, not source of truth.
2. **Beads-first execution discipline.** The `bd` issue tracker (Steve Yegge's plugin, already installed in this repo's marketplace) becomes the canonical mechanism for tracking multi-task work. Plans materialize into bead chains; execution skills pull from `bd ready`; finishing-a-development-branch reconciles bead state against code state.
3. **Lifted skills from holomush.** Three holomush workflow skills are adapted: `plan-to-beads` (formerly `bead-chain-from-plan`), `bead-create-smart`, and `handoff-prompt`.
4. **ADR capture subsystem.** A full Architecture Decision Record capture pipeline is lifted from holomush PR #3833: a skill (`capture-adrs`), a read-only sonnet agent (`adr-extractor`), a `PostToolUse` hook (`nudge-adr-capture`), and a durable lint check (`adr-doctor`).
5. **In-session review gates.** Two new adversarial read-only reviewer agents — `design-reviewer` (between brainstorming and writing-plans) and `plan-reviewer` (between writing-plans and plan-to-beads) — catch structural flaws before they cascade.

## Goals

- Decouple our development-workflow plugin from obra/superpowers' release cadence; keep upstream as a source of conceptual inspiration we cherry-pick from, not a verbatim tracking target.
- Make beads first-class in the workflow: every multi-task plan produces a bead chain; every long-running session has bd state as the durable source of truth.
- Eliminate duplicate state between plan documents and bead graph topology.
- Capture architectural decisions (ADRs) at the right moment in the workflow — after spec/plan stabilize, with full context (spec + plan + transcript window).
- Codify model selection (haiku/sonnet/opus) per bead so cost is intentional, not accidental.

## Non-goals

- Re-implementing bd functionality. We use bd as it ships and cooperate with its conventions.
- Building a generic agent dispatcher; `subagent-driven-development` already does that, we're just adding bd-awareness.
- Multi-tenant team workflows. This plugin is `fzymgc-house`-internal; ergonomics for solo + 1-2 collaborators only.
- Backwards compatibility with the existing `superpowers` plugin name (per user direction, larger break is acceptable).

## Rule 1: Specs and plans contain structure, not implementation

Specs and plans describe architecture, contracts, and interfaces. The *code* is left to the implementer.

**Allowed in specs/plans (structural / load-bearing):**

| Category | Examples |
|---|---|
| Schemas | Proto definitions, SQL DDL, YAML config shapes |
| Type contracts | Type signatures, interface definitions, exact field names + orderings |
| Service boundaries | Architecture diagrams, message shapes, RPC mode declarations (streaming vs unary) |
| Naming conventions | File paths, identifier names, label namespaces |

**Not allowed:**

- Function bodies
- Algorithm implementations
- Business logic / imperative code
- Pseudo-code that reads like implementation

**Why:** Implementers (sub-agents or future sessions) need structural details verbatim — they cannot safely infer "this RPC is server-streaming" or "this type has field ordering X" from prose. They also need implementation freedom. When specs duplicate implementation, work is duplicated and divergence risks compound. (See holomush failure mode: bead `holomush-jxo8.7.27` listed five RPCs by name without specifying streaming modes; implementer inferred unary, broke downstream beads, work redone.)

**Test:** If it defines structure (shape, contract, interface), include it. If it shows *how* to compute, leave it out.

## Rule 2: 3+ trackable tasks → epic

Plans are classified at `plan-to-beads` time:

| Task count | Bead structure |
|---|---|
| 3 or more | Parent epic + child task beads. Epic linkage via `--parent <epic-id>`. |
| 1-2 | Standalone task beads. No epic. `plan-reference` description points back. |
| 0 (design-only spec) | Skip bead creation. Plan exists as a reference document. |

## Rule 3: Use bd's structured fields; description carries narrative only

Tracked beads use `bd create`'s native flags. The `--description` field carries narrative only.

| Bead field | bd flag | Content |
|---|---|---|
| Title | positional or `--title` | Imperative-voice summary |
| Type | `--type task\|feature\|bug\|epic\|chore\|decision` | bd's built-in vocabulary |
| Parent | `--parent <epic-id>` | Hierarchical link |
| Priority | `--priority 0-4` | 0=critical, 2=default, 4=backlog |
| Labels | `--labels` | Namespaced tags (e.g. `aspect:security`, `area:jj`, `model:opus`) |
| Required skills | `--skills` | Dispatch routing hints (e.g. `jj`, `proto`, `migrations`) |
| Design link | `--spec-id <path>` + `--design <string>` or `--design-file <path>` | `--spec-id` is the spec doc path. `--design` and `--design-file` are siblings (one inline string, one read-from-file) for bead-specific design notes — use `--design-file` for anything >1 line. |
| Acceptance criteria | `--acceptance` | RFC2119 MUST/SHOULD checks |
| Verification | `--notes` | Concrete commands (e.g. `lefthook run pre-commit --all-files`, `uv run --with pytest pytest tests/`) |
| Dependencies | `--deps type:id` + `bd dep add` | Graph edges in bd, not duplicated in description |
| Fanout gates | `--waits-for` + `--waits-for-gate all-children\|any-children` | For dynamic dispatch waits |
| External ref | `--external-ref` | PR/issue/Linear URL |
| Description | `--description` / `--body-file` | **Narrative only:** Goal (one paragraph), Plan reference (with verbatim-read directive), Files touched (approximate), Out of scope (explicit non-goals) |

`bd create --validate` checks descriptions against bd's built-in section requirements per issue type. `bd config set validation.on-create warn` (or `block`) elevates this to project-default.

**Verification of bd flag inventory:** All flags listed in the table above were verified against `bd create --help` and `bd config --help` output on bd `v0.60.0` (the version installed at `~/.claude/plugins/marketplaces/beads-marketplace/plugins/beads/`) on 2026-05-14. Verified present: `--type`, `--parent`, `--priority`, `--labels`, `--skills`, `--spec-id`, `--design`, `--design-file`, `--acceptance`, `--notes`, `--deps`, `--waits-for`, `--waits-for-gate`, `--external-ref`, `--validate`, `--body-file`, `--description`, `--dry-run`. `bd config set validation.on-create warn|block` is mentioned in bd's `prime` workflow context output. Phase 1 (foundation rename) includes a re-verification step against the installed bd version at implementation time to catch any drift.

## Rule 4: No duplicate state

| State | Lives in |
|---|---|
| Graph topology (deps, parent epics) | bd's dep edges |
| Acceptance criteria | bd's `--acceptance` field |
| Design link | bd's `--spec-id` field |
| Verification commands | bd's `--notes` field |
| Bead status (open/in_progress/closed) | bd |
| Bead chain "structure" | bd (NOT a plan markdown section) |

**Implication:** the holomush-era `## Bead chain structure` plan-section convention is dropped. `plan-to-beads` reads the plan's task table directly; bd is the source of truth for the graph.

**Plan task table semantics (Rule 4 sub-clause):** The plan's task table is a **one-shot input** to `plan-to-beads`. After materialization, bd is the source of truth for what work exists and how it depends. The plan task table becomes historical record of intent at the moment of materialization. To handle re-runs cleanly:

- `plan-to-beads` detects already-materialized state via `bd list --spec-id <plan-path>` (or equivalent label match) and refuses to duplicate beads without explicit user opt-in (`--force-update`).
- Editing the plan task table after materialization does not retroactively change beads. The user must either (a) file follow-up beads manually via `bead-create-smart`, or (b) re-invoke `plan-to-beads --force-update` and review the diff.
- The plan markdown is not edited by `plan-to-beads`; bd state is the only thing that mutates. This preserves Rule 4 because the plan task table is read-once-at-materialization, not a living mirror of bd.

## Rule 5: Model selection on beads (label-driven, enforced at dispatch)

Beads carry an optional model hint via `--labels model:<haiku|sonnet|opus>`. Default is **sonnet** if no label.

**Use-case table:**

| Label | When | Examples |
|---|---|---|
| `model:haiku` | Mechanical, high-volume, low-judgment | Regex rename across N files, scaffold from template, generate test boilerplate, JSON manifest edits |
| `model:sonnet` (default) | Most implementation | New feature, bug fix, refactor with judgment, normal subagent task |
| `model:opus` | Hard reasoning, architecture, cross-cutting risk | Plan-reviewer dispatch, security-sensitive code, multi-file refactors with subtle invariants, debugging distributed-state bugs |

**Enforcement (MUST):**

- `subagent-driven-development` reads bead's `model:*` label, passes as `model` to `Agent` tool invocation.
- `executing-plans` honors the current bead's label for serial-execution session model and child `Agent` calls.
- `handoff-prompt` includes the model recommendation in briefing text.
- **Absence-of-label = sonnet.** No fallback to "highest available"; explicit default keeps cost predictable.

**Author-time discipline:**

- `plan-to-beads` proposes model labels heuristically based on task content (mechanical patterns → haiku; architecture / security keywords → opus; default sonnet). User reviews + overrides in dry-run preview.
- `bead-create-smart` accepts an explicit model arg; defaults to sonnet if omitted.

## Rule 6: The design bead — one bead spans the whole lifecycle

A single bead tracks design work from brainstorming through plan materialization. The bead's **type evolves** with the work: starts as `task` during design, promotes to `epic` at materialization time if there are 3+ child tasks, stays as `task` (with siblings) if 1-2 tasks, or closes if the work is design-only.

### Lifecycle

| Phase | Bead state | What happens |
|---|---|---|
| `brainstorming` opens | `--type=task --title="Design: <provisional>" --labels="phase:design"` | Created at session start; user opts out for throwaway exploration |
| spec drafted | `bd note <id> "Spec: <path>"` | Spec path recorded |
| design-reviewer rounds | `bd note <id> "design-review round N: <verdict> — <finding summary>"` | Each round's findings preserved as session-spanning audit trail |
| writing-plans completes | `bd note <id> "Plan: <path>"` | Plan path recorded |
| plan-reviewer rounds | `bd note <id> "plan-review round N: <verdict> — <finding summary>"` | Same pattern |
| capture-adrs files ADRs | `bd note <id> "ADRs: <bd-ids>"` | Decision-bead IDs recorded |
| `plan-to-beads` runs (3+ tasks) | `bd update <id> --type=epic --title="<feature name>"` + create children with `--parent <id>` | Bead **promotes to epic**; design-phase notes persist as epic audit trail |
| `plan-to-beads` runs (1-2 tasks) | `bd update <id> --title="<title of first plan task>"` (stays `task`); if a second plan task exists, `bd create --type=task` for it with no `--parent` (siblings, no epic) | Design bead inherits the title of the first plan task (top-to-bottom order in the plan's task table). The design-phase notes (review history, ADR IDs) travel with that first task bead. Second task is a separate bead with its own description; no parent epic since 1-2 tasks doesn't justify one. |
| `plan-to-beads` runs (0 tasks, design-only) | `bd close <id> --reason="Design-only; no implementation tracked"` | Design bead closes |
| Execution proceeds | (no design-bead changes; child beads carry the work) | |
| `finishing-a-development-branch` | (no design-bead changes; pre-flight checks operate on the epic) | |

### Verified bd behavior (sandbox test 2026-05-14, bd v0.60.0)

- `bd update <id> --type=<new-type>` accepts arbitrary type mutations (task ↔ epic ↔ task ↔ feature ↔ chore ↔ decision). No "promote" command needed.
- Notes added pre-promotion persist across type changes.
- Title, labels, status preserved across type changes.
- After promotion to epic, child beads attach normally via `--parent <id>`.
- Bd's JSON field for type is `issue_type` (not `type`) — cosmetic but worth knowing for `--json | jq` queries.
- **Untested in 2026-05-14 sandbox, must be re-verified during Phase 1:** does `bd update --type=<new>` preserve **dependency edges** (`bd dep add` relationships, `--waits-for` gates)? Rule 6 promotion depends on this being a no-op for edges. Add to Phase 1 verification checklist.

### Opt-out for ad-hoc work

`brainstorming` offers a one-prompt opt-out at session start ("Track this design in bd?"); default depends on prompt heuristics — opt out for clearly exploratory work ("let me try X to see what happens"), opt in for anything resembling a project ("I want to add Y feature"). If user opts out, the whole design-bead lifecycle is skipped; spec/plan files still get written but no bd state. `plan-to-beads` invoked later on such a spec/plan creates a fresh design-bead-then-promote at that point.

### Why this shape

- **One ID through the whole lifecycle.** Handoff briefings, ADR references, follow-up linkages all use a stable bead ID from design through execution.
- **`bd ready` surfaces in-flight design.** Without the design bead, mid-design work is invisible to bd until `plan-to-beads` fires. With it, "I'm designing X" is queryable like any other tracked work.
- **Session-spanning context for review loops.** Plan-reviewer NOT READY round 1 → revise → round 2 NOT READY → revise → round 3 READY. Without a design bead, the round-1 and round-2 findings live only in transcripts that may compact away. With it, `bd show <id>` shows the full review history.
- **No duplicate state.** Bd is the source of truth for design work-in-progress just like it's the source of truth for execution work-in-progress. Plan/spec files are the artifacts; the bead is the tracking record.
- **Portable across repos.** Uses only bd CLI features (verified against v0.60.0). Both fzymgc-house-skills and holomush can adopt the same lifecycle.

## Identity: `superpowers` → `dev-flow`

| Aspect | Current | Target |
|---|---|---|
| Plugin name | `superpowers` | `dev-flow` |
| Source directory | `superpowers/` | `dev-flow/` |
| Codex wrapper path | `plugins/superpowers/` | `plugins/dev-flow/` |
| Marketplace entry | `superpowers` in `.claude-plugin/marketplace.json` + `.agents/plugins/marketplace.json` | `dev-flow` |
| Release-please tracking | `superpowers-v*` tags | `dev-flow-v*` tags |
| Upstream relationship | "vendored fork, sync-tracked" | "originally derived from obra/superpowers v5.0.7; evolved independently with first-class jj + beads + plan-reviewer integration" |
| Sync script | `superpowers/scripts/sync-upstream` (auto-applies verbatim, diffs modified) | `dev-flow/scripts/scan-upstream` (changelog reader; surfaces upstream changes for selective cherry-pick review; never auto-writes) |
| `upstream-manifest.md` | Per-file sync status (verbatim/modified/local) | Divergence ledger — "what we did differently and why" — compounds over time as our identity |
| Per-skill `upstream:` frontmatter | Pinned to specific upstream version | Dropped; single attribution in plugin README |

The break is intentional and complete. Users with `superpowers` installed reinstall as `dev-flow`. No transition compatibility shim.

## Workflow Shape

```text
brainstorming  ──► OPEN design-bead (type=task)
  │
  ▼
spec drafted   ──► bd note: "Spec: <path>"
  │
  ▼
design-reviewer ──► bd note: "design-review round N: <verdict>"
  │                       │
  ▼                       │
 READY ◄──── NOT READY ◄──┘  (user revises spec, re-invokes brainstorming)
  │
  ▼
writing-plans
  │
  ▼
plan drafted   ──► bd note: "Plan: <path>"
  │
  ▼
plan-reviewer  ──► bd note: "plan-review round N: <verdict>"
  │                       │
  ▼                       │
 READY ◄──── NOT READY ◄──┘  (user revises plan, re-invokes writing-plans)
  │
  ▼
capture-adrs (auto-fire) ──► ADR files + decision beads
  │                       ──► bd note: "ADRs: <bd-ids>"
  ▼
plan-to-beads (conditional auto)
  │
  ├─ 3+ tasks   ──► PROMOTE design-bead to type=epic; file children with --parent
  ├─ 1-2 tasks  ──► design-bead stays type=task (becomes first task); optional sibling
  └─ 0 tasks    ──► CLOSE design-bead --reason="Design-only"
  │
  ▼
subagent-driven-development  |  executing-plans
                          │
                          ▼
                 finishing-a-development-branch
                          │
              ┌───────────┴──────────┐
              ▼                      ▼
      pre-flight: bd open?    on merge: bd close
```

### Trigger summary

| Step | Trigger | Initiator |
|---|---|---|
| `brainstorming` | User invokes | User |
| **Design bead opened** | Auto, at brainstorming start (with one-prompt opt-out for ad-hoc work) | Skill |
| `design-reviewer` | Auto, at end of brainstorming after spec written + self-review | Skill |
| `writing-plans` | User invokes after design-reviewer READY | User |
| `plan-reviewer` | Auto, at end of writing-plans | Skill |
| `capture-adrs` | Auto, at plan-reviewer READY (also: `nudge-adr-capture` hook for off-path edits; also: manual `/capture-adrs`) | Skill (primary), hook (safety net), user (manual) |
| `plan-to-beads` | Auto if plan has 3+ tasks; offer if 1-2; design-bead closes if 0 | Skill |
| **Design bead promoted to epic / kept as task / closed** | Auto at plan-to-beads based on task count | Skill |
| `subagent-driven-development` / `executing-plans` | User invokes | User |
| `handoff-prompt` | Manual only (cold-start session/agent for a specific bead — design or execution) | User |
| `bead-create-smart` | Manual only (ad-hoc beads: reviewer findings, bug reports, follow-ups) | User |
| `finishing-a-development-branch` | User invokes when implementation complete | User |

### Ordering invariants

- **Capture-adrs runs BEFORE plan-to-beads.** Decision beads exist before the epic, so the epic can have `bd dep add <epic> <decision-bead>` edges wired at creation time.
- **plan-reviewer READY is a prerequisite for capture-adrs auto-fire.** If the plan needs revision, ADRs would be premature.
- **plan-to-beads runs only on READY plans.** Materializing beads from a NOT-READY plan creates execution work against a broken target.

### Zero-candidate flows

When `capture-adrs` returns zero ADR candidates (e.g., a plan with no architectural decisions worth recording):

- Idempotency marker is **still stamped** on the spec/plan file (with `adrs=` empty). This prevents the `nudge-adr-capture` hook from re-firing on subsequent edits.
- `plan-to-beads` proceeds immediately. The "decision beads exist before epic" invariant is vacuously true (no decision beads to wire to the epic).
- No user prompt — silent pass-through.

### Reviewer NOT READY flows

When `design-reviewer` or `plan-reviewer` returns NOT READY:

- Calling skill (`brainstorming` or `writing-plans`) prints the findings inline and exits.
- **No automatic retry.** The user manually revises the spec/plan based on findings.
- The user re-invokes `brainstorming` (or `writing-plans`) to trigger another review pass.
- There is no max-iteration cap — review→revise loops are user-paced. If a verdict bounces between READY/NOT READY across runs, that's signal to broaden the design discussion rather than to keep iterating mechanically.

### Reviewer agent output contract

`design-reviewer` and `plan-reviewer` output MUST start with a machine-parseable verdict line before any prose:

```text
VERDICT: READY
```

or

```text
VERDICT: NOT READY
```

Calling skills (`brainstorming` and `writing-plans`) parse this first non-empty line via exact-match regex (`^VERDICT: (READY|NOT READY)$`) to branch on the verdict. Findings follow the verdict line in markdown, no contract required — they're for human (or implementer-LLM) consumption, not for skill branching.

If the verdict line is missing or unparseable, the calling skill treats it as NOT READY and prints the agent's full output for human review.

## Skill Inventory

### Lifted from holomush (with adaptation)

| Skill | Adapted from | Adaptation |
|---|---|---|
| `plan-to-beads` | `bead-chain-from-plan` | Drop `## Bead chain structure` section requirement. Read plan task table directly. Use full bd flag set (`--acceptance`, `--design`/`--spec-id`, `--notes`, `--deps`, `--labels`, `--skills`, `--parent`, `--type`). Conditional auto-invoke logic (0/1-2/3+ task buckets). Dry-run preview with `bd create --dry-run` before any state mutation. |
| `bead-create-smart` | same | Shrink dramatically — most of the 8-section description format collapses into bd flags. Becomes a thin helper for ad-hoc beads (reviewer findings, bug reports, follow-ups). |
| `handoff-prompt` | same | Adapt paths. Use bd's `--skills` field for dispatch routing hint. Compose with `bd prime` (bead-specific scope; prime is generic session context). Include model recommendation from bead's `model:*` label. |
| `capture-adrs` | `.claude/skills/capture-adrs/` (holomush PR #3833) | Adapt paths (`docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/adr/`). Preserve content-hash idempotency marker, per-candidate triage, triage-before-write invariant. |

### New (designed during this brainstorm)

| Skill / Agent | Role | Output contract |
|---|---|---|
| `design-reviewer` (agent) | Read-only adversarial review of spec; runs at end of `brainstorming`. Read-only sonnet. | READY \| NOT READY verdict + grounded findings (each finding cites `path:section` or `path:line`). |
| `plan-reviewer` (agent) | Read-only adversarial review of plan; runs at end of `writing-plans`. Read-only sonnet. | Same contract. |

### Lifted agents

| Agent | Adapted from | Adaptation |
|---|---|---|
| `adr-extractor` | `.claude/agents/adr-extractor.md` (holomush PR #3833) | Drop holomush-specific tools (probe, jj skill). Keep four-criterion worthiness test + transcript scan strategies + strict JSON output contract. |

### Lifted hooks

| Hook | Adapted from | Trigger |
|---|---|---|
| `nudge-adr-capture` | `.claude/hooks/nudge-adr-capture.sh` (holomush PR #3833) | `PostToolUse` on Write/Edit of paths under `docs/superpowers/specs/` or `docs/superpowers/plans/`. Emits `additionalContext` system reminder if no current `<!-- adr-capture: sha256=... -->` marker. |

### Lifted scripts

| Script | Adapted from | Wiring |
|---|---|---|
| `adr-doctor.sh` | `scripts/adr-doctor.sh` (holomush PR #3833) | Wired into `lefthook.yml` as a lint hook alongside `rumdl`. Pre-commit (lefthook) runs only on changed `docs/adr/**` files for perf; full CI pass runs all 12+ checks on every PR. |

### Modified existing dev-flow skills (formerly superpowers)

| Skill | Change |
|---|---|
| `brainstorming` | At session start: open the design bead (`bd create --type=task --title="Design: <provisional>" --labels="phase:design"` with one-prompt opt-out for ad-hoc work). Append notes at each transition (spec drafted, reviewer rounds, etc.). At end of skill body, after spec self-review: invoke `design-reviewer`. On READY, suggest `writing-plans`. |
| `writing-plans` | Append note to design bead: "Plan: <path>". At end of skill body: invoke `plan-reviewer`. On READY: auto-fire `capture-adrs`; then conditional auto-fire `plan-to-beads`. |
| `plan-to-beads` | Reads design bead ID from session context (or accepts as flag). Behavior per task count: 3+ → `bd update <design-bead-id> --type=epic --title="<feature name>"`, file children with `--parent <id>`. 1-2 → `bd update <id> --title="<feature name>"` (stays `task`), file optional sibling. 0 → `bd close <id> --reason="Design-only; no implementation tracked"`. |
| `finishing-a-development-branch` | Add pre-flight check: `bd list --status=open` filtered to current epic (or task-with-siblings group). If any open: `AskUserQuestion` to resolve (close / file follow-up / defer). After merge succeeds (Options 1/2/4): prompt `bd close <ids>` for beads whose work merged. |
| `subagent-driven-development` | When picking next task: prefer `bd ready --json | jq` to fetch next unblocked bead. Use bead's `--skills` for dispatch routing hint. Use bead's `model:*` label for Agent tool's `model` parameter (default sonnet absent label). Lifecycle: `bd update --claim` → work → `bd close`. |
| `executing-plans` | Similar bd-driven serial execution. Same model-label discipline. |
| `using-worktrees` | No content change beyond what landed in PR #63. Directory moves with the rename. |
| All other dev-flow skills (test-driven-development, dispatching-parallel-agents, etc.) | No content change. Just live at the new `dev-flow/` directory path. |

### Dropped

| Skill | Reason |
|---|---|
| `bead-chain-design` | Existed to generate the `## Bead chain structure` section in plans. We don't have that section (Rule 4). The skill's purpose vanishes. |

## ADR Capture Subsystem

Lifted from holomush PR #3833 (~2,000 lines, 5 artifacts). High-level shape:

### Components

| Component | Type | Lines (upstream) | Role |
|---|---|---|---|
| `capture-adrs` | Skill | ~217 | Orchestrator: resolve path → idempotency check → heuristic pre-scan → dispatch `adr-extractor` → per-candidate triage → write phase → stamp marker |
| `adr-extractor` | Agent (sonnet, read-only) | ~114 | Worthiness judgment + transcript scan; strict JSON output |
| `nudge-adr-capture.sh` | `PostToolUse` hook | ~111 | Emits `additionalContext` reminder when watched spec/plan edited without current marker |
| `adr-doctor.sh` | Lint script | ~235 | Durable health check (12+ named checks); pre-commit runs **on changed `docs/adr/**` files only** for perf; CI runs full pass on all of `docs/adr/`. |

### Worthiness criteria (verbatim from holomush; codified in dev-flow's AGENTS.md)

A candidate is ADR-worthy iff ALL four hold:

1. **Architectural** — not implementation detail.
2. **Has rejected alternatives** with real trade-off.
3. **Load-bearing** for future decisions or contributors.
4. **Not already captured** — must grep `docs/adr/` and `bd list --type decision` before proposing.

Score 0-4 by criteria-passed. Score < 4 is borderline (surfaced anyway, flagged).

### File-to-bead linkage discipline

- **Filename:** `docs/adr/<bd-id>-<slug>.md`. The bd-id is the canonical identifier; the slug is human-readable.
- **In-file linkage:** `**Decision:** <bd-id>` line under the `**Status:**` header.
- **Supersession:** `bd dep add <new-bd-id> <existing-bd-id> --type supersedes` + `bd close <existing-bd-id> --reason "Superseded by <new-bd-id>"` + rewrite old file's `**Status:**` to `Superseded by <new-bd-id>`.
- **README index:** `docs/adr/README.md` regenerated between `## Index` heading and the next `##`. Preserves any migration map between `<!-- BEGIN MIGRATION MAP -->` / `<!-- END MIGRATION MAP -->` sentinels (n/a for us — no legacy migration).

### Idempotency marker format

Appended as the spec/plan file's last line:

```text
<!-- adr-capture: sha256=<16-hex>; session=<short>; ts=<RFC3339>; adrs=<id1>,<id2>,... -->
```

- `sha256=...` = first 16 hex chars of SHA-256 over file content with trailing marker line stripped.
- Re-running on same content (matching SHA): no-op, exit with "Already captured" message.
- Re-running on **SHA mismatch** (file edited since last capture): re-runs the heuristic scan + extractor. If new candidates surface, normal triage flow. If **zero new candidates** (the typical case for typo fixes, prose edits, formatting changes): stamps a new marker with the current SHA and exits silently. This prevents the `nudge-adr-capture` hook from looping on every trivial edit.
- `optout=true` + `reason="..."` variant: aborts; `--re-run` does NOT override opt-out.

### Watched paths (for `nudge-adr-capture` hook)

**Repo-configurable.** Each repo adopting this skill sets its own watched-path globs at hook install time. fzymgc-house-skills defaults:

```text
docs/superpowers/specs/*.md
docs/superpowers/plans/*.md
```

Holomush (per its layout) would watch:

```text
docs/specs/*.md
docs/plans/*.md
docs/superpowers/specs/*.md
docs/superpowers/plans/*.md
```

Convention: paths are loaded from a config block at the top of the hook script (or from `dev-flow/AGENTS.md` if a centralized location is wanted). The hook ships with sensible defaults; repos override via config.

## Architecture & Interfaces

### Plugin layout (post-rename)

```text
dev-flow/
├── plugin.json
├── README.md                            # single attribution to obra/superpowers v5.0.7
├── agents/
│   ├── design-reviewer.md               # NEW
│   ├── plan-reviewer.md                 # NEW
│   └── adr-extractor.md                 # lifted
├── commands/
│   ├── review-design.md                 # NEW (slash invokes design-reviewer agent)
│   ├── review-plan.md                   # NEW
│   └── capture-adrs.md                  # NEW (slash for capture-adrs skill)
├── hooks/
│   └── nudge-adr-capture                # lifted (bash 3.2 compat)
├── references/
│   ├── vcs-preamble.md                  # existing (jj+git detection)
│   ├── upstream-manifest.md             # reframe as divergence ledger
│   └── ...
├── scripts/
│   ├── scan-upstream                    # renamed from sync-upstream
│   └── adr-doctor.sh                    # lifted
└── skills/
    ├── brainstorming/                   # modified (design-reviewer at end)
    ├── writing-plans/                   # modified (plan-reviewer + auto-fire capture-adrs + conditional plan-to-beads)
    ├── plan-to-beads/                   # NEW (lifted + adapted from bead-chain-from-plan)
    ├── bead-create-smart/               # NEW (lifted + shrunk)
    ├── handoff-prompt/                  # NEW (lifted + adapted)
    ├── capture-adrs/                    # NEW (lifted)
    ├── finishing-a-development-branch/  # modified (bd pre-flight + interactive close)
    ├── subagent-driven-development/     # modified (bd-driven + model-label dispatch)
    ├── executing-plans/                 # modified (bd-driven serial)
    └── using-worktrees/                 # unchanged content, new path
```

### Top-level repo changes

```text
.claude-plugin/marketplace.json          # rename superpowers entry → dev-flow
.agents/plugins/marketplace.json         # same
plugins/dev-flow/                        # rename from plugins/superpowers/
release-please-config.json               # superpowers-v* → dev-flow-v*
.release-please-manifest.json            # same
AGENTS.md                                # references to superpowers/ paths updated
tests/test_codex_marketplace.py          # EXPECTED_EXTRA_PATHS updated
tests/test_agent_guidance_docs.py        # any superpowers/ references updated
docs/adr/                                # new directory; README with index sentinels
```

### Skill interfaces

#### `plan-to-beads`

Inputs:

- Plan path (positional or detected from recent context).

Outputs:

- Bead manifest (dry-run, displayed to user).
- On user approval: `bd create` invocations + `bd dep add` edges.
- If 3+ tasks: an epic bead with child task beads parented to it.
- If 1-2 tasks: standalone task beads.
- If decision beads already exist for the plan's epic-worthy decisions (from prior `capture-adrs`): `bd dep add <epic> <decision-bead>` edges wired.

Side effects:

- bd state mutation (only after explicit user approval of dry-run manifest).
- Plan file: NOT mutated. (Rule 4 — no duplicate state.)

#### `bead-create-smart`

Inputs:

- Title (required).
- Type (default: `task`).
- Parent (optional epic ID).
- Acceptance criteria, design link, verification steps, dependencies, labels, skills, priority, model (all optional, all map to bd flags).
- Description body (narrative only).

Outputs:

- `bd create` invocation with flags assembled per Rule 3.
- Optional `bd dep add` if `--deps` not used.

#### `handoff-prompt`

Inputs:

- Bead ID (or chain root).
- Optional override for model recommendation.

Outputs:

- Self-contained text briefing covering:
  - Epic ID + target bead range
  - Workspace isolation instruction — defer to `dev-flow:using-worktrees` skill (handles git/jj via VCS detection; native `WorktreeCreate` hook preferred where available)
  - Spec + plan file paths (absolute)
  - Recommended model (from `model:*` label, default sonnet)
  - Required skills (from `--skills`)
  - Expected execution skill (`subagent-driven-development` or `executing-plans`)
  - Bd state recovery: `bd prime` + `bd show <id>`

#### `capture-adrs`

Inputs:

- Spec or plan path.
- Flags: `--dry-run`, `--re-run`.

Outputs (on accepted candidates):

- `bd create -t decision` invocations + decision-bead IDs captured.
- `docs/adr/<bd-id>-<slug>.md` files written.
- Supersession edges (`bd dep add --type supersedes`) if any candidate marked as superseding existing ADR.
- Idempotency marker appended to spec/plan file.
- `docs/adr/README.md` regenerated (index between sentinels).

#### `design-reviewer` / `plan-reviewer` (agents)

Inputs:

- Spec/plan path.

Outputs (strict format):

- Verdict: `READY` or `NOT READY`.
- Findings: list of grounded items, each with `path:section` (specs/plans use section anchors) and brief description.
- No fixes applied — read-only by construction.

### Bd command shapes (interfaces, structural)

```bash
# Create a task bead under an epic with full structured fields
bd create \
  --title "<imperative-voice summary>" \
  --type task \
  --parent <epic-id> \
  --priority 2 \
  --labels "model:sonnet,area:auth,aspect:security" \
  --skills "jj,proto" \
  --spec-id "docs/superpowers/specs/2026-05-14-foo.md" \
  --acceptance "<RFC2119 MUST/SHOULD checks>" \
  --notes "<verification commands>" \
  --deps "blocks:<other-bead-id>" \
  --description "<Goal paragraph. Plan reference with verbatim-read directive. Files touched. Out of scope.>" \
  --validate

# Add supersedes edge between two decision beads
bd dep add <new-decision-bd-id> <old-decision-bd-id> --type supersedes

# Discover next unblocked task (used by subagent-driven-development)
bd ready --json | jq '.[0]'

# Pre-flight check in finishing-a-development-branch
bd list --status=open --parent <epic-id> --json
```

## Implementation Order

Six phases. Each lands as a single PR (or splits if test feedback demands). **Phases are not all independent:** dependency graph is:

```text
Phase 1 (rename) ──┬─► Phase 2 (conventions)
                   ├─► Phase 3 (lifted skills)        ─┐
                   ├─► Phase 4 (ADR subsystem)        ─┼─► Phase 6 (modify skills)
                   └─► Phase 5 (review gates)         ─┘
```

Phases 1, 2 can land in parallel. Phases 3, 4, 5 can land in parallel after Phase 1. Phase 6 requires 3+4+5 merged because it wires them together in `writing-plans` / `brainstorming` / `finishing-a-development-branch`. Phase 6 is the serialization point — accept this; don't try to parallelize it. Each phase below has explicit verification steps.

### Phase 1: Foundation rename (low-risk)

- Rename `superpowers/` → `dev-flow/`.
- Update marketplace.json entries (both Claude and Codex).
- Rename `plugins/superpowers/` → `plugins/dev-flow/`.
- Update `release-please-config.json` + manifest.
- Update repo-root `AGENTS.md` (CLAUDE.md via symlink) references.
- Rename `scripts/sync-upstream` → `scripts/scan-upstream`; reframe in its own README + comments as changelog reader, not auto-applier.
- Drop per-skill `upstream:` frontmatter tags.
- Add single upstream attribution to `dev-flow/README.md`.
- Update `tests/test_codex_marketplace.py` EXPECTED_EXTRA_PATHS.
- Update `tests/test_agent_guidance_docs.py` if it references `superpowers/`.

**Risk:** Low. Mechanical rename; CI catches missed references.

**Verification:** `rg "superpowers/" -g '!docs/superpowers/specs/2026-03-16-*'` returns empty (the original fork-design spec is allowed to retain historical references). `uv run --with pytest pytest tests/test_codex_marketplace.py tests/test_agent_guidance_docs.py -v` passes. `bd create --help | grep -E "^[[:space:]]*--(type|parent|priority|labels|skills|spec-id|design|design-file|acceptance|notes|deps|waits-for|waits-for-gate|external-ref|validate|body-file|description|dry-run)\b"` returns all expected flags (re-verifies Rule 3's flag inventory against the installed bd). **Bd edge-preservation sandbox test:** create two task beads, add a dep edge between them, promote the dependent bead to `type=epic`, confirm `bd dep list` still shows the edge (validates Rule 6's promotion is non-destructive to graph topology).

### Phase 2: AGENTS.md conventions (low-risk)

- Codify Rules 1-5 in `dev-flow/AGENTS.md`.
- Reference from repo-root `AGENTS.md`.
- Add `bd config set validation.on-create warn` setup instruction.
- No code changes.

**Risk:** Trivial.

**Verification:** `rumdl check dev-flow/AGENTS.md` passes. The five rules appear under their canonical section headers (grep test). `bd config set validation.on-create warn` succeeds against a test bd database.

### Phase 3: Lift the holomush skills (medium-risk)

- Lift + adapt `plan-to-beads` (rename from `bead-chain-from-plan`).
- Lift + adapt `bead-create-smart` (shrink to flag-mapping helper).
- Lift + adapt `handoff-prompt`.
- Drop `bead-chain-design` (no equivalent).

**Risk:** Medium. Adapting `plan-to-beads` to use full bd flag set is non-trivial. Each skill needs path/convention substitution.

**Verification:** Dry-run test on a sample plan with 1, 2, and 5 task buckets — confirm conditional behavior (skip / standalone / epic + children). `plan-to-beads --dry-run` outputs valid `bd create` shell commands with all expected flags. Spec-id lookup test: run twice in a row on the same plan — second run detects existing beads via `bd list --spec-id` and refuses without `--force-update`. `bead-create-smart` smoke test: create a bead with `--type=task --acceptance="..." --notes="..."`, confirm `bd show` reflects all fields. `handoff-prompt` smoke test: generate briefing for a real bead, confirm model recommendation matches the bead's `model:*` label (or sonnet default).

### Phase 4: ADR capture subsystem (medium-high risk)

- Lift `capture-adrs` skill + adapt paths.
- Lift `adr-extractor` agent + drop holomush-specific tools.
- Lift `nudge-adr-capture.sh` hook + adapt watched-path globs.
- Lift `adr-doctor.sh` + wire into `lefthook.yml`.
- Set up `docs/adr/` directory with `README.md` index sentinels.
- Adopt selected RFC2119 invariants from holomush's spec (subset that survives translation).
- Lift the 15-fixture bash 3.2 test harness for the hook.

**Risk:** Medium-high. Most code, most invariants. Test harness lift is non-negotiable for hook reliability.

**Verification:** Lifted 15-fixture bash 3.2 test harness for the `nudge-adr-capture` hook passes on macOS-default bash. `adr-doctor.sh` runs the 12+ named checks against a sample `docs/adr/` tree and returns expected pass/fail per fixture. `capture-adrs --dry-run` on a sample spec with 2 contrived ADR candidates surfaces both via `AskUserQuestion` review; on a spec with 0 candidates, stamps the idempotency marker silently. Content-hash marker idempotency: re-running on same content is a no-op (matches "Already captured" message); re-running after a trivial edit (typo fix) with no new candidates stamps new SHA and silent-passes.

### Phase 5: New review-gate agents (medium-risk)

- Author `design-reviewer` agent (read-only sonnet, READY/NOT READY contract).
- Author `plan-reviewer` agent (same pattern).
- Add `/review-design <path>` and `/review-plan <path>` slash commands.

**Risk:** Medium. Adversarial reviewer quality depends on prompt construction; likely needs iteration after live use.

**Verification:** Manual smoke test — invoke `/review-design` on this very spec; confirm the agent emits `VERDICT: READY` or `VERDICT: NOT READY` as first non-empty line (parseable contract test). Run on a contrived bad spec (e.g., one missing the "Goals" section); confirm NOT READY with grounded findings. Run on a known-good spec; confirm READY.

### Phase 6: Modify existing dev-flow skills (highest-risk)

- `brainstorming` SKILL.md: invoke `design-reviewer` after spec.
- `writing-plans` SKILL.md: invoke `plan-reviewer`; on READY, auto-fire `capture-adrs`, then conditional auto-fire `plan-to-beads`.
- `finishing-a-development-branch` SKILL.md: pre-flight bd check + interactive close.
- `subagent-driven-development` SKILL.md: bd-driven task pickup + model-label dispatch.
- `executing-plans` SKILL.md: same for serial execution.

**Risk:** High. These are the highest-leverage skills; breaking them disrupts every workflow. Land AFTER phases 1-5 so supporting infrastructure exists.

**Verification:** End-to-end dogfood — run a real `brainstorming` session on a small project, confirm `design-reviewer` auto-fires at end and emits a parseable verdict. Continue to `writing-plans`, confirm `plan-reviewer` auto-fires, then `capture-adrs` auto-fires, then `plan-to-beads` conditionally auto-fires. Bd state after run matches expected (epic + children for 3+ tasks, standalone for 1-2). `subagent-driven-development` honors `bd ready` ordering and bead `model:*` labels. `finishing-a-development-branch` pre-flight finds open beads in the epic and prompts interactively.

## Degraded-mode behavior

### `bd` unavailable or uninitialized

If `bd --version` fails or `bd doctor` reports a broken state at the moment a skill needs bd:

- `plan-to-beads`, `bead-create-smart`, `capture-adrs` (decision-bead creation step), `finishing-a-development-branch` (pre-flight): **bail with a clear error message** ("bd CLI unavailable or database not initialized; run `bd init` or check `bd doctor`. Skill cannot proceed."). Do NOT silently skip the bd step — that creates the divergence Rule 4 is designed to prevent.
- `subagent-driven-development`, `executing-plans`: degrade to plan-task-driven mode (read plan task table directly, dispatch without bd state). Warn loudly but allow proceeding so single-shot work isn't blocked by tooling state.
- `capture-adrs` ADR-file writing (no bd dependency): proceeds normally; the decision bead creation step warns and stamps a placeholder ID in the file that the user can reconcile later.
- The `nudge-adr-capture` hook silently no-ops if bd is unreachable — it's a nudge, not a gate.

### Hard prerequisite

This integration treats bd as a hard prerequisite for tracked work. The repo's `AGENTS.md` already mandates it. If bd is broken in a worktree, the user fixes it before invoking workflow skills.

## Migration & in-flight work

This rebrand is a hard break (per user direction). Migration discipline:

- **In-flight specs/plans under `docs/superpowers/specs/` and `docs/superpowers/plans/`**: continue using the existing conventions (no `## Bead chain structure` section removal required mid-flight). New plans use the new conventions.
- **In-flight beads created under the `superpowers` plugin name**: unaffected by the rename — bead state in bd's database doesn't reference plugin names; only the skills that operate on beads change.
- **Existing `plugins/superpowers/` Codex wrapper**: replaced by `plugins/dev-flow/` in Phase 1 atomically. Codex users reinstall.
- **Conventional Commits scope**: commits previously scoped `superpowers` → use `dev-flow` going forward. Historical commits retain their original scope (no rewrites).
- **`docs/superpowers/specs/` and `docs/superpowers/plans/` directories**: kept as-is in Phase 1 (don't rename docs paths even though the plugin is renamed). Rationale: specs and plans are repo-level documentation about work, not plugin-specific; the `superpowers/` directory prefix is historical and breaking it would invalidate every existing cross-reference in those docs. Treat as an accepted naming inconsistency; document it in `dev-flow/AGENTS.md`.

## Risks & Open Questions

| Risk | Mitigation |
|---|---|
| Phase 1 misses a cross-reference to `superpowers/` | Existing test suite greps for path; CI catches most. Manual `rg superpowers` sweep before commit. |
| `plan-to-beads` mishandles bd flag set | Heavy dry-run testing; `bd create --dry-run` exists upstream. Develop against a sandboxed test bd database. |
| ADR `nudge-adr-capture` hook becomes noisy | Idempotency content-hash marker is load-bearing — must lift verbatim. 15-fixture test harness catches regressions. |
| Modifying existing skills breaks in-flight workflows | Each skill edit is a separate file; PR can land one-at-a-time inside the phase if needed. Backwards-incompatible? Acceptable — fork-harder rationale. |
| Model-label adoption inconsistency | Post-MVP: extend `adr-doctor`-style lint to warn on beads without model labels. Or rely on bd's `validation.on-create` to enforce. |
| `design-reviewer` and `plan-reviewer` agent quality | Iterate after live use. Start with conservative criteria; loosen if too noisy. |
| Upstream cherry-pick discipline atrophies | Document the `scan-upstream` workflow in `dev-flow/README.md`. Schedule a quarterly "review upstream changelog" calendar reminder. |

### Open questions (deferred)

- **`bd config validation.on-create warn` or `block`?** `warn` is safer for solo work; `block` is stricter. Default to `warn`, escalate if discipline drifts.
- **Do we want a `decision-reviewer` agent** to validate ADR worthiness during `capture-adrs`? The 4-criterion test is encoded in `adr-extractor` already. Probably no — the extractor IS the worthiness judge.
- **Should `handoff-prompt` write the briefing to `bd note <id>` automatically** so it persists alongside the bead? Possibly. Defer to live-use feedback.
- **Should `plan-to-beads` support a `--no-execute` flag** that outputs `bd create` shell commands without invoking them? Yes (already in its design — emit shell, user pipes to `bash` if approved). Confirm during Phase 3.

## References

- Holomush PR #3833 — ADR Capture skill + hook + agent + bd-id migration (the foundational lift)
- Holomush CLAUDE.md — Plan → Bead Chain convention, Pre-Push Review Gates
- Holomush skills: `bead-chain-design`, `bead-chain-from-plan`, `bead-create-smart`, `handoff-prompt`
- `bd` plugin (Steve Yegge v0.60.0) — installed in this repo's marketplace; provides the CLI surface this design builds on
- `obra/superpowers v5.0.7` — original ancestor of our `superpowers/` fork; soon to be rebranded as `dev-flow` with v5.0.7 as the cited origin point
- This repo's PR #63 — superpowers v5.1.0 sync (last fork-tracked sync; future syncs become selective cherry-picks via `scan-upstream`)
