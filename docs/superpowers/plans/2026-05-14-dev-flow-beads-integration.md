<!-- markdownlint-disable MD013 -->

# `dev-flow` Beads Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [`docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`](../specs/2026-05-14-dev-flow-beads-integration-design.md)

**Goal:** Rebrand `superpowers/` → `dev-flow/` (fork independence), integrate `bd` as the canonical workflow tracker, lift 4 holomush skills, add full ADR capture subsystem, and add two in-session review-gate agents.

**Architecture:** Six sequenced phases. Phase 1 (rename) is foundational. Phases 2-5 fan out in parallel after Phase 1 merges. Phase 6 (modify existing skills to wire everything together) serializes after 3+4+5 merge. Each phase is one PR. The plan respects the spec's Rule 1: structural shapes go here (SKILL.md frontmatter, agent tools lists, JSON manifest edits, file paths, test code, command shapes); algorithmic function bodies are left to the implementer.

**Tech Stack:** Python 3.11+ (uv-managed), bash 3.2+ (hook scripts), bd v0.60.0 CLI, lefthook (pre-commit), rumdl (markdown lint), conventional commits via cog.

---

## File Structure

### Created by this plan

| Path | Phase | Responsibility |
|---|---|---|
| `dev-flow/AGENTS.md` | 2 | Codify Rules 1-7 + plugin runtime requirements |
| `dev-flow/README.md` | 1 | Single attribution to obra/superpowers v5.0.7; MCP-server install pointers |
| `dev-flow/scripts/scan-upstream` | 1 | Changelog reader (renamed from `sync-upstream`) |
| `dev-flow/skills/plan-to-beads/SKILL.md` | 3 | Materialize plan task table → bd state (epic + children, or standalones) |
| `dev-flow/skills/bead-create-smart/SKILL.md` | 3 | Thin helper for ad-hoc beads with structured bd flags |
| `dev-flow/skills/handoff-prompt/SKILL.md` | 3 | Self-contained briefing for cold-start sessions targeting a specific bead |
| `dev-flow/skills/capture-adrs/SKILL.md` | 4 | Orchestrator: extract → triage → write ADRs |
| `dev-flow/agents/adr-extractor.md` | 4 | Read-only sonnet; 4-criterion worthiness test + transcript scan |
| `dev-flow/agents/design-reviewer.md` | 5 | Read-only sonnet; READY/NOT READY verdict on spec |
| `dev-flow/agents/plan-reviewer.md` | 5 | Read-only sonnet; READY/NOT READY verdict on plan |
| `dev-flow/commands/review-design.md` | 5 | Slash invoke for design-reviewer |
| `dev-flow/commands/review-plan.md` | 5 | Slash invoke for plan-reviewer |
| `dev-flow/commands/capture-adrs.md` | 4 | Slash invoke for capture-adrs |
| `dev-flow/hooks/nudge-adr-capture` | 4 | `PostToolUse` hook (bash 3.2 compat) |
| `dev-flow/hooks/tests/test_nudge_adr_capture.bats` | 4 | 15-fixture test harness |
| `dev-flow/scripts/adr-doctor.sh` | 4 | Durable lint (changed-files-only via pre-commit, full pass via CI) |
| `docs/adr/README.md` | 4 | Auto-regenerated index with sentinels |
| `tests/test_dev_flow_marketplace.py` | 1 | Rename/expand of `tests/test_codex_marketplace.py` for new plugin name |

### Modified by this plan

| Path | Phase | Change |
|---|---|---|
| `superpowers/` | 1 | Renamed wholesale to `dev-flow/` |
| `plugins/superpowers/` | 1 | Renamed to `plugins/dev-flow/`; symlinks retargeted |
| `.claude-plugin/marketplace.json` | 1 | Entry `superpowers` → `dev-flow` |
| `.agents/plugins/marketplace.json` | 1 | Same |
| `release-please-config.json` | 1 | Package path + name |
| `.release-please-manifest.json` | 1 | Same |
| `AGENTS.md` (repo root) | 1, 2 | Path refs + new section pointing at `dev-flow/AGENTS.md` for Rules 1-7 |
| `lefthook.yml` | 4 | Add `adr-doctor` hook |
| `dev-flow/skills/brainstorming/SKILL.md` | 6 | Design bead open + Rule 7 grounding checklist + design-reviewer auto-fire |
| `dev-flow/skills/writing-plans/SKILL.md` | 6 | Design-bead notes + grounding verification + plan-reviewer + auto-fire chain |
| `dev-flow/skills/finishing-a-development-branch/SKILL.md` | 6 | Pre-flight bd check + interactive close after merge |
| `dev-flow/skills/subagent-driven-development/SKILL.md` | 6 | bd-driven task pickup + model-label dispatch |
| `dev-flow/skills/executing-plans/SKILL.md` | 6 | Same, serial execution |

### Deleted by this plan

| Path | Phase | Reason |
|---|---|---|
| `superpowers/scripts/sync-upstream` | 1 | Renamed to `scan-upstream` |
| Per-skill `upstream:` frontmatter | 1 | Single plugin-README attribution instead |
| `## Bead chain structure` plan-section convention references | 2 | Rule 4: no duplicate state — bd is source of truth |

---

## Phase 1: Foundation Rename

**Single PR.** Mechanical rename + path-reference sweep. Lands first; everything depends on it.

**Spec reference:** §"Implementation Order" → Phase 1; §"Identity: `superpowers` → `dev-flow`".

### Task 1.1: Rename directory + plugin entry

**Files:**

- Modify: `.claude-plugin/marketplace.json`
- Modify: `.agents/plugins/marketplace.json`
- Rename: `superpowers/` → `dev-flow/`
- Rename: `plugins/superpowers/` → `plugins/dev-flow/`
- Modify symlink targets inside `plugins/dev-flow/*` to point at `../../dev-flow/`
- [ ] **Step 1: Write the failing path test**

Modify `tests/test_codex_marketplace.py`:

```python
EXPECTED_PLUGIN_ORDER = ["homelab", "pr-review", "jj", "dev-flow"]
EXPECTED_EXTRA_PATHS = {
    "homelab": [".mcp.json"],
    "pr-review": ["agents", "references"],
    "jj": ["hooks", "commands"],
    "dev-flow": ["hooks", "references", "scripts"],
}
```

