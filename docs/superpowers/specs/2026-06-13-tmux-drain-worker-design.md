# Design: Multiplexer-parameterized `drain-with-worker` skill + standalone `tmux` plugin

- **Design bead:** fhsk-3qy
- **Date:** 2026-06-13
- **Status:** Draft (pending design-reviewer)

## Problem

`/drain-with-worker` launches an autonomous `/drain` worker in a detached
**cmux** pane and arms a surface-aware watchdog. It is hard-coupled to cmux:
the command, its reference, and the `drain-watchdog` script all speak cmux's
four verbs (`new-pane`, `send`, `send-key`, `read-screen`). Operators who run
**tmux** instead of cmux have no equivalent.

We want tmux parity. Rather than fork a second `drain-with-tmux-worker`
command, we parameterize the launcher by **worker type** (the terminal
multiplexer) and lean into the direction Claude Code is moving — skills as the
auto-discovered, parameterizable extension surface — by converting the launcher
from a slash command into a **single skill that takes a worker-type argument**.

Separately, we add a reusable, standalone **`tmux` plugin** (a general tmux
usage skill) so tmux operations are normalized across the repo, not just inside
drain.

## Goals

- One `drain-with-worker` skill that drains via either **cmux** or **tmux**,
  selected by an argument (auto-detected when omitted).
- A standalone, reusable **`tmux`** usage skill in its own plugin.
- **No operational shell logic embedded in markdown.** The bead-validation and
  pane-launch sequences that currently live as a `bash` block and step-by-step
  prose move into `uv` Python scripts (matching the existing `drain-watchdog`
  precedent). Markdown invokes the scripts; it does not re-implement them.
- The launch sequence becomes **deterministic and unit-testable** instead of
  prose the model re-improvises each run.

## Non-goals

- Migrating the broader multi-mode `/drain` command itself to a skill. Out of
  scope; only the `-with-worker` launcher is converted here.
- Supporting `set`/`cascade` drains with a worker. v1 remains **epic-mode
  only** (the watchdog stall-probe is epic-specific), unchanged from today.
- Exhaustively documenting all of tmux. The `tmux` skill covers the primitives
  - gotchas an agent needs, not a full manual.

## Key facts (grounded)

- **cmux coupling is narrow.** Only four verbs across the three operational files
  this change modifies (the command, its reference, and `drain-watchdog`); the
  watchdog's intelligence (`classify()`, `ERR_RE`/`ASK_RE`, bd-poll/dolt-500
  guards) is multiplexer-agnostic. This is a driver swap, not a rewrite.
  (probe: `dev-flow/references/drain-with-worker.md`, `dev-flow/scripts/drain-watchdog`.)
- **tmux CLI mechanics** (context7 `/tmux/tmux`): detect inside tmux with
  `[ -n "$TMUX" ]`; `tmux new -dPF '#{pane_id}'` prints a `%N` pane id for a
  detached session; `new-window -P -F '#{pane_id}'` for an in-session window;
  `capture-pane -p -t %N` prints visible pane content; `send-keys -t %N`
  sends literal text vs `Enter`/`C-m`. A detached `new-session` defaults to
  **80×24** — too cramped for the Claude TUI, so we set `-x`/`-y` explicitly.
- **Skills vs commands** (context7 `/anthropics/claude-code`): both are
  model-invocable (commands via `SlashCommand`, skills via `Skill`); commands
  are not formally deprecated, but skills are the auto-discovered,
  description-triggered mechanism. In this harness a skill is still typeable as
  `/drain-with-worker`. Commands substitute `$1/$ARGUMENTS`; skills receive a
  free-form arg string the `SKILL.md` body parses in prose.
- **Plugin wiring** (probe, verified live on disk in this worktree —
  `plugins/jj/` exists with `commands -> ../../jj/commands`,
  `skills -> ../../jj/skills` symlinks and a `.codex-plugin/plugin.json`): a
  source plugin is `<name>/plugin.json` + `<name>/skills/...`, registered in
  **both** `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`,
  with a Codex wrapper under `plugins/<name>/` (symlinks back to source:
  `skills -> ../../<name>/skills`) and `extra-files` in
  `release-please-config.json` keeping `$.version` synced. (A design-review round-1
  finding claimed `plugins/` did not exist; that was a false negative from a
  symlink-blind glob — the directory and symlinks are present.)

