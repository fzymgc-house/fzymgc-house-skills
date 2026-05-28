# Consolidate `pr-review` Under `dev-flow` (Structural Move)

- **Design bead:** fhsk-ddw
- **Date:** 2026-05-28
- **Status:** Draft for review

## Problem

The repository publishes `pr-review` and `dev-flow` as separate plugins, but
they form one development pipeline and already share substrate: both run on
`bd`, both carry a VCS-detection preamble, and `dev-flow`'s
`subagent-driven-development` skill dispatches `pr-review`'s `code-reviewer`
agent by `subagent_type` — an implicit cross-plugin dependency that breaks if
only `dev-flow` is installed. Keeping them as two plugins forces duplicated
infrastructure (two VCS preambles) and prevents clean wiring of the
brainstorm → plan → implement → review → fix loop.

This spec consolidates `pr-review` into `dev-flow` as a **pure structural
move**. It deliberately changes no behavior: every skill, agent, and reference
keeps its content; only locations, manifests, and internal path references
change. Connecting the pipeline seams and removing the now-redundant second VCS
preamble are a separate follow-up effort (see Non-Goals).

## Goals

- Relocate all `pr-review` skills, agents, references, and evals under
  `dev-flow/`.
- Remove `pr-review` as an independent plugin: drop it from both marketplace
  manifests, delete its Codex wrapper, and remove its release-please packages.
- Retarget every internal `pr-review/...` path reference to `dev-flow/...`.
- Expose the moved agents (and `dev-flow`'s existing agents) to Codex by adding
  the missing `agents` symlink to the `dev-flow` wrapper.
- Leave the repo green: manifests valid, markdown lint-clean, no dangling
  `pr-review/` references, hooks tests passing.

## Non-Goals (deferred to the follow-up wiring spec)

- Wiring `finishing-a-development-branch` → `review-pr`.
- Deduplicating the two VCS preambles (`vcs-preamble.md` vs
  `vcs-detection-preamble.md`). Both land in `dev-flow/references/` unchanged;
  the 12 agents that reference `vcs-detection-preamble.md` keep pointing at it
  (the 13th, `review-gate.md`, references only `vcs-equivalence.md`).
- Resolving the `code-reviewer` ambiguity (the `pr-review` agent vs the
  `requesting-code-review/code-reviewer.md` template).
- Making the `review-pr` → `address-findings` handoff explicit.
- Any change to skill/agent prompt content beyond path strings and stripped
  version markers.

## Decisions

1. **Pure move.** Consolidation is mechanical relocation + path retarget only.
   No behavioral change ships in this effort; all wiring is the follow-up.
2. **Absorb into `dev-flow`'s version.** Drop all four `pr-review*` entries from
   `release-please-config.json` and `.release-please-manifest.json`. The moved
   review skills do **not** get their own release-please packages; they are
   covered by the top-level `dev-flow` package (consistent with how
   `capture-adrs`, `draining-beads`, etc. already lack dedicated entries). The
   now-orphaned `x-release-please-version` markers in the three moved SKILL.md
   files are removed.
3. **Hard cut.** Remove the `pr-review` entry from both marketplaces and delete
   the `plugins/pr-review/` Codex wrapper. No deprecation stub — this is the
   fzymgc-house org's own marketplace; consumers reinstall `dev-flow`.

## Target Layout

```text
dev-flow/
  agents/        # 3 existing (adr-extractor, design-reviewer, plan-reviewer)
                 # + 13 moved (api-contract-checker, code-reviewer,
                 #   code-simplifier, comment-analyzer, fix-worker,
                 #   pr-test-analyzer, review-gate, security-auditor,
                 #   silent-failure-hunter, slop-hunter, spec-compliance,
                 #   type-design-analyzer, verification-runner) = 16 flat
  commands/      # unchanged
  references/    # existing + vcs-detection-preamble.md, vcs-equivalence.md,
                 #   code-slop.md, prose-slop.md
                 # (vcs-preamble.md stays alongside; dedup deferred)
  skills/        # existing + review-pr/, address-findings/, respond-to-comments/
  evals/         # moved from pr-review/evals/
  hooks/  scripts/   # unchanged
```

The `pr-review/` directory is deleted entirely. Agent names do not collide with
`dev-flow`'s existing three; all 16 live flat (Claude auto-discovers agents; no
subdirectories).

## Work Inventory

### A. Move files (VCS-aware move per `references/vcs-preamble.md`)