Rename file `tests/test_codex_marketplace.py` → `tests/test_dev_flow_marketplace.py` if you prefer (optional — the file name is just a test container; the test names remain).

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --with pytest pytest tests/test_codex_marketplace.py -v`
Expected: FAIL — `plugins/superpowers/` exists, `plugins/dev-flow/` does not; marketplace.json still says `superpowers`.

- [ ] **Step 3: Rename directories**

```bash
git mv superpowers dev-flow
git mv plugins/superpowers plugins/dev-flow
```

- [ ] **Step 4: Update symlinks inside `plugins/dev-flow/`**

Each symlink (`hooks`, `references`, `scripts`, `skills`) points at `../../superpowers/...`. Retarget each to `../../dev-flow/...`. Use `ln -sfn ../../dev-flow/<sub> plugins/dev-flow/<sub>` per entry; verify with `ls -la plugins/dev-flow/`.

- [ ] **Step 5: Update marketplace JSON entries**

`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`: rename the `superpowers` plugin entry's `name` and `path` (or `source.path`) to `dev-flow` / `./plugins/dev-flow`.

```bash
jq empty .claude-plugin/marketplace.json .agents/plugins/marketplace.json
```

Expected: both files parse cleanly.

- [ ] **Step 6: Run test to verify pass**

Run: `uv run --with pytest pytest tests/test_codex_marketplace.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(dev-flow): rename superpowers/ directory and plugin entry to dev-flow"
```

### Task 1.2: Update release-please config

**Files:**

- Modify: `release-please-config.json`
- Modify: `.release-please-manifest.json`
- [ ] **Step 1: Identify current entries**

Run: `jq 'to_entries | map(select(.value | tostring | contains("superpowers"))) | .[].key' release-please-config.json`
Same for `.release-please-manifest.json`.

- [ ] **Step 2: Replace `superpowers` with `dev-flow`**

For each match: edit the JSON in-place using `jq --argjson` or a structured Edit. Component name `superpowers` → `dev-flow`; path `superpowers/` → `dev-flow/`. Preserve all other config (release-please tag patterns, bump rules).

- [ ] **Step 3: Validate JSON**

```bash
jq empty release-please-config.json .release-please-manifest.json
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add release-please-config.json .release-please-manifest.json
git commit -m "chore(release-please): rename superpowers component to dev-flow"
```

### Task 1.3: Sweep AGENTS.md path references

**Files:**

- Modify: `AGENTS.md` (repo root; CLAUDE.md via symlink)

- [ ] **Step 1: Identify references**

Run: `grep -n "superpowers" AGENTS.md`
Expected ~6-10 hits across structure diagram, plugin list, file paths.

- [ ] **Step 2: Update references**

Each `superpowers` reference in AGENTS.md that refers to the plugin or its directory → `dev-flow`. Exceptions: historical references in citations or commit-message examples may stay if they're recounting facts (e.g., "originally derived from obra/superpowers v5.0.7"). When in doubt, update.

- [ ] **Step 3: Rumdl check**

Run: `rumdl check AGENTS.md`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): update path references for dev-flow rename"
```

### Task 1.4: Drop per-skill `upstream:` frontmatter; add plugin README

**Files:**

- Modify: All `dev-flow/skills/*/SKILL.md` with `upstream:` metadata
- Create: `dev-flow/README.md`
- [ ] **Step 1: Identify per-skill upstream references**

Run: `grep -rn "^  upstream:" dev-flow/skills/`
Expected: ~7 hits (the previously-modified forked skills).

- [ ] **Step 2: Remove from each frontmatter**

For each SKILL.md, remove the `upstream:` line from the YAML frontmatter `metadata:` block. Preserve other metadata (author, version).

- [ ] **Step 3: Author plugin README**

Create `dev-flow/README.md` with sections:

```markdown
# dev-flow

Development workflow skills, plus first-class beads + jj integration.

## Heritage

Originally derived from [obra/superpowers v5.0.7](https://github.com/obra/superpowers). Evolved independently with first-class jj VCS support, bead-based execution tracking, ADR capture, and adversarial in-session review gates.

Future upstream changes are reviewed via `scripts/scan-upstream` (changelog reader); cherry-picked selectively rather than auto-synced.

## Plugin runtime requirements

| Component | Purpose | Soft/Hard |
|---|---|---|
| `bd` CLI v0.60.0+ | Workflow tracking | Hard prerequisite |
| `mcp__probe__*` | Code grounding | Soft |
| `mcp__context7__*` | Library docs grounding | Soft |
| `mcp__deepwiki__*` | Repo conventions grounding | Soft |
| `mcp__exa__*` | Web search grounding | Soft |
| `mcp__firecrawl-mcp__*` or `firecrawl` skill | Page-content extraction | Soft |

See `AGENTS.md` for Rules 1-7 (conventions).
```

- [ ] **Step 4: Rumdl check**

Run: `rumdl check dev-flow/README.md`

- [ ] **Step 5: Commit**

```bash
git add dev-flow/README.md dev-flow/skills/
git commit -m "refactor(dev-flow): drop per-skill upstream metadata; single plugin README attribution"
```

### Task 1.5: Rename `sync-upstream` → `scan-upstream`

**Files:**

- Rename: `dev-flow/scripts/sync-upstream` → `dev-flow/scripts/scan-upstream`
- Modify: The script's preamble comment block
- [ ] **Step 1: Rename**

```bash
git mv dev-flow/scripts/sync-upstream dev-flow/scripts/scan-upstream
```

- [ ] **Step 2: Update preamble comments**

Inside the script, replace any "sync-upstream" reference and reframe the docstring/comments:

```text
# scan-upstream: read-only upstream changelog scanner.
# Surfaces upstream obra/superpowers changes for selective cherry-pick review.
# Does NOT auto-apply changes. Compare with the per-skill divergence ledger
# in references/upstream-manifest.md to decide what to lift.
```

The script's behavior (compute SHA against manifest's `upstream_version`, fetch tarball, surface diffs) stays the same — only the framing changes. Specifically: any "auto-apply verbatim files" code path should be replaced with "surface diff and prompt user to review" — but this is implementer-discretion territory; if removing the auto-apply is intrusive, just rename + reframe and leave behavior for a follow-up.

- [ ] **Step 3: Test invocation**

Run: `./dev-flow/scripts/scan-upstream --dry-run` (or whatever flag pattern the script supports).
Expected: completes without writing files; surfaces upstream changes (or "already up to date" if local matches latest tag).

- [ ] **Step 4: Commit**

```bash
git add dev-flow/scripts/
git commit -m "refactor(dev-flow): rename sync-upstream to scan-upstream; reframe as changelog reader"
```

### Task 1.6: Verification sweep

**Goal:** Confirm Phase 1 is complete via the spec's stated verification commands.

- [ ] **Step 1: Path-reference sweep**

Run:

