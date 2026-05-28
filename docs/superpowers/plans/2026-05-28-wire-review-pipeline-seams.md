# Wire Review Pipeline Seams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire four post-consolidation review-pipeline seams in `dev-flow`: two
additive handoff suggestions, a merge of the two VCS preambles into one
sectioned file, and disambiguation of the `code-reviewer` agent vs the
in-session review template.

**Architecture:** Seams 1/2 are additive prose suggestions (no logic change).
Seam 3 merges `vcs-detection-preamble.md` into a sectioned `vcs-preamble.md`,
retargets 17 references, and updates the coupled agent-guidance test filter.
Seam 4 clarifies role docs and fixes `subagent-driven-development` (SDD). All
edits are markdown/prompt artifacts plus one Python test.

**Tech Stack:** Markdown skill/agent/reference artifacts; `tests/` (pytest);
`rumdl --no-exclude` for the rumdl-excluded `dev-flow/**` tree; `jq` unaffected.
Spec: `docs/superpowers/specs/2026-05-28-wire-review-pipeline-seams-design.md`.

---

## Ordering / dependencies

Seam 3 is a chain: author merged file (Task 3) → retarget references (Task 4) →
update test filter + run tests (Task 5). The substring trap (`vcs-preamble` ⊂
`vcs-detection-preamble`) means the test-filter swap (Task 5) MUST land only
after the detection file is deleted (Task 3) — never before. Seams 1, 2, 4
(Tasks 1, 2, 6) are independent. Task 7 verifies everything. Recommended order:
3 → 4 → 5 → 1 → 2 → 6 → 7.

VCS note: this repo is colocated jj. Per `dev-flow/references/vcs-preamble.md`,
always `jj commit -m "..."` to seal a change; never `jj new <rev>` mid-task (it
moves `@` and strands working-copy files).

---

### Task 1: Seam 1 — finishing-a-development-branch → review-pr

**Files:**

- Modify: `dev-flow/skills/finishing-a-development-branch/SKILL.md` (Option 2, both git and jj paths)

- [ ] **Step 1: Add the review-pr suggestion after the git PR-create block**

In `dev-flow/skills/finishing-a-development-branch/SKILL.md`, find the
`#### Option 2: Push and Create PR` section. Immediately before the
`**Do NOT clean up workspace** — user needs it alive to iterate on PR feedback.`
line (which follows the jj `gh pr create` block), insert:

```markdown
After the PR is created, suggest (do NOT run automatically):

> "PR #<n> created. Consider running `/review-pr <n>` to get a structured
> multi-aspect review before requesting human review."
```

- [ ] **Step 2: Verify the suggestion is present and conditional**

Run: `grep -n "review-pr <n>" dev-flow/skills/finishing-a-development-branch/SKILL.md`
Expected: one match inside Option 2.

- [ ] **Step 3: Lint**

Run: `rumdl check --no-exclude dev-flow/skills/finishing-a-development-branch/SKILL.md`
Expected: `Success: No issues found`.

- [ ] **Step 4: Commit**

Commit per `references/vcs-preamble.md`.
Message: `feat(dev-flow): suggest /review-pr after PR creation (fhsk-cph)`

---

### Task 2: Seam 2 — review-pr → address-findings

**Files:**

- Modify: `dev-flow/skills/review-pr/SKILL.md` (append step 11 after the step-10 comment template, ~line 272)

- [ ] **Step 1: Append the address-findings handoff step**

In `dev-flow/skills/review-pr/SKILL.md`, after the `### 10. Offer to Post`
section and its trailing comment-template fenced block (the file currently ends
there, ~line 272), append a new `### 11. Suggest the Fix Loop` section with this
structure (verbatim heading + content):

- Heading: `### 11. Suggest the Fix Loop`
- Intro line: "After presenting (and optionally posting) findings, check whether
  any findings were filed:"
- A `bash` fenced block containing exactly:
  `bd list --parent <parent-bead-id> --status open --json | jq 'length'`
- A bullet list:
  - **If > 0:** suggest (do NOT run automatically): "N findings filed. Run
    `/address-findings <number>` to work through them with isolated fix-workers
    and review gates."
  - **If 0:** report "No findings — the PR looks clean for the reviewed
    aspects." and stop.

The intent: a conditional handoff that never auto-runs `address-findings`,
mirroring step 10's "do not post without confirmation" discipline.

