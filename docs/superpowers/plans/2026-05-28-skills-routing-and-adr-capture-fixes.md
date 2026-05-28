# Skills Routing + capture-adrs Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three dev-flow defects — the false `--skills`→subagent routing
(replace with an `agent:<type>` label), over-eager capture-adrs worthiness, and
the ADR nudge firing on specs.

**Architecture:** Pure documentation/prompt/hook edits plus a bash+pytest test
harness change. Part A retargets reader skills to an `agent:*` documented-lookup
rule and reframes `--skills` as a description hint across five skills + the
canonical `AGENTS.md` Rule 3 table. Part B tightens `adr-extractor` worthiness
(and its mirror in the integration spec). Part C retimes the
`nudge-adr-capture` hook to plans-only and updates its test harness.

**Tech Stack:** Markdown skill/agent/spec artifacts; a POSIX-sh hook
(`nudge-adr-capture`) + bash/pytest test harness; `rumdl --no-exclude` for the
rumdl-excluded `dev-flow/**` tree. Spec:
`docs/superpowers/specs/2026-05-28-skills-routing-and-adr-capture-fixes-design.md`.

---

## Ordering

Parts A, B, C touch disjoint files and are independent. Recommended order:
A-readers (Task 1) → A-readers-2 (Task 2) → A-setters+doc (Task 3) →
B-worthiness (Task 4) → C-nudge (Task 5) → verification (Task 6). The repo is
colocated jj; per `dev-flow/references/vcs-preamble.md`, `jj commit -m` to seal
each task, never `jj new <rev>` mid-task.

---

### Task 1: Part A — fix subagent-driven-development (the core reader)

**Files:**

- Modify: `dev-flow/skills/subagent-driven-development/SKILL.md`

- [ ] **Step 1: Replace the `skills[]` routing-hint bullet (~L56)**

Replace:

```text
   - `skills[]` — the bd `--skills` field is a routing hint for which subagent type to dispatch (e.g. `review`, `test`, `debug`, `infra`).
```

with:

```text
   - `agent:*` label — look for an `agent:<subagent_type>` label. This is the only signal that selects `subagent_type` (see step 5). Absent → `general-purpose`. NOTE: the `--skills` field does NOT route; it only appends a `## Required Skills` capability hint to the bead description (read it for context, not dispatch).
```

- [ ] **Step 2: Replace the `subagent_type` mapping bullet (~L60)**

Replace the bullet beginning `- **\`subagent_type\`** — map the bead's \`skills[]\`...`
(the entire paragraph through "...when multiple skills overlap.") with:

```text
   - **`subagent_type`** — resolved by documented lookup, NOT a runtime probe (the Agent tool errors on an unregistered `subagent_type`). Carry the known-registered set; today it is `{ general-purpose }`. Read the bead's `agent:*` label: if its value is in the known set, dispatch that type; otherwise (no label, or a value not yet registered) dispatch `general-purpose`. Today every value resolves to `general-purpose`; `agent:*` is a forward-looking annotation. Never dispatch the `code-reviewer` agent here — it is the `review-pr` orchestrator's bd-finding agent and requires the orchestrator contract (`PARENT_BEAD_ID`, `PR_URL`, `ASPECT`). In-session review is the two-stage review below (spec then quality) via the `requesting-code-review` template + `general-purpose`.
```

- [ ] **Step 3: Fix the flowchart nodes (~L75, L95, L96)**

In the three flowchart lines, replace the node label
`"Read labels (model:*) + skills[]"` with `"Read labels (model:*, agent:*)"`
(all occurrences). Use a replace-all on the exact string
`Read labels (model:*) + skills[]` → `Read labels (model:*, agent:*)`.

- [ ] **Step 4: Fix the worked-example bead lines (~L171, L201)**

Replace:

```text
Bead: bd-42 — "Implement hook installation script" (labels: model:sonnet, skills: infra,test)
```

with:

```text
Bead: bd-42 — "Implement hook installation script" (labels: model:sonnet, agent:infra; Required Skills: infra,test)
```

Replace:

```text
Bead: bd-43 — "Recovery modes" (labels: model:opus, skills: infra,debug)
```

with:

```text
Bead: bd-43 — "Recovery modes" (labels: model:opus, agent:debugger; Required Skills: infra,debug)
```

- [ ] **Step 5: Lint + verify no routing-`skills[]` claim remains**

Run:

```bash
rumdl check --no-exclude dev-flow/skills/subagent-driven-development/SKILL.md
grep -n "skills\[\]" dev-flow/skills/subagent-driven-development/SKILL.md
```

Expected: rumdl clean; the `grep` returns nothing (no `skills[]` references
left).

- [ ] **Step 6: Commit**

Commit per `references/vcs-preamble.md`.
Message: `fix(dev-flow): route subagents via agent:* label, not --skills, in SDD (fhsk-07o)`

---

### Task 2: Part A — fix draining-beads + handoff-prompt readers

**Files:**

- Modify: `dev-flow/skills/draining-beads/SKILL.md`
- Modify: `dev-flow/skills/handoff-prompt/SKILL.md`
- [ ] **Step 1: draining-beads (~L135)**

Replace:

```text
   subagent_type from the bead's `skills[]` (general-purpose fallback); model from
```

with:

```text
   subagent_type from the bead's `agent:*` label (documented lookup; general-purpose fallback); model from
```

- [ ] **Step 2: handoff-prompt frontmatter (~L7)**

Replace:

```text
  label (default sonnet), routes via the bead's `--skills`, and defers
```

with:

```text
  label (default sonnet), routes via the bead's `agent:*` label, and defers
```

- [ ] **Step 3: handoff-prompt routing-hint line (~L73)**

Replace:

```text
- `--skills` list — the dispatch routing hint.
```

with:

```text
- `agent:*` label — the dispatch routing signal (documented lookup; general-purpose fallback). `--skills` is a capability hint only (appended as `## Required Skills` in the description).
```

- [ ] **Step 4: handoff-prompt routed-dispatch line (~L237)**

Replace:

```text
- Routed dispatch via the bead's `--skills` field.
```

with:

```text
- Routed dispatch via the bead's `agent:*` label.
```

Do NOT change L130 (`**Required skills (per bead \`--skills\`):**`) — that
briefing line is correct framing (a capability hint to the new session).

- [ ] **Step 5: Lint + verify**

Run:

```bash
rumdl check --no-exclude dev-flow/skills/draining-beads/SKILL.md dev-flow/skills/handoff-prompt/SKILL.md
grep -n "routes via the bead.*--skills\|dispatch routing hint\|skills\[\]" dev-flow/skills/draining-beads/SKILL.md dev-flow/skills/handoff-prompt/SKILL.md
```

Expected: rumdl clean; the `grep` returns nothing.

- [ ] **Step 6: Commit**

Commit per `references/vcs-preamble.md`.
Message: `fix(dev-flow): route via agent:* label in draining-beads + handoff-prompt (fhsk-07o)`

---

### Task 3: Part A — fix setters + the canonical AGENTS.md Rule 3 table

**Files:**

- Modify: `dev-flow/skills/plan-to-beads/SKILL.md`
- Modify: `dev-flow/skills/bead-create-smart/SKILL.md`
- Modify: `dev-flow/AGENTS.md`
- [ ] **Step 1: plan-to-beads skills/labels hint (~L137)**

Replace:

```text
   author's hints: `--labels model:<tier>`, `--skills <comma-separated>`.
```

with:

```text
   author's hints: `--labels model:<tier>` and `--labels agent:<type>` (the routing signal). `--skills <comma-separated>` appends a `## Required Skills` capability hint to the description; it does NOT route. Never set `agent:code-reviewer` on an implementer bead (that agent needs the review-pr orchestrator contract).
```

- [ ] **Step 2: plan-to-beads Rule 3 flag list (~L259)**

Replace:

```text
  `--spec-id`, `--notes`, `--deps`, `--labels`, `--skills`, `--parent`,
```

with:

```text
  `--spec-id`, `--notes`, `--deps`, `--labels` (incl. `model:*` and `agent:*`),
  `--skills` (Required-Skills hint, not routing), `--parent`,
```

- [ ] **Step 3: bead-create-smart inputs-table row (~L62)**

Replace:

```text
| Required skills | `--skills` | no | Dispatch routing hints (e.g. `jj,proto`). |
```

with:

```text
| Required skills | `--skills` | no | Appends a `## Required Skills` block to the description (capability hint, not routing). |
| Agent routing | `--labels agent:<type>` | no | Selects `subagent_type` (documented lookup; `general-purpose` fallback). |
```

- [ ] **Step 4: bead-create-smart example command (~L117)**

The example `bd create` invocation has a `--labels` line and a `--skills` line.
Add the `agent:<type>` routing label to the `--labels` value (the `--skills`
line stays — it is now correctly framed as a Required-Skills hint by the L62
table row from Step 3).

Replace:

```text
  --labels "model:sonnet,aspect:<x>,area:<y>" \
