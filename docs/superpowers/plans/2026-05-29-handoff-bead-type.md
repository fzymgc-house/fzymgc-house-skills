<!-- markdownlint-disable MD013 -->

# Handoff Bead Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ephemeral `handoff-prompt` skill with a persistent `handoff` bd type plus a conditional-workflow `handoff` skill (create + resume modes) and `/handoff` + `/handoff-resume` commands.

**Architecture:** A handoff is a first-class `handoff`-typed bead carrying session-state *delta* (not a re-snapshot of the work bead). It links `0..N` source beads via `bd dep --type related`, captures origin/VCS state, and is a one-shot baton closed on resume. One skill holds both create and resume modes, sharing a single body-schema reference file; two thin slash commands wrap the modes.

**Tech Stack:** Markdown skills/commands (Claude Code plugin format), `bd` (beads) CLI, `rumdl` lint, jj/git VCS. No compiled code; "tests" are `rumdl` lint, `jq` manifest validity, and live `bd` command exercises.

**Spec:** `docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md`
**Design bead:** fhsk-9ho
**Model intent (Rule 5):** `model:sonnet` for all tasks — Markdown skill/command authoring against a fully-specified design; no subtle cross-cutting invariants warranting opus.

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `dev-flow/skills/handoff/SKILL.md` | Conditional-workflow skill: create mode + resume mode. |
| Create | `dev-flow/skills/handoff/references/body-schema.md` | The single shared body-schema definition both modes use. |
| Create | `dev-flow/commands/handoff.md` | `/handoff [scope|bead-id...]` create entry + `/handoff init` registration mode. |
| Create | `dev-flow/commands/handoff-resume.md` | `/handoff-resume [id]` resume entry (explicit ID + auto-discover). |
| Modify | `dev-flow/skills/handoff-prompt/SKILL.md` | Replace body with redirect + supersession note; do not delete. |
| Modify | `dev-flow/skills/finishing-a-development-branch/SKILL.md` | Add a "create a handoff?" offer at session close. |

**Not modified:** `dev-flow/plugin.json` — verified at plan time that it contains only `{name, description}` and does **not** enumerate skills/commands (they auto-discover from the directories). The spec's tentative "Modify `plugin.json`" row is dropped.

---

### Task 1: Body-schema reference file

The shared schema both skill modes populate (create) and read (resume). Isolating it prevents drift between the two modes.

**Files:**

- Create: `dev-flow/skills/handoff/references/body-schema.md`
- Test: `rumdl check` on the new file
- [ ] **Step 1: Create the reference file**

Create `dev-flow/skills/handoff/references/body-schema.md`:

```markdown
# Handoff Bead Body Schema

The handoff bead body is structured Markdown. **Sections scale to content and
are omitted when not applicable** — an empty section is noise. Section order:

- **Resuming** — one line: what this handoff picks up.
- **Source beads** — the `0..N` linked bead/epic IDs, or the literal line
  `none — untracked exploration`.
- **Left off at** — concrete current state of the work.
- **In-flight** — partial work, half-made decisions, anything mid-stream.
- **Origin / VCS** — origin repo path, VCS type (jj/git), workspace name,
  bookmark/branch, change-id/commit, dirty status, **pushed status** (loud flag
  if unpushed — resume cannot fork from main).
- **Gotchas learned** — this session's hard-won knowledge worth not
  rediscovering.
- **Next concrete step** — the single next action the resuming session takes.
- **Open questions** — design decisions deliberately left for the new session
  (framed as questions, never pre-decided).
- **Out of scope** — what the new session must not bundle in (derived from the
  user's declared scope boundary).
- **Source docs** — spec / plan / ADR paths, each reachability-verified at
  create time.

## Delta, not duplication

When source beads exist, **Left off at / In-flight / Next concrete step /
Open questions** carry only the delta the linked beads + spec do not already
record. When `0` source beads exist, those sections carry the full standalone
context.

## Worked example (one source bead, jj, pushed)

\`\`\`markdown
**Resuming:** wire-format transition for the publisher refactor.

**Source beads:** fhsk-abc (related)

**Left off at:** publisher.go refactor landed + tests green.

**In-flight:** consumer call sites at internal/eventbus/publisher.go:316,431
not yet updated to the new signature.

**Origin / VCS:** repo /Volumes/Code/.../fzymgc-house-skills · jj · workspace
publisher-refactor · bookmark publisher-refactor · change kxqpmsqz · clean ·
PUSHED.

**Gotchas learned:** jj rebase -r @ silently truncates multi-commit chains —
use -s <root>.

**Next concrete step:** update the two consumer call sites, then decide the
wire-format transition (one PR vs staged).

**Open questions:** wire-format transition — single PR or staged migration?

**Out of scope:** anything in the broader crypto epic line.

**Source docs:** docs/superpowers/specs/2026-05-14-...-design.md
\`\`\`
```

