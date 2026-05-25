# `/drain-with-worker` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift holomush's local `drain-pane` skill into `dev-flow` as a
bug-fixed `/drain-with-worker` command that launches an autonomous `/drain`
worker in a detached cmux pane and arms a stall-watchdog, with a cmux-aware
handoff from `/drain`.

**Architecture:** Three pieces — a single-source-of-truth reference
(`dev-flow/references/drain-with-worker.md`) holding the cmux launch sequence +
watchdog; a thin command (`dev-flow/commands/drain-with-worker.md`) that
validates + confirms via AskUserQuestion + follows the reference; and an
additive cmux-aware handoff branch in `/drain`'s epic-mode Phase D. The worker
`/goal` condition is canonicalized in `drain.md` (with a `jj:jujutsu` clause)
and embedded verbatim in the reference, guarded against drift by a byte-identity
test.

**Tech Stack:** Markdown skills/commands/references (Claude Code plugin format),
cmux CLI (`new-pane`/`send`/`send-key`/`read-screen`), `bd` (beads) for drain
state, Python `pytest` string/structure tests (`tests/test_drain_skill.py`).

**Spec:** `docs/superpowers/specs/2026-05-25-drain-with-worker-design.md`
(design-reviewer READY round 3). Design bead: `fhsk-jmn`.

**Bead labels:** every task is string-test / markdown-edit work — apply
`model:sonnet`, `scope:drain` to all materialized beads (matches Rule 5's
sonnet-when-absent default; stated explicitly so `plan-to-beads` /
`subagent-driven-development` dispatch is unambiguous).

---

## File structure

| File | Responsibility | Action |
|------|----------------|--------|
| `dev-flow/commands/drain.md` | `/drain` command. Canonical worker condition; epic-mode Phase D gains cmux-aware handoff; `allowed-tools` delta. | Modify |
| `dev-flow/references/drain-with-worker.md` | Single source of truth for launch sequence + watchdog + gotchas; embeds the canonical worker condition verbatim. | Create |
| `dev-flow/commands/drain-with-worker.md` | Thin command: prereqs → AskUserQuestion confirm → follow the reference. | Create |
| `dev-flow/AGENTS.md` | Document `/drain-with-worker` alongside `/drain`. | Modify |
| `tests/test_drain_skill.py` | String/structure assertions for the new files + deltas. | Modify |

No `release-please-config.json` / manifest / codex-wrapper changes — command +
reference are auto-discovered, and `references/` is already symlinked in
`plugins/dev-flow/`. Note: the entire `dev-flow/` tree is **excluded from
rumdl** (vendored-fork lint scope, per `.rumdl.toml`), so the new command,
reference, and `dev-flow/AGENTS.md` are not markdown-linted — only the spec and
this plan under `docs/` are.

**Verification commands (used throughout):**

- Tests: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib`
- Markdown lint: `rumdl check <file>`
- Commit: per `references/vcs-preamble.md` (jj repo — `jj commit -m "<conventional message>"`).

---

## Task 1: Canonicalize the worker condition (add `jj:jujutsu` clause)

The reference will embed the worker condition verbatim; first make `drain.md`'s
canonical condition the single source by adding the load-bearing `jj:jujutsu`
clause (benefits every worker launch, and keeps the byte-identity invariant
satisfiable). The existing `test_worker_condition_under_limit` must stay green
(703 chars worst-case < 1500).

**Files:**

- Modify: `dev-flow/commands/drain.md` (the `## Worker condition (the /goal payload)` text block, ~lines 517–523)
- Test: `tests/test_drain_skill.py`
- [ ] **Step 1: Write the failing test**

Add to `tests/test_drain_skill.py`:

```python
def test_worker_condition_has_jj_clause() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    assert "jj:jujutsu" in tpl, (
        "canonical worker condition must tell the worker to invoke jj:jujutsu "
        "before commit/rebase/topology surgery"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_worker_condition_has_jj_clause -v --import-mode=importlib`
Expected: FAIL (`assert "jj:jujutsu" in tpl`).

- [ ] **Step 3: Edit the canonical condition**

In `dev-flow/commands/drain.md`, replace the `## Worker condition` text block with (adds the third sentence):

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Also invoke the jj:jujutsu skill before
any commit/rebase/topology surgery. Execute exactly ONE ready bead this turn
following the protocol, then stop. Goal met when: <SENTINEL>.
```

- [ ] **Step 4: Run tests to verify pass (incl. the length guard)**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k "worker_condition" -v --import-mode=importlib`
Expected: PASS for `test_worker_condition_has_jj_clause`, `test_worker_condition_under_limit`, `test_worker_condition_points_to_durable_carriers`.

