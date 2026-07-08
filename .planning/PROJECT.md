# fzymgc-house-skills

## What This Is

A multi-platform plugin/skills marketplace for the fzymgc-house org. It publishes
five single-source plugins — `homelab`, `jj`, `dev-flow`, `tmux`, `grepping` — plus a
repo-local Codex compatibility layer, so any repo in the org can install a skill by
name on either the Claude Code or Codex agent harness. It is a mature, already-shipped
project; this `.planning/` set is a retrospective bootstrap assembled from historical
design/implementation docs, not a greenfield plan.

## Core Value

Skills are single-source, discoverable, and reusable across the org's projects — a new
repo can adopt a skill with low friction and without forking content.

## Business Context

<!-- Internal org tooling; not monetized. Kept for the explicit success metric. -->

- **Customer**: fzymgc-house org repos and the agents (Claude Code + Codex) working in them
- **Success metric**: Cross-project reuse — skills are discoverable and reused across projects, with low friction to adopt a skill in a new repo
- **Strategy notes**: Dual marketplace (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) over a single-source skill tree

## Requirements

### Validated

<!-- Shipped and confirmed by the 2026-07-08 codebase map. -->

- ✓ Terraform Cloud skill behind an MCP gateway (read-only ops) — `homelab/`
- ✓ skill-qa SKILL.md validator — `homelab/`
- ✓ tmux/cmux multiplexer scripting skill — `tmux/`
- ✓ grepping (rg/ast-grep/grep) skill with advisory nudge hooks — `grepping/`
- ✓ Multi-agent PR review pipeline with bead-backed findings — `dev-flow/` (review-pr)
- ✓ Autonomous, worktree-isolated fix loop — `dev-flow/` (address-findings)
- ✓ Human-comment handling with prior review-state context — `dev-flow/` (respond-to-comments)
- ✓ Jujutsu (jj) workflow plugin with VCS detection + op-log recovery gate — `jj/`
- ✓ release-please manifest-mode versioning, one repo-wide version line
- ✓ Dual Claude + Codex marketplace over single-source skills (CI drift check)

### Active

<!-- Forward-looking. The dominant open thread. -->

- [ ] **GOV-01**: Author a superseding ADR that records the shipped plugin layout and supersedes the release-please ADR's `fzymgc-house/skills/*` package layout
- [ ] **GOV-02**: Document low-friction cross-project adoption (install path + discovery) so a new org repo can add a skill quickly

### Out of Scope

- Terraform destructive operations (create/delete workspaces, apply/discard runs, variable and private-registry management) — the terraform skill is deliberately read-only for safety
- Full MCP tool-definition exposure into context — the whole point of the gateway pattern is to keep only SKILL.md loaded
- Duplicating skill content into the Codex wrapper layer — wrappers symlink back to source; single source of truth
- Pre-commit git hooks as quality gates — jj does not fire git hooks reliably; `Taskfile.yaml` is the single gate source
- Per-skill independent version lines — superseded in practice by one repo-wide version (see Key Decisions)

## Context

- **Mature project, retrospective bootstrap.** The shipped tree is `homelab/`, `jj/`,
  `dev-flow/`, `tmux/`, `grepping/` at repo root plus `plugins/` Codex wrappers. A
  codebase map already exists at `.planning/codebase/` (authoritative; do not overwrite).
- **Layout evolved twice.** The original single `fzymgc-house` plugin was split/renamed
  into `homelab` + true `dev-flow` agents (the "pr-review" work landed inside `dev-flow`,
  not a standalone `pr-review` plugin). The LOCKED release-please ADR still encodes the
  older `fzymgc-house/skills/*` layout — recorded as locked-but-superseded below.
- **Historical/relocated skills.** Early design docs cover a `grafana` token-efficiency
  skill; grafana is no longer in the marketplace tree (relocated/removed). `miniflux` is
  a later infra skill present in `homelab/` without a corresponding design doc in this
  ingest set. Neither is asserted as a formal v1 requirement here.
- **Coordination substrate.** Beads (`bd`) is the persistent task/decision/finding layer
  across the dev-flow pipeline; worktree isolation uses a sibling `<repo>_worktrees/`
  layout enforced by hooks.
