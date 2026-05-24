<!-- design-bead: fhsk-a49 -->

# `/drain` `/goal` Handoff Redesign — Cold-Boot Worker Contract

**Status:** Draft (brainstorm output, pending design-reviewer)
**Date:** 2026-05-24
**Design bead:** `fhsk-a49`
**Supersedes:** §"Three-piece structure" (lines 54–56) of
`docs/superpowers/specs/2026-05-22-drain-skill-design.md`

## Overview

`/drain` drives autonomous bead iteration through Claude Code's `/goal`
Stop-hook built-in. The original design embedded the entire 12-step iteration
body **inside the `/goal` condition string**. Two facts discovered after that
design make the approach unsound:

1. **`/goal` takes a *condition*, not a prompt body.** Per the official docs
   (`code.claude.com/docs/en/goal.md`), the argument is a checkable predicate
   with a documented **4,000-character limit**, re-fired as a user message each
   Stop and evaluated for `met` by a fast (Haiku) judge that reads only the
   conversation transcript. The current iteration-body template measures
   **3,857 chars — 96% of the cap — before** `$DRAIN_ID`/`$EPIC_ID`/`$SCOPE`/
   `$SENTINEL` substitution and before any per-run additions. Real runs have
   visibly exceeded it. Over-limit conditions risk silent truncation of the
   tail steps (close / rejection handling / VCS verify / re-fire).

2. **`/goal` is a user-only built-in.** There is no `SlashCommand` tool for it,
   and built-ins execute only from user input. **No skill, in any session, can
   invoke `/goal`.** The current `drain.md` "Phase D — Fire `/goal`" is
   therefore fiction: the agent emits `/goal …` as output text that never
   executes as a command. A **user** (now) or an **external driver** — a
   cmux/tmux `send-keys` pane or a programmatic Agent SDK prompt submission
   (`query({prompt: "/goal …"})`), future — must submit the `/goal` turn.

This redesign makes the skill *teach and use `/goal` correctly*: the condition
becomes a small **self-contained cold-boot pointer**, the **drain bead** is the
cross-session handoff carrier, and the **iteration protocol** lives in the
`draining-beads` skill where a worker loads it on boot.

## Goals

- Keep the `/goal` condition far under the 4,000-char cap (target < 1,500),
  with a clean one-line sentinel predicate for the evaluator.
- Support a **cold worker**: a fresh Claude Code session, in the same jj
  workspace as the controller, that inherits no context and boots entirely
  from durable state (drain bead + skill) plus the `/goal` condition.
- Make the skill explicitly teach the control model: `/goal` is user-only; the
  skill emits a condition, it never fires one.
- Carry the worker handoff on the **drain bead**, not a temp file.
- Preserve the existing lessons mechanism, sentinels, halt conditions, and the
  `subagent-driven-development` inner loop unchanged.

## Non-goals

- **Controller auto-dispatch of workers** — a cmux/tmux `send-keys` pane, or a
  programmatic Agent SDK prompt submission (`query({prompt: "/goal …"})`). Leave
  room for it; do not build it. These are the paths to submit the `/goal` turn
  without a human, and are deferred to future work.
- Changing the two-tier lessons mechanism (ADR `fhsk-ce3` stands).
- Changing sentinel predicates or the three structural halt conditions.
- Changing the `subagent-driven-development` per-iteration mechanics.

## Background: how `/goal` actually works

Grounded via `claude-code-guide` against `code.claude.com/docs/en/goal.md` and
binary `2.1.148` (traces on `fhsk-a49`):

- `/goal <condition>` registers a session Stop hook. Each Stop re-injects the
  condition as a user message and a fast judge sets `goal_status.met` from the
  transcript. `/goal` (no arg) shows status; `/goal clear` removes it.
- The condition is capped at **4,000 characters** (observed via binary
  `2.1.148` string inspection, not stated in public docs — the length-guard
  test below provides margin regardless of the exact cap).
- The judge **does not run commands or read files** — it evaluates only what
  the transcript contains. The checkable predicate must be *in the condition*,
  and the worker must *report* its result each turn.
- The active goal **survives `/compact`** (it is a hook registration, not a
  prompt-bound construct) and carries across `--resume`/`--continue`.
- There is **no `@file` / file-reference syntax** for conditions.
- The agent **cannot self-invoke it mid-turn**: no `SlashCommand` tool exposes
  `/goal` to the agent's toolbox. It executes only from a submitted turn —
  interactively by a human, or programmatically via the Agent SDK
  (`query({prompt: "/goal …"})`), Remote Control, or a cmux/tmux driver.