- [ ] **Step 2: Verify lint passes**

Run: `rumdl check dev-flow/skills/handoff/references/body-schema.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`:
`jj describe -m "feat(dev-flow): handoff body-schema reference (fhsk-9ho)"`

---

### Task 2: The `handoff` skill (create + resume modes)

**Files:**

- Create: `dev-flow/skills/handoff/SKILL.md`
- Test: `rumdl check` on the new file
- [ ] **Step 1: Create the skill file**

Create `dev-flow/skills/handoff/SKILL.md`:

```markdown
---
name: handoff
description: >-
  Create or resume a persistent handoff bead — a one-shot baton that carries
  session-state delta so a fresh session can pick up work without inheriting
  the current context. Create mode takes user-stated scope, captures VCS state,
  links 0..N source beads, and writes a `handoff`-typed bead. Resume mode
  resolves a handoff (explicit ID or auto-discover), restates context, sets up
  the workspace, and closes the baton. Supersedes handoff-prompt. Use when the
  user asks for a handoff, to resume a handoff, a session starter, or to spin
  up a fresh session for some work.
allowed-tools: Read, Bash, AskUserQuestion
metadata:
  author: fzymgc-house
  origin: supersedes handoff-prompt; persistent-bead model per fhsk-9ho
---

# Handoff

Create or resume a **handoff bead**: a persistent, self-contained, one-shot
baton of type `handoff`. The bead is the source of truth; it carries
session-state *delta*, not a re-snapshot of the work bead. See
`references/body-schema.md` for the body structure both modes share.

**Announce at start:** "I'm using the handoff skill to <create|resume> a handoff."

## Mode selection

- **Create** — default; the user wants to hand off current/next work. Invoked
  by `/handoff [scope|bead-id...]` or a create-shaped request.
- **Resume** — the user names a handoff ID or asks to resume/pick up a handoff.
  Invoked by `/handoff-resume [id]`.

## Create mode

### Step 1: Scope intake (first)

Take the user's stated scope — what the next session should focus on, which
bead(s)/epic are in scope, the boundary. Read it from the invocation args or
surrounding message. Ask **exactly one** clarifying question only if scope is
absent or genuinely ambiguous. This intent is the filter for every step below;
do NOT infer scope solely from session state.

### Step 2: Pre-flight — register the type (idempotent)

\`\`\`bash
EXISTING=$(bd config get types.custom 2>/dev/null | tr -d '"' | sed 's/^.*= //')
printf '%s\n' "$EXISTING" | tr ',' '\n' | grep -qx handoff \
  || bd config set types.custom "${EXISTING:+$EXISTING,}handoff"
\`\`\`

An unregistered type makes `bd create --type handoff` fail with
`invalid issue type: handoff`.

### Step 3: Gather session state, scoped to the intent

Pull only the in-flight work, decisions, and gotchas relevant to the declared
scope — not the whole session. Map them to the body-schema sections.

### Step 4: Select & link source beads

The user's scope decides which `0..N` beads/epic are in scope. For each:

\`\`\`bash
bd dep add <handoff-id> <source-id> --type related
\`\`\`

Zero in-scope beads → a standalone handoff (no edges; **Source beads** = `none
— untracked exploration`). Defer edge creation until after Step 6 (the handoff
ID does not exist yet).

### Step 5: Capture VCS / workspace state

\`\`\`bash
if jj root >/dev/null 2>&1; then VCS=jj; else VCS=git; fi
\`\`\`

Record into the **Origin / VCS** section: origin repo path (`git rev-parse
--show-toplevel`), VCS type, workspace name, bookmark/branch, change-id
(`jj log -r @ -T 'change_id.short(12)'`) or commit, dirty status (`jj st` /
`git status --porcelain`), and pushed status. Offer to commit + push; record
state either way. If unpushed, write a **loud flag** in the body so resume
knows it cannot fork from main.

### Step 6: Verify cited paths + write the bead

For each spec/plan/ADR path, confirm reachability from main
(`git ls-tree main -- <path>`); surface orphans before writing. Then:

\`\`\`bash
bd create --type handoff --title "<scoped title>" --priority <0-4>
\`\`\`

Populate the body per `references/body-schema.md`. **Next concrete step** and
**Out of scope** derive from the scope boundary. Then wire the Step 4 edges
using the returned handoff ID.

### Step 7: Emit the pointer prompt

Print a 2-3 line pastable starter — no editorial content inside the block:

\`\`\`text
Resume handoff <handoff-id> — <title>.
Run: /handoff-resume <handoff-id>
\`\`\`

After the block, note the handoff ID and any linked source beads.

## Resume mode

### Step 1: Resolve the handoff ID

Explicit ID if given. Otherwise auto-discover:

\`\`\`bash
bd list --type handoff --status open --json
\`\`\`

(`bd list --json` returns an array; read `.[].id` / `.[].title`.) If exactly
one, offer it; if several, list and let the user pick; if none (empty array, or
the type is not registered in this repo) say so and stop — do not treat an empty
result as an error.

### Step 2: Load context

\`\`\`bash
bd show <handoff-id> --json
\`\`\`

`bd show --json` returns a single-element array — read fields as `.[0].<field>`
and the type as `.[0].issue_type` (per memory `bd-1-0-4-mol-pour-show-gotchas`).
Follow `related` edges and `bd show` each source bead/epic.

### Step 3: Stale check

If linked source work is already closed, flag it and offer to close the handoff
*without* resuming (the baton outlived its work):
`bd close <handoff-id> --reason="stale: source work already closed"`.

### Step 4: Restate context

Summarize scope, next step, and open questions back to the user.

### Step 5: Set up the workspace

- **Pushed bookmark** named in Origin/VCS: `jj git fetch` then
  `jj new <bookmark>` (git: `git fetch` + `git checkout <branch>`).
- **Unpushed in-flight work** (loud flag set): direct the user back to the
  *original* workspace — cannot fork from main.
- **Clean / no in-flight work:** defer to `dev-flow:using-worktrees` from main.

### Step 6: Close the baton

\`\`\`bash
bd close <handoff-id> --reason="resumed in <new-workspace>"
\`\`\`

One-shot lifecycle: a long effort = a chain of one-shot handoffs.

### Step 7: Claim source work

If any source bead is in scope to start now: `bd update <source-id> --claim`.

## Constraints

- **Delta, not duplication.** Reference source beads; record only what they
  cannot know.
- **No editorial content inside the pointer-prompt block.**
- **Never embed credentials, tokens, or `~/.config/...` paths.**
- **Default priority 2** when the user does not specify.
- **Degrade gracefully:** if `bd` is unavailable, fall back to the legacy
  pastable-text briefing (see `dev-flow:handoff-prompt` history).
```

