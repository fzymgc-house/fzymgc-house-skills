# Anti-AI-Slop Review Aspect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `slop` review aspect and `slop-hunter` agent to the `pr-review`
plugin that detects AI-authorship tells in both code and prose, reporting
findings as beads without overlapping the existing review agents.

**Architecture:** One new agent file (`pr-review/agents/slop-hunter.md`) modeled
exactly on `code-simplifier.md`, backed by two self-contained pattern catalogs
in `pr-review/references/`. The agent applies two anti-duplication rules: Rule A
(every finding cites a catalog pattern ID) and Rule B (defer co-owned patterns
when the owning aspect runs, driven by a new `ACTIVE_ASPECTS` orchestrator
variable). Wiring lives entirely in `pr-review/skills/review-pr/SKILL.md`.

**Tech Stack:** Markdown skill/agent artifacts; `bd` (beads) for findings;
`rumdl` for markdown linting (140-char width, MD041 H1-after-frontmatter);
validated against the spec at
`docs/superpowers/specs/2026-05-28-anti-ai-slop-review-aspect-design.md`.

---

## File Structure

- **Create** `pr-review/references/code-slop.md` — catalog of 16 code AI-tells
  (`C-1`–`C-16`), each with a one-line tell + before/after + severity hint.
- **Create** `pr-review/references/prose-slop.md` — catalog of 15 prose AI-tells
  (`P-1`–`P-15`), condensed from the `humanizer` skill + 2025–2026 sources.
- **Create** `pr-review/agents/slop-hunter.md` — the agent prompt; same shape as
  `code-simplifier.md` plus Rule A/B deferral and `ACTIVE_ASPECTS`.
- **Modify** `pr-review/skills/review-pr/SKILL.md` — five targeted edits to
  register the aspect, the selection heuristic, the model row, and
  `ACTIVE_ASPECTS` dispatch.

No JSON, no `release-please-config.json`, and no `plugin.json` changes: agents
are auto-discovered, and `pr-review` is a single tracked package keyed on the
`pr-review/` path.

There are no executable code units in this work — the deliverables are
prompt/reference markdown. The TDD "test" for each artifact is therefore
`rumdl check` (lint + MD041 structural rule) plus a structural grep assertion
that the required content is present; behavioral verification is a manual
`/review-pr` dry-run in the final task.

---

### Task 1: Code-slop pattern catalog

**Files:**

- Create: `pr-review/references/code-slop.md`

- [ ] **Step 1: Write the catalog file**

Create `pr-review/references/code-slop.md` with exactly this content:

````markdown
# Code AI-Slop Patterns (`C-n`)

Catalog of code-level AI-authorship tells for the `slop-hunter` agent. Each
finding raised against this catalog MUST cite its pattern ID (Rule A). Some
patterns are co-owned by another aspect and are deferred under Rule B — see the
`slop-hunter` agent for the deferral table.

The defining property of AI-native code is that the failure mode looks like the
success mode: it compiles, lints clean, has descriptive names, and handles every
exception, yet carries tells a careful author would strip. No single tell is
proof — weight findings by the clustering and density of tells in one change,
and prefer one well-evidenced finding over many speculative ones.

## Patterns

### C-1 — Comment restates the code

Co-owned with `comments`. A comment that narrates what the next line plainly
does.

- Before: `i += 1  # increment i by 1`
- After: `i += 1`

### C-2 — Vestigial edit narration

Comments that describe the editing history rather than the code.

- Before: `# removed old logic; previously we looped here` / `// NEW:`
- After: (delete the comment)

### C-3 — Defensive validation for impossible cases

Null/None checks or re-validation on values that internal code already
guarantees.

- Before: `user = get_current_user()  # never None here\nif user is None:\n    raise RuntimeError("no user")`
- After: `user = get_current_user()`

### C-4 — Single-use abstraction

Co-owned with `code` (YAGNI). A helper, wrapper, or interface introduced with
exactly one caller and no second use in sight.

- Before: a `def _format_name(n): return n.strip().title()` called once.
- After: inline the expression at its single call site.

### C-5 — No-consumer backwards-compat shim