- [ ] **Step 2: Verify step 11 exists**

Run: `grep -n "### 11. Suggest the Fix Loop\|address-findings <number>" dev-flow/skills/review-pr/SKILL.md`
Expected: both matches present.

- [ ] **Step 3: Lint**

Run: `rumdl check --no-exclude dev-flow/skills/review-pr/SKILL.md`
Expected: `Success: No issues found`.

- [ ] **Step 4: Commit**

Commit per `references/vcs-preamble.md`.
Message: `feat(dev-flow): suggest /address-findings after review-pr (fhsk-cph)`

---

### Task 3: Seam 3a — author the merged vcs-preamble.md

**Files:**

- Modify: `dev-flow/references/vcs-preamble.md` (rewrite to merged sectioned form)
- Delete: `dev-flow/references/vcs-detection-preamble.md`
- [ ] **Step 1: Rewrite `dev-flow/references/vcs-preamble.md` with this exact content**

````markdown
# VCS Preamble

Detect the active VCS and use the appropriate commands throughout the skill or
agent. The **core sections** (Detection through Note on jj Rebase Flag) apply to
all consumers. The **Worktree-Isolated Agent Startup** and **Orchestrator
Contract** sections at the end apply only to worktree-isolated review agents and
the orchestrator skills that dispatch them.

## Detection

```bash
VCS=$( \
  if jj root >/dev/null 2>&1; then echo "jj"; \
  elif git rev-parse --git-dir >/dev/null 2>&1; then echo "git"; \
  else echo "none"; fi \
)
if [[ "$VCS" == "none" ]]; then
  echo "STATUS: FAILED -- No VCS detected (not inside a jj or git repository)"
  exit 1
fi
```

- `jj root` succeeds in any jj workspace (including workspaces where `.jj/` is
  absent from the working directory).
- `git rev-parse --git-dir` succeeds in git worktrees where `.git` is a file
  rather than a directory.
- If the result is "none", the block above exits. Backup prose instruction:
  STOP and report `STATUS: FAILED -- No VCS detected`.

## Command Mapping

| Operation | git | jj |
|-----------|-----|-----|
| Create workspace | `git worktree add ../<repo>_worktrees/<name> -b <branch>` | `jj workspace add ../<repo>_worktrees/<name> --name <name>` |
| List workspaces | `git worktree list` | `jj workspace list` |
| Remove workspace | `git worktree remove <path>` | `jj workspace forget <name>` + `rm -rf <path>` |
| Commit | `git add <files> && git commit -m "msg"` | `jj commit -m "msg"` |
| Describe/amend | `git commit --amend -m "msg"` | `jj describe -m "msg"` |
| New change | N/A (implicit with commit) | `jj new` |
| Create branch/bookmark | `git checkout -b <name>` | `jj bookmark create <name> -r @` |
| Push | `git push -u origin <branch>` | `jj bookmark set <name> -r @ && jj git push -b <name>` |
| Fetch | `git fetch` / `git pull` | `jj git fetch` |
| Diff range (review) | `git diff <base_sha>..<head_sha>` | `jj diff --from <rev1> --to <rev2>` |
| Integrate fix | `git cherry-pick <sha>` | `jj rebase -r <change-id> -o <target>` |
| Merge to main | `git checkout main && git merge <branch>` | `jj rebase -s <rev> -o main --skip-emptied` |
| Delete branch/bookmark | `git branch -d <name>` | `jj bookmark delete <name>` |
| Force delete | `git branch -D <name>` | `jj abandon <rev>` + `jj bookmark delete <name>` |
| Current location | `git branch --show-current` | `jj log -r @ --no-graph -T 'change_id.short(8)'` |
| Status | `git status` | `jj st` |

## Workspace Path Convention

All workspaces use the **sibling directory** pattern to avoid confusing LSP servers:

```text
<repo>/                    # main repo
<repo>_worktrees/          # workspace parent (sibling)
  feature-auth/            # one workspace per task
  fix-bug-123/
```

## jj-Specific Rules

When VCS is jj, follow these additional rules:

- Always `jj git fetch` at the start of any task
- Always `jj commit -m "..."` before `jj new` — `jj new` moves `@` and files
  in the old change leave the working directory (lost-work footgun)