```bash
rg "superpowers/" -g '!docs/superpowers/specs/2026-03-16-*' -g '!docs/superpowers/plans/' -g '!docs/superpowers/specs/2026-05-14-*' -g '!docs/superpowers/specs/2026-04-03-*' -g '!docs/superpowers/specs/2026-05-02-*' -g '!docs/superpowers/specs/2026-03-11-*'
```

Expected: empty (historical-spec excludes the original fork-design doc and the new dev-flow design + plan).

- [ ] **Step 2: Test suite green**

Run: `uv run --with pytest pytest tests/ .claude/hooks/tests/ jj/hooks/tests/ -v --import-mode=importlib`
Expected: all pass.

- [ ] **Step 3: bd flag re-verification**

```bash
bd create --help | grep -E "^[[:space:]]*--(type|parent|priority|labels|skills|spec-id|design|design-file|acceptance|notes|deps|waits-for|waits-for-gate|external-ref|validate|body-file|description|dry-run)\b"
```

Expected: every flag from Rule 3 appears at least once.

- [ ] **Step 4: bd edge-preservation sandbox test**

Run a quick sandbox check to confirm Rule 6's promotion preserves dep edges:

```bash
tmp=$(mktemp -d) && (cd "$tmp" && git init -q && bd init --prefix=t1 && \
  A=$(bd create --title "A" --type task --silent) && \
  B=$(bd create --title "B" --type task --silent) && \
  bd dep add "$B" "$A" && \
  bd update "$B" --type epic && \
  bd dep list "$B" | grep -q "$A" && echo "edges preserved" || echo "edges LOST")
```

Expected: `edges preserved`.

- [ ] **Step 5: No commits needed (verification-only task)**

If any step fails, file a follow-up issue and address before opening the Phase 1 PR.

---

## Phase 2: AGENTS.md Conventions

**Single PR.** Codifies Rules 1-7 in `dev-flow/AGENTS.md`. Pure docs; trivial risk.

**Spec reference:** §"Rule 1", §"Rule 2", §"Rule 3", §"Rule 4", §"Rule 5", §"Rule 6", §"Rule 7".

**Depends on:** Phase 1 merged (the `dev-flow/` directory must exist).

### Task 2.1: Author `dev-flow/AGENTS.md`

**Files:**

- Create: `dev-flow/AGENTS.md`

- [ ] **Step 1: Author the file**

Structure: H1 "Dev-Flow Conventions" + a brief preamble + one H2 per rule + the runtime-requirements table from `dev-flow/README.md` (or a link to it). Each Rule section is a near-verbatim copy of the spec's matching rule section, adapted for the agent-instruction tone (RFC2119 explicit, point at the spec for evidence/rationale).

Required H2 sections (verbatim wording):

```text
## Rule 1: Structure in specs/plans, implementation in code
## Rule 2: 3+ trackable tasks → epic
## Rule 3: Use bd's structured fields; description carries narrative only
## Rule 4: No duplicate state
## Rule 5: Model selection on beads (label-driven)
## Rule 6: The design bead — one bead spans the lifecycle
## Rule 7: Grounding before design — codebase + dependencies first
## bd config setup
```

- [ ] **Step 2: Add bd config setup section**

The setup section calls out `bd config set validation.on-create warn` as recommended (or `block` for strictness; default to `warn`):

```bash
bd config set validation.on-create warn
```

This enables bd's built-in section-requirement validation on every `bd create` without needing `--validate` per-call.

- [ ] **Step 3: Reference from repo-root AGENTS.md**

Modify `AGENTS.md` (repo root): add a section pointing at `dev-flow/AGENTS.md`:

```markdown
### Dev-Flow Conventions

For workflow-skill conventions (Rules 1-7 covering spec/plan discipline, bead lifecycle, model selection, and grounding tools), see [`dev-flow/AGENTS.md`](dev-flow/AGENTS.md).
```

- [ ] **Step 4: Lint**

Run: `rumdl check dev-flow/AGENTS.md AGENTS.md`
Expected: PASS.

- [ ] **Step 5: Smoke test the bd config setting**

```bash
bd config set validation.on-create warn
bd config get validation.on-create
```

Expected: returns `warn`.

- [ ] **Step 6: Commit**

```bash
git add dev-flow/AGENTS.md AGENTS.md
git commit -m "docs(dev-flow): codify Rules 1-7 in dev-flow/AGENTS.md"
```

---

## Phase 3: Lift the Holomush Skills

**Single PR.** Three skills lifted + adapted. `bead-chain-design` intentionally NOT lifted.

**Spec reference:** §"Skill Inventory" → "Lifted from holomush"; §"Rule 6"; §"Rule 7".

**Depends on:** Phase 1 merged.

### Task 3.1: Lift + adapt `plan-to-beads`

**Files:**