Co-owned with `code` (YAGNI). A re-export, alias, or deprecation path for code
that has no existing consumers.

- Before: `# keep old name for compatibility\nlegacy_fn = new_fn`
- After: (delete; new code needs no migration path)

### C-6 — Padded docstring

Marketing adjectives, restating the signature, or multi-paragraph blocks on
trivial functions.

- Before: `"""A robust, efficient, scalable utility that adds two numbers together in a performant manner."""`
- After: `"""Add two numbers."""` (or no docstring for an obvious helper)

### C-7 — Test asserts the mock, not the outcome

A test whose only assertion is that a mock/framework method was called.

- Before: `service.save(x)\nassert mock_db.save.called`
- After: assert the observable result: `assert repo.get(x.id) == x`

### C-8 — Silenced rather than deleted dead code

`_unused` renames, `# noqa`, `// eslint-disable` used to quiet code that should
just be removed.

- Before: `_result = compute()  # noqa: F841`
- After: (delete the unused statement)

### C-9 — Swallowed errors / empty catch

Co-owned with `errors`. Over-broad handlers that discard exceptions or fabricate
silent fallbacks for conditions that should propagate.

- Before: `try:\n    do()\nexcept Exception:\n    pass`
- After: let it raise, or handle the specific exception with intent.

### C-10 — Speculative configuration

Co-owned with `code` (YAGNI). Flags, parameters, or config for hypothetical
future requirements with no current caller.

- Before: `def render(self, *, experimental_mode=False, future_format=None):` with neither argument used.
- After: `def render(self):`

### C-11 — Hallucinated import

A plausible-sounding module or symbol that does not exist. Severity `important`
(the code cannot run). Verify against the dependency manifest (`package.json`,
`requirements.txt`, `go.mod`); skip if no manifest is in the diff context.

- Before: `from express_validator_utils import sanitize`
- After: use a real, declared dependency.

### C-12 — Stale / deprecated API

A training-cutoff API that still "works" so it passes tests.

- Before: `const buf = new Buffer(data)` / `url.parse(req.url)`
- After: `const buf = Buffer.from(data)` / `new URL(req.url, base)`

### C-13 — Copy-paste clone

Co-owned with `simplify`. A large near-identical block duplicated with one field
changed where a human would extract a helper. Respect "three similar lines beats
a premature abstraction" — flag only sizable clones, not C-4-style premature
abstraction.

- Before: two ~30-line route handlers identical except for a table name.
- After: one parameterized handler.

### C-14 — Hardcoded placeholder secret/value

`critical` when it reaches a security-relevant path.

- Before: `SECRET_KEY = "your-secret-key"` / `password = "change-me"`
- After: load from configuration/environment; never commit placeholders.

### C-15 — Stylistic discontinuity

The change uses different naming, error-handling, or logging conventions than
the surrounding file/module — the clearest tell of code generated in isolation.

- Before: `camelCase` locals dropped into an all-`snake_case` module; `print()`
  debugging in a module that uses a structured logger everywhere else.
- After: match the conventions already in the file.

### C-16 — Comment-as-section-header banners

Banner comments and uniform comment density (evenly distributed explanatory
comments rather than clustered around the genuinely non-obvious).

- Before: `# ===== User Authentication =====`
- After: (delete; let function/section names carry the structure)

## Sources

- "5 Code Smells Only AI Creates" (dev.to) — hallucinated import, copy-paste
  clone, empty catch, stale API, over-engineered singleton.
- "Code Review Checklist for AI-Generated Code" (gitautoreview.com).
- "How to Identify If Code Is Written by AI" (aquilax.ai) — stylistic
  discontinuity, comment-as-section-header, what-not-why comments, uniform
  comment density, placeholder secrets.
- "9 Dead Giveaways That AI Wrote This Code" / LLM-native code-smell coverage.
````

- [ ] **Step 2: Verify it lints clean**

