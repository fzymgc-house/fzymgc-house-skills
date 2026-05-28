# Consolidate pr-review Under dev-flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate the `pr-review` plugin's skills, agents, references, and evals
into `dev-flow`, removing `pr-review` as an independent plugin — a pure
structural move with no behavior change.

**Architecture:** Move files, retarget internal `pr-review/` path references to
`dev-flow/`, drop `pr-review` from both marketplaces and from release-please,
delete its Codex wrapper, add the missing `agents` symlink to the dev-flow
wrapper, and update the tests + docs that name `pr-review`. The repo is a
colocated jj repo: jj auto-tracks plain `mv`/`rm`; use jj for any explicit VCS
op per `references/vcs-preamble.md`.

**Tech Stack:** Markdown skill/agent artifacts; JSON manifests
(`marketplace.json`, `release-please-config.json`, `.release-please-manifest.json`);
`jq` for JSON validation; `rumdl` for markdown lint; `pytest` for the repo test
suite; `bd` substrate is unaffected.

---

## Spec

`docs/superpowers/specs/2026-05-28-consolidate-pr-review-under-dev-flow-design.md`
(design-reviewer READY). Read it before starting.

## Refinement of spec Section H (grounded during planning)

The spec said the agent-guidance test, repointed at `dev-flow/agents`, "should
hold for all 16" agents. Grounding showed this is **false**: dev-flow's three
existing agents (`adr-extractor`, `design-reviewer`, `plan-reviewer`) are
read-only reviewers that do **not** contain `Read `AGENTS.md`` and do not run in
worktrees. Asserting on all 16 would break the test. The 13 moved review agents
are exactly those whose body references a VCS preamble
(`vcs-detection-preamble` or `vcs-equivalence`). Task 5 therefore **filters** the
test to those agents rather than asserting on every file in `dev-flow/agents/`.

## File Structure / ordering

A structural move cannot leave every intermediate commit green: the test suite
references `pr-review` paths until Task 5 lands. This is expected (the spec's
Verification section states it). Tasks run in this order so the final state is
green: move (1) → retarget refs (2) → marketplaces + wrapper (3) → release-please
(4) → tests (5) → docs (6) → full verification (7).

---

### Task 1: Move the pr-review tree into dev-flow

**Files:**

- Move: `pr-review/agents/*.md` → `dev-flow/agents/`
- Move: `pr-review/skills/{review-pr,address-findings,respond-to-comments}` → `dev-flow/skills/`
- Move: `pr-review/references/{vcs-detection-preamble,vcs-equivalence,code-slop,prose-slop}.md` → `dev-flow/references/`
- Move: `pr-review/evals/` → `dev-flow/evals/`
- Delete: `pr-review/plugin.json`, `pr-review/CHANGELOG.md`, and the three skill `CHANGELOG.md` files (removed with the directory)
- [ ] **Step 1: Move agents, skills, references, evals**

Run:

```bash
mv pr-review/agents/*.md dev-flow/agents/
mv pr-review/skills/review-pr pr-review/skills/address-findings pr-review/skills/respond-to-comments dev-flow/skills/
mv pr-review/references/vcs-detection-preamble.md pr-review/references/vcs-equivalence.md pr-review/references/code-slop.md pr-review/references/prose-slop.md dev-flow/references/
mv pr-review/evals dev-flow/evals
```

- [ ] **Step 2: Remove the now-empty pr-review tree**

Run:

```bash
rm -f pr-review/plugin.json
rm -rf pr-review
```

Note: `pr-review/evals-workspace/` is gitignored (untracked) and is removed by
`rm -rf pr-review`; nothing tracked is lost.

- [ ] **Step 3: Verify the move landed**

Run:

```bash
ls dev-flow/agents/ | wc -l
ls dev-flow/skills/ | grep -E 'review-pr|address-findings|respond-to-comments'
ls dev-flow/references/ | grep -E 'vcs-detection-preamble|vcs-equivalence|code-slop|prose-slop'
test ! -d pr-review && echo "pr-review removed"
```

Expected: agent count is `16`; three review skills listed; four references listed; `pr-review removed`.

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `refactor(dev-flow): move pr-review tree into dev-flow (fhsk-ddw)`

