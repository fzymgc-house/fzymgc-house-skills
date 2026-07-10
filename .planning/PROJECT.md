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
- ✓ **GOV-01**: Superseding ADRs record the shipped layout — `fhsk-o9o` (release-please, corrected six-manifest sync, supersedes `fhsk-dgo`) + `fhsk-wdk` (5-plugin root layout; `fzymgc-house/skills/*` superseded-in-practice) — *Validated in Phase 5*
- ✓ **GOV-02**: Cross-project adoption documented (`docs/adoption.md`) + CI drift gate (`tests/test_skill_catalog.py`) enforcing catalog completeness — *Validated in Phase 5*

### Active

<!-- No open requirements. The dominant governance thread closed in Phase 5. -->

- *None — all v1 requirements validated. GOV-01 and GOV-02 closed in Phase 5 (see Validated above).*

### Out of Scope

- Terraform destructive operations (create/delete workspaces, apply/discard runs, variable and private-registry management) — the terraform skill is deliberately read-only for safety
- Full MCP tool-definition exposure into context — the whole point of the gateway pattern is to keep only SKILL.md loaded
- Duplicating skill content into the Codex wrapper layer — wrappers symlink back to source; single source of truth
- Pre-commit git hooks as quality gates — jj does not fire git hooks reliably; `Taskfile.yaml` is the single gate source
- Per-skill independent version lines — superseded in practice by one repo-wide version (see Key Decisions)

## Context

- **Current state — v1.0 shipped (2026-07-10).** All five phases complete; the 5-plugin
  marketplace (`homelab`/`jj`/`dev-flow`/`tmux`/`grepping`) is live on both Claude Code and
  Codex. Plugin-layout governance is reconciled (ADRs `fhsk-o9o` + `fhsk-wdk`) and cross-project
  adoption is documented (`docs/adoption.md`) and CI-enforced (`tests/test_skill_catalog.py`).
  All v1 requirements validated; milestone archived to `.planning/milestones/v1.0-*`.
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
`fzymgc-house/skills/*` paths are SUPERSEDED in practice. Formally reconciled in Phase 5 by ADR
`fhsk-o9o` (re-homes the versioning decision, corrects the sync list to six manifests, supersedes
`fhsk-dgo`) and `fhsk-wdk` (records the shipped 5-plugin root layout) — GOV-01 closed.
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
| release-please, manifest mode, one repo-wide version | Automated, conflict-free version + changelog sync across plugins | ✓ Good (layout formally reconciled by `fhsk-o9o`/`fhsk-wdk`, Phase 5) |
| jj op-log-rewind gated MUST NOT + recovery ladder | Op log is repo-global; restores clobbered concurrent agents | ✓ Good |
| Beads as PR-review persistence (Approach B) | Single source of truth; survives session boundaries | ✓ Good (ADR still Draft/unlocked) |
| Dual marketplace over single-source symlinks | Reuse on Claude + Codex without forking content | ✓ Good |
| Sibling worktree layout for fix agents | Nested `.claude/worktrees/` confused LSP; agents clobbered base repo | ✓ Good |
| `pr-review` work folded into `dev-flow` agents | Restructure landed review agents in the workflow plugin, not a separate plugin | ✓ Good (shipped layout recorded in `fhsk-wdk`, Phase 5) |

## ADR Decision Register (Pass 2)

Compact register of the 31 active LOCKED ADR decisions ingested from `docs/adr/`
(Pass 2), plus two Phase-5 governance ADRs (`fhsk-o9o`, `fhsk-wdk`) appended below
and marked `(Phase 5)`; `fhsk-dgo` is now superseded by `fhsk-o9o`. Full statements
live in `.planning/intel/pass2/decisions.md`; the Pass-2 ADRs are retrospective and
map to already-Complete phases 1–4.
Format: `DEC-adr-fhsk-XXX` — one-line decision — source — status.

### Drain harness & workers

