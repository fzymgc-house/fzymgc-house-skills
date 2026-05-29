<!-- markdownlint-disable MD013 -->

# `dev-flow`: `handoff` Bead Type + Create/Resume Skill

**Date:** 2026-05-29
**Status:** Proposed
**Deciders:** Sean Brandt (`@seanb4t`)
**Supersedes:** `handoff-prompt` skill (ephemeral-prompt model)
**Bead:** [fhsk-9ho](../../../README.md) — *Design: handoff as a first-class bead type + resume flow*

## Overview

Today's `handoff-prompt` skill is **read-side only and ephemeral**: it reads a *work* bead and emits a paste-ready ~80-line text briefing the user copies into a fresh session. Nothing about the handoff is persisted — there is no record a handoff was issued, `bd ready` / `bd list` cannot surface pending ones, and the briefing must be pasted immediately or it is lost. The holomush parent skill (262 lines, 8 steps) is the same model with more worked examples.

This design makes the handoff a **first-class, persistent, self-contained bead** of a new `handoff` custom type. The bead is the source of truth. It carries the **session-state delta** needed to resume work — *not* a re-snapshot of the work bead, spec, or plan. Three pieces:

1. **`handoff` custom bd type** — registered idempotently (mirroring `/drain init`). Makes handoffs queryable (`bd list -t handoff --status open` = pending batons; `--status closed` = a session-boundary history log) and gives them a lifecycle.
2. **`handoff` skill** (evolved from `handoff-prompt`) — a conditional-workflow skill with **create mode** and **resume mode** sharing one body-schema reference. User-stated scope is a first-class create input.
3. **`/handoff` and `/handoff-resume` thin slash commands** — operator entry points wrapping the two skill modes.

The defining principle: **the handoff bead carries session-state delta, not duplication.** When source beads exist, the body references them (`bd dep related` edges) and records only what they cannot know — where work was left off, in-flight VCS state, gotchas learned, the next concrete step. When no source bead exists (untracked exploration), the body carries full standalone context. This is what keeps the handoff from becoming a stale duplicate of the work bead.

## Goals

- Make every handoff a persistent, queryable, auditable bead with a clear lifecycle.
- Support `0..N` source beads/epics per handoff — work with **zero** (untracked exploration), **one**, **many**, or an **epic**.
- Make the **user the author of the handoff's scope**; the skill does mechanical capture within that boundary, never inferring scope purely from session state.
- Capture origin-repo and VCS/workspace state (jj/git, workspace, bookmark/change-id, dirty + pushed status) so a fresh session can reach in-flight work.
- Eliminate the stale-duplicate trap by carrying session-state *delta* and *references*, not re-snapshots.
- Keep the change additive and supersede `handoff-prompt` gracefully (redirect + origin note, not deletion).

## Non-Goals

- Replacing `bd`'s native issue tracking. Handoffs are batons *about* work, not the work items themselves.
- Auto-surfacing handoffs at every session start via hook infra (rejected — nags when irrelevant; see Alternatives).
- Cross-machine workspace teleportation. Resume reconstructs a *fresh* workspace from a pushed ref where possible; unpushed in-flight work is flagged, not magically transported.
- A long-lived "living document" handoff (rejected — see Lifecycle).

## The `handoff` Custom Type

Registered the same way the `drain` type is, idempotently:

```bash
EXISTING=$(bd config get types.custom 2>/dev/null | tr -d '"' | sed 's/^.*= //')
printf '%s\n' "$EXISTING" | tr ',' '\n' | grep -qx handoff \
  || bd config set types.custom "${EXISTING:+$EXISTING,}handoff"
```

Registration is folded into the first `/handoff` create. `init` is also an
explicit keyword mode of the `/handoff` command (`/handoff init`, mirroring
`/drain init`) that runs the registration block and exits without creating a
bead. An unregistered type makes `bd create --type handoff` fail loudly
(`invalid issue type`), so registration is a hard pre-flight of create mode.

**Why a type, not a label or note?** A custom type gives:

- **Queryability** — `bd list -t handoff --status open` cleanly enumerates pending batons; a label would collide with the `--label-pattern` / `--label-regex` no-op bug documented for bd ≤1.0.4 (see fhsk-4ut). `--type=` filters reliably.
- **Lifecycle** — open = pending, closed = consumed. The closed set is a free session-boundary history.
- **Distinct identity** — a handoff is conceptually not a task/bug/feature; it is a baton about them.

## Bead Body Schema

The body is structured Markdown. Sections scale to content and are **omitted when not applicable** (an empty section is noise). Order:

- **Resuming** — one line: what this handoff picks up.
- **Source beads** — the `0..N` linked bead/epic IDs, or the literal line "none — untracked exploration".
- **Left off at** — concrete current state of the work.
- **In-flight** — partial work, half-made decisions, anything mid-stream.
- **Origin / VCS** — origin repo path, VCS type (jj/git), workspace name, bookmark/branch, change-id/commit, dirty status, **pushed status** (loud flag if unpushed — resume cannot fork from main).
- **Gotchas learned** — this session's hard-won knowledge worth not rediscovering.
- **Next concrete step** — the single next action the resuming session should take.
- **Open questions** — design decisions deliberately left for the new session (framed as questions, never pre-decided).
- **Out of scope** — what the new session must not bundle in (derived from the user's scope boundary).
- **Source docs** — spec / plan / ADR paths, each reachability-verified at create time.

When `0` source beads exist, **Left off at**, **In-flight**, **Next concrete step**, and **Open questions** carry the full standalone context. When source beads exist, those sections carry only the delta the beads/spec do not already record.

## Source-Bead Links

Each in-scope source bead/epic gets a `bd dep` edge from the handoff. The
dependency *type* is a flag, not a positional argument (a bare second
positional is parsed as a bead ID):

```bash
bd dep add <handoff-id> <source-id> --type related
# equivalent: bd dep relate <handoff-id> <source-id>
```

Both forms verified against the live `bd` CLI (`bd dep add --help`): the
two-positional form is valid and `related` is an accepted `--type` value.
`--type related` (not the default `blocks`, nor `parent-child`) — the handoff
neither blocks nor parents the work; it references it. Edges produce cross-links
in `bd show` for both directions. Zero edges → a standalone handoff. The user's
declared scope decides which of the session's touched beads become edges.

## Create Flow (`/handoff [scope hint | bead-id...]`)

1. **Scope intake (first).** Take the user's stated scope — what the next session should focus on, which bead(s)/epic are in scope, the boundary. Read it from the invocation args / surrounding message; ask exactly one clarifying question only if scope is absent or genuinely ambiguous. **This intent is the filter for every step below.** The skill MUST NOT infer scope solely from session state.
2. **Pre-flight: register type** (idempotent block above).
3. **Gather session state, scoped to the intent.** Pull only the in-flight work, decisions, and gotchas relevant to the declared scope — not the whole session.
4. **Select & link source beads.** The user's scope decides which `0..N` beads/epic get `bd dep related` edges. None → standalone handoff.
5. **Capture VCS / workspace.** Record origin repo path, VCS type, workspace name, bookmark/change-id, dirty + pushed status. Offer to commit + push; record state either way. Flag unpushed work loudly in the body.
6. **Verify cited paths reachable.** For each spec/plan/ADR path, confirm it is reachable from `main` (`git ls-tree main -- <path>`); surface orphans before writing.
7. **Write the bead.** `bd create --type handoff --title "<scoped title>" --priority N`, populate the body schema. **Next step** and **Out of scope** derive from the scope boundary.
8. **Emit the pointer prompt** — a 2–3 line pastable starter, no editorial content:

   ```text
   Resume handoff fhsk-XYZ — <title>.
   Run: /handoff-resume fhsk-XYZ
   ```

## Resume Flow (`/handoff-resume [id]`)

1. **Resolve the handoff ID.** Explicit ID if given. Otherwise auto-discover: `bd list -t handoff --status open`; if exactly one, offer it; if several, list and let the user pick; if none, say so and stop.
2. **Load context.** `bd show <id>` + follow `related` edges (`bd show` each source bead/epic). When reading JSON, note `bd show --json` returns a single-element array — read fields as `.[0].<field>` and the type as `.[0].issue_type` (per memory `bd-1-0-4-mol-pour-show-gotchas`).
3. **Stale check.** If linked source work is already closed, flag it and offer to close the handoff *without* resuming (the baton outlived its work).
4. **Restate** the resumed context to the user (scope, next step, open questions).
5. **Set up workspace.** If the Origin/VCS section names a *pushed* bookmark: `jj git fetch` then `jj new <bookmark>` (or `git fetch` + `git checkout`). If work was **unpushed**, the loud flag drives the user back to the *original* workspace (cannot fork from main). If clean / no in-flight work: defer to `dev-flow:using-worktrees` from main.
6. **Close the baton.** `bd close <handoff-id>` — one-shot lifecycle. A long effort across sessions becomes a chain of one-shot handoffs (H1 closed on resume → H2 created at next session end → …).
7. **Claim source work** if any: `bd update <source-id> --claim`.

## Lifecycle

```text
session 1 end  -> /handoff           -> create H1 (open)
session 2 start-> /handoff-resume H1  -> read H1, bd close H1
session 2 end  -> /handoff           -> create H2 (open)
session 3 start-> /handoff-resume H2  -> read H2, bd close H2
```

`bd list -t handoff --status open` = pending batons. `--status closed` = session-boundary history. Each handoff is a point-in-time snapshot — honest about staleness, no "latest-only overwrite" drift.

## Integration Points

- **`finishing-a-development-branch`** — add a "create a handoff?" offer at session close, alongside the existing integration options.
- **holomush `landing-sequence`** — its step 7 ("Handoff (optional)") points at `superpowers:handoff-prompt`; redirect to `/handoff`.
- **`handoff-prompt`** — superseded. Replace its body with a redirect to the `handoff` skill + an origin note; do not delete (existing references and muscle memory).
- **No-bd environments** — if `bd` is unavailable, degrade gracefully to the old pastable-text briefing (the ephemeral model remains the fallback, not the default).

## Packaging

Approach **A** (chosen): one `handoff` skill with conditional create/resume modes sharing a single body-schema reference file, plus thin `/handoff` and `/handoff-resume` commands. Rationale: one conceptual unit, one schema (no duplication), matches the repo's conditional-workflow best practice and the "handoff-resume *section* of the skill" framing.

Rejected: **B** two single-purpose skills (duplicates the body schema, doubles files for a tightly-coupled pair); **C** evolve `handoff-prompt` for create + add only a resume command (splits the unit, leaves create under a misleading name).

## Files Touched

| Action | Path | What |
|--------|------|------|
| Create | `dev-flow/skills/handoff/SKILL.md` | The conditional-workflow skill (create + resume modes). |
| Create | `dev-flow/skills/handoff/references/body-schema.md` | The shared body-schema reference both modes populate/read. |
| Create | `dev-flow/commands/handoff.md` | `/handoff` command: scope intake → create mode; `/handoff init` keyword mode for type registration. |
| Create | `dev-flow/commands/handoff-resume.md` | `/handoff-resume [id]` command: explicit ID + auto-discover → resume mode. |
| Modify | `dev-flow/skills/handoff-prompt/SKILL.md` | Replace body with a redirect to the `handoff` skill + origin/supersession note. Do not delete. |
| Modify | `dev-flow/skills/finishing-a-development-branch/SKILL.md` | Add a "create a handoff?" offer at session close, alongside existing integration options. |
| Modify | `dev-flow/plugin.json` | Register the new skill/commands if the manifest enumerates them (verify at plan time). |
| Reference (no change) | holomush `landing-sequence` | Its step 7 redirect to `/handoff` lives in the holomush repo, not this one — note as cross-repo follow-up, out of scope for this plan. |

Plan-phase path verification: confirm each `Create` path's parent directory exists and follows the plugin's skill/command layout; confirm each `Modify` path is reachable from `main`.

## Test Strategy

| Area | Check |
|------|-------|
| Type registration | `/handoff init` on a repo without the type registers it; re-running is idempotent (no duplicate in `types.custom`); `bd create --type handoff` succeeds after registration and fails loudly before. |
| Create — links | A create with `N` in-scope beads produces a `handoff` bead with exactly `N` `--type related` edges; a zero-source create produces a standalone bead with no edges. |
| Create — VCS capture | Body records repo path, VCS type, workspace, bookmark/change-id, and pushed status; unpushed state produces the loud flag. |
| Create — scope filter | Session state outside the declared scope is excluded from the body. |
| Resume — discovery | Explicit ID resolves directly; no-ID with one open handoff offers it; with several, lists; with none, stops cleanly. |
| Resume — lifecycle | Resume closes the handoff (`bd close`); a stale handoff (source work already closed) is flagged and offered for close-without-resume. |
| Degrade | With `bd` unavailable, create falls back to the legacy pastable-text briefing. |

## Alternatives Considered

- **Handoff subsumes the work bead** (no separate work bead). Rejected — conflates the baton with the work and loses the work bead's own type/lifecycle.
- **Structured note on the work bead** (no new type). Rejected — not independently queryable, no distinct lifecycle, and breaks the `0`-source-bead case entirely.
- **Living-document handoff** (one durable bead re-described each session). Rejected — "latest-only" body loses per-boundary history; one-shot batons are honest about staleness.
- **Session-bootstrap auto-surfacing** (bd prime / SessionStart hook lists open handoffs every session). Rejected — touches hook infra and nags every session even when irrelevant. Auto-discover on explicit resume covers the need without the noise.
- **Keep the full 80-line pastable briefing** alongside the bead. Rejected — redundancy that drifts; a 2–3 line pointer prompt plus the authoritative bead is enough.

## Edge Cases

- **Stale handoff** — linked work already closed → flag, offer to close the handoff without resuming.
- **Multiple open handoffs** — resume lists them and lets the user pick.
- **Unpushed in-flight work** — loud flag in the body; resume re-enters the original workspace rather than forking from main.
- **No source bead** — fully standalone handoff; body carries complete context; no `related` edges.
- **No-bd environment** — degrade to the legacy pastable-text briefing.

## References

- `dev-flow/skills/handoff-prompt/SKILL.md` — the superseded ephemeral-prompt skill (grounding/probe).
- holomush `handoff-prompt` SKILL.md (262 lines) — the parent skill; same ephemeral model (grounding/probe).
- `docs/superpowers/specs/2026-05-22-drain-skill-design.md` §custom-type registration — the `bd config set types.custom` idempotent pattern this design mirrors.
- `docs/adr/fhsk-buu-use-bd-create-type-drain-drain-bead-creation-not-bd-mol-pour.md` — `bd create -t <type>` over `bd mol pour` for single custom-typed beads.
- Memory: `bd-1-0-4-mol-pour-show-gotchas` — `bd show --json` returns an array (`.[0]`), `issue_type` not `type`; `--label-pattern` is a no-op in bd ≤1.0.4 (motivates type-not-label).
<!-- adr-capture: sha256=c563c974be868541; session=cli; ts=2026-05-29T17:13:03Z; adrs=fhsk-s15,fhsk-8xn,fhsk-57f -->
