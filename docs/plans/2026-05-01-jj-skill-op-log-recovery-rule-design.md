# jj Skill — Op-Log Recovery Rule (Design)

**Date:** 2026-05-01
**Bead:** fzymgc-house-skills-5qh
**Status:** Approved (awaiting implementation plan)

## Background

In a multi-agent workspace, an agent in workspace `holomush-8qr` ran
`jj op restore <op>` to clean up local state. Because the operation log is
**repo-global** (shared across every workspace in the same repo, including
secondary `jj workspace add` workspaces), this rewound the global view
across every concurrent workspace, including `gh-jj-fix` where another agent
was actively editing.

The downstream failure was subtle. `jj op restore` did not directly
overwrite working-copy files in the other workspace. Instead:

1. The other workspace's working copy became *stale* relative to the new
   global view.
2. The next `jj` command in the stale workspace triggered
   `jj workspace update-stale`.
3. `update-stale` picked the surviving commit at the recorded change-id
   from the rewound op log — which was the *pre-edit* version.
4. The agent's recent edits were silently replaced with older content.

The skill currently recommends `jj op restore` as the recovery path
(`SKILL.md` lines 241–246) and lists it in `references/jj-reference.md`
without flagging the multi-workspace hazard.

## Decision

Adopt **Option B** from the 2026-05-01 brainstorm: gate the op-log-rewind
class (`jj op restore`, `jj op abandon`) behind explicit user approval and
publish a recovery ladder that pushes agents toward the safe alternatives
(`--at-op` for inspection, `jj undo` for the most recent op, `jj op revert`
for surgical past-op fixes).

Wording is **MUST NOT**, not "ASK USER FIRST."

## Files Touched

| File | Change |
|---|---|
| `jj/skills/jujutsu/SKILL.md` | Replace existing "Warning — op log semantics" block (lines 241–246) with an expanded Recovery & Hazards section: ladder, MUST NOT gate, two `jj undo` traps. |
| `jj/skills/jujutsu/references/jj-reference.md` | Update "When to Use Which" table (lines 345–355): demote `op restore` and add `op abandon` with MUST NOT wording, promote `op revert` as the default for past-op fixes. Add an "Inspect first with `--at-op`" subsection. |
| `jj/skills/jujutsu/CHANGELOG.md` | One-line entry recording the new rule. |

No new files. No hook changes. No agent changes. No edits to
`pr-review/`, `superpowers/`, or VCS preambles (recovery surface is not
everyday VCS surface — confirmed by greps before implementation).

## The Recovery Ladder (canonical text)

The following text is the source of truth. It will be embedded verbatim
in `SKILL.md` and referenced (not duplicated) from `jj-reference.md`.

> When you need to recover from a bad state in a jj repo, work through
> these in order. Stop at the first one that fits.
>
> 1. **Inspect read-only first.** `jj --at-op=<op-id> log` shows the repo
>    as it looked at any past op without mutating anything. Use this to
>    understand what happened before reaching for any recovery command.
> 2. **`jj undo`** — for the most recent successful op only. Two traps:
>    - If `jj undo` errors with "cannot undo a merge" and suggests
>      `jj op restore`, stop and ask the user. Do not follow the hint.
>    - Never `jj undo` a `jj git push`. It corrupts bookmarks. If you
>      just pushed and need to back out, ask the user.
> 3. **`jj op revert <op-id>`** — surgical fix for a specific past op.
>    Appends a new operation that inverts the target without rewinding
>    the op log. Lock-free safe and won't disturb concurrent workspaces.
>    Use `--what=repo` to keep remote-tracking refs.
> 4. **`jj op restore <op-id>` and `jj op abandon`** — **MUST NOT run
>    without explicit user approval.** These rewind / prune the *global*
>    op log. In multi-workspace repos, other workspaces go stale and
>    `jj workspace update-stale` may resurrect pre-rewind content
>    (silently losing later edits). No per-workspace scoping flag exists
>    — the blast radius is structural.

## The Why-Block (canonical text)

This paragraph lives next to the gate in `SKILL.md` so the reasoning
travels with the rule:

> The op log is repo-global, not per-workspace. When one workspace runs
> `jj op restore`, the global view rewinds, which makes every other
> workspace stale. The next jj command in a stale workspace runs
> `jj workspace update-stale` and picks the surviving commit at the
> recorded change-id from the rewound view — which is the pre-rewind
> version. Concurrent edits in other workspaces can disappear this way.
> `jj op abandon` has the same blast radius and an active upstream bug
> (jj-vcs/jj#9208) where it silently breaks `jj undo` afterward.
> `jj op revert` does not have this problem — it appends rather than
> rewinds.

## Grounded Claims (citations for reviewers)

The recovery ladder and gate rest on these upstream-grounded facts.
Reviewers should sanity-check before merging.

| Claim | Source |
|---|---|
| Op log is repo-global; `jj op restore` makes other workspaces stale; no per-workspace scoping exists. | DeepWiki on jj-vcs/jj (queried 2026-05-01); `OperationRestoreArgs` accepts only `operation` + `--what` (no workspace flag). |
| `jj op revert` appends a new op inverting a target — does not rewind. | `docs/operation-log.md` in jj-vcs/jj; DeepWiki confirms. |
| `jj undo` of a merge fails and suggests `jj op restore`. | DeepWiki; corroborated by Hacker News discussion thread. |
| `jj undo` of a `jj git push` produces conflicted bookmarks. | "Undoing mistakes" in *Jujutsu for everyone*; jj-vcs.dev FAQ. |
| `jj op abandon` after `jj op restore` silently breaks `jj undo`. | Open bug **jj-vcs/jj#9208** (2026-03-27). |
| Concurrent multi-workspace operations have additional documented hazards beyond `op restore`. | Open bugs **jj-vcs/jj#8737** and **#9314** (out of scope here; tracked separately). |

## Out of Scope

These are real and worth doing, but not in this change:

- **Multi-workspace concurrency doctrine** (Option C from the brainstorm).
  The user-facing rule is "serialize op-log writes across agents in
  multi-agent repos" but the enforcement story is unclear and the
  research surfaced two separate open upstream bugs (#8737, #9314). File
  as a follow-up bead.
- **`hooks/guard-jj-mutating`** that would automatically block
  `jj op restore` / `jj op abandon` invocations the way
  `hooks/guard-git-mutating` blocks mutating git commands in jj repos.
  Useful belt-and-suspenders but a separable change. File as a follow-up
  bead.
- **VCS preamble updates** in `pr-review/` and `superpowers/`. These
  preambles cover everyday VCS surface, not recovery surface. Confirmed
  via grep that they do not currently mention `op restore` / `op abandon`.

## Validation

After implementation:

- `bd preflight` (lint, stale, orphans) clean.
- `rumdl check` clean for all three edited files (project uses rumdl,
  140 char line width, config in `.rumdl.toml`).
- Manual eyeball of rendered Markdown for the table changes in
  `jj-reference.md`.
- Conventional-commit message validated by `cog`.

## Acceptance Criteria

- `SKILL.md` recovery section contains the ladder verbatim and the
  why-block, both quoted above.
- `jj-reference.md` "When to Use Which" table demotes `op restore` and
  adds `op abandon`, both with MUST NOT wording.
- `jj-reference.md` has a new "Inspect first with `--at-op`" subsection
  immediately preceding the recovery commands.
- `CHANGELOG.md` has one entry summarizing the rule.
- All three files pass `rumdl check`.
- Two follow-up beads filed (concurrency doctrine, jj-mutating guard
  hook) before implementation closes.