- [ ] **Step 5: Lint + commit**

`dev-flow/` is excluded from rumdl, so no markdown lint applies here.
Commit per `references/vcs-preamble.md`: `feat(drain): add jj:jujutsu clause to canonical worker condition (fhsk-jmn)`

---

## Task 2: Create the bug-fixed reference

Lift `holomush/.claude/skills/drain-pane/SKILL.md` into a reference doc, fixing
the `bd show --json` type bug (`.[0].type // .type` → `.[0].issue_type`, drop all
`// .x` object-fallbacks) and embedding the canonical worker condition verbatim.

**Files:**

- Create: `dev-flow/references/drain-with-worker.md`
- Test: `tests/test_drain_skill.py`
- [ ] **Step 1: Write the failing tests**

Add to `tests/test_drain_skill.py` (path constants go near the top, beside `DRAIN_CMD`):

```python
DRAIN_WITH_WORKER_REF = REPO_ROOT / "dev-flow" / "references" / "drain-with-worker.md"
DRAIN_WITH_WORKER_CMD = REPO_ROOT / "dev-flow" / "commands" / "drain-with-worker.md"


def test_reference_uses_issue_type_not_type() -> None:
    text = DRAIN_WITH_WORKER_REF.read_text()
    assert ".[0].issue_type" in text, "must read the array element's issue_type field"
    assert ".type //" not in text, "the buggy '.type //' object-fallback must be gone"
    assert "// .metadata" not in text, "drop the '// .metadata' object-fallback"
    assert "// .status" not in text, "drop the '// .status' object-fallback"


def test_reference_prereqs_refuse_early() -> None:
    text = DRAIN_WITH_WORKER_REF.read_text()
    # type / status / mode / metadata / cmux guards all present
    assert 'issue_type // empty' in text or '.[0].issue_type' in text
    assert '"in_progress"' in text
    assert '"epic"' in text
    for meta in ("drain_workspace", "drain_scope", "drain_sentinel"):
        assert meta in text, f"prereq must guard {meta}"
    assert "command -v cmux" in text, "must refuse when cmux is not on PATH"


def test_reference_watchdog_completion_keys_on_bead_closed() -> None:
    text = DRAIN_WITH_WORKER_REF.read_text()
    assert '"closed"' in text, "watchdog completion = drain bead status closed"
    assert "startswith(" in text, "epic child probe filters by '<scope>.' prefix"
    # the cleaned status read has no object-fallback
    assert '.status // .status' not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k reference -v --import-mode=importlib`
Expected: FAIL (`FileNotFoundError` — the reference does not exist yet).

- [ ] **Step 3: Create the reference**

Create `dev-flow/references/drain-with-worker.md` with this exact content:

````markdown
# Drain with worker — launch sequence & watchdog

Launch a `/drain` worker in a **detached cmux pane** and arm a **stall-watchdog**, so an
autonomous bead-drain runs without occupying — or stalling — your orchestrating session.
This reference is followed by `/drain-with-worker <drain-id>` and by `/drain`'s
`--with-worker` handoff offer. It does the two things `/drain` itself can't: the cmux pane
mechanics + launch sequence, and the watchdog. There is **no handoff file** — the worker
reads its assignment from `bd show <drain-id> --json`.

**v1 is epic-mode only.** The watchdog child-probe is epic-specific (`startswith("<epic>.")`);
`set`/`cascade` drains are rejected fail-fast by the prerequisites below.

## Prerequisites (refuse early)