- Create: `dev-flow/skills/plan-to-beads/SKILL.md`
- Create: `dev-flow/skills/plan-to-beads/tests/test_plan_to_beads.py` (or `.bats` if shell-only)

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/skills/bead-chain-from-plan/SKILL.md`

- [ ] **Step 1: Write the failing test fixtures**

Create three sample plan files under `dev-flow/skills/plan-to-beads/tests/fixtures/`:

```text
fixtures/
├── plan-0-tasks.md       # design-only spec, no task table
├── plan-2-tasks.md       # 2 tasks; expect 2 standalone beads, design bead becomes first
└── plan-5-tasks.md       # 5 tasks; expect 1 epic + 5 child beads, design bead promoted
```

Write a test that invokes `plan-to-beads --dry-run <fixture>` and asserts the output bd-command manifest matches expected per Rule 6's lifecycle table.

```python
def test_plan_to_beads_dry_run_5_tasks_promotes_to_epic(plan_5_tasks_fixture, design_bead_id):
    result = subprocess.run(
        [SKILL_INVOKE, str(plan_5_tasks_fixture), "--design-bead", design_bead_id, "--dry-run"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert f"bd update {design_bead_id} --type=epic" in result.stdout
    assert result.stdout.count("bd create --type=task --parent") == 5
```

Repeat for 2-tasks and 0-tasks cases.

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run --with pytest pytest dev-flow/skills/plan-to-beads/tests/ -v`
Expected: FAIL — SKILL.md doesn't exist yet.

- [ ] **Step 3: Adapt SKILL.md from holomush**

Copy `bead-chain-from-plan/SKILL.md` from holomush as starting point. Major adaptations per spec:

- Drop all references to `## Bead chain structure` section parsing.
- Read plan's task table directly (look for the standard plan's `### Task N:` headers + the "Files" sub-list).
- Use the full bd flag set per Rule 3 (`--acceptance`, `--design-file`, `--spec-id`, `--notes`, `--deps`, `--labels`, `--skills`, `--parent`, `--type`, `--priority`).
- Implement Rule 6 lifecycle (3+/1-2/0 task buckets; design bead promotion via `bd update --type=epic`).
- Honor `--dry-run` by emitting `bd create ...` and `bd update ...` shell commands to stdout without executing.
- Honor `--force-update` to override the "already-materialized" guard.
- Detect already-materialized state via `bd list --spec-id <plan-path>`.

Reference the spec sections in the SKILL.md preamble; do NOT inline implementation logic.

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run --with pytest pytest dev-flow/skills/plan-to-beads/tests/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add dev-flow/skills/plan-to-beads/
git commit -m "feat(dev-flow): lift plan-to-beads skill from holomush; adapt to Rules 4/6"
```

### Task 3.2: Lift + adapt `bead-create-smart`

**Files:**

- Create: `dev-flow/skills/bead-create-smart/SKILL.md`
- Create: `dev-flow/skills/bead-create-smart/tests/test_bead_create_smart.py`

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/skills/bead-create-smart/SKILL.md`

- [ ] **Step 1: Write the failing test**

Test that invoking the skill with a minimal arg set (title + type + acceptance + parent) produces a valid `bd create` shell command using structured flags (not description-section padding):

```python
def test_bead_create_smart_uses_structured_flags():
    result = subprocess.run(
        [SKILL_INVOKE, "--title", "Add X", "--type", "task", "--parent", "test-epic-1",
         "--acceptance", "MUST do X", "--dry-run"],
        capture_output=True, text=True
    )
    assert "bd create" in result.stdout
    assert "--type task" in result.stdout
    assert "--parent test-epic-1" in result.stdout
    assert "--acceptance" in result.stdout
    # Description should be narrative-only, no embedded "## Acceptance criteria" section
    assert "## Acceptance" not in result.stdout
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --with pytest pytest dev-flow/skills/bead-create-smart/tests/ -v`
Expected: FAIL.

- [ ] **Step 3: Adapt SKILL.md from holomush**

Copy `bead-create-smart/SKILL.md` from holomush as starting point. Major adaptations:

- Shrink the 8-section description format. Per Rule 3, structured fields replace most sections.
- Keep description narrative-only: Goal (one paragraph), Plan reference (with verbatim-read directive), Files touched (approximate), Out of scope.
- All other content goes to dedicated flags (`--acceptance`, `--notes`, `--design`/`--design-file`, `--spec-id`, `--deps`, `--labels`, `--skills`).
- Accept an optional `--model haiku|sonnet|opus` arg that translates to `--labels model:<value>` per Rule 5.
- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dev-flow/skills/bead-create-smart/
git commit -m "feat(dev-flow): lift bead-create-smart skill; shrink to structured-flag helper"
```

### Task 3.3: Lift + adapt `handoff-prompt`

**Files:**

- Create: `dev-flow/skills/handoff-prompt/SKILL.md`
- Create: `dev-flow/skills/handoff-prompt/tests/test_handoff_prompt.py`

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/skills/handoff-prompt/SKILL.md`

- [ ] **Step 1: Write the failing test**

Test that invocation with a bead ID produces a briefing including: workspace isolation instruction (deferring to `dev-flow:using-worktrees`), model recommendation from the bead's `model:*` label, spec/plan paths, expected execution skill.

```python
def test_handoff_prompt_includes_model_recommendation(opus_labeled_bead_id):
    result = subprocess.run([SKILL_INVOKE, opus_labeled_bead_id], capture_output=True, text=True)
    assert "model: opus" in result.stdout.lower() or "opus" in result.stdout
    assert "using-worktrees" in result.stdout
    assert "bd prime" in result.stdout
    assert "bd show" in result.stdout
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Adapt SKILL.md**

Copy `handoff-prompt/SKILL.md` from holomush; adapt:

- Reference `dev-flow:using-worktrees` for workspace setup (not holomush's Taskfile commands).
- Read bead's `model:*` label via `bd show <id> --json | jq -r '.[0].labels[]?' | grep '^model:'`; default sonnet if absent.
- Include `bd prime` + `bd show <id>` as session-bootstrap instructions.
- Skills routing via bead's `--skills` field.
- [ ] **Step 4: Run test**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dev-flow/skills/handoff-prompt/
git commit -m "feat(dev-flow): lift handoff-prompt skill; integrate model labels + using-worktrees"
```

### Task 3.4: Confirm `bead-chain-design` NOT lifted

- [ ] **Step 1: Verify**

```bash
test ! -d dev-flow/skills/bead-chain-design
```

Expected: directory does not exist. Rule 4 means we don't need it; this task documents the intentional absence.

No commit needed.

---

## Phase 4: ADR Capture Subsystem

**Single PR.** Lifts capture-adrs + adr-extractor + nudge-adr-capture + adr-doctor.sh.

**Spec reference:** §"ADR Capture Subsystem"; §"Rule 7" (adr-extractor tools).

**Depends on:** Phase 1 merged.

**Source PR:** [holomush PR #3833](https://github.com/holomush/holomush/pull/3833).

### Task 4.1: Set up `docs/adr/` skeleton

**Files:**

- Create: `docs/adr/README.md`

- [ ] **Step 1: Write the failing index test**

Add `tests/test_adr_docs.py`:

```python
def test_adr_readme_has_index_sentinels():
    text = (REPO_ROOT / "docs/adr/README.md").read_text()
    assert "<!-- BEGIN INDEX -->" in text or "## Index" in text
    assert "## Writing guidelines" in text
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Author docs/adr/README.md**

```markdown
# Architecture Decision Records (ADRs)

This directory captures architectural decisions made during the brainstorming and planning phases of work tracked by `dev-flow`.

## Index

<!-- BEGIN INDEX -->
*(empty — populated by `capture-adrs` skill on first ADR commit)*
<!-- END INDEX -->

## Writing guidelines

ADRs are captured by the [`capture-adrs` skill](../../dev-flow/skills/capture-adrs/SKILL.md) automatically after `plan-reviewer` returns READY. Each ADR pairs a markdown file with a `bd` decision bead. Filename convention: `<bd-id>-<slug>.md`.

For the worthiness criteria and supersession discipline, see the spec at `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md` § "ADR Capture Subsystem".
```

- [ ] **Step 4: Test pass**

- [ ] **Step 5: Commit**

```bash
git add docs/adr/README.md tests/test_adr_docs.py
git commit -m "feat(adr): set up docs/adr/ with README + index sentinels"
```

### Task 4.2: Lift `adr-extractor` agent

**Files:**

- Create: `dev-flow/agents/adr-extractor.md`

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/agents/adr-extractor.md`

- [ ] **Step 1: Adapt frontmatter**

Copy verbatim from holomush; modify frontmatter `tools:` per spec:

```yaml
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - mcp__probe__search_code
  - mcp__probe__extract_code
  - mcp__probe__grep
```

Drop the `skills:` block (holomush had `jj:jujutsu` — not applicable to us; agents in dev-flow don't reference plugin skills).

- [ ] **Step 2: Adapt body**

Keep the four-criterion worthiness test verbatim. Keep the transcript scan strategies. Keep the strict JSON output contract. The body is repo-agnostic except for:

- Replace any holomush-specific path references (e.g., `docs/adr/<bd-id>`) with the generic pattern (which happens to match ours).

- [ ] **Step 3: Smoke test agent loads**

```bash
ls -la dev-flow/agents/adr-extractor.md
head -20 dev-flow/agents/adr-extractor.md  # frontmatter check
```

Verify the frontmatter is valid YAML and Claude Code can register the agent (no validation gate here; this is structural).

- [ ] **Step 4: Commit**

```bash
git add dev-flow/agents/adr-extractor.md
git commit -m "feat(adr): lift adr-extractor agent; tools per Rule 7"
```

### Task 4.3: Lift `capture-adrs` skill

**Files:**

- Create: `dev-flow/skills/capture-adrs/SKILL.md`
- Create: `dev-flow/commands/capture-adrs.md` (slash invoke)

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/skills/capture-adrs/SKILL.md`

- [ ] **Step 1: Adapt SKILL.md**

Copy verbatim, then adapt:

- Spec-path regex: `^(.*/)?docs/(superpowers/)?(specs|plans)/.+\.md$` (already matches our layout).
- File-target path: `docs/adr/<bd-id>-<slug>.md` (unchanged).
- ADR README sentinels: use our `<!-- BEGIN INDEX -->` / `<!-- END INDEX -->` (note: holomush used `MIGRATION MAP` sentinels for legacy; we don't need that since we have no legacy migration).
- Idempotency marker: unchanged (`<!-- adr-capture: sha256=...; session=...; ts=...; adrs=... -->`).
- Honor SHA-mismatch + 0-new-candidates case per spec §"Idempotency marker format" (stamp new marker silently).
- [ ] **Step 2: Add slash command**

Create `dev-flow/commands/capture-adrs.md`:

```markdown
---
description: Extract ADR-worthy decisions from a finalized spec or plan; file bd decision records + docs/adr/ files
arguments: required
allowed-tools: "Read, Edit, Write, Bash, AskUserQuestion, mcp__probe__*, mcp__context7__*"
---

Invoke the `capture-adrs` skill against the file path provided in `${ARG}`.
```

- [ ] **Step 3: Smoke test**

```bash
ls -la dev-flow/skills/capture-adrs/SKILL.md dev-flow/commands/capture-adrs.md
rumdl check dev-flow/skills/capture-adrs/SKILL.md dev-flow/commands/capture-adrs.md
```

- [ ] **Step 4: Commit**

```bash
git add dev-flow/skills/capture-adrs/ dev-flow/commands/capture-adrs.md
git commit -m "feat(adr): lift capture-adrs skill + slash command"
```

### Task 4.4: Lift `nudge-adr-capture` hook + test harness

**Files:**

- Create: `dev-flow/hooks/nudge-adr-capture`
- Create: `dev-flow/hooks/tests/test_nudge_adr_capture.bats` (or `.sh` if bats unavailable)

**Source:** `/Volumes/Code/github.com/holomush/holomush/.claude/hooks/nudge-adr-capture.sh`

- [ ] **Step 1: Lift script verbatim**

Copy `.claude/hooks/nudge-adr-capture.sh` from holomush. Modifications:

- Watched-paths config at top of script: load from a `WATCHED_GLOBS` env var or default to our paths (`docs/superpowers/specs/*.md`, `docs/superpowers/plans/*.md`). Document the override convention in a comment block per spec §"Watched paths".
- Keep bash 3.2 compatibility (no `[[`-style bashisms beyond what 3.2 supports).
- [ ] **Step 2: Lift 15-fixture test harness**

Copy the test fixture files + harness from holomush. Adapt path globs to match our watched paths. Test fixtures should cover:

1. New file in `docs/superpowers/specs/` → nudge fires
2. Edit to existing file with current marker → silent no-op
3. Edit to existing file with stale marker (SHA mismatch) → nudge fires
4. Edit to file with `optout=true` marker → silent no-op
5. New file outside watched paths → silent no-op
6. ... (remaining 10 fixtures from holomush; lift verbatim and adjust path-globs only)

- [ ] **Step 3: Wire hook into superpowers' hooks.json**

Modify `dev-flow/hooks/hooks.json` (or its equivalent): add `nudge-adr-capture` as a `PostToolUse` hook entry. Reference the spec §"Architecture & Interfaces" → plugin layout for the exact JSON shape.

- [ ] **Step 4: Run test harness**

```bash
bats dev-flow/hooks/tests/test_nudge_adr_capture.bats
```

Expected: all 15 fixtures pass.

- [ ] **Step 5: Commit**

```bash
git add dev-flow/hooks/nudge-adr-capture dev-flow/hooks/tests/ dev-flow/hooks/hooks.json
git commit -m "feat(adr): lift nudge-adr-capture PostToolUse hook + 15-fixture test harness"
```

### Task 4.5: Lift `adr-doctor.sh` + wire into lefthook

**Files:**

- Create: `dev-flow/scripts/adr-doctor.sh`
- Modify: `lefthook.yml`

**Source:** `/Volumes/Code/github.com/holomush/holomush/scripts/adr-doctor.sh`

- [ ] **Step 1: Lift script**

Copy verbatim from holomush. Modifications:

- Path constants at top: `docs/adr/` (matches ours).
- Add a `--changed-only` flag that limits checks to files passed as arguments (used by lefthook pre-commit per spec).
- [ ] **Step 2: Wire into lefthook**

Modify `lefthook.yml` to add a pre-commit hook:

```yaml
pre-commit:
  commands:
    # ... existing entries ...
    adr-doctor:
      glob: "docs/adr/*.md"
      run: ./dev-flow/scripts/adr-doctor.sh --changed-only {staged_files}
```

- [ ] **Step 3: Add CI workflow integration**

Update or add a step in `.github/workflows/` to run `./dev-flow/scripts/adr-doctor.sh` (full pass, no `--changed-only`) on every PR.

- [ ] **Step 4: Smoke test**

```bash
./dev-flow/scripts/adr-doctor.sh
```

Expected: passes against the empty `docs/adr/` (no ADRs yet means most checks are vacuously true; meta-test `invariant_coverage` covers the "are there any ADRs" assertion).

- [ ] **Step 5: Commit**

```bash
git add dev-flow/scripts/adr-doctor.sh lefthook.yml .github/workflows/
git commit -m "feat(adr): lift adr-doctor.sh; wire into lefthook (changed-only) + CI (full pass)"
```

---

## Phase 5: New Review-Gate Agents

**Single PR.** Authors `design-reviewer` + `plan-reviewer`. Both read-only sonnet adversarial reviewers with VERDICT contract.

**Spec reference:** §"Skill Inventory" → "New (designed during this brainstorm)"; §"Rule 7" → plan-reviewer enforcement; §"Workflow Shape" → reviewer output contract.

**Depends on:** Phase 1 merged.

### Task 5.1: Author `design-reviewer` agent

**Files:**

- Create: `dev-flow/agents/design-reviewer.md`
- Create: `dev-flow/commands/review-design.md`
- [ ] **Step 1: Write the failing contract test**

Add `tests/test_review_gate_agents.py`:

```python
def test_design_reviewer_verdict_regex_match():
    sample_output = """VERDICT: READY

## Strengths
- well-grounded
"""
    match = re.match(r"^VERDICT: (READY|NOT READY)$", sample_output.splitlines()[0])
    assert match
    assert match.group(1) == "READY"


def test_design_reviewer_not_ready_regex_match():
    sample_output = "VERDICT: NOT READY\n\n## Findings\n1. ..."
    match = re.match(r"^VERDICT: (READY|NOT READY)$", sample_output.splitlines()[0])
    assert match
    assert match.group(1) == "NOT READY"
```

(These are contract tests for the calling-skill's parsing logic, not agent-behavior tests; agent behavior is LLM-driven and tested via dogfood.)

- [ ] **Step 2: Verify fail (no agent file yet)**

- [ ] **Step 3: Author agent frontmatter + body**

```yaml
---
name: design-reviewer
description: Read-only adversarial review of a spec document. Emits READY/NOT READY verdict + grounded findings. Authorized to flag ungrounded specs per Rule 7.
model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - mcp__probe__search_code
  - mcp__probe__extract_code
  - mcp__probe__grep
  - mcp__context7__resolve-library-id
  - mcp__context7__query-docs
  - mcp__deepwiki__read_wiki_structure
  - mcp__deepwiki__read_wiki_contents
  - mcp__deepwiki__ask_question
---

# design-reviewer

You perform read-only adversarial review of spec documents. ...

## Output contract

Your output MUST start with a machine-parseable verdict on the first non-empty line:

```text
VERDICT: READY
```

or

```text
VERDICT: NOT READY
```

After the verdict, emit findings in markdown. Each finding cites `path:section` (specs have section anchors) or `path:line` for code references. ...

## What to look for

1. **Rule 1 compliance**: spec doesn't contain function bodies / algorithmic implementation
2. **Internal consistency**: sections don't contradict each other
3. **Ambiguity**: things that will cost time at plan-writing
4. **Missing scope**: degraded-mode behavior, edge cases
5. **Rule 7 grounding**: named libraries/APIs without context7 traces, file paths that don't exist (verify via probe), function signatures that don't match probe extract_code

```text

(Full body lifted from this session's dogfood prompts — the agent's content is essentially a codified version of the prompts that ran in the brainstorm.)

- [ ] **Step 4: Author slash command**

```markdown
---
description: Read-only adversarial review of a spec. Emits VERDICT: READY|NOT READY + findings.
arguments: required
allowed-tools: "Read, Grep, Glob, mcp__probe__*, mcp__context7__*, mcp__deepwiki__*"
---

Dispatch the `design-reviewer` agent against the spec at `${ARG}`.
```

- [ ] **Step 5: Run contract tests**

```bash
uv run --with pytest pytest tests/test_review_gate_agents.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add dev-flow/agents/design-reviewer.md dev-flow/commands/review-design.md tests/test_review_gate_agents.py
git commit -m "feat(dev-flow): add design-reviewer agent + /review-design command"
```

### Task 5.2: Author `plan-reviewer` agent

**Files:**

- Create: `dev-flow/agents/plan-reviewer.md`
- Create: `dev-flow/commands/review-plan.md`
- [ ] **Step 1: Author agent**

Same frontmatter shape as `design-reviewer` but include `Bash` in tools (for `bd show <design-bead-id>` to verify grounding traces per Rule 7's grounding-trace contract). Body adapted for plan-review context:

```yaml
---
name: plan-reviewer
description: Read-only adversarial review of a plan document. Emits READY/NOT READY verdict + grounded findings. Authorized to flag ungrounded plans per Rule 7.
model: sonnet
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - mcp__probe__search_code
  - mcp__probe__extract_code
  - mcp__probe__grep
  - mcp__context7__resolve-library-id
  - mcp__context7__query-docs
  - mcp__deepwiki__read_wiki_structure
  - mcp__deepwiki__read_wiki_contents
  - mcp__deepwiki__ask_question
---

# plan-reviewer

You perform read-only adversarial review of plan documents...

## Rule 7 enforcement: grounding-trace verification

For each library or external API named in the plan:

1. Look up the design bead ID (from the plan's metadata or by querying `bd list --spec-id <plan-path>`).
2. Run `bd show <design-bead-id> --notes` and grep for `grounding/context7:` lines mentioning the library.
3. If absent: this is a NOT READY finding.

For each file path in "Files touched":

1. Run `mcp__probe__search_code` on the path's basename.
2. If no hits in the codebase AND the file is listed as Modify (not Create): NOT READY finding.

For each function signature in plan code blocks:

1. Run `mcp__probe__extract_code` for the symbol.
2. If signature mismatches: NOT READY finding.
```

- [ ] **Step 2: Author slash command**

Same shape as `/review-design`, dispatching `plan-reviewer`.

- [ ] **Step 3: Commit**

```bash
git add dev-flow/agents/plan-reviewer.md dev-flow/commands/review-plan.md
git commit -m "feat(dev-flow): add plan-reviewer agent + /review-plan command"
```

### Task 5.3: Smoke-test both agents

- [ ] **Step 1: Run `/review-design` against this very spec**

```bash
# In Claude Code: /review-design /Volumes/Code/.../docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
```

Expected: agent emits `VERDICT: READY` or `VERDICT: NOT READY` as first non-empty line; findings follow.

- [ ] **Step 2: Run `/review-plan` against this very plan**

Same as above; agent should accept the plan file path.

- [ ] **Step 3: Run against a contrived bad spec**

Create a temporary spec missing the "Goals" section and a contrived bad library citation. Run `/review-design` against it; confirm NOT READY with the gap as a finding.

- [ ] **Step 4: No commit needed (verification task)**

---

## Phase 6: Modify Existing dev-flow Skills

**Single PR (or split per-skill if review feedback demands).** The most invasive phase. Wires Phases 3+4+5 together.

**Spec reference:** §"Skill Inventory" → "Modified existing dev-flow skills"; §"Rule 6"; §"Rule 7"; §"Workflow Shape".

**Depends on:** Phases 3, 4, and 5 ALL merged.

### Task 6.1: Modify `brainstorming` SKILL.md

**Files:**

- Modify: `dev-flow/skills/brainstorming/SKILL.md`

- [ ] **Step 1: Update frontmatter allowed-tools**

```yaml
allowed-tools: "Read, Edit, Write, Bash, AskUserQuestion, mcp__probe__*, mcp__context7__*, mcp__deepwiki__*, mcp__exa__*, mcp__firecrawl-mcp__firecrawl_scrape"
```

- [ ] **Step 2: Add "Open design bead" section near skill start**

Add a new section after "Announce at start" and before "Understanding the idea". Reference the spec §"Rule 6" → lifecycle. Pseudocode (the implementer translates to actual prose / tool calls):

```text
1. Ask user: "Open a design bead in bd to track this work? (Y/n)"
   - Default Y for substantive prompts; default N for clearly exploratory ones.
2. On Y: bd create --type=task --title="Design: <provisional>" --labels="phase:design" --spec-id="" --priority=2
3. Capture the returned bead ID; reference it for all subsequent grounding-trace notes.
4. On N: skip bead, proceed without tracking.
```

- [ ] **Step 3: Add "Rule 7 grounding checklist" section**

Before "Propose 2-3 approaches", add a MUST-do checklist:

- Probe codebase for prior art on the topic (`mcp__probe__search_code "<feature name>"`).
- For each library/framework named in any approach: `mcp__context7__resolve-library-id` + `query-docs`. Append `bd note <design-bead-id> "grounding/context7: <id> — <summary>"`.
- For upstream-repo conventions: `mcp__deepwiki__read_wiki_structure` → `read_wiki_contents` or `ask_question`. Append `bd note "grounding/deepwiki: <repo> — <summary>"`.
- Optional: `mcp__exa__web_search_exa` + `firecrawl_scrape` for state-of-the-art questions.
- [ ] **Step 4: Add design-reviewer auto-fire at skill end**

Replace "Invoke writing-plans skill" section with:

```text
After spec self-review passes and the file is written:

1. Invoke the `design-reviewer` agent against the spec path.
2. Parse the agent's first non-empty line via regex `^VERDICT: (READY|NOT READY)$`.
3. If READY: append note "design-review READY (round N)" to the design bead; suggest next step (writing-plans).
4. If NOT READY: append note "design-review round N NOT READY: <finding summary>" to the design bead; print findings inline; exit. User revises and re-invokes brainstorming.
```

- [ ] **Step 5: Lint**

```bash
rumdl check dev-flow/skills/brainstorming/SKILL.md
```

- [ ] **Step 6: Commit**

```bash
git add dev-flow/skills/brainstorming/SKILL.md
git commit -m "feat(brainstorming): integrate design bead + Rule 7 grounding + design-reviewer auto-fire"
```

### Task 6.2: Modify `writing-plans` SKILL.md

**Files:**

- Modify: `dev-flow/skills/writing-plans/SKILL.md`

- [ ] **Step 1: Update frontmatter allowed-tools**

Same grounding suite as `brainstorming`.

- [ ] **Step 2: Add design-bead-notes integration**

In the "Save plans to" section: after saving the plan, append `bd note <design-bead-id> "Plan: <path>"`. Add a step before "Self-Review" that re-verifies grounding per Rule 7 (probe file paths, context7 re-verify any library APIs in plan code blocks).

- [ ] **Step 3: Add plan-reviewer auto-fire**

After self-review:

```text
1. Invoke the `plan-reviewer` agent against the plan path. Pass the design bead ID as additional context.
2. Parse VERDICT regex.
3. If READY: append note "plan-review READY (round N)"; proceed to capture-adrs.
4. If NOT READY: append note "plan-review round N NOT READY: <findings>"; print findings; exit. User revises plan and re-invokes writing-plans.
```

- [ ] **Step 4: Add capture-adrs + plan-to-beads auto-fire chain**

On plan-reviewer READY:

```text
1. Invoke `capture-adrs <plan-path>` (skill, not slash command). On zero candidates: stamp idempotency marker silently, continue.
2. Count plan tasks. If 3+: auto-invoke `plan-to-beads <plan-path>`. If 1-2: prompt user. If 0: bd close <design-bead-id> --reason="Design-only; no implementation tracked".
3. plan-to-beads handles design bead promotion to epic (3+) or rename (1-2) per Rule 6.
```

- [ ] **Step 5: Lint + commit**

```bash
rumdl check dev-flow/skills/writing-plans/SKILL.md
git add dev-flow/skills/writing-plans/SKILL.md
git commit -m "feat(writing-plans): integrate plan-reviewer + auto-fire capture-adrs + plan-to-beads"
```

### Task 6.3: Modify `finishing-a-development-branch` SKILL.md

**Files:**

- Modify: `dev-flow/skills/finishing-a-development-branch/SKILL.md`

- [ ] **Step 1: Add pre-flight bd check**

Before presenting the 4-option menu, add a step:

```text
1. Determine the current epic ID (from the design bead if it was promoted, or by querying `bd list --spec-id <plan-path>`).
2. Run `bd list --status=open --parent <epic-id>`. If any open beads exist:
   a. Display them.
   b. Use AskUserQuestion: "Resolve open beads before finishing? Close all / File follow-ups / Defer / Continue anyway"
   c. If "Close all": prompt close for each.
   d. If "File follow-ups": invoke bead-create-smart for each.
   e. If "Defer": bd update <id> --defer=+30d for each.
   f. If "Continue anyway": warn loudly, proceed.
```

- [ ] **Step 2: Add post-merge interactive close**

After Option 1 (merge) or Option 2 (PR) succeeds, prompt the user to close beads whose work merged:

```text
1. Identify in-flight beads in the epic.
2. AskUserQuestion: "Which beads merged with this work? (multi-select)"
3. For selected: bd close <id> --reason="Merged in <branch-name>".
4. If all epic children closed: bd close <epic-id> --reason="Epic complete; all children closed".
```

- [ ] **Step 3: Lint + commit**

```bash
rumdl check dev-flow/skills/finishing-a-development-branch/SKILL.md
git add dev-flow/skills/finishing-a-development-branch/SKILL.md
git commit -m "feat(finishing): pre-flight bd check + interactive close after merge"
```

### Task 6.4: Modify `subagent-driven-development` SKILL.md

**Files:**

- Modify: `dev-flow/skills/subagent-driven-development/SKILL.md`

- [ ] **Step 1: Add bd-driven task pickup**

In the "Pick next task" section:

```text
1. Run `bd ready --json | jq '.[0]'` to get the next unblocked bead (excluding blocked, claimed, in_progress).
2. Read its labels for `model:*` (default sonnet if absent) and `--skills` for routing.
3. Atomically claim: `bd update <id> --claim`.
4. Read the bead's full description + acceptance + notes (`bd show <id>`).
5. Dispatch a fresh subagent with: subagent_type=appropriate-for-skills, model=<from-label>, prompt assembled from bead description + spec/plan paths from --spec-id.
6. After subagent returns: review (spec then quality per existing process). On approval: `bd close <id> --reason="..."`. On rejection: bd update --status=open and revise instructions.
```

- [ ] **Step 2: Lint + commit**

```bash
rumdl check dev-flow/skills/subagent-driven-development/SKILL.md
git add dev-flow/skills/subagent-driven-development/SKILL.md
git commit -m "feat(subagent-driven-development): bd ready + model-label dispatch"
```

### Task 6.5: Modify `executing-plans` SKILL.md

**Files:**

- Modify: `dev-flow/skills/executing-plans/SKILL.md`

- [ ] **Step 1: Add bd-driven serial execution**

Same shape as subagent-driven-development but serial:

```text
1. bd ready to get next bead.
2. bd update --claim.
3. Set session model per bead's model:* label (or stay default if no label).
4. Execute the bead's work in this session.
5. bd close on completion.
6. Loop to next bd ready bead until none.
```

- [ ] **Step 2: Lint + commit**

```bash
rumdl check dev-flow/skills/executing-plans/SKILL.md
git add dev-flow/skills/executing-plans/SKILL.md
git commit -m "feat(executing-plans): bd-driven serial execution + model labels"
```

### Task 6.6: End-to-end dogfood test

- [ ] **Step 1: Run a real brainstorming session on a tiny project**

Pick something trivial (e.g., "add a `bd doctor --check=foo` custom check"). Run `brainstorming` end-to-end:

- Design bead opens
- Rule 7 grounding checklist runs (probe + context7 for any libs)
- Spec drafted
- design-reviewer fires, emits VERDICT line
- writing-plans takes over
- Plan drafted
- plan-reviewer fires, emits VERDICT line
- capture-adrs auto-fires (likely 0 candidates for trivial work)
- plan-to-beads auto-fires (likely 1-2 tasks)
- subagent-driven-development executes the bead(s)
- finishing-a-development-branch reconciles bd state
- [ ] **Step 2: Verify each transition produces the expected bd state**

```bash
bd show <design-bead-id>
```

Expected: full audit trail in notes (spec drafted, reviewer rounds, ADRs, materialization).

- [ ] **Step 3: Document any issues**

File follow-up beads for anything that didn't work end-to-end. These become the Phase 7+ tightening backlog.

- [ ] **Step 4: No commit needed (verification task)**

---

## Self-Review (checked against spec)

**Spec coverage:**

| Spec section | Covered by |
|---|---|
| Rule 1: structure not implementation | Phase 2 Task 2.1 (AGENTS.md codifies); enforcement via plan-reviewer (Phase 5) |
| Rule 2: 3+ tasks → epic | Phase 3 Task 3.1 (plan-to-beads implements); Phase 2 (codify in AGENTS.md) |
| Rule 3: bd structured fields | Phase 3 Tasks 3.1, 3.2; Phase 2 (AGENTS.md) |
| Rule 4: no duplicate state | Phase 3 Task 3.1 (plan-to-beads drops chain section parsing); Phase 2 (codify) |
| Rule 5: model selection labels | Phase 3 Task 3.2 (bead-create-smart supports `--model`); Phase 6 Tasks 6.4, 6.5 (dispatch honors) |
| Rule 6: design bead lifecycle | Phase 3 Task 3.1 (plan-to-beads promotion); Phase 6 Task 6.1 (brainstorming opens it); Phase 6 Task 6.3 (finishing reconciles) |
| Rule 7: grounding before design | Phase 5 Tasks 5.1, 5.2 (reviewer agents have probe/context7/deepwiki); Phase 6 Tasks 6.1, 6.2 (brainstorming + writing-plans apply checklist) |
| Identity rebrand | Phase 1 Tasks 1.1-1.5 |
| Workflow Shape | Phase 6 Tasks 6.1, 6.2 (brainstorming + writing-plans wire the chain) |
| Plugin runtime requirements | Phase 1 Task 1.4 (README documents); Phase 2 Task 2.1 (AGENTS.md repeats) |
| ADR capture subsystem | Phase 4 Tasks 4.1-4.5 |
| Degraded-mode behavior | Phase 6 Tasks 6.1-6.5 (each skill mod respects bd-unavailable per spec) |
| Migration & in-flight work | Phase 1 (no automatic migration; in-flight uses old paths until completed) |

**Placeholder scan:** No "TBD", "TODO", "implement later", or "Add appropriate error handling" appear. Every step references either a verbatim spec section, a verbatim source file path in holomush, or a concrete command/code block.

**Type consistency:** Bead-related verbs are consistent (`bd create`, `bd update`, `bd close`, `bd note`, `bd dep add`, `bd ready`). Skill names are consistent (`plan-to-beads`, `bead-create-smart`, `handoff-prompt`, `capture-adrs`, `design-reviewer`, `plan-reviewer`).

**Known soft spots (acceptable):**

- Phase 4 Task 4.4 (15-fixture bash test harness): exact fixture list is "lift from holomush", not enumerated here. The lift is mechanical; full enumeration would balloon the plan. Implementer reads `/Volumes/Code/github.com/holomush/holomush/.claude/hooks/tests/` directly.
- Phase 5 agent bodies: described as "Full body lifted from this session's dogfood prompts". The actual prose is judgment territory; the contract (VERDICT line, tools list, model) is locked.
- Phase 6 skill modifications: described in prose, not as exact diffs. The skill file structures are flexible enough that exact diffs would over-constrain; the implementer adapts to whatever the v5.1.0 base looks like.

---

## Execution Handoff

**Plan complete and saved to** `docs/superpowers/plans/2026-05-14-dev-flow-beads-integration.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. With six phases and parallel-eligible Phases 2-5, this is the natural fit. Sequence: Phase 1 alone, then Phases 2-5 in parallel, then Phase 6 serially.

2. **Inline Execution** — execute tasks in this session using `executing-plans`. Batch execution with checkpoints for review. Suitable if you want to do Phase 1 yourself and dispatch the rest.

Which approach?