```

with:

```text
  --labels "model:sonnet,agent:<type>,aspect:<x>,area:<y>" \
```

- [ ] **Step 5: AGENTS.md Rule 3 table (~L58)**

Replace:

```text
| Required skills | `--skills` (dispatch routing hint) |
```

with:

```text
| Required skills | `--skills` (capability hint; appends `## Required Skills` to the description) |
| Agent routing | `--labels agent:<type>` (selects subagent_type; documented lookup, `general-purpose` fallback) |
```

- [ ] **Step 6: Lint + verify**

Run:

```bash
rumdl check --no-exclude dev-flow/skills/plan-to-beads/SKILL.md dev-flow/skills/bead-create-smart/SKILL.md dev-flow/AGENTS.md
grep -rn "dispatch routing hint\|routing hint" dev-flow/skills/plan-to-beads/SKILL.md dev-flow/skills/bead-create-smart/SKILL.md dev-flow/AGENTS.md
```

Expected: rumdl clean; the `grep` returns nothing.

- [ ] **Step 7: Commit**

Commit per `references/vcs-preamble.md`.
Message: `fix(dev-flow): reframe --skills as hint + add agent:* routing in setters + AGENTS.md (fhsk-07o)`

---

### Task 4: Part B — tighten capture-adrs worthiness

**Files:**

- Modify: `dev-flow/agents/adr-extractor.md`
- Modify: `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
- [ ] **Step 1: Rewrite the adr-extractor worthiness block (~L25–44)**

Replace the block from `## Worthiness criteria` through
`...borderline — surface it anyway, but flag in your output.` with:

```text
## Worthiness criteria

A candidate is ADR-worthy iff it passes ALL of the following. **Surface only
candidates that pass all four (score == 4).** Anything that fails one or more
goes in `dropped` with a reason — do NOT surface borderline candidates.

1. **Architecturally load-bearing** — the decision constrains *future code*:
   system structure, public interfaces / APIs, data model, cross-component
   contracts, or trust / dependency boundaries. If reversing it would only churn
   process or files (not code behavior or structure), it is NOT architectural.
2. **Has rejected alternatives with a real trade-off** — necessary but NOT
   sufficient. Alternatives listed by a `brainstorming` `AskUserQuestion` prompt
   do not make a routine choice architectural; the fork must be genuinely
   structural.
3. **Load-bearing for future contributors** — six months out, "why is X this
   way" should be answerable here.
4. **Not already captured** in `docs/adr/` — you MUST grep / probe the directory
   and run `bd list --type decision` first. If a related ADR exists, propose
   `supersedes` rather than "new."

**Exclusion list (auto-drop, never surface):** process / workflow sequencing
("do X before Y"); packaging, versioning, or release-tooling mechanics; file
organization, moves, or refactor mechanics; naming / slug conventions;
documentation or wording choices; tooling / config changes that do not alter
runtime behavior.

Score each candidate 0–4 by criteria passed. Only score == 4 (and not matching
the exclusion list) is surfaced; all else is dropped.
```

- [ ] **Step 2: Fix the output-cap prose (~L110–112)**

Replace:

```text
fit everything, prioritize candidates by `worthiness_score` descending
```

with:

```text
fit everything, prioritize candidates by `worthiness_score` descending (note:
only score == 4 candidates are surfaced; lower scores are in `dropped`)
```

- [ ] **Step 3: Mirror into the integration spec (~L451–458)**

In `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`,
replace this exact block (the heading at ~L449 through the Score line at ~L458):

```text
### Worthiness criteria (verbatim from holomush; codified in dev-flow's AGENTS.md)

A candidate is ADR-worthy iff ALL four hold:

1. **Architectural** — not implementation detail.
2. **Has rejected alternatives** with real trade-off.
3. **Load-bearing** for future decisions or contributors.
4. **Not already captured** — must grep `docs/adr/` and `bd list --type decision` before proposing.

Score 0-4 by criteria-passed. Score < 4 is borderline (surfaced anyway, flagged).
```