## Architecture

Four artifacts.

### Artifact 1 — `uv` scripts (logic out of markdown)

All under `dev-flow/scripts/`, extensionless, `#!/usr/bin/env -S uv run --script`,
PEP 723 header, **stdlib-only** — matching `drain-watchdog`.

**`_muxdriver.py`** (new shared module). A `Multiplexer` abstraction with
`CmuxDriver` and `TmuxDriver` implementations and a `detect()` selector. One
tested home for every cmux/tmux verb; command construction is pure, so unit
tests assert the argv without spawning a multiplexer.

| Method | cmux | tmux |
|---|---|---|
| `spawn(drain_id)` → ref | `cmux new-pane --type terminal --direction right --focus false` → `surface:N` | `$TMUX` set → `new-window -P -F '#{pane_id}'`; else `new-session -d -s drain-<id> -x 220 -y 50 -P -F '#{pane_id}'` → `%N` |
| `send_text(ref, s)` | `cmux send --surface <ref> <s>` | `tmux send-keys -t <ref> -l <s>` |
| `send_enter(ref)` | `cmux send-key --surface <ref> Enter` | `tmux send-keys -t <ref> Enter` |
| `read_screen(ref)` | `cmux read-screen --surface <ref>` | `tmux capture-pane -p -t <ref>` |

`detect()`: `$TMUX` set → `tmux`; else `cmux` on PATH → `cmux`; else `tmux` on
PATH → `tmux`; else refuse. tmux `spawn()` with `$TMUX` set runs `new-window`; if
that fails (e.g. a session that disallows it), the driver surfaces the stderr and
the launch refuses rather than proceeding against an unknown ref.

**Module-sharing decision (resolved):** `_muxdriver.py` is a plain stdlib module,
**not** a `uv` script — it has no PEP 723 header and no shebang. `drain-worker-launch`
and `drain-watchdog` import it by inserting their own resolved directory on
`sys.path`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _muxdriver
```

`Path(__file__).resolve()` is reliable for a `uv run --script` entrypoint (the
kernel exec resolves the shebang to an absolute path, so `__file__` is set). The
"stdlib-only" rule still holds — `_muxdriver` imports nothing outside the stdlib;
it is shared *source*, not a third-party dependency. The rejected alternative was
duplicating the driver into both scripts (two homes to keep in sync); sharing wins
because the argv construction is the one thing both scripts must agree on exactly.

**`drain-worker-launch`** (new). Args: `--drain-id <id>`,
`--worker-type {auto,cmux,tmux}` (default `auto`), `--check`.

- **Validation (refuse early):** reads `bd show <id> --json` (single-element
  array; `issue_type` not `type`), asserts `issue_type=drain`,
  `status=in_progress`, `drain_mode=epic`, and non-empty
  `drain_workspace`/`drain_scope`/`drain_sentinel`; resolves the multiplexer via
  `detect()` (or the explicit arg) and confirms it is on PATH. On any failure,
  prints the reason and exits non-zero.
- **`--check` mode:** runs validation + multiplexer resolution only, prints the
  resolved plan (`workspace`, `scope`, `sentinel`, `multiplexer`) and exits.
  No side effects. This feeds the skill's confirm gate.
- **Launch mode (default):** spawns the surface, then runs the
  **verified-per-step** sequence in code — `cd <workspace>` (verify `pwd`),
  `direnv allow` (verify `direnv: loading`, not `…is blocked`),
  `claude --dangerously-skip-permissions` (wait ~6s), trust-folder `Enter`,
  then the thin `/goal` Worker condition (long send → sleep 3 → `Enter`; verify
  `Goal set:`). On success prints `multiplexer=<type>` and `surface=<ref>` on
  stdout for the orchestrator to pass to the watchdog. Each step's verification
  reproduces the gotcha guards documented in the current reference.

**`drain-watchdog`** (modify). Add `--multiplexer {cmux,tmux}` (default
`cmux`, preserving existing callers that pass no flag). `read_surface()` and
`nudge()` delegate to `_muxdriver`. `classify()`, `ERR_RE`/`ASK_RE`, the
bd-array / dolt-500 guards, and the EXIT-marker protocol are **unchanged**.

### Artifact 2 — `drain-with-worker` skill (thin markdown)

Convert the command into a skill:

- **New:** `dev-flow/skills/drain-with-worker/SKILL.md`
- **New/relocated:** `dev-flow/references/drain-with-worker.md` keeps the shared
  conceptual material — prerequisites rationale, the byte-identical Worker
  condition, the watchdog reaction table, and the gotchas table — but the
  executable steps now point at the `uv` scripts. tmux verb mechanics reference
  the `tmux` skill (Artifact 3); cmux mechanics are described inline as today.
- **Delete:** `dev-flow/commands/drain-with-worker.md`.

**SKILL.md frontmatter** (skills in this repo support `allowed-tools` — e.g.
`review-pr`, `address-findings` declare it; it is optional but used here because
the body shells out). The skill declares `name`, `description`, and an
`allowed-tools` set adapted from the old command — note the raw `Bash(cmux:*)`
verb permission is **gone** (cmux/tmux verbs now live inside the scripts), replaced
by the two script-invocation permissions:

```yaml
allowed-tools: ["Read", "AskUserQuestion", "PushNotification",
  "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)",
  "Bash(command -v cmux:*)", "Bash(command -v tmux:*)",
  "Bash(dev-flow/scripts/drain-worker-launch:*)",
  "Bash(dev-flow/scripts/drain-watchdog:*)"]