- `DEC-adr-fhsk-0cd` — Bootstrap the drain harness explicitly via `/drain init` with pre-flight checks; missing assets error rather than silently mutate — source `docs/adr/fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md` — LOCKED
- `DEC-adr-fhsk-5dj` — Replace the drain-with-worker command with a parameterized skill taking an optional worker-type arg, supporting multiple multiplexers — source `docs/adr/fhsk-5dj-convert-drain-worker-command-parameterized-skill.md` — LOCKED
- `DEC-adr-fhsk-8g6` — Drain workers autonomously finish branches (push + PR) via non-interactive finishing-a-development-branch at the clean sentinel — source `docs/adr/fhsk-8g6-drain-finishes-branch-autonomously-push-pr-at-clean-sentinel.md` — LOCKED
- `DEC-adr-fhsk-8yz` — Extract shared cmux/tmux driver logic into a `_muxdriver.py` stdlib module for protocol consistency across scripts — source `docs/adr/fhsk-8yz-share-cmux-tmux-driver-logic-via-muxdriver-module-not-script.md` — LOCKED
- `DEC-adr-fhsk-dtk` — Require AskUserQuestion confirmation before launching privileged /drain-with-worker workers; never auto-fire — source `docs/adr/fhsk-dtk-gate-drain-worker-launch-behind-askuserquestion-never-auto-f.md` — LOCKED
- `DEC-adr-fhsk-e4i` — Skills emit /goal conditions for a user/driver to submit; never invoke /goal directly (agents lack the tool) — source `docs/adr/fhsk-e4i-never-invoke-goal-from-skill-emit-condition-user-or-driver-s.md` — LOCKED
- `DEC-adr-fhsk-eqt` — Move the 12-step drain iteration protocol into the dev-flow skill, off the /goal condition, avoiding 4K-char truncation — source `docs/adr/fhsk-eqt-store-drain-iteration-protocol-skill-not-goal-condition.md` — LOCKED
- `DEC-adr-fhsk-thw` — Adopt /goal (not /loop) as the sole autonomous bead-queue drain primitive, eliminating timer-based prompt drift — source `docs/adr/fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md` — LOCKED
- `DEC-adr-fhsk-ce3` — Store drain lessons as bd notes on drain (ephemeral) or epic (persistent) beads, not the prompt body — source `docs/adr/fhsk-ce3-store-drain-lessons-bd-notes-rather-than-prompt-body.md` — LOCKED
- `DEC-adr-fhsk-buu` — Use `bd create --type drain` for audit-trail drain beads instead of `bd mol pour` (verified bd incompatibilities); supersedes fhsk-rqh — source `docs/adr/fhsk-buu-use-bd-create-type-drain-drain-bead-creation-not-bd-mol-pour.md` — LOCKED

### Beads / handoff / session-state

- `DEC-adr-fhsk-57f` — One handoff skill with conditional create/resume modes over a shared body-schema; thin `/handoff` + `/handoff-resume` entry points — source `docs/adr/fhsk-57f-package-handoff-create-and-resume-as-one-conditional-workflo.md` — LOCKED
- `DEC-adr-fhsk-8xn` — Handoff beads carry only the session-state delta via bd dep edges; reject full re-snapshots as drift/maintenance burden — source `docs/adr/fhsk-8xn-carry-session-state-delta-handoff-body-not-full-re-snapshot.md` — LOCKED
- `DEC-adr-fhsk-s15` — Register a custom bd type for handoffs for independent querying, a distinct lifecycle, and untracked-exploration support — source `docs/adr/fhsk-s15-use-custom-bd-type-handoffs-not-label-or-note.md` — LOCKED
- `DEC-adr-fhsk-zds` — Use the drain bead (with `drain_workspace`/`drain_sentinel` metadata) as the durable cross-session handoff carrier, not temp files — source `docs/adr/fhsk-zds-use-drain-bead-as-cross-session-handoff-carrier-not-temp-fil.md` — LOCKED
- `DEC-adr-fhsk-hj3` — Close beads at merge time, not fix commit; Phase 4 leaves the bead in_progress and suggests finishing-a-development-branch — source `docs/adr/fhsk-hj3-leave-bead-progress-at-hand-off-delegate-closure-merge.md` — LOCKED
- `DEC-adr-fhsk-3xn` — Phase 0 of solving-a-bead hard-blocks on any open blocker dependency rather than emitting a soft warning — source `docs/adr/fhsk-3xn-hard-block-skill-entry-unmet-bead-blocker-dependencies.md` — LOCKED
- `DEC-adr-fhsk-bj8` — Use `agent:<type>` bead labels as the sole subagent dispatch signal with a static known-set fallback to general-purpose — source `docs/adr/fhsk-bj8-use-agent-label-as-sole-subagent-dispatch-signal.md` — LOCKED
- `DEC-adr-fhsk-ypt` — Demote bug-bead suggested fixes to non-authoritative hypotheses, routing them through systematic-debugging — source `docs/adr/fhsk-ypt-treat-bug-bead-suggested-fixes-as-non-authoritative-hypothes.md` — LOCKED