with a tightened summary matching the agent (keep the `###` heading line, drop
the now-inaccurate "verbatim from holomush" claim):

```text
### Worthiness criteria (codified in dev-flow's adr-extractor + AGENTS.md)

A candidate is ADR-worthy iff it passes ALL four (score == 4); borderline
(< 4) candidates are dropped, not surfaced:

1. **Architecturally load-bearing** — constrains future code (structure,
   interfaces, data model, cross-component contracts, trust/dependency
   boundaries); not process/file churn.
2. **Has rejected alternatives** with a real trade-off — necessary but not
   sufficient; brainstorming-prompt alternatives do not by themselves qualify.
3. **Load-bearing** for future contributors.
4. **Not already captured** (else `supersedes`).

Auto-drop (never surface): process/sequencing, packaging/versioning/release
mechanics, file-org/refactor mechanics, naming conventions, doc/wording
choices, runtime-inert tooling config. Only score == 4 is surfaced.
```

- [ ] **Step 4: Lint + verify**

Run:

```bash
rumdl check --no-exclude dev-flow/agents/adr-extractor.md
rumdl check docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
grep -rn "surface it anyway\|surfaced anyway" dev-flow/agents/adr-extractor.md docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
```

Expected: rumdl clean; the `grep` returns nothing (the lenient phrasing is
gone); the exclusion list is present in both files.

- [ ] **Step 5: Commit**

Commit per `references/vcs-preamble.md`.
Message: `fix(dev-flow): tighten adr-extractor worthiness to architectural-only (fhsk-07o)`

---

### Task 5: Part C — retime the nudge to plans-only

**Files:**

- Modify: `dev-flow/hooks/nudge-adr-capture`
- Modify: `dev-flow/hooks/tests/test_nudge_adr_capture.sh`
- Modify: `dev-flow/hooks/tests/test_nudge_adr_capture.py`
- [ ] **Step 1: Change the watched regex (~L47)**

Replace:

```text
WATCHED_REGEX="${WATCHED_GLOBS:-^(.*/)?docs/(superpowers/)?(specs|plans)/.+\.md$}"
```

with:

```text
WATCHED_REGEX="${WATCHED_GLOBS:-^(.*/)?docs/(superpowers/)?plans/.+\.md$}"
```

- [ ] **Step 2: Update the header comments (~L20–29)**

Replace:

```text
# Defaults shipped here cover the dev-flow / fzymgc-house-skills layout:
#   docs/superpowers/specs/*.md
#   docs/superpowers/plans/*.md
#
# Holomush (kept here as a reference for forks) additionally watches
# docs/specs/*.md and docs/plans/*.md; the bundled default regex below is
# permissive enough to accept both shapes.
#
# To override, export WATCHED_GLOBS before this hook runs, e.g.:
#   export WATCHED_GLOBS='^(.*/)?docs/(superpowers/)?(specs|plans)/.+\.md$'
```

with:

```text
# Defaults shipped here watch PLAN files only (ADR capture runs after
# writing-plans, never during brainstorming on specs):
#   docs/superpowers/plans/*.md
#   docs/plans/*.md   (flat layout, e.g. holomush forks)
#
# Specs are intentionally NOT watched — the nudge must not fire during the
# spec/brainstorming phase.
#
# To override, export WATCHED_GLOBS before this hook runs, e.g.:
#   export WATCHED_GLOBS='^(.*/)?docs/(superpowers/)?plans/.+\.md$'
```

- [ ] **Step 3: Repoint the firing-test helper to plans (~L84)**

In `dev-flow/hooks/tests/test_nudge_adr_capture.sh`, the `make_spec()` helper
writes under `docs/specs/`. Change its path to `docs/plans/` so the firing
cases (9 no-marker, 11 stale, 13 malformed) exercise a watched path:

Replace:

```text
  local p="$tmpdir/docs/specs/$name.md"
```

with:

```text
  local p="$tmpdir/docs/plans/$name.md"
```

- [ ] **Step 4: Reframe the spec-path case comments (cases 2, 4, 7)**

Update the comments on the three spec-path cases so they reflect the new rule
(spec paths are no longer watched). The expected outputs stay `0 ""` (silent):

- Case 2 comment → `# --- Case 2: docs/specs flat → no longer watched → silent ---`
- Case 4 comment → `# --- Case 4: docs/superpowers/specs nested → no longer watched → silent ---`
- Case 7 comment → `# --- Case 7: worktree docs/specs path → no longer watched → silent ---`
- [ ] **Step 5: Add a real-spec-file-silent regression case**

