# Decisions (ADR intel)

Synthesized from ADR-classified planning docs. Higher-precedence than SPEC/PRD/DOC.
Two decisions are LOCKED (cannot be auto-overridden); one is PROPOSED (Draft, not locked).

---

## DEC-release-please-manifest-versioning

- source: docs/plans/2026-02-16-release-please-design.md
- status: LOCKED (Status: Approved)
- scope: versioning + changelog automation, marketplace/plugin/SKILL.md version fields, release workflow

Decision: Integrate release-please as a GitHub Action in **manifest (flat) mode**.

- One root package tracks the plugin-level version; updates `.claude-plugin/marketplace.json` `$.version` and `fzymgc-house/plugin.json` `$.version` via the native `jsonpath` updater.
- One package **per skill** tracks skill-level versions; updates each `SKILL.md` `metadata.version` line via the `generic` updater keyed on the `# x-release-please-version` marker comment.
- A drift-detection CI check keeps the release-please config in sync with the actual skill directories.
- release-please bumps only packages touched by conventional commits; a combined Release PR accumulates changes until merged.

Note (provenance only, not a merge): the ADR enumerates packages under `fzymgc-house/skills/{grafana,terraform,review-pr,respond-to-pr-comments,address-review-findings,skill-qa}`. Later SPEC/DOC sources propose a `homelab`/`pr-review` directory layout that contradicts this. Under precedence this LOCKED ADR's layout wins — see INGEST-CONFLICTS.md INFO entries. Downstream should author a superseding ADR before adopting the restructured paths.

---

## DEC-jj-op-log-recovery-gate

- source: docs/plans/2026-05-01-jj-skill-op-log-recovery-rule-design.md
- status: LOCKED (Status: Approved, awaiting implementation plan; bead fzymgc-house-skills-5qh)
- scope: jj skill op-log recovery safety, multi-workspace hazard prevention

Decision: Adopt Option B. Gate the op-log-rewind class (`jj op restore`, `jj op abandon`) behind explicit user approval, worded as **MUST NOT** (not "ask user first"). Publish a canonical recovery ladder pushing agents toward safe alternatives:

1. Inspect read-only first: `jj --at-op=<op-id> log` (no mutation).
2. `jj undo` — most-recent successful op only. Traps: if it errors "cannot undo a merge" and suggests `jj op restore`, stop and ask the user; never `jj undo` a `jj git push` (corrupts bookmarks).
3. `jj op revert <op-id>` — surgical inverse of a specific past op without rewinding global state.

Rationale: the op log is repo-global across all workspaces; `jj op restore` in one workspace silently reverted a concurrent agent's edits via stale-workspace `update-stale` resolution.

Files touched: `jj/skills/jujutsu/SKILL.md`, `jj/skills/jujutsu/references/jj-reference.md`, `jj/skills/jujutsu/CHANGELOG.md`. No hook/agent/pr-review/superpowers changes.

---

## DEC-beads-review-persistence

- source: docs/plans/2026-02-15-beads-review-integration-design.md
- status: PROPOSED (Status: Draft — locked:false; do NOT treat as locked)
- scope: review-pr + respond-to-pr-comments persistence layer

Decision: Use beads as the persistent data layer between PR-review skills (**Approach B: subagents create finding beads directly** via `bd` CLI, no intermediate JSONL).

- Orchestrator creates a PR-review parent bead and passes its ID to subagents.
- Subagents create child finding beads via `bd create`.
- respond-to-pr-comments queries beads for prior review state; re-reviews output deltas.
- Hierarchy: Epic (optional) → PR Review bead (one per PR) → Finding beads (children). Labels discriminate review beads from regular project issues.
- Rejected: Approach A (orchestrator converts JSONL — double-processing) and Approach C (JSONL + sync script — two sources of truth).

Because this ADR is Draft/unlocked, it can be overridden by a later locked decision without a hard block.