## Architecture: a three-way split

| Carrier | Holds | Lifetime / scope | Worker reads via |
|---|---|---|---|
| `/goal` **condition** | boot pointer + the sentinel predicate | re-fired each Stop | (submitted as the worker's first input) |
| **drain bead** | mode, scope, sentinel, workspace, lessons, rejections | durable, session- and workspace-agnostic | `bd show <drain-id> --json` |
| **`draining-beads` skill** | the 12-step iteration protocol + control-model guidance | installed via plugins; loaded once per worker session | `Skill(dev-flow:draining-beads)` |

Operational instructions live in the skill; run-specific state lives in the
bead; only the predicate + boot pointer live in the condition.

### Control model

```text
Controller session                         Worker session (fresh `claude`)
------------------                         --------------------------------
/drain epic <id>      ── creates+stamps ─▶ (drain bead in shared bd DB)
  emits /goal <cond>  ── operator copies ─▶ user submits:  /goal <cond>
  (STOPS — cannot                              │ iteration 1 cold-boots:
   fire /goal)                                 │   invoke skill → bd show →
                                               │   cd workspace → run 1 bead →
                                               │   report sentinel
                                               ▼ Stop hook re-fires <cond> …
```

The controller and worker are **different Claude sessions in the same jj
workspace**. The worker inherits no controller context; the `/goal` condition
plus durable state is its entire input. A human submits the `/goal` turn today;
a cmux/tmux driver may submit it later (out of scope).

## The drain bead as worker briefing

`bd show <drain-id> --json` is the worker's complete assignment. Existing
fields stay; two are added.

| Field | Storage | Purpose | Status |
|---|---|---|---|
| `drain_mode` | metadata | mode dispatch (epic/set/cascade) | exists |
| `drain_scope` | metadata | scope ids | exists |
| `drain_started_at` | metadata | audit | exists |
| `drain_workspace` | metadata | dir to `cd` into before any bd/jj/file op | **new** |
| `drain_sentinel` | metadata | human-readable predicate; lets `worker`/`resume` regenerate the condition without recomputation | **new** |
| `lesson:` / `rejection:` / `halt:` | notes | forward-applied lessons, circuit-breaker counts, halt audit | exists |

## The `/goal` condition template

Substituted at emit time with `<DRAIN_ID>` and `<SENTINEL>` (≈330 chars):

```text
Drain worker for bead <DRAIN_ID>: invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to that workspace before
any bd/jj/file op. Execute exactly ONE ready bead this turn per the protocol,
then stop. Goal met when: <SENTINEL>.
```

`<SENTINEL>` is the actual predicate (e.g. *"all beads under epic
holomush-9mxr are closed"*), **not** "see the bead" — the judge needs the
predicate in the condition text, and the worker reports its sentinel-check
result (step 1) for the judge to match.

The re-fired condition always says "invoke the skill"; the worker reloads it
only if not already in context (true on iteration 1 and after `/compact`),
giving automatic post-compaction recovery without per-iteration waste.

## Where the protocol lives, and how the files change

### `draining-beads` skill (grows) — the worker's executable home

- The canonical **12-step iteration protocol**, relocated from
  `drain.md`, phrased as "you are the worker; do exactly one iteration."
- A new **"Using `/goal` correctly"** section: `/goal` is user-only and the
  skill never fires it; the controller/worker split; the self-contained
  condition contract; the cold-boot sequence; post-`/compact` recovery.
- Unchanged: sentinel design, halt conditions, lessons mechanism, edge cases.

### `drain.md` (shrinks) — a pure setup/emit command

- Phase A pre-flight: unchanged.
- Phase B create+stamp bead: also stamps `drain_workspace` + `drain_sentinel`.
- Phase B stamps `drain_workspace` as the **absolute path to the jj workspace
  root** the worker must `cd` to (revisit relative-vs-absolute when cmux/tmux
  dispatch lands — see open questions).
- Phase C compose sentinel: unchanged (now also persisted to the bead).
- **Phase D reframed** from "Fire `/goal`" to "**Emit** the `/goal <condition>`
  (with `<DRAIN_ID>`/`<SENTINEL>` substituted) + launch instructions, then
  stop." The command must not attempt to invoke `/goal`.
- The `## Iteration body` block is **deleted** (lives in the skill).
- New `worker <drain-id>` mode and reframed `resume <drain-id>` mode both
  regenerate the condition from the bead and emit it. `resume` recovers a
  *halted* run (inspects `halt:` notes first); `worker` attaches to a *live*
  drain.

Codex parity: a Codex worker reads the same skill protocol + bead and runs the
loop manually (Codex has no `/goal`) — the existing documented fallback, now
pointed at the skill instead of a deleted command body.

## Approach selection: bead+skill (A) with file fallback (B)

The redesign rests on one unproven assumption: that a cold worker, given only
the short condition, reliably loads the skill and runs a full iteration. The
**first implementation task is an empirical spike** that decides A vs B.

**Spike:** fresh `claude` session → submit `/goal <condition>` against a
throwaway test drain bead → observe whether it (1) invokes the skill,
(2) `bd show`s the bead, (3) `cd`s to the workspace, (4) runs exactly one ready
bead, (5) reports the sentinel, (6) re-fires and iterates; then (7) survives a
`/compact` and re-bootstraps.

- **Pass → Approach A** (skill-resident protocol, no file).
- **Fail → Approach B**: materialize a gitignored `.drain/<drain-id>.md` (viable
  because controller and worker share the workspace) holding the protocol, and
  point the condition at a `Read` instead of a `Skill` invoke. Everything else
  is identical. Adds a `.gitignore` entry for `.drain/`.

## Decisions (ADR-worthy — flag for `capture-adrs`)

1. **Iteration protocol lives in the `draining-beads` skill**, not the `/goal`
   condition. Reverses §54–56 of the 2026-05-22 spec (part of harness-split
   ADR `fhsk-0o2`): the "keep it cached by embedding" rationale is moot (skill
   loads once per worker session) and embedding is untenable under the 4K cap.
2. **The `/goal` condition is a self-contained cold-boot pointer** carrying only
   the boot instruction + the sentinel predicate.
3. **The drain bead is the cross-session handoff carrier** (not a temp file);
   gains `drain_workspace` + `drain_sentinel`.
4. **The skill never fires `/goal`.** Setup commands emit the condition for a
   user/driver to submit. This is a correctness statement about a user-only
   built-in, not a stylistic choice.

## Testing strategy

- Deterministic: `drain.md` stamps `drain_workspace`/`drain_sentinel`
  correctly; the emitted condition substitutes `<DRAIN_ID>`/`<SENTINEL>` and
  asserts **length < 1,500 chars** (regression guard against 4K creep).
- Behavioral: the cold-boot spike above (candidate for a `drain` eval).
- Docs: `rumdl` on changed markdown; existing hook test suite stays green.

## Files added / changed

| File | Change |
|---|---|
| `docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md` | **added** (this spec) |
| `dev-flow/skills/draining-beads/SKILL.md` | + relocated 12-step protocol; + "Using `/goal` correctly"; update overview/architecture; fix stale cross-refs (the "12-step body embedded in `commands/drain.md`" line and the 2026-05-22 "source of truth" pointer) |
| `dev-flow/commands/drain.md` | Phase B stamps new fields; Phase D emit-not-fire; delete iteration body; add `worker` mode; reframe `resume` |
| `.gitignore` | **only if** fallback B selected (`.drain/`) |
| `dev-flow/AGENTS.md` | one-line mention of `worker` mode |

## Open questions / future work

- **Controller auto-dispatch via cmux/tmux** (`send-keys` of the `/goal`
  condition into a worker pane) — the only no-human automation path; design
  leaves room but does not implement.
- Whether `drain_workspace` should be absolute or workspace-relative once
  cmux/tmux dispatch lands (a driver may launch the worker from elsewhere).

## References

### Grounding traces (recorded as bd notes on `fhsk-a49`)

- `grounding/claude-code-guide`: `/goal` official doc — condition (≤4,000 char
  predicate), user-only built-in, judge reads transcript only, survives
  `/compact`, no `@file` syntax.
- `grounding/probe+spec`: 2026-05-22 spec §54–56 embedded the body for cache
  reasons and predates knowledge of the 4K cap; measured body = 3,857 chars.

### Related specs

- `docs/superpowers/specs/2026-05-22-drain-skill-design.md` (original design)

### ADR references

- `fhsk-thw` (`/goal` over `/loop`) — unchanged
- `fhsk-0o2` (harness split) — partially superseded by Decision 1
- `fhsk-ce3` (lessons in bd notes) — unchanged
- `fhsk-0cd` (`/drain init` explicit) — unchanged
<!-- adr-capture: sha256=bf1d57d79e596a6d; session=cli; ts=2026-05-24T17:17:01Z; adrs=fhsk-eqt,fhsk-zds,fhsk-e4i -->