```bash
DRAIN_ID="$1"
B=$(bd show "$DRAIN_ID" --json)
# bd show always returns a single-element ARRAY; the type field is `issue_type`, not `type`.
[ "$(jq -r '.[0].issue_type // empty' <<<"$B")" = "drain" ]    || { echo "Not a drain bead: $DRAIN_ID" >&2; exit 1; }
[ "$(jq -r '.[0].status // empty' <<<"$B")" = "in_progress" ]  || { echo "Drain $DRAIN_ID not in_progress (already closed?)" >&2; exit 1; }
# v1 = epic-mode only: the watchdog child-probe below is epic-specific. Fail fast otherwise.
MODE=$(jq -r '.[0].metadata.drain_mode // empty' <<<"$B")
[ "$MODE" = "epic" ] || { echo "drain-with-worker v1 supports epic-mode drains only (got mode='$MODE'); set/cascade need a different watchdog child-probe — not yet specified." >&2; exit 1; }
WORKSPACE=$(jq -r '.[0].metadata.drain_workspace // empty' <<<"$B")
SCOPE=$(jq -r '.[0].metadata.drain_scope // empty' <<<"$B")
SENTINEL=$(jq -r '.[0].metadata.drain_sentinel // empty' <<<"$B")
[ -n "$WORKSPACE" ] && [ -n "$SCOPE" ] && [ -n "$SENTINEL" ] || { echo "Drain bead missing drain_workspace/drain_scope/drain_sentinel metadata" >&2; exit 1; }
command -v cmux >/dev/null 2>&1 || { echo "cmux not on PATH — drain-with-worker needs the cmux CLI" >&2; exit 1; }
```

## Launch sequence (drive cmux from your own pane)

Each step is **verified before the next** — the cwd, direnv, and submit steps each failed
live when chained or assumed. Capture the new surface ref from step 1 and reuse it.