Run: `rumdl check pr-review/references/code-slop.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify all 16 pattern IDs are present**

Run: `grep -c '^### C-' pr-review/references/code-slop.md`
Expected: `16`

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `feat(pr-review): add code-slop pattern catalog (fhsk-rhh)`

---

### Task 2: Prose-slop pattern catalog

**Files:**

- Create: `pr-review/references/prose-slop.md`

- [ ] **Step 1: Write the catalog file**

Create `pr-review/references/prose-slop.md` with exactly this content:

````markdown
# Prose AI-Slop Patterns (`P-n`)

Catalog of prose-level AI-authorship tells for the `slop-hunter` agent, condensed
from the `humanizer` skill and 2025–2026 analyses of LLM writing. Applies
anywhere prose lives: standalone docs (`.md`, `.rst`, `.txt`) and code
comments/docstrings. Every finding raised against this catalog MUST cite its
pattern ID (Rule A).

No single P-pattern is proof — human writers use em-dashes and say "delve". The
signal is clustering. Raise a prose-slop finding when several tells co-occur in
one passage, not on an isolated word. Project conventions in `AGENTS.md` /
`CLAUDE.md` win (a repo that mandates emoji headings suppresses `P-7`).

## Patterns

### P-1 — Significance / legacy inflation

- Before: "Established in 1989, marking a pivotal moment in the evolution of the field."
- After: "Established in 1989 to publish regional statistics."

### P-2 — Promotional language

- Before: "a seamless, powerful, cutting-edge solution that boasts rich features"
- After: "supports CSV export and scheduled reports."

### P-3 — Superficial `-ing` pseudo-depth and the hedging-verb family

`ensuring`, `highlights`, `supports`, `reflects`, `underpins`, `aligns with`.
Per 2026 analyses this verb family is now the strongest lexical tell ("ensuring"
over-represented ~4.3x); a human just says what the thing does.

- Before: "The cache layer, ensuring robustness and highlighting the importance of speed, ..."
- After: "The cache layer reduces median latency from 200ms to 40ms."

### P-4 — Rule-of-three padding

- Before: "fast, reliable, and scalable"
- After: "handles 10k requests/sec."

### P-5 — Em-dash overuse

Weak on its own now (only ~18.5% of AI text carries one) — treat as
corroborating, never a standalone finding.

- Before: "The tool — which is new — works well — most of the time."
- After: "The tool is new and works well most of the time."

### P-6 — Title Case In Headings

- Before: `## Strategic Negotiations And Global Partnerships`
- After: `## Strategic negotiations and global partnerships`

### P-7 — Emoji-decorated headings or bullets

- Before: `🚀 **Launch:** ships in Q3`
- After: `The product ships in Q3.`

### P-8 — Inline-header vertical lists

- Before: `- **Performance:** improved through optimized algorithms.`
- After: prose that names the actual change.

### P-9 — Negative parallelism / tailing negation

- Before: "It's not just a tool, it's a movement." / "The options come from the
  selection, no guessing."
- After: "It is a tool." / "The options come from the selection."

### P-10 — Filler and excessive hedging

- Before: "In order to achieve this, it is important to note that it could
  potentially possibly help."
- After: "This helps."

### P-11 — Signposting

- Before: "Let's dive in. Here's what you need to know."
- After: (delete; start with the content)

### P-12 — Chatbot artifacts / cutoff disclaimers

- Before: "Great question! I hope this helps! While details are limited as of my
  last update, ..."
- After: (delete; state the fact directly)

### P-13 — The "crucial role in shaping" sentence shape

Statistically the single most formulaic LLM structure.

- Before: "Caching plays a crucial role in shaping system performance." /
  "is essential for" / "serves as a testament to"
- After: "Caching cuts repeated database reads."

### P-14 — Evidence-free intensifier adverbs

`significantly`, `effectively`, `directly`, `increasingly`, `vastly`. If a number
can't back the intensifier, cut it.

- Before: "significantly improves performance"
- After: "cuts p95 latency by 30%."

### P-15 — Vocabulary clichés

`delve`, `tapestry`, `realm`, `multifaceted`, `pivotal`, `bustling`,
`underscore`, `testament`, `foster`, `embark`, `myriad`, `leverage`, `robust`,
`holistic`, `comprehensive`, `synergy`, `paradigm`, `groundbreaking`,
`transformative`. Individually fine; clustered they produce press-release
texture.