- Use **change IDs** (not commit hashes) — they survive rewrites
- Do NOT `jj describe` or rewrite commits that have been pushed
- Use `--skip-emptied` for cleanup rebases (auto-abandons empty commits)
- Prefer `jj rebase --skip-emptied` over manual `jj abandon`
- `@` is the empty working-copy commit; use `@-` for the meaningful committed
  state when verifying or reviewing

## Note on jj Rebase Flag

The destination flag for `jj rebase` is `-o` / `--onto` (not `-d` /
`--destination`, which is deprecated). All examples in this file use `-o`.

---

## Worktree-Isolated Agent Startup

> Worktree-isolated review agents MUST follow this section after Detection.
> General workflow skills, and orchestrator skills running from the main repo
> root, skip everything below this line.

### Verify location

Confirm the agent is operating inside a worktree workspace (sibling
`_worktrees/` directory), not the default workspace:

- **jj:**

  ```bash
  _cwd=$(pwd -P 2>/dev/null) || _cwd=$(pwd)
  _parent_dir=$(basename "$(dirname "$_cwd")")
  case "$_parent_dir" in
    *_worktrees) ;;  # good
    *)
      echo "STATUS: FAILED -- Operating in default workspace (direct parent '$_parent_dir' does not end in _worktrees). Dispatch to a worktree workspace instead."
      exit 1
      ;;
  esac
  ```

  The check verifies the **direct parent directory** ends with `_worktrees`, so
  a repo at `/home/user/code_worktrees/myrepo` (parent: `myrepo`) does not
  trigger a false positive. Do NOT rely on `jj workspace list` to identify the
  current workspace; jj 0.39+ emits no `(current)` marker. A false-negative
  causes a safe `STATUS: FAILED` (the agent refuses to proceed; no corruption).

- **git:**

  ```bash
  _branch=$(git branch --show-current 2>/dev/null) || {
    echo "STATUS: FAILED -- git branch check failed"; exit 1
  }
  [[ -z "$_branch" ]] && {
    echo "STATUS: FAILED -- detached HEAD in git worktree — expected branch worktree/*"; exit 1
  }
  case "$_branch" in
    worktree/*) ;;  # good — operating on a worktree branch
    *)
      echo "STATUS: FAILED -- On branch '$_branch', expected worktree/*"
      exit 1
      ;;
  esac
  ```

If anything looks wrong, STOP and report `STATUS: FAILED`.

### Path rules (worktree agents)

- Use ONLY relative paths for all file operations.
- Do NOT `cd` outside your working directory.
- Do NOT use absolute paths from diffs or PR metadata — translate them to
  relative paths within your worktree.

Use the detected VCS for all operations. When jj is detected, you MUST use jj
for ALL mutating VCS operations (commits, workspaces, rebases, status). Never
use mutating git commands in jj repos. Read-only git and `gh` CLI are safe. See
`dev-flow/references/vcs-equivalence.md` for command equivalents.

## Orchestrator Contract

When a worktree-isolated agent reports `STATUS: FAILED` with a VCS detection
failure message:

1. **Do NOT retry** — VCS detection failure is deterministic; the worktree was
   created without proper VCS initialization.
2. **Log the failure** — include the agent name and worktree path.
3. **Clean up the worktree** — it is unusable without VCS.
4. **Re-queue the finding** — mark FAILED with the VCS error detail.

Orchestrator skills (`address-findings`, `review-pr`) should check for
`STATUS: FAILED` in agent responses before parsing VCS-specific fields
(`WORKTREE_BRANCH`, `CHANGE_ID`).
````

- [ ] **Step 2: Delete the old detection preamble**

Run: `rm -f dev-flow/references/vcs-detection-preamble.md`

- [ ] **Step 3: Lint the merged file**

Run: `rumdl check --no-exclude dev-flow/references/vcs-preamble.md`
Expected: `Success: No issues found`.

- [ ] **Step 4: Commit**

Commit per `references/vcs-preamble.md`.
Message: `refactor(dev-flow): merge vcs-detection-preamble into vcs-preamble (fhsk-cph)`

---

### Task 4: Seam 3b — retarget the 17 references

**Files:**

- Modify: 12 review agents + 3 review skills referencing `vcs-detection-preamble.md` (path substitution)
- Modify: `dev-flow/references/vcs-equivalence.md` (prose reword)
- Modify: `dev-flow/evals/evals.json` (expected-text reword)
- [ ] **Step 1: Path-substitute the agent + skill references**