After Case 13 (malformed) and before Case 14, add a new case that creates a real
spec file (NOT via the now-plans `make_spec`) with no marker and asserts silent,
proving specs are unwatched even when the file exists:

```bash
# --- Case 13b: real spec file, no marker → silent (specs not watched) ---
real_spec="$tmpdir/docs/specs/real-no-marker.md"
mkdir -p "$(dirname "$real_spec")"
printf 'spec body without marker\n' > "$real_spec"
expect_case "real-spec-silent" \
  "$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$real_spec")" \
  0 ""
```

- [ ] **Step 6: Update the harness pass count + the pytest assertion**

The `.sh` ends with `echo "passed=$pass failed=$fail"`. Adding one case makes the
total 16. Update the pytest wrapper assertion in
`dev-flow/hooks/tests/test_nudge_adr_capture.py`:

Replace:

```text
    assert "passed=15 failed=0" in result.stdout, result.stdout
```

with:

```text
    assert "passed=16 failed=0" in result.stdout, result.stdout
```

- [ ] **Step 7: Run the hook test harness**

Run:

```bash
uv run --with pytest pytest dev-flow/hooks/tests/test_nudge_adr_capture.py -v --import-mode=importlib
```

Expected: PASS, with the bash harness reporting `passed=16 failed=0` (spec paths
silent, plan paths fire).

- [ ] **Step 8: Commit**

Commit per `references/vcs-preamble.md`.
Message: `fix(dev-flow): retime nudge-adr-capture to plans only (fhsk-07o)`

---

### Task 6: Full-surface verification

**Files:**

- (No file changes unless a guard fails)

- [ ] **Step 1: No routing-`skills` claims survive**

Run:

```bash
grep -rn "skills\[\]" dev-flow/ --include="*.md"
grep -rn "dispatch routing hint\|routes via the bead.*--skills" dev-flow/
```

Expected: both return nothing.

- [ ] **Step 2: agent:* rule + prohibition present**

Run:

```bash
grep -rln "agent:\*\|agent:<type>\|known-registered\|documented lookup" dev-flow/skills/subagent-driven-development/SKILL.md dev-flow/skills/draining-beads/SKILL.md dev-flow/skills/handoff-prompt/SKILL.md
grep -rn "agent:code-reviewer" dev-flow/skills/plan-to-beads/SKILL.md dev-flow/skills/subagent-driven-development/SKILL.md
```

Expected: the three readers reference the `agent:*` rule; the `code-reviewer`
prohibition is present.

- [ ] **Step 3: Worthiness tightened in both files**

Run:

```bash
grep -rn "surface it anyway\|surfaced anyway" dev-flow/ docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
grep -rln "Exclusion list\|auto-drop\|score == 4" dev-flow/agents/adr-extractor.md
```

Expected: first grep nothing; second confirms the exclusion list + score gate.

- [ ] **Step 4: Full test suite**

Run:

```bash
uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ dev-flow/hooks/tests/ tests/ --import-mode=importlib -q
```

Expected: all pass (nudge harness `passed=16`). The worktree-create temp-repo
test is occasionally flaky on parallel runs; re-run once if a single git-commit
error appears.

- [ ] **Step 5: Lint sweep + CI lint repro**

Run:

```bash
rumdl check --no-exclude dev-flow/skills/subagent-driven-development/SKILL.md \
  dev-flow/skills/draining-beads/SKILL.md dev-flow/skills/handoff-prompt/SKILL.md \
  dev-flow/skills/plan-to-beads/SKILL.md dev-flow/skills/bead-create-smart/SKILL.md \
  dev-flow/agents/adr-extractor.md
rumdl check AGENTS.md docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
```

Expected: clean. (`dev-flow/AGENTS.md` is the per-plugin file; the repo-root
`AGENTS.md` is separate — confirm the dev-flow one lints under `--no-exclude`.)

- [ ] **Step 6: Commit (only if a guard required a fix)**

Commit per `references/vcs-preamble.md`.
Message: `test(dev-flow): verify skills-routing + capture-adrs fixes (fhsk-07o)`
<!-- adr-capture: sha256=9a6dbc7e025b2f9a; session=15501658; ts=2026-05-28T23:26:14Z; adrs=fhsk-bj8 -->