```

There is no `argument-hint` field on skills; the `[worker-type] <drain-id>`
contract is documented in the description and parsed in the body.

**SKILL.md body** (the only shell it contains is script-invocation lines):

1. Parse `[worker-type] <drain-id>` from the invocation. `worker-type` is
   optional (`cmux`|`tmux`); omitted → `auto`.
2. Run `dev-flow/scripts/drain-worker-launch --check --drain-id <id> --worker-type <t>`.
   On non-zero, surface the reason and stop.
3. Confirm gate via `AskUserQuestion` ("Launch the autonomous worker for
   `<id>` via `<multiplexer>` now?" → Launch / Cancel). Proceed only on Launch.
4. Run `dev-flow/scripts/drain-worker-launch --drain-id <id> --worker-type <t>`;
   capture `multiplexer=` / `surface=` from its output.
5. Arm `dev-flow/scripts/drain-watchdog --multiplexer <m> --drain-id <id>
   --scope <scope> --surface <ref>` as a background task; react to its `EXIT=`
   markers per the reaction table and re-arm (except on `complete`).

**Worker condition** stays byte-identical with `dev-flow/commands/drain.md`'s
`## Worker condition` section (enforced by an updated byte-identical test).

**Default behavior:** auto-detect (Goal-aligned with `detect()`); an explicit
`worker-type` argument always overrides.

### Artifact 3 — standalone `tmux` plugin

```text
tmux/plugin.json                         # {name:"tmux", version, description}
tmux/skills/tmux/SKILL.md                # general tmux usage skill
plugins/tmux/.codex-plugin/plugin.json   # Codex wrapper manifest
plugins/tmux/skills -> ../../tmux/skills # symlink (jj-wrapper convention)
```

`tmux/skills/tmux/SKILL.md` — a teaching/reference skill (illustrative `tmux`
command examples are fine here; this is the documentation surface, not embedded
operational logic). Scope:

- **Detect context:** `[ -n "$TMUX" ]`.
- **Spawn + capture ref:** `new-window -P -F '#{pane_id}'` vs detached
  `new-session -d -s <name> -x 220 -y 50 -P -F '#{pane_id}'` (size flags matter).
