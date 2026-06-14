# Drain with worker — launch sequence & watchdog

Launch a `/drain` worker in a **detached multiplexer surface** and arm a **surface-aware
watchdog**, so an autonomous bead-drain runs without occupying — or stalling — your
orchestrating session. This reference is followed by `/drain-with-worker [worker-type]
<drain-id>` and by `/drain`'s `--with-worker` handoff offer. It does the two things `/drain`
itself can't: the multiplexer surface mechanics + launch sequence, and the watchdog. There is
**no handoff file** — the worker reads its assignment from `bd show <drain-id> --json`.

**v1 is epic-mode only.** The watchdog child-probe is epic-specific (`startswith("<epic>.")`);
`set`/`cascade` drains are rejected fail-fast by the prerequisites below.

## Prerequisites (refuse early)

Validation is owned by `${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch`. Run it in
check mode — it refuses fail-fast on a non-drain bead, a closed/!in_progress
bead, a non-epic mode, a missing multiplexer, or absent
`drain_workspace`/`drain_scope`/`drain_sentinel` metadata (the `issue_type`
field, not `type`, is the bead type):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch --check --drain-id <drain-id> --worker-type <auto|cmux|tmux>
```

On a non-zero exit, surface the printed reason and stop.

## Launch sequence

The verified pane-launch sequence (spawn → `cd` + verify `pwd` → `direnv allow`

- verify → `claude --dangerously-skip-permissions` → trust prompt → fire the
thin `/goal` with a 3s pre-submit pause) is implemented in
`${CLAUDE_PLUGIN_ROOT}/scripts/drain-worker-launch`. It prints `multiplexer=<name>` and
`surface=<ref>` on success. For the tmux primitives it builds on (spawn a
window vs detached session, `send-keys` vs Enter, `capture-pane`), see the
`tmux` skill.

## Worker condition (the `/goal` payload — submit verbatim)

This is the canonical condition, embedded verbatim from `dev-flow/commands/drain.md`'s
`## Worker condition` section. The two MUST stay byte-identical (enforced by
`tests/test_drain_skill.py::test_worker_condition_byte_identical`).

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Also invoke the jj:jujutsu skill before
any commit/rebase/topology surgery. Execute exactly ONE ready bead this turn
following the protocol, then stop. Goal met when: <SENTINEL>.
```

## Surface-aware watchdog (arm after the worker is iterating)

Arm `${CLAUDE_PLUGIN_ROOT}/scripts/drain-watchdog` as a **background** task in your orchestrating session
(`run_in_background: true`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/drain-watchdog \
  --multiplexer <multiplexer> --drain-id <drain-id> --scope <epic-scope> --surface <surface-ref>
```

It is a self-contained `uv` script (extensionless, `#!/usr/bin/env -S uv run --script`, stdlib
only) that does two jobs — and the second is why a bare count-stall probe was never enough:

- **Self-heals count-stalls** — when the `/goal` Stop hook drops a re-fire (worker idle
  mid-drain, no open child), it nudges the worker directly via the active multiplexer and
  keeps watching. Completion keys on the drain bead `status == closed`, never a child count;
  child counts filter `startswith("<scope>.")` to exclude the drain bead itself. [Gotcha #6]
- **Wakes you on input-blocked / API-error states** — a question, a permission prompt the
  bypass guard still catches (e.g. the `rm -rf` confirmation), or an API / rate-limit error
  stalls the worker **without moving the closed-count**, so the count-probe is blind to it.
  It reads the surface every ~75s and **exits** on these (`api-error` → rc 10,
  `blocked-input` → rc 11), firing the background-task completion notification so you hear
  about it in seconds — not 20–30 min later.

A "Continue the drain" nudge is the *wrong* answer to a question or an API error, so the script
never nudges in those states: it exits and hands the decision back to you. It **exits to wake**
rather than echoing in place because a background task notifies the orchestrator on exit, not
on stdout — an infinite echo-only loop would block silently forever. [Gotcha #8, #9]

The classification regexes (`classify()`) and the bd-array / dolt-500 guards live in the script
and are unit-tested in `tests/test_drain_skill.py`; do not re-derive them inline. `--poll` and
`--strikes` are tunable (defaults 75s / 5 strikes ≈ 6 min debounce).

The script exits with a tagged `EXIT=<reason>` marker on its first stdout line. When the
background task finishes, read its tail and react per reason — then **re-arm** it (relaunch the
same command) to keep watching, except on `complete`:

| `EXIT=` | What happened | React |
|---|---|---|
| `complete` | Drain bead closed | **PushNotification** ("drain complete — landing needs you"); idle-poll through the interactive `finishing-a-development-branch` landing. The worker closes the drain bead **before** that landing, so it runs unmonitored and can stall on a rate-limit or the merge/PR menu. Do **not** re-arm. |
| `blocked-input` | Worker waiting on a question or a permission prompt the bypass guard still catches | **PushNotification** + surface the prompt text to the operator. Do **not** auto-answer — the safe response is unknowable generically. [Gotcha #10] After the human answers (or you approve a prompt you can verify is safe), re-arm. |
| `api-error` | Worker hit an API / rate-limit / overloaded error | **PushNotification**. Rate-limit/overload usually self-clears: wait a backoff, confirm recovery by reading the surface, then re-arm. A hard failure needs a worker restart. |

## Gotchas (each cost a live mistake)

| # | Trap | Guard |
|---|------|-------|
| 1 | Multiplexer split does NOT inherit cwd; `cd X && claude` chains drop the `cd` | `cd` as its own send, verify `pwd` by reading the surface |
| 2 | Worker stalls on the first permission prompt | launch with `--dangerously-skip-permissions` |
| 3 | `/goal` rejects conditions >4000 chars | use the thin bead-driven condition (no handoff file) |
| 4 | `cmux --surface` rejects a bare index (`--surface 12` errors) | pass the **full ref `surface:<N>`** — capture it verbatim from `new-pane` and reuse the prefixed form in every send/key/read operation |
| 5 | Fresh split hits a blocked `.envrc` → no workspace env | `direnv allow` + verify `direnv: loading` before launch |
| 6 | Drain bead is itself an in_progress epic child → stall signature unreachable | filter `startswith("$SCOPE.")` to count task-children only |
| 7 | Long drain drifts from main; pre-push rebase conflicts; `jj new` forks topology | worker condition tells it to invoke `jj:jujutsu` |
| — | Long multi-line nudge races the TUI submit (types but doesn't send) | SHORT single-line nudge + 2s before Enter; `Escape` clears a stuck box |
| — | Watchdog completion via closed-count is wrong (review-finding beads inflate it) | completion = **drain bead status==closed**, never a count |
| — | Worker closes the drain bead BEFORE the interactive landing | PushNotification + idle-poll through landing |
| 8 | Count-stall probe is blind to questions / permission prompts / API errors — closed-count doesn't move, so it never strikes (or nudges "Continue" into a prompt) | read the surface every ~75s; classify api-error / blocked-input; nudge only in the healthy branch |
| 9 | An infinite echo-only loop never wakes the orchestrator (background tasks notify on **exit**, not on stdout) | the surface-watcher **exits** with `EXIT=<reason>`; the orchestrator reacts to the tail + re-arms |
| 10 | Auto-answering a worker question / permission prompt can fire a destructive or wrong action | never auto-answer; PushNotification + hand the decision to the operator |