- [ ] **Step 2: Verify lint passes**

Run: `rumdl check dev-flow/skills/handoff/SKILL.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify required H1 after frontmatter (MD041)**

Run: `rg -n '^# Handoff$' dev-flow/skills/handoff/SKILL.md`
Expected: a match at the first heading line (agents need an H1 right after frontmatter).

- [ ] **Step 4: Commit**

`jj describe -m "feat(dev-flow): handoff skill with create + resume modes (fhsk-9ho)"`

---

### Task 3: The `/handoff` command (create + init modes)

**Files:**

- Create: `dev-flow/commands/handoff.md`
- Test: `rumdl check` on the new file
- [ ] **Step 1: Create the command file**

Create `dev-flow/commands/handoff.md`:

```markdown
---
description: Create a handoff bead (one-shot resume baton). Modes: init, create.
argument-hint: "init | [scope hint | bead-id...]"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Bash(bd config get types.custom:*)", "Bash(bd config set types.custom:*)", "Bash(bd create:*)", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd note:*)", "Bash(bd dep add:*)", "Bash(jj root:*)", "Bash(jj st:*)", "Bash(jj log:*)", "Bash(git rev-parse:*)", "Bash(git status:*)", "Bash(git ls-tree:*)", "Bash(jq:*)"]
---