### Review & slop pipeline

- `DEC-adr-fhsk-2us` — Use ACTIVE_ASPECTS deferral in slop-hunter to suppress co-owned patterns when owning aspects are present, eliminating duplicate findings — source `docs/adr/fhsk-2us-use-active-aspects-deferral-cross-aspect-deduplication-slop.md` — LOCKED

### Plugin packaging & marketplace

- `DEC-adr-fhsk-a6v` — Ship tmux as a standalone plugin at the level of jj/homelab (not folded into dev-flow) for cross-boundary reuse — source `docs/adr/fhsk-a6v-add-tmux-as-standalone-plugin-rather-than-folding-into-dev-f.md` — LOCKED
- `DEC-adr-fhsk-wdk` — Record the shipped 5-plugin root layout (homelab/jj/dev-flow/tmux/grepping) with Codex thin wrappers; mark the design-plan `fzymgc-house/skills/*` layout superseded-in-practice and PR-review-inside-dev-flow; Related to fhsk-o9o + fhsk-a6v — source `docs/adr/fhsk-wdk-record-shipped-5-plugin-root-layout-superseding-design-plan.md` — LOCKED (Phase 5, GOV-01)

### ADR / release / CI tooling

- `DEC-adr-fhsk-4bi` — Use @probelabs/maid via bunx as the primary Mermaid lint engine, with optional mmdc render-validate fallback — source `docs/adr/fhsk-4bi-adopt-probelabs-maid-as-primary-mermaid-lint-engine.md` — LOCKED
- `DEC-adr-fhsk-bmn` — Add a bd-free INV-A25 CI check for ADR YAML frontmatter title, complementing the bd-guarded INV-A22 content-fidelity check — source `docs/adr/fhsk-bmn-add-bd-free-inv-a25-frontmatter-check-alongside-bd-guarded-i.md` — LOCKED
- `DEC-adr-fhsk-dgo` — Adopt release-please (over cog) with restored in-file plugin versions + CHANGELOG.md; supersedes fhsk-toy and fhsk-7y4 — source `docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md` — LOCKED, SUPERSEDED by `fhsk-o9o` (Phase 5)
- `DEC-adr-fhsk-o9o` — Re-home the release-please decision forward intact, correcting the version-synced manifest list from four to the current six (`+ tmux/plugin.json`, `grepping/plugin.json`); supersedes fhsk-dgo — source `docs/adr/fhsk-o9o-use-release-please-file-plugin-versions-across-six-shipped-m.md` — LOCKED (Phase 5, GOV-01)
- `DEC-adr-fhsk-h3z` — Move conventional-commit validation from a local git hook to a CI check on the PR title (reliable across jj/git) — source `docs/adr/fhsk-h3z-validate-conventional-commits-at-pr-title-boundary-ci.md` — LOCKED
- `DEC-adr-fhsk-nlw` — Rewrite ADR tooling (render-adr, adr-doctor) as PEP 723 `uv run --script` Python modules for in-memory render matching + unit tests — source `docs/adr/fhsk-nlw-rewrite-adr-scripts-as-python-pep-723-uv-run-script-modules.md` — LOCKED
- `DEC-adr-fhsk-slp` — Add YAML title frontmatter to all ADR files and drop the body H1 to satisfy the Starlight docs build — source `docs/adr/fhsk-slp-adopt-yaml-title-frontmatter-adr-files-drop-body-h1.md` — LOCKED

