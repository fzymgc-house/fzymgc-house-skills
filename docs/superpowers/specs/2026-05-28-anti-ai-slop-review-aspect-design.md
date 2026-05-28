# Anti-AI-Slop Review Aspect (Code + Docs)

- **Design bead:** fhsk-rhh
- **Date:** 2026-05-28
- **Status:** Draft for review
- **Plugin:** `pr-review`

## Problem

AI-generated code and documentation carry recognizable tells that a careful
human author would strip before committing: comments that restate the code,
vestigial "removed old logic" narration, defensive validation for cases that
cannot occur, single-use abstractions, padded docstrings, prose littered with
em-dashes and "it's not just X, it's Y" parallelism. None of the existing
`pr-review` agents target these tells as a class. `code-reviewer` checks
standards and bugs, `comment-analyzer` checks comment *accuracy*,
`code-simplifier` checks *clarity*. A comment can be accurate, clear, and
standards-compliant while still being obvious AI slop.

The `humanizer` skill catalogs 28 prose AI-tells but (a) lives in the user's
dotfiles, not this repo, and (b) *rewrites* text rather than reviewing it. We
need a review-only detector, integrated into the `/review-pr` orchestrator,
covering both code and prose.

## Goals

- Detect AI-authorship tells in PR diffs for both code and prose.
- Integrate as a first-class `review-pr` aspect (`slop`), part of the default
  `all` run.
- Report-only: emit findings as beads matching the existing agent contract;
  fixes are handled downstream by `address-findings` / `fix-worker`.
- Be self-contained: bundle condensed pattern catalogs so the agent does not
  depend on the dotfiles `humanizer` skill being installed.
- Produce zero duplicate findings with adjacent aspects.

## Non-Goals

- Auto-fixing or rewriting (explicitly deferred to the existing fix pipeline).
- Replacing `humanizer` for prose authoring (that skill mutates; this reviews).
- Reviewing code outside the PR diff.
- A standalone directly-invoked skill. This is an orchestrated aspect only.

## The provenance lens (boundary definition)

The agent's distinguishing question is **provenance, not quality**: "does this
change bear the fingerprints of unreviewed AI generation that a careful human
author would have removed?"

| Agent | Question it asks |
|-------|------------------|
| `comment-analyzer` | Is this comment accurate / will it rot? |
| `code-simplifier` | Can this be clearer without changing behavior? |
| `code-reviewer` | Does this violate project standards or have bugs? |
| **`slop-hunter`** (new) | Does this carry an AI-authorship tell a human would remove? |

### Anti-duplication: two complementary rules

Some catalog patterns are genuinely co-owned by an adjacent aspect (verified
against the agent prompts: `comment-analyzer` explicitly flags comments that
"merely restate obvious code"; `silent-failure-hunter` owns swallowed errors;
`code-reviewer` is "ruthless about YAGNI"). The catalog-ID rule alone does NOT
prevent duplication, because it only constrains what `slop-hunter` raises — it
imposes no obligation on the other agents. So two rules are needed.

**Rule A — named-pattern discipline (intra-agent).** Every `slop-hunter`
finding MUST cite a specific catalog pattern ID (e.g. `C-3`, `P-9`). If you
cannot name the pattern, it is not a slop finding and you MUST NOT raise it.
This stops `slop-hunter` from drifting into vague "this could be better"
territory that belongs to other aspects.

**Rule B — cross-aspect deferral (inter-agent).** `slop-hunter` is the
"catch what the specialists miss" net. For each *co-owned* pattern, it
suppresses the finding when the owning aspect is part of the current run, and
only raises it when that aspect is absent. The orchestrator passes the running
aspect set to `slop-hunter` as `ACTIVE_ASPECTS` (new variable, see Orchestrator
wiring).

| Co-owned pattern | Owning aspect | `slop-hunter` raises it only when |
|------------------|---------------|-----------------------------------|
| `C-1` (comment restates code) | `comments` | `comments` ∉ `ACTIVE_ASPECTS` |
| `C-9` (swallowed errors / empty catch) | `errors` | `errors` ∉ `ACTIVE_ASPECTS` |
| `C-4`, `C-5`, `C-10` (YAGNI: single-use abstraction, no-consumer shim, speculative config) | `code` | `code` ∉ `ACTIVE_ASPECTS` |
| `C-13` (copy-paste clone — "extract a helper" is redundancy elimination) | `simplify` | `simplify` ∉ `ACTIVE_ASPECTS` |