- `pr-review/agents/*.md` (13) → `dev-flow/agents/`
- `pr-review/skills/review-pr/` → `dev-flow/skills/review-pr/`
- `pr-review/skills/address-findings/` → `dev-flow/skills/address-findings/`
- `pr-review/skills/respond-to-comments/` → `dev-flow/skills/respond-to-comments/`
- `pr-review/references/vcs-detection-preamble.md` → `dev-flow/references/`
- `pr-review/references/vcs-equivalence.md` → `dev-flow/references/`
- `pr-review/references/code-slop.md` → `dev-flow/references/`
- `pr-review/references/prose-slop.md` → `dev-flow/references/`
- `pr-review/evals/` → `dev-flow/evals/`
- Delete `pr-review/plugin.json`.
- `pr-review/CHANGELOG.md` and the three skill-level `CHANGELOG.md` files are
  removed along with the directory (release history is preserved in git; the
  skills no longer have independent release-please packages per Decision 2).
  The skill-level CHANGELOGs do **not** move with their skills.
- `pr-review/evals-workspace/` is gitignored (untracked); it is not moved and
  needs no action.

### B. Retarget internal path references

In all moved files, replace literal `pr-review/` path prefixes with `dev-flow/`.
There are exactly **four** distinct referenced paths under `pr-review/`
(confirmed by grep over `agents/`, `skills/`, `references/`):
`vcs-detection-preamble.md`, `vcs-equivalence.md`, `code-slop.md`,
`prose-slop.md`. Reference sites by path:

- **`vcs-detection-preamble.md`** — the Environment block of **12** moved
  agents (every agent except `review-gate.md`), plus `review-pr/SKILL.md` and
  `address-findings/SKILL.md`.
- **`vcs-equivalence.md`** — `fix-worker.md`, `verification-runner.md`,
  `review-gate.md`, and `vcs-detection-preamble.md` itself (it cross-references
  the equivalence table).
- **`code-slop.md`** and **`prose-slop.md`** — `slop-hunter.md`.

The Verification dangling-reference grep is the backstop that proves no
`pr-review/` prefix survives, but the four paths above are the complete known
set to retarget.

`${CLAUDE_PLUGIN_ROOT}`-based paths (e.g. respond-to-comments's
`pr_comments` script invocation) require **no** change — `CLAUDE_PLUGIN_ROOT`
resolves relative to whichever plugin owns the skill, and the script moves with
its skill directory.

### C. Strip orphaned version markers

Remove the `version: X # x-release-please-version` metadata markers from the
three moved SKILL.md files (`review-pr`, `address-findings`,
`respond-to-comments`), since they are no longer independently released.

### D. Marketplaces

- `.claude-plugin/marketplace.json`: remove the `pr-review` plugin entry.
- `.agents/plugins/marketplace.json`: remove the `pr-review` plugin entry.

### E. Codex wrapper

The wrapper symlinks are real, git-tracked symlinks (git mode `120000`).
Confirmed current state:

- `plugins/pr-review/` contains `.codex-plugin/plugin.json` plus symlinks
  `agents` → `../../pr-review/agents`, `references` → `../../pr-review/references`,
  `skills` → `../../pr-review/skills`.
- `plugins/dev-flow/` contains `.codex-plugin/plugin.json` plus symlinks
  `hooks`, `references`, `scripts`, `skills` — **but no `agents` symlink.**

(Note for reviewers: an isolated worktree may not materialize these symlinks;
verify against the real working tree with `ls -la plugins/<name>/` and
`git ls-files -s plugins/ | grep 120000`, not a sandbox checkout.)

Actions:

- Delete `plugins/pr-review/` in full (the `.codex-plugin/plugin.json` and its
  three symlinks).
- Add an `agents` symlink to `plugins/dev-flow/`:
  `agents -> ../../dev-flow/agents`. The existing `references` and `skills`
  symlinks already point at whole directories, so the moved review references
  and skills are exposed automatically once the files land — no other
  `plugins/dev-flow/` symlink change is required. After the change, verify
  `plugins/dev-flow/` has exactly: `agents`, `hooks`, `references`, `scripts`,
  `skills` symlinks + `.codex-plugin/`.

### F. release-please

- `release-please-config.json`: remove the `pr-review`,
  `pr-review/skills/review-pr`, `pr-review/skills/address-findings`, and
  `pr-review/skills/respond-to-comments` package entries.
- `.release-please-manifest.json`: remove the matching version keys.

### G. Docs