# /handoff

Create a persistent handoff bead. See `dev-flow:handoff` for the full
create/resume workflow and `references/body-schema.md` for the body structure.

Parse `$ARGUMENTS`:

- `init` — Bootstrap this repo: register the `handoff` custom type (idempotent).
- anything else / empty — Treat as the **scope hint** and/or source bead IDs;
  invoke the `dev-flow:handoff` skill in **create mode**.

## Init mode (`/handoff init`)

Idempotent, per-repo. Registers the `handoff` custom type so
`bd create --type handoff` works (an unregistered type fails with
`invalid issue type: handoff`):

\`\`\`bash
EXISTING=$(bd config get types.custom 2>/dev/null | tr -d '"' | sed 's/^.*= //')
printf '%s\n' "$EXISTING" | tr ',' '\n' | grep -qx handoff \
  || bd config set types.custom "${EXISTING:+$EXISTING,}handoff"
\`\`\`

Print the resulting `bd config get types.custom` and exit without creating a
bead.

## Create mode

Invoke the `dev-flow:handoff` skill (create mode). Pass `$ARGUMENTS` through as
the scope hint / source bead IDs. The skill runs the type pre-flight itself, so
`/handoff init` is optional before a first create.
```

- [ ] **Step 2: Verify lint + JSON-in-frontmatter validity**

Run: `rumdl check dev-flow/commands/handoff.md`
Expected: `Success: No issues found in 1 file`

Run: `rg -n '^allowed-tools:' dev-flow/commands/handoff.md`
Expected: one match (frontmatter array present, matching the `drain.md` shape).

- [ ] **Step 3: Commit**

`jj describe -m "feat(dev-flow): /handoff command (init + create) (fhsk-9ho)"`

---

### Task 4: The `/handoff-resume` command

**Files:**

- Create: `dev-flow/commands/handoff-resume.md`
- Test: `rumdl check` on the new file
- [ ] **Step 1: Create the command file**

Create `dev-flow/commands/handoff-resume.md`:

```markdown
---
description: Resume a handoff bead (explicit ID or auto-discover), then close the baton.
argument-hint: "[handoff-id]"
allowed-tools: ["Read", "Grep", "Glob", "AskUserQuestion", "Bash(bd show:*)", "Bash(bd list:*)", "Bash(bd update:*)", "Bash(bd close:*)", "Bash(bd note:*)", "Bash(bd dep list:*)", "Bash(jj root:*)", "Bash(jj git fetch:*)", "Bash(jj new:*)", "Bash(git fetch:*)", "Bash(jq:*)"]
---

# /handoff-resume

Resume a handoff bead. See `dev-flow:handoff` for the full resume workflow.

Parse `$ARGUMENTS`:

- `<handoff-id>` — resume that handoff directly.
- empty — auto-discover: `bd list --type handoff --status open --json`; if one,
  offer it; if several, list and let the user pick; if none, say so and stop.

Invoke the `dev-flow:handoff` skill in **resume mode** with the resolved ID. The
skill loads context, runs the stale check, restates, sets up the workspace,
closes the baton (`bd close`), and claims source work if in scope.
```

- [ ] **Step 2: Verify lint passes**

Run: `rumdl check dev-flow/commands/handoff-resume.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Commit**

`jj describe -m "feat(dev-flow): /handoff-resume command (fhsk-9ho)"`

---

### Task 5: Supersede `handoff-prompt`

Replace the skill body with a redirect + supersession note. Keep the file
(existing references and muscle memory) and keep its degraded-mode value
(legacy pastable text when `bd` is unavailable).

**Files:**

- Modify: `dev-flow/skills/handoff-prompt/SKILL.md`
- Test: `rumdl check` on the modified file
- [ ] **Step 1: Replace the body below the frontmatter**

Keep the YAML frontmatter's `name: handoff-prompt` but replace everything from
the `# Handoff Prompt` H1 onward with:

```markdown
# Handoff Prompt (superseded)

> **Superseded by `dev-flow:handoff`.** Handoffs are now persistent
> `handoff`-typed beads created via `/handoff` and resumed via
> `/handoff-resume`, not ephemeral paste-ready text. See the `handoff` skill
> and `docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md`.

## When this skill still applies

Only as a **degraded-mode fallback** when `bd` is unavailable: this skill's
original behaviour — emit a self-contained paste-ready briefing text for a
fresh session — remains a valid last resort. The `handoff` skill falls back to
this pattern automatically when it cannot reach `bd`.

## Migration

- "give me a handoff" → `/handoff [scope]`
- "resume that work" → `/handoff-resume [id]`

The persistent-bead model carries session-state delta (not a re-snapshot of the
work bead), is queryable (`bd list --type handoff --status open`), and has a
one-shot baton lifecycle. See the spec for rationale.
```

- [ ] **Step 2: Verify lint passes**

Run: `rumdl check dev-flow/skills/handoff-prompt/SKILL.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify no stale internal references to the old workflow remain**

Run: `rg -n 'Step [0-9]|80 lines|paste-ready briefing' dev-flow/skills/handoff-prompt/SKILL.md`
Expected: no matches for the old step-by-step workflow (only the migration note).

- [ ] **Step 4: Commit**

`jj describe -m "refactor(dev-flow): supersede handoff-prompt with handoff skill (fhsk-9ho)"`

---

### Task 6: Integrate the handoff offer into `finishing-a-development-branch`

Add a "create a handoff?" offer at session close. The natural insertion point
is **after Step 5.5 (Post-Merge Interactive Close)** and before/within Step 6
cleanup — once integration is decided, offer to capture a handoff for any
leftover or next-phase work.

**Files:**

- Modify: `dev-flow/skills/finishing-a-development-branch/SKILL.md` (insert a new step after line 338's `### Step 5.5` block, before `### Step 6: Cleanup Workspace`)
- Test: `rumdl check` on the modified file
- [ ] **Step 1: Insert the new step**

Immediately before the `### Step 6: Cleanup Workspace` header, insert:

```markdown
### Step 5.6: Offer a Handoff (optional)

If there is leftover or next-phase work the user wants a fresh session to pick
up, offer to capture it as a handoff bead before cleanup.

1. **Ask via `AskUserQuestion`:** "Create a handoff bead for next-session work?
   (Create / Skip)".
2. **Create:** invoke `dev-flow:handoff` (create mode). Provide the just-finished
   epic/bead IDs as candidate scope; the user confirms the boundary. The skill
   captures VCS state (which, post-merge or post-push, will record the pushed
   ref so resume can fork cleanly).
3. **Skip:** proceed to cleanup.

This pairs with `/handoff-resume` at the start of the next session.
```