Because `code` runs on every `all` invocation, the YAGNI trio is in practice
always deferred to `code-reviewer`; `slop-hunter` only picks them up when a user
explicitly runs `slop` in isolation (`/review-pr <PR> slop`). All **other**
patterns — `C-2`, `C-3`, `C-6`, `C-7`, `C-8`, `C-11`, `C-12`, `C-14`, `C-15`,
`C-16`, and every prose `P-pattern` — have no other owner and are always
`slop-hunter`'s to raise.
(No existing agent reviews prose *style*; `comment-analyzer` judges comment
*accuracy/rot*, a different axis, so the P-patterns do not overlap it.)

**Rule A worked example:** "this 40-line function could be split" has no named
slop pattern → defer to `code-simplifier`. **Rule B worked example:** an empty
`catch {}` under a default `all` run → suppressed (errors aspect owns it); the
same `catch {}` under a lone `slop` run → raised as `C-9`.

The agent also queries prior `aspect:slop` findings across turns (the existing
cross-turn dedup mechanism) before raising new ones.

## Pattern catalogs

Two reference files under `pr-review/references/`, each pattern carrying a
stable ID, a one-line tell, a before/after, and a severity hint.

### `references/code-slop.md` (code tells, `C-n`)

- **C-1** Comment restates the code (`// increment i`).
- **C-2** Vestigial narration of edits (`// removed old logic`, `// previously
  we did X`, `// NEW:`).
- **C-3** Defensive validation for cases internal code guarantees cannot occur
  (null checks on framework-guaranteed values, re-validating already-validated
  input).
- **C-4** Abstraction (helper, wrapper, interface) used exactly once with no
  second caller in sight.
- **C-5** Backwards-compat shim / re-export / deprecation alias for code that
  has no existing consumers (new code does not need a migration path).