The 12 review agents and 3 review skills reference the file by path. Substitute
the path across them:

```bash
grep -rl "vcs-detection-preamble.md" dev-flow/agents/ dev-flow/skills/ \
  | xargs sed -i '' 's#vcs-detection-preamble\.md#vcs-preamble.md#g'
```

(`sed -i ''` is BSD/macOS; GNU sed uses `sed -i`.)

- [ ] **Step 2: Reword the prose reference in vcs-equivalence.md**

Note: Step 1's `sed` scope (`dev-flow/agents/ dev-flow/skills/`) does **not**
reach `dev-flow/references/`, so this file is untouched by it and needs a manual
edit. Line 11 reads:

```text
**Note:** The detection pattern (see `vcs-detection-preamble.md`) uses `jj root`
```

Edit it to reference the merged file's Detection section:

```text
**Note:** The detection pattern (see the Detection section of `vcs-preamble.md`) uses `jj root`
```

- [ ] **Step 3: Reword the evals.json reference**

`dev-flow/evals/evals.json` references `vcs-detection-preamble` inside an
`expected_output` (or similar) string describing agent behavior. Update that
string to say `vcs-preamble` so the eval describes what agents actually
reference post-merge. Keep the JSON valid.

- [ ] **Step 4: Verify no detection-preamble reference survives**

Run: `grep -rn "vcs-detection-preamble" dev-flow/ | grep -v CHANGELOG`
Expected: no output.

- [ ] **Step 5: Validate JSON + lint**

Run:

```bash
jq empty dev-flow/evals/evals.json
rumdl check --no-exclude dev-flow/references/vcs-equivalence.md \
  dev-flow/agents/*.md dev-flow/skills/review-pr/SKILL.md \
  dev-flow/skills/address-findings/SKILL.md \
  dev-flow/skills/respond-to-comments/SKILL.md
```

Expected: no jq error; `rumdl` clean.

- [ ] **Step 6: Commit**

Commit per `references/vcs-preamble.md`.
Message: `refactor(dev-flow): retarget vcs-detection-preamble refs to vcs-preamble (fhsk-cph)`

---

### Task 5: Seam 3c — update the coupled test filter

**Files:**

- Modify: `tests/test_agent_guidance_docs.py:30` (the review-agent filter)

- [ ] **Step 1: Swap the dead marker, keep `vcs-equivalence`**

In `tests/test_agent_guidance_docs.py`, the review-agent filter currently reads:

```python
        if "vcs-detection-preamble" not in text and "vcs-equivalence" not in text:
            continue
```

Replace it with:

```python
        if "vcs-preamble" not in text and "vcs-equivalence" not in text:
            continue
```

Rationale: after Task 3/4, the 12 agents that referenced `vcs-detection-preamble`
now reference `vcs-preamble`; `review-gate.md` references only `vcs-equivalence`;
the 3 read-only reviewers reference neither. Keeping both markers selects exactly
the 13 review agents. Dropping `vcs-equivalence` would exclude `review-gate` and
fail `assert checked >= 13`.

- [ ] **Step 2: Run the agent-guidance test**

Run: `uv run --with pytest pytest tests/test_agent_guidance_docs.py -v --import-mode=importlib`
Expected: both tests PASS; the review-agent test reports `checked >= 13`.

- [ ] **Step 3: Commit**

Commit per `references/vcs-preamble.md`.
Message: `test(dev-flow): key agent-guidance filter on merged vcs-preamble (fhsk-cph)`

---

### Task 6: Seam 4 — disambiguate code-reviewer

**Files:**

- Modify: `dev-flow/agents/code-reviewer.md` (role note)
- Modify: `dev-flow/skills/requesting-code-review/code-reviewer.md` (template note)
- Modify: `dev-flow/skills/subagent-driven-development/SKILL.md` (lines ~60, ~243)
- [ ] **Step 1: Note the agent's review-pr-only role**

In `dev-flow/agents/code-reviewer.md`, immediately after the `# Code Reviewer`
H1, insert:

```markdown
> **Scope:** This is the `review-pr` orchestrator's `code`-aspect agent. It is
> dispatched only with the orchestrator contract (`PARENT_BEAD_ID`, `PR_URL`,
> `ASPECT`) and files findings as beads. For ad-hoc or in-session code review
> (no review epic), use the `requesting-code-review` skill's template instead.
```