- [ ] **Step 2: Verify lint passes**

Run: `rumdl check dev-flow/skills/finishing-a-development-branch/SKILL.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify step ordering**

Run: `rg -n '^### Step 5\.5|^### Step 5\.6|^### Step 6' dev-flow/skills/finishing-a-development-branch/SKILL.md`
Expected: lines in order 5.5 → 5.6 → 6.

- [ ] **Step 4: Commit**

`jj describe -m "feat(dev-flow): offer handoff at branch finish (fhsk-9ho)"`

---

### Task 7: End-to-end validation

Exercise the real `bd` path (register → create → link → resume-close) and run
the repo's quality gates over every touched file. This both validates the
implementation and performs the legitimate one-time `handoff` type registration
for this repo (dogfooding).

**Files:**

- Test: live `bd` commands + `rumdl` + `jq`

- [ ] **Step 1: Register the type and confirm**

Run:

```bash
EXISTING=$(bd config get types.custom 2>/dev/null | tr -d '"' | sed 's/^.*= //')
printf '%s\n' "$EXISTING" | tr ',' '\n' | grep -qx handoff \
  || bd config set types.custom "${EXISTING:+$EXISTING,}handoff"
bd config get types.custom
```

Expected: output includes `handoff` (alongside `drain`). Re-running the block
must not duplicate it (idempotency check — run it twice, confirm one `handoff`).

- [ ] **Step 2: Create a throwaway handoff + link + close**

Run:

```bash
H=$(bd create --type handoff --title "TEST handoff e2e" --priority 3 --json | jq -r '.id')
bd dep add "$H" fhsk-9ho --type related
bd show "$H" --json | jq -r '.[0].issue_type, (.[0].dependencies | length)'
bd list --type handoff --status open --json | jq -r '.[].id' | grep -qx "$H" && echo "discoverable OK"
bd close "$H" --reason="e2e validation complete"
bd delete "$H" 2>/dev/null || true   # already closed; deletion is best-effort cleanup
```

Expected: `issue_type` prints `handoff`; dependency count ≥ 1;
`discoverable OK` prints; close succeeds. The bead is closed regardless; the
`bd delete` is best-effort cleanup so a stray closed test bead is harmless.

- [ ] **Step 3: Lint every touched markdown file**

Run:

```bash
rumdl check \
  dev-flow/skills/handoff/SKILL.md \
  dev-flow/skills/handoff/references/body-schema.md \
  dev-flow/commands/handoff.md \
  dev-flow/commands/handoff-resume.md \
  dev-flow/skills/handoff-prompt/SKILL.md \
  dev-flow/skills/finishing-a-development-branch/SKILL.md \
  docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md \
  docs/superpowers/plans/2026-05-29-handoff-bead-type.md
```

Expected: `Success: No issues found in 8 files`.

- [ ] **Step 4: Confirm manifests still valid**

Run: `jq empty .agents/plugins/marketplace.json .claude-plugin/marketplace.json dev-flow/plugin.json`
Expected: no output (all valid JSON), exit 0.

- [ ] **Step 5: Run the hook test suite (unchanged surface, sanity)**

Run: `uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -v --import-mode=importlib`
Expected: all pass (this change touches no hooks; confirms no collateral breakage).

- [ ] **Step 6: Commit**

`jj describe -m "test(dev-flow): validate handoff type lifecycle + gates (fhsk-9ho)"`
<!-- adr-capture: sha256=8437357bd1d755bb; session=cli; ts=2026-05-29T17:13:03Z; adrs=fhsk-s15,fhsk-8xn,fhsk-57f -->