- Before: "Let's delve into this comprehensive, robust tapestry of features."
- After: "These features cover authentication, billing, and reporting."

## Sources

- Wikipedia, "Signs of AI writing" (via the `humanizer` skill).
- Kobak et al. 2025, "excess vocabulary"; list at
  `github.com/berenslab/llm-excess-vocab`.
- writehuman.ai, "The Real Signature of AI Writing Isn't the Em-Dash Anymore"
  (2026) — hedging verbs, "crucial role in shaping", intensifiers.
- bloomberry.ai AI-writing-patterns database; telltale-ai; synkrlab phrase list.
````

- [ ] **Step 2: Verify it lints clean**

Run: `rumdl check pr-review/references/prose-slop.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify all 15 pattern IDs are present**

Run: `grep -c '^### P-' pr-review/references/prose-slop.md`
Expected: `15`

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `feat(pr-review): add prose-slop pattern catalog (fhsk-rhh)`

---

### Task 3: The slop-hunter agent

**Files:**

- Create: `pr-review/agents/slop-hunter.md`

- [ ] **Step 1: Write the agent file**

Create `pr-review/agents/slop-hunter.md` with exactly this content:

````markdown
---
name: slop-hunter
description: >-
  Detects AI-authorship tells in code and prose changes. Used by the review-pr
  orchestrator for the `slop` aspect.
model: sonnet
isolation: worktree
tools: Read, Grep, Glob, Bash
---

# Slop Hunter

You detect AI-authorship slop: changes that bear the fingerprints of unreviewed
AI generation a careful human author would have stripped. Your lens is
**provenance, not quality** — "would a human have removed this before
committing?" — which is what separates you from the clarity, accuracy, and
standards agents.

## Environment

You are running in an isolated worktree. Follow the startup procedure in
`pr-review/references/vcs-detection-preamble.md` to detect VCS and verify your
location before proceeding.

## Scope and Standards

### Scope

Your review scope is **exactly** the PR diff provided by the orchestrator. Only
flag tells in code or prose added or modified in this PR. Pre-existing slop in
unchanged code is out of scope unless the change directly touches it.

### Project Standards

1. Read `AGENTS.md` (root and any nested ones) for shared conventions and
   documentation style.
2. Read `CLAUDE.md` (root and nested) only as a Claude-specific addendum.
3. Project conventions override catalog defaults. If a repo mandates emoji
   headings, suppress `P-7`; if it uses banner comments throughout, suppress
   `C-16`.

## Catalogs

Read both pattern catalogs before analyzing:

- `pr-review/references/code-slop.md` — code tells `C-1`–`C-16`.
- `pr-review/references/prose-slop.md` — prose tells `P-1`–`P-15`.

## Two anti-duplication rules

**Rule A — named-pattern discipline.** Every finding MUST cite a specific catalog
pattern ID (e.g. `C-3`, `P-9`) in its title. If you cannot name the pattern, it
is not a slop finding and you MUST NOT raise it. "This could be clearer" with no
pattern ID belongs to another aspect.

**Rule B — cross-aspect deferral.** Some patterns are co-owned by another aspect.
The orchestrator passes `ACTIVE_ASPECTS` (comma-separated aspect keys running in
this invocation, excluding `slop`). Suppress a co-owned pattern when its owning
aspect is present; raise it only when that aspect is absent:

| Pattern | Owning aspect | Raise only when |
|---------|---------------|-----------------|
| `C-1` | `comments` | `comments` ∉ `ACTIVE_ASPECTS` |
| `C-9` | `errors` | `errors` ∉ `ACTIVE_ASPECTS` |
| `C-4`, `C-5`, `C-10` | `code` | `code` ∉ `ACTIVE_ASPECTS` |
| `C-13` | `simplify` | `simplify` ∉ `ACTIVE_ASPECTS` |

All other patterns (`C-2`, `C-3`, `C-6`, `C-7`, `C-8`, `C-11`, `C-12`, `C-14`,
`C-15`, `C-16`, and every `P-pattern`) have no other owner — always yours to
raise. Prose `P-patterns` never defer to `comments`: that agent judges comment
*accuracy/rot*, a different axis from prose *style/provenance*.

## Density principle

No single tell is proof. AI's failure mode looks like the success mode. Raise a
finding when tells cluster in one change; prefer one well-evidenced finding over
many speculative ones.

## Bead Output

Create a bead for each finding via `bd create`. The orchestrator provides these
variables in the task prompt: `PARENT_BEAD_ID`, `TURN`, `PR_URL`,
`ACTIVE_ASPECTS`. Your aspect is `slop`. Lead each title with the pattern ID.

### Creating Findings

```bash
bd create "<C-n|P-n>: <first sentence of finding>" \
  --parent $PARENT_BEAD_ID \
  --type <bug|task|feature> \
  --priority <0-3> \
  --labels "pr-review-finding,aspect:slop,severity:<critical|important|suggestion>,turn:$TURN" \
  --external-ref "$PR_URL" \
  --description "<full details: pattern ID, file:line, suggested fix>" \
  --silent