- [ ] **Step 2: Note the template's distinct role**

In `dev-flow/skills/requesting-code-review/code-reviewer.md`, immediately after
the `# Code Reviewer Prompt Template` H1 / its first line, insert:

```markdown
> This is the in-session review **template** (filled by a `general-purpose`
> subagent). It is distinct from the `code-reviewer` agent
> (`dev-flow/agents/code-reviewer.md`), which is the `review-pr` orchestrator's
> bd-finding agent.
```

- [ ] **Step 3: Fix the SDD subagent_type mapping (line ~60)**

In `dev-flow/skills/subagent-driven-development/SKILL.md`, the bullet currently
reads:

```markdown
   - **`subagent_type`** — map the bead's `skills[]` to an available agent type. Heuristic: `general-purpose` if no match; `code-reviewer` if `skills[]` includes `review`; specific types (e.g. `test-author`) if available and matching. Implementer judgment governs the mapping when multiple skills overlap.
```

Replace with:

```markdown
   - **`subagent_type`** — map the bead's `skills[]` to an available agent type. Heuristic: `general-purpose` if no match; specific types (e.g. `test-author`) if available and matching. Do NOT map `skills[]` containing `review` to the `code-reviewer` agent — that agent is the `review-pr` orchestrator's bd-finding agent and requires the orchestrator contract. In-session review is handled by the two-stage review below (spec then quality) using the `requesting-code-review` template via `general-purpose`. Implementer judgment governs the mapping when multiple skills overlap.
```

- [ ] **Step 4: Reconcile the "final code-reviewer" line (~243)**

In the same file, the example line reads:

```markdown
[Dispatch final code-reviewer (opus) for entire implementation]
```

Replace with:

```markdown
[Dispatch final code-quality review (opus) for the entire implementation, using the requesting-code-review template via general-purpose]
```

- [ ] **Step 5: Lint the touched files**

Run: `rumdl check --no-exclude dev-flow/agents/code-reviewer.md dev-flow/skills/requesting-code-review/code-reviewer.md dev-flow/skills/subagent-driven-development/SKILL.md`
Expected: `Success: No issues found`.

- [ ] **Step 6: Commit**

Commit per `references/vcs-preamble.md`.
Message: `docs(dev-flow): disambiguate code-reviewer agent vs requesting-code-review template (fhsk-cph)`

---

### Task 7: Full-surface verification

**Files:**

- (No file changes unless a guard fails)

- [ ] **Step 1: Dangling-reference guard**

Run: `grep -rn "vcs-detection-preamble" . 2>/dev/null | grep -v CHANGELOG | grep -v '\.jj/'`
Expected: no output (file and all references gone).

- [ ] **Step 2: Full test suite**

Run: `uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ --import-mode=importlib -q`
Expected: all pass (the worktree-create temp-repo test is occasionally flaky on
parallel runs; re-run once if a single git-commit error appears).

- [ ] **Step 3: Reproduce the CI lint command**

Run:

```bash
rumdl check --no-exclude homelab/skills/*/SKILL.md \
  dev-flow/skills/review-pr/SKILL.md \
  dev-flow/skills/address-findings/SKILL.md \
  dev-flow/skills/respond-to-comments/SKILL.md \
  jj/skills/*/SKILL.md \
  dev-flow/skills/using-worktrees/SKILL.md \
  dev-flow/skills/requesting-code-review/SKILL.md \
  dev-flow/references/vcs-preamble.md \
  jj/commands/*.md \
  dev-flow/agents/*.md
```

Expected: `Success: No issues found`.

- [ ] **Step 4: Confirm the handoffs and disambiguation landed**

Run:

```bash
grep -c "review-pr <n>" dev-flow/skills/finishing-a-development-branch/SKILL.md
grep -c "address-findings <number>" dev-flow/skills/review-pr/SKILL.md
grep -c "review-pr. orchestrator" dev-flow/agents/code-reviewer.md
```

Expected: each `>= 1`.

- [ ] **Step 5: Commit (only if a guard required a fix)**

Commit per `references/vcs-preamble.md`.
Message: `test(dev-flow): verify review pipeline seam wiring (fhsk-cph)`
<!-- adr-capture: sha256=0deec0c50ca3efc1; session=15501658; ts=2026-05-28T21:15:50Z; adrs= -->
