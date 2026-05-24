# `/drain` `/goal` Cold-Boot Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework `/drain` so the `/goal` condition is a short self-contained
cold-boot pointer (drain bead + skill), the iteration protocol lives in the
`draining-beads` skill, and the command emits the `/goal` payload instead of
pretending to fire it.

**Architecture:** Three carriers — a tiny `/goal` condition (boot pointer +
sentinel predicate), the drain bead (run state via `bd show`), and the
`draining-beads` skill (the 12-step protocol). A cold worker session boots from
the condition alone. `drain.md` becomes a setup/emit tool; the protocol moves
into the skill.

**Tech Stack:** Markdown skills/commands (`dev-flow/`), `bd` (beads/Dolt)
metadata + notes, `pytest` doc-validation tests, `rumdl`, `lefthook`. VCS is jj
(colocated) — use jj per `references/vcs-preamble.md`.

**Spec:** `docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md`
· **Design bead:** `fhsk-a49`

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `dev-flow/commands/drain.md` | setup/emit command; modes init/epic/set/cascade/resume/**worker** | Modify |
| `dev-flow/skills/draining-beads/SKILL.md` | relocated 12-step worker protocol + "Using `/goal` correctly" | Modify |
| `tests/test_drain_skill.py` | doc-validation: condition length/shape, emit-not-fire, stamps, relocation, worker mode | Create |
| `dev-flow/AGENTS.md` | one-line mention of `worker` mode | Modify |
| `.drain/` + `.gitignore` | **only if Task 1 selects fallback B** (goal-file protocol) | Conditional |

**Canonical worker-condition template** (Approach A; substituted with
`<DRAIN_ID>`/`<SENTINEL>` at emit time, ~360 chars):

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Execute exactly ONE ready bead this
turn following the protocol, then stop. Goal met when: <SENTINEL>.
```

---

### Task 1: Empirical cold-boot spike (operator-assisted — decides A vs B)

This gates the rest. `/goal` is user-only, so a human must submit it; the
implementer prepares fixtures + the exact line, the operator runs it and reports.

**Files:** none (throwaway bd state + scratch files).

- [ ] **Step 1: Create a throwaway test epic + two trivial child beads**

```bash
EPIC=$(bd create --title "SPIKE drain cold-boot" --description "throwaway" --type epic --json | jq -r '.id')
B1=$(bd create --title "SPIKE bead 1" --description "Create /tmp/spike1.txt containing 'hello'." --type task --parent "$EPIC" --json | jq -r '.id')
B2=$(bd create --title "SPIKE bead 2" --description "Create /tmp/spike2.txt containing 'world'." --type task --parent "$EPIC" --json | jq -r '.id')
echo "EPIC=$EPIC B1=$B1 B2=$B2"
```

- [ ] **Step 2: Create + stamp a throwaway drain bead (mirrors Phase B/C)**

```bash
WS=$(jj root 2>/dev/null || git rev-parse --show-toplevel)
SENT="All beads under epic $EPIC are closed."
DR=$(bd create --title "SPIKE drain" --description "spike" --type drain --label phase:run --json | jq -r '.id')
bd update "$DR" --set-metadata "drain_mode=epic" --set-metadata "drain_scope=$EPIC" \
  --set-metadata "drain_started_at=$(date -u +%FT%TZ)" \
  --set-metadata "drain_workspace=$WS" --set-metadata "drain_sentinel=$SENT"
bd update "$DR" --parent "$EPIC" --status=in_progress
echo "DRAIN=$DR"
```

(If `drain` type is unregistered, run `/drain init` first.)

- [ ] **Step 3: Hand the operator the exact cold-boot line**

Print for the operator to run in a **fresh** `claude` session (same jj
workspace, new session), substituting the real ids:

```text
/goal Drain worker for bead <DR>. Invoke the dev-flow:draining-beads skill for the iteration protocol, then run `bd show <DR> --json` for your assignment (workspace, mode, scope, lessons, rejection counts). cd to the workspace named in that bead before any bd/jj/file operation. Execute exactly ONE ready bead this turn following the protocol, then stop. Goal met when: All beads under epic <EPIC> are closed.
```

- [ ] **Step 4: Operator observes the cold worker against this checklist**

Record yes/no for each: (1) invoked `dev-flow:draining-beads`; (2) ran
`bd show <DR>`; (3) `cd`'d to the workspace; (4) ran exactly ONE ready bead (not
zero, not both); (5) reported the sentinel result; (6) Stop hook re-fired and
ran the second bead; (7) after a manual `/compact` mid-run, re-bootstrapped
(re-read skill/bead) and continued.

- [ ] **Step 5: Decide and record**

Run: `bd note fhsk-a49 "spike result: A|B — <checklist outcomes>"`

- All 7 pass → **Approach A** (skill-resident). Skip Task 10.
- Any of 1/2/7 fail (won't load skill / loses protocol post-compact) →
  **Approach B**. Do Task 10.
- 4 fails (zero or both beads) → tighten the imperative wording in the Task 3
  template ("exactly ONE ready bead, then STOP and let the Stop hook re-fire")
  and re-run this spike before choosing.
- [ ] **Step 6: Tear down fixtures**

Run: `bd close "$B1" "$B2" "$DR" --reason="spike"; bd close "$EPIC" --reason="spike"`
then `rm -f /tmp/spike1.txt /tmp/spike2.txt`. Do not commit any spike state.

---

### Task 2: Add the doc-validation test file (red)

**Files:**

- Create: `tests/test_drain_skill.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAIN_CMD = REPO_ROOT / "dev-flow" / "commands" / "drain.md"
DRAIN_SKILL = REPO_ROOT / "dev-flow" / "skills" / "draining-beads" / "SKILL.md"

CONDITION_MAX = 1500


def _condition_template(text: str) -> str:
    m = re.search(r"^##\s+Worker condition.*?```text\n(.*?)\n```", text, re.S | re.M)
    assert m, "drain.md must define a '## Worker condition' section with a ```text template"
    return m.group(1)


def test_worker_condition_under_limit() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    worst = tpl.replace("<DRAIN_ID>", "fhsk-" + "x" * 24).replace(
        "<SENTINEL>",
        "All beads in the cascade-reachable set from {"
        + ", ".join(["fhsk-xxxxxx"] * 12)
        + "} are closed.",
    )
    assert len(worst) < CONDITION_MAX, f"worker condition is {len(worst)} chars (limit {CONDITION_MAX})"


def test_worker_condition_points_to_durable_carriers() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    assert "<DRAIN_ID>" in tpl and "<SENTINEL>" in tpl
    assert "bd show <DRAIN_ID>" in tpl
    assert ("dev-flow:draining-beads" in tpl) or (".drain/<DRAIN_ID>.md" in tpl)


def test_phase_d_emits_not_fires() -> None:
    text = DRAIN_CMD.read_text()
    assert "Fire `/goal`" not in text, "Phase D must EMIT the condition, not fire it"
    assert "<PROMPT_BODY>" not in text, "the inline iteration-body payload must be gone"


def test_drain_stamps_workspace_and_sentinel() -> None:
    text = DRAIN_CMD.read_text()
    assert text.count("drain_workspace=") >= 3, "epic/set/cascade must each stamp drain_workspace"
    assert text.count("drain_sentinel=") >= 3, "epic/set/cascade must each stamp drain_sentinel"


def test_iteration_body_removed_from_command() -> None:
    assert "## Iteration body" not in DRAIN_CMD.read_text(), "12-step body must move to the skill"


def test_skill_carries_protocol_and_goal_guidance() -> None:
    text = DRAIN_SKILL.read_text()
    assert "Using `/goal` correctly" in text
    assert "Atomic claim" in text and "Two-stage review" in text
    assert ("user-only" in text.lower()) or ("cannot self-invoke" in text.lower())


def test_skill_has_no_stale_crossrefs() -> None:
    assert "embedded in `commands/drain.md`" not in DRAIN_SKILL.read_text()


def test_worker_mode_present() -> None:
    text = DRAIN_CMD.read_text()
    assert "worker <drain-id>" in text, "argument-hint/dispatch must list worker mode"
    assert "## Worker mode" in text
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib`
Expected: FAIL (no `## Worker condition` section; "Fire `/goal`" still present; etc.).

- [ ] **Step 3: Commit**

`jj describe -m "test(drain): doc-validation for /goal cold-boot handoff (red)"` then `jj new`.

---

### Task 3: Add the `## Worker condition` template section to `drain.md`

**Files:**

- Modify: `dev-flow/commands/drain.md` (insert before `## Iteration body`, ~line 477)

- [ ] **Step 1: Insert the canonical condition section** (Approach A wording),
  immediately before the `## Iteration body` heading:

````markdown
## Worker condition (the `/goal` payload)

Phases D below **emit** this condition for an operator (or a cmux/tmux / Agent
SDK driver) to submit as a worker's `/goal` turn. The skill never fires `/goal`
— see `dev-flow:draining-beads` "Using `/goal` correctly". Substitute
`<DRAIN_ID>` and `<SENTINEL>`; submit the result verbatim:

```text
Drain worker for bead <DRAIN_ID>. Invoke the dev-flow:draining-beads skill for
the iteration protocol, then run `bd show <DRAIN_ID> --json` for your assignment
(workspace, mode, scope, lessons, rejection counts). cd to the workspace named in
that bead before any bd/jj/file operation. Execute exactly ONE ready bead this
turn following the protocol, then stop. Goal met when: <SENTINEL>.
```
````

- [ ] **Step 2: Run the length + shape tests**

Run (expected PASS):

```bash
uv run --with pytest pytest \
  tests/test_drain_skill.py::test_worker_condition_under_limit \
  tests/test_drain_skill.py::test_worker_condition_points_to_durable_carriers \
  -v --import-mode=importlib
```

- [ ] **Step 3: Commit**

`jj describe -m "feat(drain): add self-contained worker /goal condition template"` then `jj new`.

---

### Task 4: Reframe Phase D in all three mode blocks (emit, not fire)

**Files:**

- Modify: `dev-flow/commands/drain.md` (epic 169-175, set 296-302, cascade 427-433;
  intro lines 47, 180, 307)

- [ ] **Step 1: Replace each of the three `Phase D — Fire \`/goal\``** blocks
  (and their `/goal <PROMPT_BODY>` body) with:

```markdown
**Phase D — Emit the `/goal` condition** (the command does NOT run `/goal`;
`/goal` is a user-only built-in):

Print the **Worker condition** (see that section) with `<DRAIN_ID>` and
`<SENTINEL>` substituted, prefixed with: "Launch a fresh `claude` worker in this
workspace and submit the following as its first input (do not run it here):".
Then stop — do not attempt to invoke `/goal`.
```

- [ ] **Step 2: Reword every stale `/goal` reference** (not just the three Phase
  D blocks):
  - The three intro lines (47, 180, 307): change "**(D)** fires `/goal` with the
    iteration body from `dev-flow:draining-beads`." to "**(D)** emits the `/goal`
    worker condition for an operator/driver to submit."
  - The **resume fall-through line** (`drain.md:475`): change "fall through to the
    same `/goal <PROMPT_BODY>` invocation as the original mode (Phase D directive).
    The iteration body in Task 8 handles all three modes via the `$MODE`
    substitution." to "fall through to **Phase D — Emit the `/goal` condition**,
    which emits the Worker condition for the recovered `$MODE`/`$SCOPE`/`$SENTINEL`."
  - Verify nothing stale survives: `rg -n 'PROMPT_BODY|Fire .{0,2}/goal' dev-flow/commands/drain.md`
    → expect **zero** matches.

- [ ] **Step 3: Run the emit test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_phase_d_emits_not_fires -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 4: Commit**

`jj describe -m "feat(drain): Phase D emits the /goal condition instead of fire fiction"` then `jj new`.

---

### Task 5: Stamp `drain_workspace` + `drain_sentinel` (Phase B + C; resume recovery)

**Files:**

- Modify: `dev-flow/commands/drain.md` (Phase B stamps: epic 150-154, set 279-282,
  cascade 406-409; Phase C: epic 165-167, set ~290, cascade ~417; resume 443-453)

- [ ] **Step 1: In each Phase B**, before the `bd update … --set-metadata` call, add:

```bash
WORKSPACE=$(jj root 2>/dev/null || git rev-parse --show-toplevel)  # absolute jj workspace root
```

and extend the existing stamp call with one more line:

```bash
  --set-metadata "drain_workspace=$WORKSPACE" \
```

- [ ] **Step 2: In each Phase C**, after the `SENTINEL=…` line, add:

```bash
bd update "$DRAIN_ID" --set-metadata "drain_sentinel=$SENTINEL"
```

- [ ] **Step 3: Teach resume to recover the new fields** (`drain.md:443-453`),
  after the existing `MODE`/`SCOPE`/`STARTED_AT` recovery:

```bash
WORKSPACE=$(echo "$META" | jq -r '.drain_workspace // empty')
SENTINEL=$(echo "$META" | jq -r '.drain_sentinel // empty')
[ -n "$SENTINEL" ] || echo "Drain bead $DRAIN_ID has no drain_sentinel; recompose from mode/scope." >&2
```

(Resume falls through to Phase D emit, which uses `$DRAIN_ID`/`$SENTINEL`.)

- [ ] **Step 4: Run the stamping test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_drain_stamps_workspace_and_sentinel -v --import-mode=importlib`
Expected: PASS (≥3 occurrences each).

- [ ] **Step 5: Commit**

`jj describe -m "feat(drain): stamp drain_workspace + drain_sentinel for cold-boot recovery"` then `jj new`.

---

### Task 6: Relocate the 12-step protocol into the skill + "Using `/goal` correctly"

**Files:**

- Modify: `dev-flow/skills/draining-beads/SKILL.md`

- [ ] **Step 1: Add a `## Iteration protocol (worker)` section** containing the
  12 steps, phrased for the worker ("You are the drain worker; run exactly one
  iteration per Stop"). Port the steps verbatim from `drain.md`'s current
  `## Iteration body` (lines 482-547), keeping the **already-fixed epic step 4**:
  `bd ready --parent "$EPIC_ID" --json` (NOT a `.parent` jq filter). Keep
  set/cascade filters as-is.

- [ ] **Step 2: Add a `## Using \`/goal\` correctly` section** stating: `/goal`
  is a **user-only** built-in (no `SlashCommand` tool; the agent cannot
  self-invoke it); the skill/command only **emits** the condition; a user or a
  cmux/tmux / Agent SDK driver submits it; the controller/worker split (separate
  cold session, same jj workspace); the cold-boot sequence (invoke skill →
  `bd show` → `cd` → one bead → report sentinel); and post-`/compact` recovery
  (the re-fired condition re-points at skill + bead).

- [ ] **Step 3: Run the skill-content test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_skill_carries_protocol_and_goal_guidance -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 4: Commit**

`jj describe -m "feat(draining-beads): relocate worker protocol + add /goal control-model guidance"` then `jj new`.

---

### Task 7: Delete the iteration body from `drain.md`

**Files:**

- Modify: `dev-flow/commands/drain.md` (remove `## Iteration body`, ~lines 477-550 to EOF)

- [ ] **Step 1: Delete the section** — remove the entire
  `## Iteration body (\`/goal\` Stop-hook prompt)` heading, its fenced 12-step
  block, and the trailing paragraph about substituting values into `/goal`'s
  condition. The protocol now lives only in the skill (Task 6).

- [ ] **Step 2: Run the removal test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_iteration_body_removed_from_command -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 3: Commit**

`jj describe -m "refactor(drain): remove inline iteration body (now in the skill)"` then `jj new`.

---

### Task 8: Add `worker <drain-id>` mode + frontmatter/dispatch

**Files:**

- Modify: `dev-flow/commands/drain.md` (frontmatter line 3 argument-hint; dispatch
  list 11-18; add a `## Worker mode` section near Resume)

- [ ] **Step 1: Update argument-hint** (frontmatter line 3):

```text
argument-hint: "init | epic <id> | set <id...> | cascade <id...> | worker <drain-id> | resume <drain-id>"
```

- [ ] **Step 2: Add a dispatch bullet** (list 11-18):

```markdown
- `worker <drain-id>` — Emit the `/goal` condition for a fresh worker to attach
  to a live drain (regenerates from the bead; does not create or re-stamp).
```

- [ ] **Step 3: Add the `## Worker mode` section** (note the 4-backtick outer
  fence so the inner `bash` block nests correctly):

````markdown
## Worker mode (`/drain worker <drain-id>`)

Attaches a fresh worker to an existing (live) drain. Reduced pre-flight only:

```bash
DRAIN_ID="$1"
bd types | grep -q drain || { echo "Run /drain init first." >&2; exit 1; }
META=$(bd show "$DRAIN_ID" --json | jq -r '.[0].metadata')
SENTINEL=$(echo "$META" | jq -r '.drain_sentinel // empty')
[ -n "$SENTINEL" ] || { echo "$DRAIN_ID missing drain_sentinel; was it created by /drain?" >&2; exit 1; }
```

Then fall through to **Phase D — Emit the `/goal` condition** (Worker condition
with `$DRAIN_ID`/`$SENTINEL`). Unlike `resume`, `worker` does NOT inspect
`halt:` notes or re-stamp the bead — it only regenerates the launch payload.
````

- [ ] **Step 4: Run the worker-mode test**

Run: `uv run --with pytest pytest tests/test_drain_skill.py::test_worker_mode_present -v --import-mode=importlib`
Expected: PASS.

- [ ] **Step 5: Commit**

`jj describe -m "feat(drain): add worker mode to attach a fresh /goal worker"` then `jj new`.

---

### Task 9: Fix stale cross-refs + AGENTS.md mention

**Files:**

- Modify: `dev-flow/skills/draining-beads/SKILL.md` (overview ~line 37; References ~157)

- Modify: `dev-flow/AGENTS.md`

- [ ] **Step 1: Fix the stale skill references** — replace the line stating the
  iteration runs "the 12-step body embedded in `commands/drain.md`" with: "the
  12-step protocol in this skill's *Iteration protocol (worker)* section." In
  the References table, add
  `docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md` (the
  2026-05-22 spec stays as historical/original).

- [ ] **Step 2: Mention worker mode in AGENTS.md** — under the `/drain` mention,
  add one line: "`/drain worker <drain-id>` emits a `/goal` condition for a
  separate cold worker session (same jj workspace); the skill never fires
  `/goal` itself."

- [ ] **Step 3: Run the stale-crossref test + full file suite**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib`
Expected: PASS (all functions).

- [ ] **Step 4: Commit**

`jj describe -m "docs(draining-beads): fix stale cross-refs; note worker mode in AGENTS"` then `jj new`.

---

### Task 10 (CONDITIONAL — only if Task 1 selected Approach B): goal-file protocol

Skip entirely if Task 1 selected Approach A.

**Files:**

- Modify: `dev-flow/commands/drain.md` (Worker condition template; Phase B materialization)
- Modify: `.gitignore`
- Modify: `tests/test_drain_skill.py`
- [ ] **Step 1: Switch the condition pointer to a file read** — in the
  `## Worker condition` template, replace "Invoke the dev-flow:draining-beads
  skill for the iteration protocol" with "Read `.drain/<DRAIN_ID>.md` for the
  iteration protocol".
- [ ] **Step 2: Materialize the protocol file in each Phase B** (after bead
  creation):

```bash
mkdir -p "$WORKSPACE/.drain"
SKILL="$WORKSPACE/dev-flow/skills/draining-beads/SKILL.md"
# Extract the "## Iteration protocol (worker)" section (up to the next "## ")
# from the skill — the single source of truth — into the per-drain file.
awk '/^## Iteration protocol \(worker\)/{f=1;print;next} f&&/^## /{exit} f' \
  "$SKILL" > "$WORKSPACE/.drain/$DRAIN_ID.md"
```

The `awk` keeps the skill as the single source of truth — the file is a
rendered copy, not a fork. If the skill's section heading changes, update the
`awk` pattern to match.

- [ ] **Step 3: Gitignore the directory** — add `.drain/` to `.gitignore`.

- [ ] **Step 4: Update the test** — `test_worker_condition_points_to_durable_carriers`
  already accepts `.drain/<DRAIN_ID>.md`; add an assertion that `.gitignore`
  contains `.drain/`.

- [ ] **Step 5: Run tests + commit**

Run: `uv run --with pytest pytest tests/test_drain_skill.py -v --import-mode=importlib` → PASS.
`jj describe -m "feat(drain): fallback B — goal-file protocol in gitignored .drain/"` then `jj new`.

---

### Task 11: Final verification gate

**Files:** none (verification only)

- [ ] **Step 1: Lint changed docs**

Run (expected no issues):

```bash
rumdl check --no-exclude \
  dev-flow/commands/drain.md \
  dev-flow/skills/draining-beads/SKILL.md \
  docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md \
  docs/superpowers/plans/2026-05-24-drain-goal-handoff.md
```

- [ ] **Step 2: Full test surface**

Run: `uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -v --import-mode=importlib`
Expected: all pass (incl. `tests/test_drain_skill.py`).

- [ ] **Step 3: Re-run the cold-boot spike against the FINAL condition** — repeat
  Task 1 Steps 1-6 using the now-shipped Worker condition (regenerate via
  `/drain worker <drain-id>`), confirming a real worker drains 2 beads
  end-to-end and the Stop hook terminates at the sentinel. Record:
  `bd note fhsk-a49 "final spike: PASS — N beads drained, sentinel terminated cleanly"`.

- [ ] **Step 4: Lefthook pre-commit**

Run: `lefthook run pre-commit --all-files`
Expected: pass.

- [ ] **Step 5: Confirm clean tree**

Run: `jj st` — confirm no stray spike state; all work committed.

---

## Notes for the implementer

- **VCS is jj.** Commit per `references/vcs-preamble.md`: `jj describe -m "…"`
  then `jj new`. Do not use `git commit`. Conventional-commit subjects
  (`cog verify` runs in commit-msg).
- **The `bd ready --parent` fix** (epic step 4; PR #90 / `fhsk-maa`) is the
  *correct* protocol text to port in Task 6 — do not reintroduce the
  `select(.parent == …)` jq filter.
- **One source of truth for the protocol:** after this plan the 12 steps live in
  the skill only. `drain.md` references it; do not duplicate.
- **`/goal` is user-only** — no task should write code/skill text claiming the
  agent runs `/goal`.
<!-- adr-capture: sha256=b3e0f180cc289ab4; session=cli; ts=2026-05-24T17:17:01Z; adrs=fhsk-eqt,fhsk-zds,fhsk-e4i -->