- **C-6** Padded docstrings: marketing adjectives ("robust, scalable,
  efficient"), restating the signature, multi-paragraph blocks on trivial
  functions.
- **C-7** Tests that assert mock/framework behavior (`expect(mock).toHaveBeenCalled`
  as the only assertion) rather than real outcomes.
- **C-8** `_unused` / `_var` renames or `// noqa` to silence rather than delete
  dead code.
- **C-9** Over-broad `try/except` (or `catch {}`) that swallows errors or
  fabricates fallbacks for conditions that should propagate.
- **C-10** Speculative configuration, feature flags, or parameters for
  hypothetical future requirements with no current caller.
- **C-11** Hallucinated / fabricated imports: plausible-sounding modules or
  symbols that do not exist (`express-validator-utils`). Severity `important`
  (the code cannot run). Verify against the dependency manifest
  (`package.json`, `requirements.txt`, `go.mod`, etc.); skip if no manifest is
  present in the diff context.
- **C-12** Stale / deprecated API usage from a training cutoff
  (`new Buffer(...)`, `url.parse`, deprecated framework calls) that still
  "works" so it passes tests.
- **C-13** Copy-paste clone: a large near-identical block duplicated with one
  field changed where a human would extract a helper. (Distinct from C-4:
  C-13 is *too much* duplication, C-4 is *premature* abstraction. Respect the
  "three similar lines beats a premature abstraction" rule — flag only sizable
  clones.)
- **C-14** Hardcoded placeholder secrets / values left in code
  (`"your-secret-key"`, `"change-me"`, `"SECRET_KEY_HERE"`, `TODO`-as-value).
  (`critical` when it reaches a security-relevant path.)
- **C-15** Stylistic discontinuity: the change uses different naming, error
  handling, or logging conventions than the surrounding file/module — the
  clearest tell of code generated in isolation without project context.
- **C-16** Comment-as-section-header banners (`# ===== User Auth =====`) and
  uniform comment density (evenly distributed explanatory comments rather than
  clustered around the genuinely non-obvious).

**Meta-signal (guidance, not a numbered finding).** The defining property of
AI-native code is that the *failure mode looks like the success mode*: it
compiles, lints clean, has descriptive names, and handles every exception — yet
solves the wrong problem or arrives "fully formed" with logging/docs/error
handling a human would have added incrementally. No single tell is proof; the
signal is the *clustering and density* of tells in one change. Weight findings
accordingly and prefer one well-evidenced finding over many speculative ones.

**Handoff:** "code solves a problem the ticket did not ask for" (requirement
misalignment) is `spec-compliance`'s aspect, not `slop`. Do not raise it here.

### `references/prose-slop.md` (prose tells, `P-n`)

Condensed from the `humanizer` catalog to the subset that survives in technical
docs and comments. Cites `humanizer` and the Wikipedia "Signs of AI writing"
page as origin.

- **P-1** Significance/legacy inflation ("marks a pivotal moment", "stands as a
  testament").
- **P-2** Promotional language ("seamless", "powerful", "cutting-edge",
  "boasts").
- **P-3** Superficial `-ing` pseudo-depth and the **hedging-verb family**
  ("ensuring", "highlights", "supports", "reflects", "underpins", "aligns
  with"). Per 2026 analyses this verb family is now the *strongest* lexical
  tell ("ensuring" over-represented ~4.3x); a human just says what the thing
  does.
- **P-4** Rule-of-three padding ("fast, reliable, and scalable").
- **P-5** Em-dash overuse where commas/periods read cleaner. (Weak on its own
  now — only ~18.5% of AI text carries one — so treat as corroborating, never
  as a standalone finding.)
- **P-6** Title Case In Headings.
- **P-7** Emoji-decorated headings or bullets.
- **P-8** Inline-header vertical lists (`- **Performance:** ...`).
- **P-9** Negative parallelism / tailing negation ("it's not just X, it's Y";
  "no guessing").
- **P-10** Filler and excessive hedging ("in order to", "it is important to
  note that", "could potentially possibly").
- **P-11** Signposting ("Let's dive in", "Here's what you need to know").
- **P-12** Chatbot artifacts ("Great question!", "I hope this helps", "Of
  course!") and knowledge-cutoff disclaimers left in committed text.
- **P-13** The signature AI sentence shape **"X plays a crucial / critical /
  pivotal role in shaping Y"** and its kin ("is essential for", "serves as a
  testament to") — statistically the single most formulaic structure in LLM
  prose.
- **P-14** Intensifier adverbs asserting magnitude without evidence
  ("significantly", "effectively", "directly", "increasingly", "vastly"). If a
  number can't back the intensifier, cut it.
- **P-15** Vocabulary clichés over-indexed in LLM output: *delve, tapestry,
  realm, multifaceted, pivotal, bustling, underscore, testament, foster,
  embark, myriad, leverage, robust, holistic, comprehensive, synergy,
  paradigm, groundbreaking, transformative*. Individually fine; clustered they
  produce press-release texture.

**Density principle (shared with code).** No single P-pattern is proof — human
writers use em-dashes and say "delve". The signal is *clustering*. Raise a
prose-slop finding when several tells co-occur in one passage, not on an
isolated word. Project conventions in `AGENTS.md`/`CLAUDE.md` win (a repo that
mandates emoji headings suppresses `P-7`).

### Prose scope

Prose patterns apply **anywhere prose lives** — standalone docs (`.md`, `.rst`,
`.txt`) AND code comments / docstrings. Handoff rule with `comment-analyzer`:
`slop-hunter` judges *style/provenance* (P-patterns), `comment-analyzer` judges
*accuracy/rot*. A comment can earn findings from both, but they will be
different findings (one cites a P-pattern, the other cites inaccuracy), so they
do not duplicate.

## Agent contract

`pr-review/agents/slop-hunter.md`, structured identically to the existing
review agents:

- **Frontmatter:** `name: slop-hunter`, `description` (one line + "Used by the
  review-pr orchestrator for the `slop` aspect."), `model: sonnet`,
  `isolation: worktree`, `tools: Read, Grep, Glob, Bash`.
- **Environment block:** follow `pr-review/references/vcs-detection-preamble.md`
  to detect VCS and verify location.
- **Project standards:** read root + nested `AGENTS.md` (and `CLAUDE.md`
  addendum) before analysis. Project conventions override catalog defaults
  (e.g. if a repo mandates emoji headings, suppress `P-7`).
- **Scope:** exactly the PR diff. Pre-existing slop in unchanged code is out of
  scope unless the change directly touches it.
- **Cross-aspect deferral:** apply Rule B above using `ACTIVE_ASPECTS`. Suppress
  `C-1` when `comments` is active, `C-9` when `errors` is active,
  `C-4`/`C-5`/`C-10` when `code` is active, and `C-13` when `simplify` is
  active.
- **Findings:** report-only. Use the canonical `bd create` block matching the
  other review agents (cf. `code-simplifier.md`), substituting `aspect:slop` and
  leading the title with the pattern ID:

  ```bash
  bd create "<C-n|P-n>: <first sentence of finding>" \
    --type <bug|task|feature> \
    --priority <0-3> \
    --parent "$PARENT_BEAD_ID" \
    --labels "pr-review-finding,aspect:slop,severity:<critical|important|suggestion>,turn:$TURN" \
    --external-ref "$PR_URL" \
    --silent \
    --description "..."
  ```

  Use the standard severity→priority map shared by the other agents. Praise is
  not beaded (mention it in the return summary instead).
- **Severity guidance:** most slop is `suggestion`; `C-3`/`C-9` (swallowed
  errors, validation masking real bugs) and `C-14` (placeholder secret on a
  security path) may rise to `important`/`critical`; everything else rarely
  above `suggestion`.
- **Cross-turn dedup:** query
  `bd list --parent "$PARENT_BEAD_ID" --label "aspect:slop" --status open --json`
  before raising new findings.
- **Return value:** terse 2-3 line summary (counts by severity + most notable
  item). No JSONL, no full finding bodies.

## Orchestrator wiring (`review-pr/SKILL.md`)

- Add `slop` to the `argument-hint` aspect list and the Review Aspects table:
  `| slop | slop-hunter | AI-authorship tells in code and prose |`.
- Add a row to the **Select Applicable Agents** table (step 4):
  `| Code or prose added OR \`slop\` requested | \`slop\` |`. Under `all`, every
  agent runs regardless of heuristics (existing rule), so `slop` runs by
  default.
- Add a model-selection row (`slop-hunter | sonnet | Rarely`).
- Add `slop-hunter` to the dispatch logic / agent name list (`subagent_type`).
- **Pass the new `ACTIVE_ASPECTS` variable** to the `slop-hunter` task prompt.
  Construction and format are explicit to avoid plan-author ambiguity:
  - **When:** built after step 4 (Select Applicable Agents) resolves the run's
    agent set, and passed in the step-7 `slop-hunter` task prompt alongside the
    existing `PARENT_BEAD_ID`, `TURN`, `PR_URL`, `ASPECT` variables.
  - **Format:** comma-separated **aspect keys** (the left-column keys of the
    step-4 table: `code,errors,comments,simplify,...`), NOT agent names. Rule B
    matches on these keys. Omit `slop` itself from the value (a run cannot defer
    to itself).
  - This is the only agent that needs the variable; no other agent's variable
    set changes.
  - **Batching:** `slop-hunter` depends on no other agent's output, so it may
    run in any batch; place it in the second batch (after `security` + `code`)
    to stay within the 3-concurrent-task limit.

## Files

## New

- `pr-review/agents/slop-hunter.md`
- `pr-review/references/code-slop.md`
- `pr-review/references/prose-slop.md`

## Edit

- `pr-review/skills/review-pr/SKILL.md` (aspect wiring)
- Any `pr-review` README / docs that enumerate agents or aspects (verify during
  implementation).

## No change

- `release-please-config.json` / `.release-please-manifest.json`: the
  `pr-review` package is keyed on the `"pr-review"` path with no sub-path
  filter, so any commit touching `pr-review/**` bumps it. Agents and references
  are not separate package markers; adding files under `pr-review/` needs no
  manifest change.

## Testing / verification

- `rumdl check` on the three new markdown files and the edited SKILL.md
  (140-char width, MD041 H1-after-frontmatter for the agent file).
- `jq empty` on any touched JSON (none expected).
- Manual: dry-run `/review-pr <PR#> slop` against a PR containing seeded slop
  (one C-pattern, one P-pattern) and confirm exactly the expected beads are
  created with correct `aspect:slop` labels and pattern IDs in titles.
- Deferral check (Rule B): on a diff containing an empty `catch {}` and a
  code-restating comment, run the default `all` set and confirm `slop-hunter`
  raises neither `C-9` nor `C-1` (owned by `errors`/`comments`, both active).
  Then run `/review-pr <PR#> slop` alone and confirm `slop-hunter` now raises
  both. This proves `ACTIVE_ASPECTS` deferral works in both directions.
- Discipline check (Rule A): confirm every emitted slop finding's title leads
  with a catalog ID; reject any finding that cannot name a pattern.

## Sources

The catalogs synthesize and condense these; each reference file should cite its
origins.

Prose tells:

- Wikipedia, "Signs of AI writing" (via the `humanizer` skill).
- Kobak et al. 2025, "excess vocabulary" study; word list at
  `github.com/berenslab/llm-excess-vocab` (delve r≈28, underscores, showcasing,
  pivotal, intricate, realm).
- writehuman.ai, "The Real Signature of AI Writing Isn't the Em-Dash Anymore"
  (2026) — hedging verbs, "X plays a crucial role in shaping Y", intensifiers.
- bloomberry.ai AI-writing-patterns database; telltale-ai; synkrlab phrase list.

Code tells:

- "5 Code Smells Only AI Creates" (dev.to) — hallucinated import, copy-paste
  clone, empty catch, stale API, over-engineered singleton.
- "Code Review Checklist for AI-Generated Code" (gitautoreview.com).
- "How to Identify If Code Is Written by AI" (aquilax.ai) — stylistic
  discontinuity, comment-as-section-header, what-not-why comments, uniform
  comment density, placeholder secrets.
- "9 Dead Giveaways That AI Wrote This Code" / LLM-native code-smell coverage.

## Open questions

None blocking. Catalog pattern lists are the starting set and may grow during
implementation as real PRs surface new tells.