- **Target by pane-id `%N`, never index** (indices renumber).
- **Drive:** `send-keys -t %N -l 'text'` then a separate `send-keys -t %N Enter`
  — the send/submit race and why they are separate calls.
- **Read:** `capture-pane -p -t %N` (+ `-S -N` for scrollback).
- **Lifecycle:** `list-sessions`/`list-panes -F`, `kill-session -t`,
  `kill-pane -t`.
- Brief windows / layouts / copy-mode coverage so it is genuinely reusable.

### Artifact 4 — wiring, tests, docs

**Plugin registration:**

- Add `tmux` to `.claude-plugin/marketplace.json` and
  `.agents/plugins/marketplace.json`.
- Add `tmux/plugin.json` `$.version` to `release-please-config.json`
  `extra-files`.
- Create the Codex wrapper `plugins/tmux/`.

**Taskfile gating:** add `tmux/skills/*/SKILL.md`, the new
`dev-flow/skills/drain-with-worker/SKILL.md`, and
`dev-flow/references/drain-with-worker.md` to the gated markdown vars; add
`tmux/plugin.json` to `PLUGIN_JSON`.

**`/drain` Phase D:** widen the epic-mode launcher probe to **cmux-or-tmux** and
hand off to the parameterized skill (auto-detect picks the launcher). Two concrete
edits to `drain.md`:

- **Probe string:** `command -v cmux` → `command -v cmux || command -v tmux`. This
  retains the literal substring `command -v cmux`, so the existing
  `test_drain_epic_phase_d_offers_worker` assertion (`"command -v cmux" in text`)
  still passes; the offer text changes from "via cmux" to "via the detected
  multiplexer".
- **Frontmatter:** add `Bash(tmux:*)` and `Bash(command -v tmux:*)` to `drain.md`'s
  `allowed-tools` (it currently lists `Bash(cmux:*)` / `Bash(command -v cmux:*)`).
  `test_drain_allowed_tools_gained_launch_toolset` asserts `Bash(cmux:*)` is
  present — still true — so it passes unchanged.

**Tests** (`tests/test_drain_skill.py` and a new `tests/test_muxdriver.py`). The
command→skill conversion **breaks four existing tests** that read the command file
directly; each must be rewritten to target the skill + scripts:

| Existing test | Why it breaks | Replacement assertion |
|---|---|---|
| `test_drain_with_worker_command_frontmatter` (L208) | reads `commands/drain-with-worker.md` (deleted) | assert `skills/drain-with-worker/SKILL.md` frontmatter has the `allowed-tools` set above incl. both script permissions |
| `test_drain_with_worker_command_body` (L215) | same file | assert SKILL.md body invokes `drain-worker-launch` and arms `drain-watchdog --multiplexer` |
| `test_reference_arms_the_watchdog_script` (L132) | asserts `--drain-id/--scope/--surface` in the *command* frontmatter | re-point at SKILL.md; assert it also passes `--multiplexer` |
| `test_reference_prereqs_refuse_early` (L114) | asserts `command -v cmux` in the *reference* — moved into `drain-worker-launch` | re-point: assert the reference delegates refuse-early to `drain-worker-launch`, and add a `test_muxdriver.py` check that `detect()`/validation refuses with no multiplexer |

`test_reference_uses_issue_type_not_type` (L106) and
`test_iteration_body_removed_from_command` (L75) must be re-pointed at the new
file paths but keep their intent.

Two tests stay green with no change but are called out so the plan author does not
touch them by reflex: `test_reference_arms_the_watchdog_script`'s second clause
currently reads `_frontmatter(DRAIN_WITH_WORKER_CMD.read_text())` — the replacement
swaps only that read for the SKILL.md path (the reference-body clause is unchanged);
and `test_surface_monitoring_documented_in_skill` (L184) asserts `read-screen` in
the **`draining-beads`** skill, which this change does not modify, so it must remain
green untouched. New coverage:

- `tests/test_muxdriver.py`: argv construction per multiplexer (cmux vs tmux verb
  table), tmux `spawn()` placement branch (`$TMUX` set → `new-window`; unset →
  `new-session`), `detect()` precedence, refuse-with-no-multiplexer.
- `drain-worker-launch --check`: validation against a faked `bd` (subprocess shim),
  asserting refuse-early on each bad-bead case and a correct plan on the happy path.
- `drain-watchdog --multiplexer tmux`: `read_surface`/`nudge` build the tmux argv
  via `_muxdriver`; the existing `classify()` tests and the default `cmux` path stay
  green (back-compat).
- Worker-condition byte-identical test: re-pointed at the SKILL.md/reference.

**Docs:** AGENTS.md — "three source plugins" → "four"; document the
`drain-with-worker` skill's worker-type argument and the `tmux` plugin.

## Data flow

```text
/drain-with-worker [tmux] <id>
      │
      ▼
SKILL.md  ──► drain-worker-launch --check ──► (validate bead, resolve mux) ──► plan
      │                                                                          │
      ▼  AskUserQuestion (confirm) ◄────────────────────────────────────────────┘
      │
      ▼
drain-worker-launch ──► _muxdriver(spawn→cd→direnv→claude→trust→/goal) ──► multiplexer=, surface=
      │
      ▼
drain-watchdog --multiplexer <m> --surface <ref>  ──(EXIT= marker)──►  orchestrator reaction + re-arm
```

`_muxdriver` is the single seam where cmux/tmux differ; everything upstream and
downstream is multiplexer-agnostic.

## Error handling

- **Refuse early** in `drain-worker-launch`: wrong bead type/status/mode,
  missing metadata, or no usable multiplexer → non-zero exit with a clear
  reason; the skill surfaces it and stops.
- **Bad poll resilience** in the watchdog is unchanged: unreadable `bd` reads
  (dolt 500) and empty surface reads never trigger a false nudge.
- **Blocked-input / api-error** surface states still EXIT-to-wake the
  orchestrator; the watchdog never auto-answers a question or permission prompt.
- **Degraded grounding** (context7 unavailable during build) is a build-time
  concern, not runtime.

## Testing strategy

The win of moving logic into `uv` scripts is testability. `_muxdriver` argv
construction and `detect()` precedence are pure functions. `drain-worker-launch
--check` validation runs against a faked `bd` (subprocess shim) with no
multiplexer present. The launch *sequence* itself (which drives a live pane)
stays integration-level and is exercised manually, but every decision it makes
(which verb, which placement, which multiplexer) is unit-tested via the driver.

## Resolved decisions (design-review round 1)

- **Module sharing — resolved.** `_muxdriver.py` is a plain stdlib module (no PEP
  723 header), imported via resolved-`sys.path` insertion by both scripts (see
  Artifact 1). Duplication was the rejected alternative.
- **SKILL.md `allowed-tools` contract — resolved.** Specified in Artifact 2; skills
  in this repo do support the field.
- **Breaking tests — enumerated.** Four command-reading tests named in Artifact 4
  with replacement assertions; Phase D probe string chosen to keep its test green.
- **`plugins/` existence — rebutted.** Round-1 claimed the dir was absent; verified
  present with symlinks in this worktree (see Key facts).

## Remaining risks

- **Skill argument parsing is prose-interpreted**, not `$1` substitution. The
  SKILL.md must be explicit about extracting `worker-type`/`drain-id` from the
  free-form arg so the model parses reliably.
- **Detached tmux session sizing.** `220×50` is a reasonable default; if the
  operator's real terminal is larger, the worker TUI is still usable but not
  matched. Acceptable for v1.
- **tmux `new-window` failure** in a constrained session is surfaced as a launch
  refusal (Artifact 1), not silently swallowed — but the recovery path (fall back
  to a detached session?) is deferred to v2.
<!-- adr-capture: sha256=e82744cdf4cab5c5; session=cli; ts=2026-06-13T12:49:03Z; adrs=fhsk-5dj,fhsk-8yz,fhsk-a6v -->