1. **New pane** (don't steal focus): `cmux new-pane --type terminal --direction right --focus false` → capture `surface:<N>`.
2. **cd as its OWN verified step** — never chain `cd X && claude`:
   `cmux send --surface <s> "cd $WORKSPACE"` → `cmux send-key --surface <s> Enter` → `cmux send --surface <s> "pwd"` + Enter → `cmux read-screen --surface <s>` and **confirm pwd == `$WORKSPACE`**. [Gotcha #1]
3. **`direnv allow`** — a fresh split hits a *blocked* `.envrc`: `cmux send --surface <s> "direnv allow"` + Enter → `read-screen` and confirm `direnv: loading` (not `…is blocked`). [Gotcha #5]
4. **Launch with bypass** — `cmux send --surface <s> "claude --dangerously-skip-permissions"` + Enter; wait ~6s. [Gotcha #2]
5. **Trust-folder prompt** — option 1 ("Yes, I trust this folder") is pre-highlighted: `cmux send-key --surface <s> Enter`.
6. **Fire the thin `/goal`** — substitute `<DRAIN_ID>`/`<SENTINEL>` into the Worker condition below, `cmux send` it, **sleep 3** (it's long; long sends race the submit), then `cmux send-key --surface <s> Enter`. `read-screen` and confirm `Goal set:` + `/goal active`. [Gotcha #3, nudge-race]

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

## Watchdog (arm after the worker is iterating)

Run as a **background** bash loop in your orchestrating session (`run_in_background: true`).
It nudges the worker when the `/goal` Stop hook drops a re-fire, and self-completes when the
drain bead closes.

```bash
DRAIN_ID="<drain-id>"; SCOPE="<epic-scope>"; SURFACE="<surface-ref>"
NUDGE="Continue the drain: run the next ready iteration now per your active /goal."
prev=-1; strikes=0
while true; do
  st=$(bd show "$DRAIN_ID" --json 2>/dev/null | jq -r '.[0].status // "unknown"')
  if [ "$st" = "closed" ]; then echo "DRAIN COMPLETE: $DRAIN_ID closed"; break; fi   # completion = DRAIN BEAD CLOSED, never a count
  # task-children only — EXCLUDE the drain bead itself (it is an epic child, in_progress for the whole run) [Gotcha #6]
  inprog=$(bd list --parent "$SCOPE" --status in_progress --json 2>/dev/null | jq 'if type=="array" then ([.[]|select(.id|startswith("'"$SCOPE"'."))]|length) else -1 end')
  closed=$(bd list --parent "$SCOPE" --status closed --json 2>/dev/null | jq 'if type=="array" then ([.[]|select(.id|startswith("'"$SCOPE"'."))]|length) else -1 end')
  [ "$inprog" -lt 0 ] || [ "$closed" -lt 0 ] && { sleep 180; continue; }             # dolt 500 — never nudge on an unreadable poll
  if [ "$inprog" -eq 0 ] && [ "$closed" -eq "$prev" ]; then
    strikes=$((strikes+1))
    if [ "$strikes" -ge 2 ]; then                                                     # ~6min debounce
      cmux send --surface "$SURFACE" "$NUDGE"; sleep 2; cmux send-key --surface "$SURFACE" Enter   # SHORT nudge + 2s so it SUBMITS
      strikes=0
    fi
  else strikes=0; fi
  prev=$closed; sleep 180
done
```

On `DRAIN COMPLETE`: send a **PushNotification** ("drain complete — landing needs you") and
keep a lightweight idle-poll through the interactive `finishing-a-development-branch` landing.
The worker closes the drain bead **before** that landing, so the landing runs unmonitored and
can stall on a rate-limit or the merge/PR menu.

## Gotchas (each cost a live mistake)

| # | Trap | Guard |
|---|------|-------|
| 1 | cmux split does NOT inherit cwd; `cd X && claude` chains drop the `cd` | `cd` as its own send, verify `pwd` via read-screen |
| 2 | Worker stalls on the first permission prompt | launch with `--dangerously-skip-permissions` |
| 3 | `/goal` rejects conditions >4000 chars | use the thin bead-driven condition (no handoff file) |
| 5 | Fresh split hits a blocked `.envrc` → no workspace env | `direnv allow` + verify `direnv: loading` before launch |
| 6 | Drain bead is itself an in_progress epic child → stall signature unreachable | filter `startswith("$SCOPE.")` to count task-children only |
| 7 | Long drain drifts from main; pre-push rebase conflicts; `jj new` forks topology | worker condition tells it to invoke `jj:jujutsu` |
| — | Long multi-line nudge races the TUI submit (types but doesn't send) | SHORT single-line nudge + 2s before Enter; `Escape` clears a stuck box |
| — | Watchdog completion via closed-count is wrong (review-finding beads inflate it) | completion = **drain bead status==closed**, never a count |
| — | Worker closes the drain bead BEFORE the interactive landing | PushNotification + idle-poll through landing |
````

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k reference -v --import-mode=importlib`
Expected: PASS for the three `test_reference_*` tests.

- [ ] **Step 5: Lint + commit**

`dev-flow/` is excluded from rumdl, so no markdown lint applies here.
Commit: `feat(drain): add bug-fixed drain-with-worker launch reference (fhsk-jmn)`

---

## Task 3: Verify the single-condition (byte-identity) invariant

Now that both the canonical condition (Task 1) and the embedded copy (Task 2)
exist, lock them together with a byte-identity test so future edits to one
without the other fail CI.

**Files:**

- Test: `tests/test_drain_skill.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_drain_skill.py`:

```python
def test_worker_condition_byte_identical() -> None:
    cmd_tpl = _condition_template(DRAIN_CMD.read_text())
    ref_tpl = _condition_template(DRAIN_WITH_WORKER_REF.read_text())
    assert cmd_tpl == ref_tpl, (
        "the worker condition embedded in the reference must be byte-identical to "
        "drain.md's canonical condition"
    )
    assert "jj:jujutsu" in ref_tpl
```

(`_condition_template` matches a `## Worker condition` heading + a `` ```text `` fence; the
reference's section uses the same heading and fence, so the existing extractor works on both.)

- [ ] **Step 2: Run test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_worker_condition_byte_identical -v --import-mode=importlib`
Expected: PASS (Tasks 1 & 2 already produced identical text). If it FAILS, the
two blocks differ — reconcile them to the Task 1 canonical text (do not edit the
test).

- [ ] **Step 3: Commit**

Commit: `test(drain): assert worker condition is byte-identical across command and reference (fhsk-jmn)`

---

## Task 4: Create the `/drain-with-worker` command

Thin command: prerequisites → AskUserQuestion confirm gate → follow the reference.

**Files:**

- Create: `dev-flow/commands/drain-with-worker.md`
- Test: `tests/test_drain_skill.py`
- [ ] **Step 1: Write the failing tests**

Add to `tests/test_drain_skill.py`:

```python
def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    assert m, "command must start with YAML frontmatter"
    return m.group(1)


def test_drain_with_worker_command_frontmatter() -> None:
    fm = _frontmatter(DRAIN_WITH_WORKER_CMD.read_text())
    assert "AskUserQuestion" in fm, "confirm gate needs AskUserQuestion"
    assert "Bash(cmux:*)" in fm, "launch needs cmux"
    assert "PushNotification" in fm, "watchdog completion needs PushNotification"


def test_drain_with_worker_command_body() -> None:
    text = DRAIN_WITH_WORKER_CMD.read_text()
    assert "references/drain-with-worker.md" in text, "must delegate to the reference"
    assert "AskUserQuestion" in text, "must confirm before launch"
    assert "epic" in text, "must state epic-mode-only"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k drain_with_worker_command -v --import-mode=importlib`
Expected: FAIL (`FileNotFoundError`).

- [ ] **Step 3: Create the command**

Create `dev-flow/commands/drain-with-worker.md`:

````markdown
---
description: Launch a /drain worker in a detached cmux pane + arm a stall-watchdog (epic-mode drains).
argument-hint: "<drain-id>"
allowed-tools: ["Read", "AskUserQuestion", "PushNotification", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(jq:*)", "Bash(command -v cmux:*)", "Bash(cmux:*)", "Bash(direnv:*)", "Bash(sleep:*)"]
---

# /drain-with-worker

Launch an autonomous `/drain` worker for an existing **live** drain bead in a detached cmux
pane, and arm a stall-watchdog so the drain self-heals while you walk away. Mint the bead
first with `/drain epic <id>`; pass the bead id it reports here.

**v1 is epic-mode only** (the watchdog stall-probe is epic-specific). set/cascade drains are
refused fail-fast — drain them via the `/goal` condition `/drain` emits.

## Step 1 — Prerequisites (refuse early)

Parse `$ARGUMENTS` as `<drain-id>`. Execute the **Prerequisites** block from
`references/drain-with-worker.md` (type=drain, status=in_progress, mode=epic, non-empty
`drain_workspace`/`drain_scope`/`drain_sentinel`, `cmux` on PATH). On any failure, print the
message and stop.

## Step 2 — Confirm gate (AskUserQuestion)

Show the launch plan — new pane → `cd <workspace>` → `direnv allow` →
`claude --dangerously-skip-permissions` → fire the `/goal` for `<drain-id>` → arm watchdog —
and ask via **AskUserQuestion**: "Launch the autonomous worker for `<drain-id>` now?" with
options **Launch** / **Cancel**. Proceed only on **Launch**. (This gate is the single
confirmation; never launch without it.)

## Step 3 — Follow the reference

Execute the **Launch sequence** and arm the **Watchdog** exactly as specified in
`references/drain-with-worker.md`. Do not improvise the cmux mechanics — each step is
verified-before-next for documented reasons (see the Gotchas table in the reference).
````

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k drain_with_worker_command -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

`dev-flow/` is excluded from rumdl, so no markdown lint applies here.
Commit: `feat(drain): add /drain-with-worker command (fhsk-jmn)`

---

## Task 5: Wire the cmux-aware handoff into `/drain` (epic Phase D) + `allowed-tools` delta

After epic-mode Phase D emits the condition, probe `command -v cmux` and offer launch. Add the
launch+watchdog toolset to `drain.md`'s `allowed-tools` (the inline "Launch now" path runs the
reference under `/drain`'s command context, so it needs those tools).

**Files:**

- Modify: `dev-flow/commands/drain.md` (frontmatter `allowed-tools` line 4; epic-mode Phase D block ~lines 174–180)
- Test: `tests/test_drain_skill.py`
- [ ] **Step 1: Write the failing tests**

Add to `tests/test_drain_skill.py`:

```python
def test_drain_allowed_tools_gained_launch_toolset() -> None:
    fm = _frontmatter(DRAIN_CMD.read_text())
    assert "AskUserQuestion" in fm, "inline launch offer needs AskUserQuestion"
    assert "Bash(cmux:*)" in fm, "inline launch needs cmux"


def test_drain_epic_phase_d_offers_worker() -> None:
    text = DRAIN_CMD.read_text()
    assert "command -v cmux" in text, "Phase D must probe for cmux"
    assert "/drain-with-worker" in text, "Phase D must hand off to /drain-with-worker"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -k "allowed_tools_gained or epic_phase_d" -v --import-mode=importlib`
Expected: FAIL.

- [ ] **Step 3a: Edit the `allowed-tools` frontmatter**

In `dev-flow/commands/drain.md` line 4, add these entries to the existing `allowed-tools`
array (additive — remove nothing): `"AskUserQuestion"`, `"PushNotification"`,
`"Bash(command -v cmux:*)"`, `"Bash(cmux:*)"`, `"Bash(direnv:*)"`, `"Bash(sleep:*)"`,
`"Bash(jq:*)"`. (`Bash(jq:*)` is also a pre-existing omission — jq is already used in the body.)

- [ ] **Step 3b: Edit the epic-mode Phase D handoff**

Replace the epic-mode Phase D prose (`drain.md` ~lines 176–179, the "Print the **Worker
condition**…Then stop" paragraph) with:

```markdown
Print the **Worker condition** (see that section) with `<DRAIN_ID>` and
`<SENTINEL>` substituted, prefixed with: "Launch a fresh `claude` worker in this
workspace and submit the following as its first input (do not run it here):".
Do not attempt to invoke `/goal` (it is a user-only built-in).

**Then probe for an autonomous launcher:** run `command -v cmux`.

- **cmux present** → ask via **AskUserQuestion**: "Launch the autonomous worker
  for `$DRAIN_ID` now?" with options **Launch now** / **Just give me the command** /
  **Not now**.
  - *Launch now* → this prompt IS the confirm gate; follow
    `references/drain-with-worker.md` for `$DRAIN_ID` inline (skip that command's
    own gate — already confirmed here).
  - *Just give me the command* → print `/drain-with-worker $DRAIN_ID`.
  - *Not now* → print `/drain-with-worker $DRAIN_ID` for later, plus the emitted
    `/goal` condition above as the manual fallback.
- **cmux absent** → the emitted `/goal` condition above is the handoff; stop.
```

(Leave the `set`/`cascade` Phase D paragraphs unchanged — worker-pane is epic-only.)

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib`
Expected: PASS for the whole file (incl. unchanged existing tests —
`test_phase_d_emits_not_fires` still passes because the epic block keeps "do
not …invoke `/goal`" and adds no "Fire `/goal`").

- [ ] **Step 5: Lint + commit**

`dev-flow/` is excluded from rumdl, so no markdown lint applies here.
Commit: `feat(drain): cmux-aware /drain-with-worker handoff in epic Phase D (fhsk-jmn)`

---

## Task 6: Document `/drain-with-worker` in `dev-flow/AGENTS.md`

**Files:**

- Modify: `dev-flow/AGENTS.md` (the "Autonomous epic drain (`/drain`)" paragraph, ~line 9)
- Test: `tests/test_drain_skill.py`
- [ ] **Step 1: Write the failing test**

Add to `tests/test_drain_skill.py`:

```python
def test_agents_doc_mentions_drain_with_worker() -> None:
    agents = (REPO_ROOT / "dev-flow" / "AGENTS.md").read_text()
    assert "/drain-with-worker" in agents, "AGENTS.md must document the new command"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_agents_doc_mentions_drain_with_worker -v --import-mode=importlib`
Expected: FAIL.

- [ ] **Step 3: Edit AGENTS.md**

Append to the end of the "Autonomous epic drain (`/drain`)" paragraph in `dev-flow/AGENTS.md`:

```markdown
For epic-mode drains, `/drain-with-worker <drain-id>` launches the worker
autonomously in a detached cmux pane and arms a stall-watchdog (confirm-gated;
requires the `cmux` CLI). `/drain epic <id>` offers this launch directly when
`cmux` is on PATH. See `dev-flow/references/drain-with-worker.md`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_agents_doc_mentions_drain_with_worker -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

`dev-flow/` is excluded from rumdl, so no markdown lint applies here.
Commit: `docs(drain): document /drain-with-worker in dev-flow AGENTS.md (fhsk-jmn)`

---

## Task 7: Full quality gates

**Files:** none (verification only)

- [ ] **Step 1: Run the full drain test suite**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib`
Expected: PASS (all existing + new tests).

- [ ] **Step 2: Lint the rumdl-scoped markdown**

Only `docs/` is in rumdl's scope (`dev-flow/` is excluded per `.rumdl.toml`).

Run: `rumdl check docs/superpowers/specs/2026-05-25-drain-with-worker-design.md docs/superpowers/plans/2026-05-25-drain-with-worker.md`
Expected: `Success: No issues found`.

- [ ] **Step 3: Run the pre-commit gate**

Run: `lefthook run pre-commit --all-files`
Expected: all hooks pass.

- [ ] **Step 4: Verify clean tree**

Run: `jj st`
Expected: no uncommitted changes (all tasks committed).

---

## Out of scope (tracked separately)

- **holomush cleanup:** delete `holomush/.claude/skills/drain-pane/`, redirect to
  `/drain-with-worker` once this is published. File in the holomush repo, not here.
- **`cmux claude-teams`:** evaluate as a simpler launch primitive than `new-pane`+`send` (v2).
- **set/cascade watchdog:** an explicit bead-id-set stall probe would unlock non-epic modes.
- **`/drain --with-worker` flag sugar:** only if one-shot ergonomics prove necessary.
<!-- adr-capture: sha256=25633e86f0674d3f; session=cli; ts=2026-05-25T18:05:56Z; adrs= -->