---

### Task 2: Retarget internal path references and strip version markers

**Files:**

- Modify: the 12 moved agents referencing `pr-review/references/vcs-detection-preamble.md`
- Modify: `dev-flow/agents/{fix-worker,verification-runner,review-gate}.md` and `dev-flow/references/vcs-detection-preamble.md` (reference `vcs-equivalence.md`)
- Modify: `dev-flow/agents/slop-hunter.md` (references `code-slop.md`, `prose-slop.md`)
- Modify: `dev-flow/skills/review-pr/SKILL.md`, `dev-flow/skills/address-findings/SKILL.md`
- Modify: `dev-flow/skills/{review-pr,address-findings,respond-to-comments}/SKILL.md` (strip version markers)
- [ ] **Step 1: Retarget all `pr-review/` path prefixes to `dev-flow/`**

Every internal reference uses one of four paths. Replace the `pr-review/`
prefix with `dev-flow/` across all moved files:

```bash
grep -rl "pr-review/" dev-flow/agents/ dev-flow/skills/ dev-flow/references/ \
  | xargs sed -i '' 's#pr-review/references/#dev-flow/references/#g'
```

(`sed -i ''` is the BSD/macOS form; on GNU sed use `sed -i`.) This covers all
four referenced paths since every one is under `pr-review/references/`.

- [ ] **Step 2: Verify no `pr-review/` path reference remains in moved files**

Run: `grep -rn "pr-review/" dev-flow/ | grep -v CHANGELOG`
Expected: no output.

- [ ] **Step 3: Strip orphaned release-please version markers**

The three moved SKILL.md files carry `version: X.Y.Z # x-release-please-version`
in their metadata. Since they no longer have release-please packages
(Decision 2), remove those marker lines. For each of
`dev-flow/skills/review-pr/SKILL.md`,
`dev-flow/skills/address-findings/SKILL.md`,
`dev-flow/skills/respond-to-comments/SKILL.md`, delete the line matching
`^  version: .* # x-release-please-version$` from the YAML frontmatter.

- [ ] **Step 4: Verify the markers are gone**

Run: `grep -rn "x-release-please-version" dev-flow/skills/review-pr dev-flow/skills/address-findings dev-flow/skills/respond-to-comments`
Expected: no output.

- [ ] **Step 5: Lint the touched markdown**

Run:

```bash
rumdl check dev-flow/skills/review-pr/SKILL.md \
  dev-flow/skills/address-findings/SKILL.md \
  dev-flow/skills/respond-to-comments/SKILL.md dev-flow/agents/*.md
```

Expected: `Success: No issues found`.

- [ ] **Step 6: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `refactor(dev-flow): retarget pr-review path refs + drop version markers (fhsk-ddw)`

---

### Task 3: Update marketplaces and the Codex wrapper

**Files:**

- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`
- Delete: `plugins/pr-review/`
- Create: `plugins/dev-flow/agents` symlink
- [ ] **Step 1: Remove the `pr-review` entry from the Claude marketplace**

In `.claude-plugin/marketplace.json`, delete the object in `.plugins[]` whose
`name` is `"pr-review"` (the `{ "name": "pr-review", "description": ..., "source": "./pr-review" }`
entry). Resulting plugin order: `homelab`, `jj`, `dev-flow`.

- [ ] **Step 2: Remove the `pr-review` entry from the Codex marketplace**

In `.agents/plugins/marketplace.json`, delete the object in `.plugins[]` whose
`name` is `"pr-review"` (the entry with `source.path == "./plugins/pr-review"`).

- [ ] **Step 3: Delete the pr-review Codex wrapper**

Run: `rm -rf plugins/pr-review`

- [ ] **Step 4: Add the `agents` symlink to the dev-flow wrapper**

`plugins/dev-flow/` currently has `hooks`, `references`, `scripts`, `skills`
symlinks but no `agents`. Add it so the 16 agents are exposed to Codex:

```bash
ln -s ../../dev-flow/agents plugins/dev-flow/agents
```

- [ ] **Step 5: Verify JSON validity and the symlink**

Run:

```bash
jq empty .claude-plugin/marketplace.json .agents/plugins/marketplace.json
jq -r '.plugins[].name' .claude-plugin/marketplace.json
ls -L plugins/dev-flow/agents/ | wc -l
test ! -d plugins/pr-review && echo "wrapper removed"
```

Expected: no jq error; the three names `homelab`, `jj`, `dev-flow` (one per
line); agent count `16`; `wrapper removed`.

- [ ] **Step 6: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `refactor(dev-flow): drop pr-review from marketplaces + add dev-flow agents symlink (fhsk-ddw)`

---

### Task 4: Remove pr-review release-please packages

**Files:**

- Modify: `release-please-config.json`
- Modify: `.release-please-manifest.json`
- [ ] **Step 1: Remove the four `pr-review*` package entries from the config**

In `release-please-config.json`, delete these keys from `.packages`:
`"pr-review"`, `"pr-review/skills/review-pr"`,
`"pr-review/skills/address-findings"`, `"pr-review/skills/respond-to-comments"`.

- [ ] **Step 2: Remove the four `pr-review*` keys from the manifest**

In `.release-please-manifest.json`, delete the keys `"pr-review"`,
`"pr-review/skills/review-pr"`, `"pr-review/skills/address-findings"`,
`"pr-review/skills/respond-to-comments"`.

- [ ] **Step 3: Verify validity and absence**

Run:

```bash
jq empty release-please-config.json .release-please-manifest.json
jq -r '.packages | keys[]' release-please-config.json | grep -c pr-review
jq -r 'keys[]' .release-please-manifest.json | grep -c pr-review
```

Expected: no jq error; both grep counts are `0`.

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `chore(dev-flow): drop pr-review release-please packages (fhsk-ddw)`

---

### Task 5: Update the test suite

**Files:**

- Modify: `tests/test_agent_guidance_docs.py`
- Modify: `tests/test_codex_marketplace.py`
- [ ] **Step 1: Repoint and filter the agent-guidance test**

In `tests/test_agent_guidance_docs.py`, replace the `PR_REVIEW_AGENTS_DIR`
constant and the test body so it targets `dev-flow/agents` but only asserts on
the worktree review agents (those referencing a VCS preamble), preserving the
original guarantee without breaking on dev-flow's three read-only reviewers.

Replace line 9:

```python
PR_REVIEW_AGENTS_DIR = REPO_ROOT / "pr-review" / "agents"
```

with:

```python
AGENTS_DIR = REPO_ROOT / "dev-flow" / "agents"
```

Replace the entire `test_pr_review_agents_read_agents_before_claude` function
with:

```python
def test_review_agents_read_agents_before_claude() -> None:
    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    assert agent_files

    checked = 0
    for agent_file in agent_files:
        text = agent_file.read_text()
        # Only worktree-isolated review agents carry a VCS preamble; the
        # read-only artifact reviewers (adr-extractor, design-reviewer,
        # plan-reviewer) do not and are out of scope for this assertion.
        if "vcs-detection-preamble" not in text and "vcs-equivalence" not in text:
            continue
        checked += 1
        assert "Read `AGENTS.md`" in text, f"{agent_file} must read AGENTS.md"
        if "CLAUDE.md" in text:
            assert text.index("AGENTS.md") < text.index("CLAUDE.md"), (
                f"{agent_file} must reference AGENTS.md before CLAUDE.md"
            )

    assert checked >= 13, f"expected >=13 review agents, checked {checked}"