```

**Severity → priority mapping:**

| Severity | Priority | Default type |
|----------|----------|-------------|
| critical | 0 | bug |
| important | 1 | bug or task |
| suggestion | 2 | task |

Most slop is `suggestion`. `C-3` / `C-9` may rise to `important`; `C-11`
(hallucinated import) is `important`; `C-14` (placeholder secret on a security
path) may be `critical`.

**Praise**: Do NOT create beads for praise. Mention noteworthy clean code in your
return summary.

### Re-reviews (turn > 1)

```bash
bd list --parent $PARENT_BEAD_ID --label "aspect:slop" --status open --json
```

- **Resolved**: `bd update <id> --status closed`
- **Still present**: leave open, do not duplicate
- **New**: create a new bead with the current turn number

### Return to Orchestrator

Return only a terse summary (2-3 lines): finding counts by severity and the
single most notable tell. Do NOT return JSONL or full finding details.
````

- [ ] **Step 2: Verify it lints clean (including MD041 H1-after-frontmatter)**

Run: `rumdl check pr-review/agents/slop-hunter.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 3: Verify the deferral table and ACTIVE_ASPECTS contract are present**

Run: `grep -c 'ACTIVE_ASPECTS' pr-review/agents/slop-hunter.md`
Expected: `6` (Rule B intro line, four deferral-table rows, Bead Output variable list)

Run: `grep -E 'aspect:slop|--silent|--external-ref' pr-review/agents/slop-hunter.md | wc -l`
Expected: `3` or more

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `feat(pr-review): add slop-hunter agent (fhsk-rhh)`

---

### Task 4: Wire the `slop` aspect into the orchestrator

**Files:**

- Modify: `pr-review/skills/review-pr/SKILL.md`

- [ ] **Step 1: Add `slop` to the argument-hint**

Find this line:

```text
argument-hint: "PR# [aspects: all|code|errors|tests|types|comments|security|api|spec|simplify]"
```

Replace with:

```text
argument-hint: "PR# [aspects: all|code|errors|tests|types|comments|security|api|spec|simplify|slop]"
```

- [ ] **Step 2: Add the `slop` row to the Review Aspects table**

Find this line:

```text
| `simplify` | code-simplifier | Clarity, redundancy, maintainability |
```

Add immediately after it:

```text
| `slop` | slop-hunter | AI-authorship tells in code and prose |
```

- [ ] **Step 3: Add the selection heuristic row**

In the "### 4. Select Applicable Agents" table, find:

```text
| After other reviews OR `simplify` requested | `simplify` |
```

Add immediately after it:

```text
| Code or prose added OR `slop` requested | `slop` |
```

- [ ] **Step 4: Add the model-escalation row**

In the "### 5. Model Escalation" table, find:

```text
| code-simplifier | sonnet | Rarely |
```

Add immediately after it:

```text
| slop-hunter | sonnet | Rarely |
```

- [ ] **Step 5: Document the `ACTIVE_ASPECTS` variable in dispatch**

