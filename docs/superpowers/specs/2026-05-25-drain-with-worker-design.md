<!-- design-bead: fhsk-jmn -->

# `/drain-with-worker` — Autonomous Worker-Pane Launcher

**Status:** Draft (brainstorm output, pending design-reviewer)
**Date:** 2026-05-25
**Design bead:** `fhsk-jmn`
**Fulfills:** the deferred "controller auto-dispatch via l/tmux driver" from
ADR `fhsk-e4i` and ADR `fhsk-zds` (the `drain_workspace` metadata was added
specifically to "pave the way for a future l/tmux driver").

## Overview

`/drain` mints a typed drain bead (Phases A–C) and **emits** a thin `/goal`
condition (Phase D), then stops — by design, because `/goal` is a user-only
built-in that no skill can fire (ADR `fhsk-e4i`). Today the operator must then
either paste that condition into a worker session by hand, or run holomush's
**local** `drain-pane` skill, which launches a separate `claude` worker in a
detached cmux pane, fires the `/goal` there, and arms a
stall-watchdog so the drain self-heals while the operator walks away.

That `drain-pane` skill lives only in `holomush/.claude/skills/drain-pane/` —
it was never lifted into the marketplace, and it carries a latent bug in its
bead-type prerequisite check (see [Bug fix](#bug-fix)). This spec lifts it into
`dev-flow` as a first-class, bug-fixed command and wires a clean handoff from
`/drain`.

The concrete multiplexer is **cmux** (`/opt/homebrew/bin/cmux`, "control cmux
via Unix socket") — a CLI, not a skill. The launch sequence depends only on its
`new-pane`, `send`, `send-key`, and `read-screen` subcommands (all verified
present), addressing panes by `surface:N` refs.

## Goals

1. Lift the launch + watchdog mechanics into `dev-flow` as the single source of
   truth, reusable from more than one entry point.
2. Expose worker launch as a **separate command** `/drain-with-worker <drain-id>`
   (not a `--with-worker` flag) for execution reliability and zero regression on
   the large multi-mode `drain.md`.
3. Gate every launch behind an explicit **AskUserQuestion confirm** — never
   auto-fire a `--dangerously-skip-permissions` worker silently.
4. Make `/drain` hand off cleanly: when `cmux` is present, offer launch; when
   absent, emit the manual `/goal` condition.
5. Fix the bead-type prerequisite bug as part of the lift.

## Non-goals

- **No `/drain --with-worker` flag.** Folding a 137-line cmux-launch + watchdog
  procedure as a conditional branch onto the 519-line, three-mode × three-scope
  `drain.md` risks silent skips in a prompt-expanded command. Deferred as
  possible thin sugar only if one-shot ergonomics later prove necessary (YAGNI).
- **No set/cascade support (v1).** The watchdog stall-probe is epic-specific
  (children share the `<epic>.` id prefix). `/drain-with-worker` fail-fast
  rejects non-epic drains; set/cascade still drain via the manually-pasted
  `/goal` condition.
- **No handoff file.** The worker reads its entire assignment from
  `bd show <drain-id> --json` (preserves ADR `fhsk-zds`).
- **No holomush changes in this repo's PR.** Deleting the local `drain-pane`
  skill and redirecting it is a separate follow-up bead in that repo.

## Architecture

### Three pieces

| Piece | Path | Responsibility |
|-------|------|----------------|
| Reference | `dev-flow/references/drain-with-worker.md` | Single source of truth: cmux launch sequence, worker `/goal` condition template, background stall-watchdog loop, gotchas table. |
| Command | `dev-flow/commands/drain-with-worker.md` | Thin entry point: prerequisite validation → AskUserQuestion confirm gate → follow the reference. |
| Handoff | `dev-flow/commands/drain.md` (additive only) | After Phase D: probe `command -v cmux` → offer launch / emit copy-paste command / emit manual `/goal`. |

### `/drain-with-worker <drain-id>` flow

1. **Prerequisites (refuse early).** Read `B=$(bd show "$DRAIN_ID" --json)`.
   - `.[0].issue_type == "drain"` else reject "Not a drain bead".
   - `.[0].status == "in_progress"` else reject "already closed?".
   - `.[0].metadata.drain_mode == "epic"` else reject (set/cascade need a
     different watchdog probe — not yet specified).
   - `.[0].metadata.drain_workspace`, `.drain_scope`, and `.drain_sentinel` all
     non-empty. `drain_scope` is **required** — the watchdog's
     `startswith("<scope>.")` child filter degenerates to matching every bead if
     `$SCOPE` is empty, so an absent scope must refuse, not warn. (Source skill
     extracts all three: holomush `SKILL.md` lines 47–49.)
   - `command -v cmux` succeeds else reject "cmux not on PATH".
2. **Confirm gate (AskUserQuestion).** Show the launch plan (pane → cd
   `<workspace>` → direnv → `claude --dangerously-skip-permissions` → fire
   `/goal`, then arm watchdog). Options: **Launch** / **Cancel**. Proceed only
   on Launch. Skipped only on the pre-confirmed path (see below).
3. **Follow the reference** — execute the launch sequence and arm the watchdog.

**Pre-confirmation calling convention.** There is exactly one way the confirm
gate is skipped: `/drain`'s "Launch now" branch (below) follows
`references/drain-with-worker.md` **inline**, having already confirmed via its
own AskUserQuestion. The command frontmatter's `allowed-tools` (below) is the
only contract; there is no `--yes` flag, env var, or sentinel file. When
`/drain-with-worker` is invoked directly as a slash command, the gate always
fires.

The new command's `allowed-tools` frontmatter (each existing `dev-flow/commands/`
command declares this explicitly):

```yaml
allowed-tools: ["Read", "AskUserQuestion", "PushNotification",
  "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)", "Bash(command -v cmux:*)",
  "Bash(cmux:*)", "Bash(direnv:*)", "Bash(sleep:*)"]
```

### `/drain` handoff (additive)

After Phase D emits the `/goal` condition, `/drain` probes `command -v cmux`:

- **cmux present** → AskUserQuestion: "Launch the autonomous worker for
  `<bead>` now?" with options **Launch now** / **Just give me the command** /
  **Not now**.
  - *Launch now* → follow `references/drain-with-worker.md` for `<bead>` inline.
    This prompt **is** the confirm gate; the launch does not re-prompt.
  - *Just give me the command* → print copy-paste `/drain-with-worker <bead>`.
  - *Not now* → print the command for later + the manual `/goal` fallback.
- **cmux absent** → emit the manual `/goal` condition for paste into a worker
  session (current behavior, unchanged).

The launch *prose* lives **only** in the reference; `/drain`'s addition is a
short probe → ask → follow-reference branch, not inlined procedure. But because
"Launch now" executes the reference under `/drain`'s own command context, its
`allowed-tools` frontmatter must gain the launch+watchdog toolset. Required
delta to `drain.md` `allowed-tools` (additive — no existing entry removed):
`"AskUserQuestion"`, `"PushNotification"`, `"Bash(command -v cmux:*)"`,
`"Bash(cmux:*)"`, `"Bash(direnv:*)"`, `"Bash(sleep:*)"`, `"Bash(jq:*)"`. (`Read`
and `Bash(bd show:*)`/`Bash(bd list:*)` are already present. Note `Bash(jq:*)` is
*also* absent from `drain.md`'s current `allowed-tools` despite existing modes
already using `jq` — a pre-existing latent omission this delta incidentally
fixes; it is not new surface introduced by this feature.) Omitting this delta
yields a command that blocks at the AskUserQuestion call or the cmux probe — so
it is a required, not optional, part of the edit. This is the deliberate cost of
the "offer to launch inline" decision; the prose stays lean even though the tool
whitelist grows.

### Launch sequence (in the reference)

Each step verified before the next (each failed live when chained or assumed):

1. `cmux new-pane --type terminal --direction right --focus false` → capture
   `surface:<N>`.
2. **`cd` as its own verified step** — `send "cd $WORKSPACE"` → `send-key Enter`
   → `send "pwd"` + Enter → `read-screen` and confirm pwd. Never chain
   `cd X && claude`.
3. `direnv allow` → confirm `direnv: loading` (a fresh split hits a blocked
   `.envrc`).
4. `send "claude --dangerously-skip-permissions"` + Enter; wait ~6s.
5. Trust-folder prompt — `send-key Enter` (option 1 pre-highlighted).
6. Fire the thin `/goal` — substitute `<DRAIN_ID>`/`<SENTINEL>` into the worker
   condition, `send`, **sleep 3** (long sends race the submit), `send-key
   Enter`; `read-screen` and confirm `Goal set:` + `/goal active`.

### Worker `/goal` condition — single canonical source

There must be **one canonical** worker condition. `drain.md` owns it in its
`## Worker condition (the /goal payload)` section (lines 510–523), emitted by the
`worker`/`epic`/`set`/`cascade` setup modes.

**Embed, not pointer — guarded by a test.** The reference *embeds* the condition
text verbatim in a fenced block, because the launching agent `cmux send`s it into
the worker pane and must have the literal text inline (a pointer that forces the
agent to open `drain.md` mid-launch is fragile). `drain.md` remains the canonical
owner; the reference's copy is execution-time duplication. Drift is prevented not
by convention but by **test assertion 6** (below), which asserts the two fenced
templates are byte-identical and both carry the `jj:jujutsu` clause — a CI failure
the moment one is edited without the other. (This is why assertion 6 is
byte-identity and not a no-template check.)

The lifted holomush condition adds one load-bearing clause the canonical text
lacks: `Also invoke the jj:jujutsu skill before any commit/rebase/topology
surgery.` A long drain drifts from `main`, so the finish-branch pre-push rebase
conflicts and per-iteration `jj new` can fork the topology — the worker must use
canonical jj recipes, not improvise. This clause benefits **every** worker
launch, not just pane ones.

**Resolution:** add that clause to `drain.md`'s canonical Worker condition (so
all modes emit it), and embed the identical text in the reference (per the
embed-not-pointer rule above). The canonical text — verbatim in both places —
becomes:

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Also invoke the jj:jujutsu skill before
any commit/rebase/topology surgery. Execute exactly ONE ready bead this turn
following the protocol, then stop. Goal met when: <SENTINEL>.
```

This eliminates the divergence: `/drain worker <id>` and `/drain-with-worker`
emit byte-identical conditions for the same bead.

### Watchdog (background loop in the orchestrating session)

- Completion = **drain bead `status == closed`**, never a child count
  (review-finding beads inflate counts).
- Stall probe (epic-mode): count task-children via
  `select(.id | startswith("<scope>."))`, **excluding** the drain bead itself
  (it is an in_progress epic child for the whole run).
- Dolt-500 tolerance: on an unreadable poll (`-1` sentinel) sleep and continue;
  never nudge on a bad read.
- Nudge: SHORT single-line message + 2s gap before `send-key Enter` (long
  multi-line nudges race the TUI submit). ~6 min debounce (5 strikes at 75s poll).
- On `DRAIN COMPLETE`: `PushNotification` + lightweight idle-poll through the
  interactive `finishing-a-development-branch` landing (the worker closes the
  drain bead *before* that landing, which then runs unmonitored).

### Addendum 2026-05-29 — surface-aware watchdog

The original count-stall probe is **blind to input-blocked and API-error states**:
a worker question, a permission prompt the bypass guard still catches (e.g. the
`rm -rf` confirmation), or an API / rate-limit / overloaded error stalls the worker
**without moving the closed-count**. The probe never strikes (no count change is
*expected* while blocked), and even if it did, its "Continue the drain" nudge is the
wrong response to a question. Operators were discovering blocked workers only after a
20–30 min idle gap. The watchdog is upgraded to scan the worker surface each tick:

- **Extracted to a script.** The watchdog is no longer inline bash in the reference —
  it is a self-contained `uv` script, `dev-flow/scripts/drain-watchdog` (extensionless,
  `#!/usr/bin/env -S uv run --script`, stdlib only). Python over bash because the
  classification regexes and the `bd show` array / dolt-500 guards become directly
  **unit-testable** (`classify()` is a pure function imported in the test suite),
  rather than asserted as strings in markdown. It takes `--drain-id` / `--scope` /
  `--surface` plus tunable `--poll` (75s) / `--strikes` (5). Follows the repo's
  established `dev-flow/scripts/<name>` invocation + `Bash(...:*)` allowed-tools
  convention (cf. `render-adr`).
- **Cadence**: base poll tightened to ~75s (was 180s) so a blocked prompt is caught
  fast; the count-stall debounce moves to 5 strikes to preserve the ~6 min window.
- **Surface scan** each tick: `cmux read-screen --surface <s>` (last 40 lines),
  classified by `classify()` into `api-error` (`API Error|overloaded|rate.?limit|429|
  529|Internal server error|Connection error|fetch failed`) and `blocked-input`
  (`Do you want to|Would you like|❯ N.|N. Yes/No/Allow|trust .*folder|proceed?`).
  Error wins over a co-occurring retry prompt (more urgent signal).
- **Exit-to-wake, not nudge.** On `api-error` (rc 10) / `blocked-input` (rc 11) the
  script **exits** with a tagged `EXIT=<reason>` first line. A background task notifies
  the orchestrator on **exit**, not on stdout, so exiting is what actually wakes the
  controller; an infinite echo-only loop would block silently. The count-stall
  self-nudge stays in the loop and is only reached on a healthy surface, so it can never
  nudge "Continue" into a permission prompt.
- **Reaction table** (orchestrator, on task finish): `complete` → PushNotification +
  landing idle-poll, do not re-arm; `blocked-input` → PushNotification + surface the
  prompt, **never auto-answer** (safe response unknowable generically), re-arm after
  the human/controller resolves it; `api-error` → PushNotification, wait a backoff,
  confirm recovery via `read-screen`, re-arm (hard failure → restart worker).

Reflected in `dev-flow/scripts/drain-watchdog` (the watchdog itself + `classify()`),
`dev-flow/references/drain-with-worker.md` (Surface-aware watchdog section + Gotchas

## 8–#10), `dev-flow/commands/drain-with-worker.md`, the `draining-beads` skill's

*Worker surface monitoring* edge case, and `tests/test_drain_skill.py` (classify unit
tests + completion/child-probe invariants moved from the reference to the script).

### Bug fix

Root cause confirmed against live bd: `bd show --json` returns a single-element
**array**, and the type field is **`issue_type`**, not `type`
(`.[0] | has("type") == false`, `has("issue_type") == true`).

The source skill's prerequisite uses `'.[0].type // .type // empty'`:
`.[0].type` is always `null` → the `// .type` alternative then indexes the
**array root** with a string → `jq: error: Cannot index array with string
"type"`.

Fix throughout the lifted reference:

- `.[0].type` → `.[0].issue_type` (compare to `"drain"`).
- Remove **every** `// .x` object-fallback (source lines 42–43, 45, 47–49, 91):
  bd always returns an array, so the fallback is dead code whose only effect is
  to raise on a null primary. The watchdog's source line 91
  `'.[0].status // .status // "unknown"'` cleans to `'.[0].status // "unknown"'`
  (keep the `"unknown"` default — it drives the no-nudge-on-bad-read path).
- Replace the misleading source comment (line 41) that claims the fallback
  "also accept[s] an object payload".

### Files added / changed

- **Add** `dev-flow/references/drain-with-worker.md` (lifted + bug-fixed; fires
  but does not redefine the canonical worker condition).
- **Add** `dev-flow/commands/drain-with-worker.md` (thin command) with the
  `allowed-tools` frontmatter specified in *Architecture › Pre-confirmation
  calling convention*.
- **Edit** `dev-flow/commands/drain.md`, three deltas: (a) additive cmux-aware
  handoff branch after Phase D; (b) `allowed-tools` delta (the launch+watchdog
  toolset listed in *Architecture › `/drain` handoff*); (c) augment the canonical
  `## Worker condition` text with the `jj:jujutsu` clause.
- **Edit** `dev-flow/AGENTS.md` (document the new command alongside `/drain`).
- **Edit** `tests/test_drain_skill.py` (assertions below).
- **No** `release-please-config.json` / `.release-please-manifest.json` /
  marketplace / codex-wrapper changes — command + reference are auto-discovered,
  and `references/` is already symlinked in `plugins/dev-flow/`. Normal
  release-please bumps the `dev-flow` plugin.

### Testing strategy

Extend `tests/test_drain_skill.py` (string/structure assertions, the existing
pattern). Add a path constant `DRAIN_WITH_WORKER_REF =
"dev-flow/references/drain-with-worker.md"` and `DRAIN_WITH_WORKER_CMD =
"dev-flow/commands/drain-with-worker.md"` alongside the existing `drain.md` /
`draining-beads/SKILL.md` paths (an explicit path prevents a typo'd path from
making an assertion vacuously pass).

1. The reference's jq reads `.[0].issue_type` and contains **no** `// .type`,
   `// .metadata`, or `// .status` object-fallbacks.
2. Prerequisites reject: non-drain bead, non-`in_progress`, non-epic mode,
   missing `drain_workspace`/`drain_scope`/`drain_sentinel`, and absent `cmux`.
3. Watchdog completion keys on drain-bead `status == closed` (not a count) and
   the child probe carries the `startswith("<scope>.")` filter.
4. `/drain` emits a `/drain-with-worker <bead>` handoff and probes `command -v
   cmux`.
5. The new command's `allowed-tools` includes `AskUserQuestion` and
   `Bash(cmux:*)`; `drain.md`'s `allowed-tools` gained the same two (the inline
   launch path would otherwise be blocked).
6. **Single worker condition:** the canonical condition text in `drain.md` and
   the condition the reference fires are byte-identical, and both contain the
   `jj:jujutsu` clause.

Quality gates: `rumdl` on the new/edited markdown; `uv run pytest
tests/test_drain_skill.py`; `lefthook run pre-commit`.

### Open questions / future work

- **holomush cleanup** (separate bead, that repo): delete local
  `.claude/skills/drain-pane/`, redirect to `/drain-with-worker` once published.
- **cmux `claude-teams`**: cmux exposes `claude-teams` + `hooks setup` — a
  possibly-simpler launch primitive than `new-pane` + `send`. Evaluate as a v2
  simplification; v1 keeps the proven sequence.
- **set/cascade watchdog**: a probe over an explicit bead-id set would unlock
  `/drain-with-worker` for non-epic modes.
- **`/drain --with-worker` sugar**: thin wrapper that points the user at
  `/drain-with-worker <bead>` — only if one-shot ergonomics prove necessary.

### References

- Source skill: `holomush/.claude/skills/drain-pane/SKILL.md` (137 lines).
- `dev-flow/commands/drain.md`, `dev-flow/skills/draining-beads/SKILL.md`.
- ADR `fhsk-e4i` (never invoke `/goal` from a skill; emit condition for a
  user/driver), ADR `fhsk-zds` (drain bead as cross-session handoff carrier;
  `drain_workspace` paves the way for an l/tmux driver).
- `docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md`.
- `cmux --help` (subcommands `new-pane`/`send`/`send-key`/`read-screen`).
<!-- adr-capture: sha256=f09286ae1cde86ae; session=cli; ts=2026-05-25T18:05:56Z; adrs=fhsk-dtk -->