```

- [ ] **Step 2: Update the Codex marketplace test constants**

In `tests/test_codex_marketplace.py`, replace line 9:

```python
EXPECTED_PLUGIN_ORDER = ["homelab", "pr-review", "jj", "dev-flow"]
```

with:

```python
EXPECTED_PLUGIN_ORDER = ["homelab", "jj", "dev-flow"]
```

and replace the `EXPECTED_EXTRA_PATHS` dict (lines 10-15):

```python
EXPECTED_EXTRA_PATHS = {
    "homelab": [".mcp.json"],
    "pr-review": ["agents", "references"],
    "jj": ["hooks", "commands"],
    "dev-flow": ["hooks", "references", "scripts"],
}
```

with:

```python
EXPECTED_EXTRA_PATHS = {
    "homelab": [".mcp.json"],
    "jj": ["hooks", "commands"],
    "dev-flow": ["agents", "hooks", "references", "scripts"],
}
```

- [ ] **Step 3: Run the affected tests**

Run: `uv run --with pytest pytest tests/test_agent_guidance_docs.py tests/test_codex_marketplace.py -v --import-mode=importlib`
Expected: all tests PASS (the agent-guidance test reports `checked >= 13`; the
marketplace tests accept the three-plugin layout and dev-flow's `agents` path).

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `test(dev-flow): update agent + marketplace tests for consolidation (fhsk-ddw)`

---

### Task 6: Update docs

**Files:**

- Modify: `AGENTS.md` (CLAUDE.md is a symlink to it)
- Modify: `README.md`
- [ ] **Step 1: Update AGENTS.md**

In `AGENTS.md`: change the four-plugin description to three (`homelab`, `jj`,
`dev-flow`); update the repository-structure tree so the `pr-review/` subtree is
removed and the review skills (`review-pr`, `address-findings`,
`respond-to-comments`), the review agents, and the slop catalogs appear under
`dev-flow/`. Update any prose that enumerates the four source plugins.

- [ ] **Step 2: Update README.md**

In `README.md`: remove the `### pr-review` section heading and fold its content
into the `dev-flow` description; delete the
`claude plugin install pr-review@fzymgc-house-skills` command; update the Codex
prose that names `pr-review/` and `plugins/pr-review/`; remove the `pr-review/`
line from the structure tree.

- [ ] **Step 3: Verify docs lint and reference cleanliness**

Run: `rumdl check AGENTS.md README.md && grep -rn "pr-review" AGENTS.md README.md | grep -v CHANGELOG`
Expected: `rumdl` clean; the grep returns nothing (no surviving `pr-review`
mention in either doc).

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `docs(dev-flow): update AGENTS.md + README for pr-review consolidation (fhsk-ddw)`

---

### Task 7: Full-surface verification

**Files:**

- (No file changes unless a guard fails)

- [ ] **Step 1: Dangling-reference guard**

Run: `grep -rn "pr-review/" dev-flow/ .claude-plugin/ .agents/ plugins/ ./*.json ./*.md 2>/dev/null | grep -v CHANGELOG`
Expected: no output (no surviving `pr-review/` path reference outside CHANGELOGs;
`evals-workspace/` no longer exists).

- [ ] **Step 2: No-plugin guard**

Run:

```bash
grep -l "pr-review" .claude-plugin/marketplace.json \
  .agents/plugins/marketplace.json release-please-config.json \
  .release-please-manifest.json 2>/dev/null
```

Expected: no output (no manifest or release-please file names `pr-review`).

- [ ] **Step 3: Symlink guard**

Run: `ls -l plugins/dev-flow/ | grep -E 'agents|hooks|references|scripts|skills' | wc -l && ls -L plugins/dev-flow/agents/ | wc -l`
Expected: `5` symlinks present; resolved `agents` dir lists `16`.

- [ ] **Step 4: Full test suite**

Run: `uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -v --import-mode=importlib`
Expected: all tests PASS.

- [ ] **Step 5: JSON + markdown sanity**

Run:

```bash
jq empty .claude-plugin/marketplace.json .agents/plugins/marketplace.json \
  release-please-config.json .release-please-manifest.json \
  plugins/*/.codex-plugin/plugin.json
rumdl check AGENTS.md README.md dev-flow/skills/review-pr/SKILL.md \
  dev-flow/skills/address-findings/SKILL.md \
  dev-flow/skills/respond-to-comments/SKILL.md
```

Expected: no jq error; `rumdl` clean.

- [ ] **Step 6: Commit (only if a guard required a fix)**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `test(dev-flow): verify pr-review consolidation (fhsk-ddw)`
<!-- adr-capture: sha256=33a36db76969a3f5; session=15501658; ts=2026-05-28T19:58:58Z; adrs= -->