In "### 7. Launch Review Agents", find:

```text
- `prompt`: Include the PR diff, plus these variables:
  `PARENT_BEAD_ID`, `TURN`, `PR_URL`, `ASPECT`
```

Replace with:

```text
- `prompt`: Include the PR diff, plus these variables:
  `PARENT_BEAD_ID`, `TURN`, `PR_URL`, `ASPECT`. For the `slop-hunter` agent
  also pass `ACTIVE_ASPECTS`: the comma-separated aspect keys of all selected
  agents for this run (the left-column keys from step 4, e.g.
  `code,errors,comments,simplify`), excluding `slop` itself. It drives the
  agent's Rule B deferral.
```

- [ ] **Step 6: Note batch placement**

In "### 7. Launch Review Agents", find:

```text
**Batching**: Launch at most 3 concurrent Task calls per message.
Run `security` + `code` in the first batch. Wait for each batch to
complete before launching the next.
```

Replace with:

```text
**Batching**: Launch at most 3 concurrent Task calls per message.
Run `security` + `code` in the first batch. Wait for each batch to
complete before launching the next. `slop` depends on no other agent's
output; run it in the second batch.
```

- [ ] **Step 7: Verify it lints clean**

Run: `rumdl check pr-review/skills/review-pr/SKILL.md`
Expected: `Success: No issues found in 1 file`

- [ ] **Step 8: Verify all five wiring points landed**

Run: `grep -c 'slop' pr-review/skills/review-pr/SKILL.md`
Expected: `5` or more (argument-hint, aspects table, selection row, model row, ACTIVE_ASPECTS/batching text)

Run: `grep -c 'ACTIVE_ASPECTS' pr-review/skills/review-pr/SKILL.md`
Expected: `1`

- [ ] **Step 9: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `feat(pr-review): wire slop aspect into review-pr orchestrator (fhsk-rhh)`

---

### Task 5: Full-surface verification

**Files:**

- (No file changes — verification only)

- [ ] **Step 1: Lint every touched markdown file together**

Run: `rumdl check pr-review/references/code-slop.md pr-review/references/prose-slop.md pr-review/agents/slop-hunter.md pr-review/skills/review-pr/SKILL.md`
Expected: `Success: No issues found in 4 files`

- [ ] **Step 2: Confirm no dangling JSON/manifest changes are needed**

Run: `git status --short` (or `jj st`)
Expected: only the four files above appear; `release-please-config.json`, `.release-please-manifest.json`, and `plugin.json` are NOT listed.

- [ ] **Step 3: Cross-check catalog/agent consistency**

The agent's Rule B table must defer exactly `C-1`, `C-9`, `C-4`, `C-5`, `C-10`,
`C-13`. Confirm each appears in `code-slop.md` and is marked co-owned:

Run: `grep -E '^### C-(1|4|5|9|10|13) ' pr-review/references/code-slop.md | wc -l`
Expected: `6`

- [ ] **Step 4: Manual dry-run (deferral check, Rule B)**

On a test PR containing an empty `catch {}` (or `except Exception: pass`) and a
code-restating comment:

- Run `/review-pr <PR#>` (default `all`): confirm `slop-hunter` raises **neither**
  `C-9` nor `C-1` (the `errors` and `comments` aspects own them and are active).
- Run `/review-pr <PR#> slop` (lone): confirm `slop-hunter` now raises **both**
  `C-9` and `C-1`.

This proves `ACTIVE_ASPECTS` deferral works in both directions. If you cannot run
a live PR, state so explicitly rather than claiming success.

- [ ] **Step 5: Manual dry-run (discipline check, Rule A)**

Confirm every emitted slop finding's title leads with a catalog ID (`C-n` or
`P-n`). Any finding without a pattern ID is a Rule A violation.

- [ ] **Step 6: Final commit (if any verification fixes were made)**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`.
Message: `test(pr-review): verify slop aspect wiring and deferral (fhsk-rhh)`
<!-- adr-capture: sha256=be2e51b7a4cf34cc; session=15501658; ts=2026-05-28T16:57:03Z; adrs=fhsk-2us -->