- `CLAUDE.md` and `AGENTS.md`: change the four-plugin description to three
  (`homelab`, `jj`, `dev-flow`); update the repository-structure tree; note
  that the review skills (`review-pr`, `address-findings`,
  `respond-to-comments`), the review agents, and the slop catalogs now live
  under `dev-flow/`.
- `README.md`: has five `pr-review` references — the `### pr-review` section
  heading (line ~22), the `claude plugin install pr-review@fzymgc-house-skills`
  command (line ~89), Codex prose naming `pr-review/` (lines ~98, ~103), and
  the `pr-review/` line in the structure tree (line ~148). Fold the
  `### pr-review` section's content into the `dev-flow` description, drop the
  standalone install command, and update the tree. The dangling-reference grep
  catches the path-form (`pr-review/`) mentions but NOT the heading or install
  command, so these must be edited by hand.

### H. Tests

The structural move breaks three assertions in `tests/`; update them as part of
this work:

- `tests/test_agent_guidance_docs.py:9`: `PR_REVIEW_AGENTS_DIR = REPO_ROOT /
  "pr-review" / "agents"` → point at `dev-flow/agents`. After the move this
  directory holds all 16 agents (13 moved + 3 existing); the test's
  "agents read AGENTS.md before CLAUDE.md" assertion should hold for all of
  them. Rename the constant to drop the `PR_REVIEW_` prefix for clarity.
- `tests/test_codex_marketplace.py:9`: remove `"pr-review"` from
  `EXPECTED_PLUGIN_ORDER` → `["homelab", "jj", "dev-flow"]`.
- `tests/test_codex_marketplace.py:10`: in `EXPECTED_EXTRA_PATHS`, remove the
  `"pr-review": ["agents", "references"]` entry and add `"agents"` to the
  `dev-flow` list → `"dev-flow": ["agents", "hooks", "references", "scripts"]`
  (reflecting the new `agents` symlink from Section E).

## Verification

- `jq empty` on `.claude-plugin/marketplace.json`,
  `.agents/plugins/marketplace.json`, `release-please-config.json`, and
  `.release-please-manifest.json` — all valid JSON.
- `rumdl check` clean on every moved/edited markdown file plus `CLAUDE.md`,
  `AGENTS.md`, and `README.md`.
- **Dangling-reference guard:** a recursive `grep` for `pr-review/` across
  `dev-flow/`, `.claude-plugin/`, `.agents/`, `plugins/`, and the root `*.json`
  / `*.md` files returns nothing outside CHANGELOGs and the gitignored
  `evals-workspace/`. (Historical CHANGELOG mentions are acceptable.)
- **No-plugin guard:** neither marketplace manifest nor the release-please
  config names `pr-review` as a plugin/package.
- **Symlink guard:** `ls -L plugins/dev-flow/agents/` resolves and lists all 16
  agents.
- **Test suite green:** the full suite (`uv run --with pytest pytest`
  over `.claude/hooks/tests/`, `jj/hooks/tests/`, `tests/`) passes **after the
  Section H test updates land**. The `tests/` directory IS affected by this
  move (agent-path and marketplace assertions), so the suite will fail until
  Section H is applied — this is expected, not a regression. The
  `.claude/hooks/` and `jj/hooks/` paths are untouched.
- **Skill resolution sanity:** the moved skills resolve under the `dev-flow`
  namespace (e.g. `dev-flow:review-pr`); the `/review-pr`, `/address-findings`,
  and `/respond-to-comments` invocations still function.

## Risks

- **Missed path reference.** A `pr-review/...` reference left unretargeted
  silently breaks an agent's preamble load. Mitigated by the dangling-reference
  grep guard in Verification.
- **Codex agent exposure regression.** If the `plugins/dev-flow/agents` symlink
  is forgotten, all 16 agents vanish from the Codex layer. Mitigated by the
  symlink guard.
- **Namespace change for callers.** Skills move from the `pr-review:` namespace
  to `dev-flow:`. Any external doc or muscle-memory invoking `pr-review:review-pr`
  must switch to `dev-flow:review-pr`. The bare `/review-pr` slash command is
  unaffected. Documented in the CLAUDE.md/AGENTS.md update.

## Follow-up

A separate spec wires the pipeline seams now that the plugin boundary is gone:
`finishing-a-development-branch` → `review-pr`, VCS-preamble dedup, the
`code-reviewer` ambiguity, and the `review-pr` → `address-findings` handoff.