- **Ingest provenance.** Derived from 20 classified docs (3 ADR, 5 SPEC, 12 DOC; 0 PRD).
  With no PRD, requirements below were derived from decisions/constraints/context.

## Constraints

- **Tech stack**: Skills are SKILL.md + Python/Bash supporting code; Python via `uv`; markdown linted by rumdl; quality gates in `Taskfile.yaml` (mirrored in CI)
- **Compatibility**: Claude stays first-class (`.claude-plugin` manifests unchanged); Codex is a thin wrapper layer — skills must remain single-source with no duplication
- **VCS**: When `jj root` succeeds, treat the repo as jj; mutating VCS ops go through jj, read-only git is allowed
- **Versioning**: One repo-wide version line; release-please syncs manifests automatically — never bump versions by hand
- **Security**: Terraform token via `TFE_TOKEN` env to the subprocess; no destructive infra ops; op-log-rewind ops gated behind explicit approval

## Key Decisions

<decisions>
<decision id="DEC-release-please-versioning" locked="true" source="docs/plans/2026-02-16-release-please-design.md">
Adopt release-please as a GitHub Action in manifest (flat) mode for versioning + changelog
automation. LOCKED. Reconciliation: the ADR enumerates per-skill packages under
`fzymgc-house/skills/{grafana,terraform,review-pr,respond-to-pr-comments,address-review-findings,skill-qa}`;
the shipped reality is a SINGLE repo-wide version line synced across all plugin manifests,
and the directory layout is `homelab/dev-flow/jj/tmux/grepping`. The decision (release-please,
manifest mode, automated version sync) is locked; the specific per-skill package layout and
`fzymgc-house/skills/*` paths are SUPERSEDED in practice. A superseding ADR is recommended (GOV-01).
</decision>
<decision id="DEC-jj-op-log-recovery-gate" locked="true" source="docs/plans/2026-05-01-jj-skill-op-log-recovery-rule-design.md">
Gate the op-log-rewind class (`jj op restore`, `jj op abandon`) behind explicit user approval,
worded as MUST NOT (not "ask first"). Publish a canonical recovery ladder: (1) read-only inspect
`jj --at-op=<op-id> log`; (2) `jj undo` for the most-recent successful op only, with traps
(never undo a `jj git push`; stop and ask if it errors on a merge); (3) `jj op revert <op-id>` for
a surgical inverse without rewinding global state. Rationale: the op log is repo-global across
workspaces; a restore in one workspace silently reverted a concurrent agent's edits. LOCKED.
</decision>
<decision id="DEC-beads-review-persistence" locked="false" status="proposed" source="docs/plans/2026-02-15-beads-review-integration-design.md">
Use beads as the persistent data layer between PR-review skills (Approach B: subagents create
finding beads directly via `bd`, no intermediate JSONL). Hierarchy: PR Review bead → child Finding
beads; labels discriminate review beads from project issues. PROPOSED / Draft (not locked) — shipped
in practice in `dev-flow` (review-pr, address-findings), but the ADR itself remains unlocked and
could be superseded without a hard block.
</decision>
</decisions>

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| release-please, manifest mode, one repo-wide version | Automated, conflict-free version + changelog sync across plugins | ✓ Good (layout claims superseded — see GOV-01) |
| jj op-log-rewind gated MUST NOT + recovery ladder | Op log is repo-global; restores clobbered concurrent agents | ✓ Good |
| Beads as PR-review persistence (Approach B) | Single source of truth; survives session boundaries | ✓ Good (ADR still Draft/unlocked) |
| Dual marketplace over single-source symlinks | Reuse on Claude + Codex without forking content | ✓ Good |
| Sibling worktree layout for fix agents | Nested `.claude/worktrees/` confused LSP; agents clobbered base repo | ✓ Good |
| `pr-review` work folded into `dev-flow` agents | Restructure landed review agents in the workflow plugin, not a separate plugin | ✓ Good (contradicts ADR paths — GOV-01) |

---

*Last updated: 2026-07-08 after retrospective `.planning/` bootstrap from ingest intel*