### Memory model

- `DEC-adr-fhsk-e0u` — Adopt a two-tier spine (repo-wide) / overlay (workspace-local) scope model for the memory-curator plugin — source `docs/adr/fhsk-e0u-use-two-tier-spine-overlay-memory-scope-model.md` — LOCKED
- `DEC-adr-fhsk-p07` — Replace the blocking Stop-hook capture nudge with a silent SessionStart briefing + throttled PostToolUse nudge — source `docs/adr/fhsk-p07-replace-blocking-stop-hook-capture-nudge-silent-sessionstart.md` — LOCKED

### Miniflux curation

- `DEC-adr-fhsk-0qz` — Keep deterministic blocklist/keeplist regex rules server-side in Miniflux; Claude handles ranking, digest prose, and rule proposals — source `docs/adr/fhsk-0qz-split-curation-into-deterministic-rules-miniflux-and-reasoni.md` — LOCKED
- `DEC-adr-fhsk-pqw` — Wrap the Miniflux client directly (no MCP intermediary), diverging from the homelab MCP-gateway pattern — source `docs/adr/fhsk-pqw-wrap-miniflux-client-directly-not-via-mcp-gateway.md` — LOCKED
- `DEC-adr-fhsk-qs9` — Resolve Miniflux URL/API-key with env vars taking precedence over the XDG config file — source `docs/adr/fhsk-qs9-use-env-then-file-config-resolution-miniflux-credentials.md` — LOCKED

### Superseded ADRs (historical, not active)

- `fhsk-0o2` — Split the drain harness into formula + command (Stop-hook body) + canonical-reference skill — SUPERSEDED (locked:false); supersedes / back-references fhsk-eqt — source `docs/adr/fhsk-0o2-split-drain-harness-into-formula-command-and-skill.md`
- `fhsk-7y4` — Single repo-wide version replacing per-package semver streams — SUPERSEDED by fhsk-dgo — source `docs/adr/fhsk-7y4-adopt-single-repo-wide-version-replacing-per-package-streams.md`
- `fhsk-rqh` — `bd mol pour` with a versioned formula for drain bead creation — SUPERSEDED by fhsk-buu — source `docs/adr/fhsk-rqh-use-bd-mol-pour-versioned-formula-drain-bead-creation.md`
- `fhsk-toy` — Tag-only cog releases with no commit to main — SUPERSEDED by fhsk-dgo — source `docs/adr/fhsk-toy-use-tag-only-cog-releases-no-commit-main.md`

## Supporting Specs & Constraints (Pass 3)

Pass 3 ingested 44 design/spec/plan docs (`docs/superpowers/{plans,specs}` + `docs/dev-flow-pipeline.md` + `docs/adr/README.md`) — the design/spec elaborations behind the locked ADRs above. They added **0 new decisions**; by precedence (ADR > SPEC > DOC) all 44 were subordinated as supporting detail:

- **19 technical constraints** (implementation contracts, NFRs, protocols, schemas) — see `.planning/intel/pass3/constraints.md`
- **21 context groups** (dev-flow pipeline architecture, runbooks, reference docs) — see `.planning/intel/pass3/context.md`
- Superseded-in-practice and recorded as historical: the cog release flow (→ release-please / `fhsk-dgo`) and the original drain-skill design (→ cold-boot redesign).

Conflict report: `.planning/INGEST-CONFLICTS-pass3.md` (0 blockers, 0 warnings, 6 info).

---

*Last updated: 2026-07-10 after v1.0 "Skills Marketplace" milestone — all five phases shipped, all v1 requirements validated; ROADMAP/REQUIREMENTS archived to `.planning/milestones/v1.0-*`. Prior: 2026-07-10 Phase 5 complete (GOV-01/GOV-02 validated: ADRs `fhsk-o9o` + `fhsk-wdk`, `docs/adoption.md`, catalog drift gate); 2026-07-09 Pass 3 supporting specs/docs (44) subordinated as constraints/context; Pass 2 ADR intel (docs/adr, 35 ADRs) merged into the ADR Decision Register; 2026-07-08 retrospective `.planning/` bootstrap from ingest intel*
