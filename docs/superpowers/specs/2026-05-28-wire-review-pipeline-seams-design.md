# Wire Review Pipeline Seams (Post-Consolidation)

- **Design bead:** fhsk-cph
- **Date:** 2026-05-28
- **Status:** Draft for review

## Problem

Now that `pr-review` lives inside `dev-flow` (PR #101), four seams that the
consolidation deliberately deferred can be wired as same-plugin edits:

1. `finishing-a-development-branch` creates a PR but never points the user at
   `review-pr`, so the produced PR sits unreviewed unless the user knows to run
   `/review-pr` themselves.
2. `review-pr` ends after presenting/posting findings and never points the user
   at `address-findings`, so the fix loop is a manual jump.
3. Two VCS preambles coexist in `dev-flow/references/` — `vcs-preamble.md`
   (general skills) and `vcs-detection-preamble.md` (review agents) — sharing a
   detection block that can drift.
4. The name `code-reviewer` is ambiguous: it is both a worktree-isolated
   **agent** (`dev-flow/agents/code-reviewer.md`, used only by the `review-pr`
   orchestrator and requiring `PARENT_BEAD_ID`/`PR_URL`/`ASPECT`) and a prose
   **template** (`dev-flow/skills/requesting-code-review/code-reviewer.md`, for
   in-session review via a `general-purpose` subagent). `subagent-driven-development`
   conflates them: its SKILL.md maps `skills[] == review` to
   `subagent_type: code-reviewer` (which resolves to the orchestrator agent
   whose contract it cannot satisfy), even though its real review stage uses the
   template.

## Goals

- Wire the two handoffs as additive suggestions (no change to existing
  merge/PR/review logic).
- Collapse the two VCS preambles into one sectioned `vcs-preamble.md`,
  retargeting all references and keeping every consumer's behavior intact.
- Disambiguate `code-reviewer` by clarifying roles and fixing the
  `subagent-driven-development` (SDD) mapping — **no renames**, no change to how
  `review-pr` dispatches its `code` aspect.
- Keep the repo green: the agent-guidance test's review-agent filter is updated
  in lockstep with the preamble merge.

## Non-Goals

- Renaming the `code-reviewer` agent or any other agent.
- Changing `review-pr`'s aspect dispatch, agent contracts, or finding behavior.
- Consolidating the requesting-code-review template onto the agent (rejected:
  the agent needs a bd review epic + orchestrator vars the in-session flow lacks).
- Any new review aspect or agent.

## Seam 1: `finishing-a-development-branch` → `review-pr`

In `dev-flow/skills/finishing-a-development-branch/SKILL.md`, Option 2 ("Push
and Create PR") ends each VCS branch with `gh pr create` then a "Do NOT clean up
workspace" note. Add an additive suggestion after PR creation (both the git and
jj branches):

> After the PR is created, suggest: "PR #<n> created. Consider running
> `/review-pr <n>` before requesting human review." Do not run it automatically.

No change to the merge/PR/cleanup decision logic.

## Seam 2: `review-pr` → `address-findings`

In `dev-flow/skills/review-pr/SKILL.md`, the workflow ends at step 10 ("Offer to
Post"). Add a closing step 11 that — **only when findings were created** — points
the user at the fix loop:

> If any findings were filed (open beads under the review epic), suggest:
> "N findings filed. Run `/address-findings <n>` to work through them." Do not
> run it automatically.

When zero findings were filed, say so and stop. No change to the review/dispatch
logic.

## Seam 3: Merge the VCS preambles

The two files are not duplicates: `vcs-detection-preamble.md` (125 lines) is a
worktree-aware superset of `vcs-preamble.md` (64 lines), sharing only the
detection block. Merge into a single sectioned `dev-flow/references/vcs-preamble.md`:

| Section | Audience | Source |
|---------|----------|--------|
| Detection | all consumers | shared (both files) |
| Command Mapping | all consumers | vcs-preamble |
| Workspace Path Convention | all consumers | vcs-preamble |
| jj-Specific Rules (+ rebase note) | all consumers | vcs-preamble |
| Worktree-isolated agent startup (location verify + `STATUS: FAILED`) | review agents only | vcs-detection-preamble |
| Orchestrator contract | review agents (orchestrators) | vcs-detection-preamble |

The worktree/orchestrator sections open with an explicit applicability line
("Worktree-isolated review agents MUST follow this section; general workflow
skills skip it.") so general consumers know to stop after the core sections.

**Actions:**

- Rewrite `dev-flow/references/vcs-preamble.md` to the merged, sectioned form.
- Delete `dev-flow/references/vcs-detection-preamble.md`.
- Retarget the **17** files that reference `vcs-detection-preamble.md` to
  `vcs-preamble.md` (13 review agents, the 3 review skills `review-pr` /
  `address-findings` / `respond-to-comments`, `vcs-equivalence.md`, and
  `evals/evals.json`). Each review agent's Environment block currently says
  "Follow the startup procedure in `dev-flow/references/vcs-detection-preamble.md`
  to detect VCS and verify your location" — repoint the path; the merged file's
  "Detection" + "Worktree-isolated agent startup" sections satisfy
  "detect VCS and verify your location".
- `dev-flow/references/upstream-manifest.md` references `vcs-preamble.md` (the
  survivor) and does **not** list `vcs-detection-preamble.md`, so it needs no
  change for the merge. (Verified: zero `vcs-detection-preamble` mentions.)
- The merged `vcs-preamble.md` is already in the CI lint list
  (`check-skills.yml`); it MUST lint clean under `rumdl --no-exclude`.

### Seam 3 coupling: the agent-guidance test

`tests/test_agent_guidance_docs.py` filters review agents by
`"vcs-detection-preamble" not in text and "vcs-equivalence" not in text`. After
the merge, no file contains `vcs-detection-preamble`, so the `vcs-detection-preamble`
clause matches nothing and the filter would drop the 12 agents that referenced
it, failing `assert checked >= 13`. In the **same change**, swap the dead marker
for the surviving one, keeping `vcs-equivalence`:

```python
        if "vcs-preamble" not in text and "vcs-equivalence" not in text:
            continue
```

Grounded reference distribution (verified): 12 review agents reference
`vcs-detection-preamble.md` (→ `vcs-preamble.md` after retarget); `review-gate.md`
references **only** `vcs-equivalence.md` (not the detection preamble). The 3
read-only reviewers (`adr-extractor`, `design-reviewer`, `plan-reviewer`)
reference neither. So the two-marker filter above selects exactly the 13 review
agents (12 via `vcs-preamble`, `review-gate` via `vcs-equivalence`) and none of
the reviewers. Keeping `vcs-equivalence` is required — do not drop it, or
`review-gate` falls out and `checked` is 12.

## Seam 4: Disambiguate `code-reviewer`

No renames. Clarify roles in three places:

- **`dev-flow/agents/code-reviewer.md`**: add one sentence near the top stating
  it is the `review-pr` orchestrator's `code`-aspect agent, dispatched only with
  the orchestrator contract (`PARENT_BEAD_ID`, `PR_URL`, `ASPECT`); it is not for
  ad-hoc or in-session dispatch.
- **`dev-flow/skills/requesting-code-review/code-reviewer.md`**: add one line
  noting this is the in-session review **template** (filled by a
  `general-purpose` subagent), distinct from the `code-reviewer` agent.
- **`dev-flow/skills/subagent-driven-development/SKILL.md`** (line ~60): fix the
  `skills[] == review → subagent_type: code-reviewer` mapping. SDD's in-session
  two-stage review uses the requesting-code-review template via `general-purpose`
  (as its own `code-quality-reviewer-prompt.md` already does). Reword so the
  heuristic does not name the `code-reviewer` agent as a dispatch target; point
  review-type tasks at the template/`general-purpose` path instead. Reconcile the
  "Dispatch final code-reviewer (opus)" line (~243) with the same guidance.

## Verification

- **Dangling-reference guard:** `grep -rn "vcs-detection-preamble" .` returns
  nothing outside CHANGELOGs (the file and all references are gone).
- **Lint:** `rumdl check --no-exclude dev-flow/references/vcs-preamble.md` and
  the touched SKILLs/agents — clean.
- **Full test suite:** `uv run --with pytest pytest .claude/hooks/tests/
  jj/hooks/tests/ tests/ --import-mode=importlib` passes, including the updated
  `test_agent_guidance_docs.py` (review-agent filter keyed on `vcs-preamble`,
  `checked >= 13`).
- **CI lint command** (reproduce locally): the `check-skills.yml` rumdl
  invocation still resolves every path; `vcs-preamble.md` is present and clean;
  no path names `vcs-detection-preamble`.
- **Handoff smoke (manual):** read `finishing-a-development-branch` Option 2 and
  `review-pr` step 11 to confirm the suggestions are present, conditional, and
  never auto-run.

## Risks

- **Missed preamble reference** → an agent points at a deleted file. Mitigated
  by the dangling-reference grep guard.
- **Test filter substring trap:** `"vcs-preamble"` is a substring of
  `"vcs-detection-preamble"`. This is harmless *after* the merge (the longer
  string no longer exists) but the filter change MUST land in the same commit as
  the file deletion, never before.
- **review-gate filter dependency:** `review-gate.md` references only
  `vcs-equivalence.md`, so the test filter MUST retain the `vcs-equivalence`
  clause (see Seam 3 coupling). Dropping it silently reduces `checked` to 12 and
  fails the test — the failure is loud, not silent, so this is low-risk but
  called out explicitly.

## Out of scope / follow-up

None pending. This closes the consolidation follow-up; no further wiring seams
are tracked.
