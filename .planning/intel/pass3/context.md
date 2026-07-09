# Context (DOC intel — Pass 3)

Provenance: Pass 3 ingest, MERGE mode. 23 DOC-classified docs — implementation runbooks and
two reference docs. Lowest precedence; subordinate to ADR/SPEC when they overlap. Each is an
elaboration of an existing locked decision + its Pass-3 SPEC contract. Keyed by topic,
source-attributed. Deduplicated against Pass 1 `.planning/intel/context.md`.

---

## dev-flow pipeline architecture (reference) — NEW

- source: docs/dev-flow-pipeline.md
- Linear dev-flow pipeline with adversarial review gates: brainstorming → writing-plans →
  capture-adrs → plan-to-beads → subagent-driven-development / executing-plans → draining-beads
  → review-pr → address-findings, with a bead-graph junction and PR integration. design-reviewer
  and plan-reviewer are the adversarial gates. This is the connective-tissue narrative for the
  Pass-2 locked dev-flow decisions.

## ADR authoring guidelines + index (reference) — NEW

- source: docs/adr/README.md
- Index and writing guidance for capturing ADRs during planning; points at capture-adrs skill,
  bd-backed ADR store, and the current ADR set (fhsk-bmn/nlw/slp, fhsk-0qz/pqw/qs9,
  fhsk-5dj/8yz/a6v/8g6, fhsk-dgo). Confirms bd-as-source-of-truth + frontmatter conventions.

## Hooks bash→Python migration (runbook) — NEW

- source: docs/superpowers/plans/2026-03-11-hook-python-migration.md
- Step-by-step migration of worktree-create / worktree-remove / post-edit-format hooks to
  Python uv scripts with pytest. Executes CON-p3-hook-python-runtime.

## superpowers → jj fork rollout (runbook) — NEW

- source: docs/superpowers/plans/2026-03-16-superpowers-jj-fork.md
- 7-chunk plan forking obra/superpowers v5.0.2 with jj/git VCS abstraction, skill mods,
  commands/agents/hooks, and release integration. Executes the jj-fork SPEC (CON-p3-upstream-
  manifest, CON-p3-vcs-preamble-set).

## jj plugin hardening (runbook)

- source: docs/superpowers/plans/2026-04-03-jj-plugin-hardening.md
- Pager safety, parallel-agent collision, undo semantics, test assertions. Executes
  CON-p3-jj-pager-safety, CON-p3-jj-workspace-collision.

## guard-jj-mutating hook (runbook)

- source: docs/superpowers/plans/2026-05-02-guard-jj-mutating.md
- Implements the PreToolUse/Bash op-guard hook. Executes CON-p3-guard-jj-op-marker (locked
  DEC-jj-op-log-recovery-gate).

## dev-flow beads integration + fork independence (runbook)

- source: docs/superpowers/plans/2026-05-14-dev-flow-beads-integration.md
- Six-phase rebrand superpowers/ → dev-flow/, bd workflow tracking, ADR capture lift, review-gate
  agents. Executes CON-p3-dev-flow-rules and the Pass-2 dev-flow locked decisions.

## ADR evolution machinery (runbook)

- source: docs/superpowers/plans/2026-05-22-adr-evolution.md
- Makes bd the source of truth for ADR content, markdown derived. Executes
  CON-p3-adr-bd-source-of-truth (locked fhsk-nlw/slp/bmn).

## Drain feature evolution lineage (runbooks) — NEW narrative

- sources: docs/superpowers/plans/2026-05-22-drain-skill.md;
  docs/superpowers/plans/2026-05-24-drain-goal-handoff.md;
  docs/superpowers/plans/2026-05-25-drain-with-worker.md;
  docs/superpowers/plans/2026-06-13-tmux-drain-worker.md
- Evolutionary chain: /drain + draining-beads → cold-boot /goal handoff redesign →
  drain-with-worker pane launcher → multiplexer-parameterized (cmux/tmux) skill. Each supersedes
  or extends the prior; all subordinate to the locked drain ADRs. Executes CON-p3-drain-
  sentinel-protocol, CON-p3-drain-watchdog, CON-p3-mux-driver-protocol.

## Anti-AI-slop review aspect (runbook)

- source: docs/superpowers/plans/2026-05-28-anti-ai-slop-review-aspect.md
- Adds slop-hunter aspect + code-slop/prose-slop catalogs to review-pr. Executes
  CON-p3-slop-pattern-catalogs (locked fhsk-2us).

## Consolidate pr-review under dev-flow (runbook)

- source: docs/superpowers/plans/2026-05-28-consolidate-pr-review-under-dev-flow.md
- Structural move of pr-review into dev-flow. Executes CON-p3-pr-review-consolidation.

## Skills routing + capture-adrs fixes (runbook)

- source: docs/superpowers/plans/2026-05-28-skills-routing-and-adr-capture-fixes.md
- agent:* dispatch label, ADR capture worthiness, nudge timing. Executes CON-p3-skills-routing
  (locked fhsk-bj8/p07).

## Wire review pipeline seams (runbook)

- source: docs/superpowers/plans/2026-05-28-wire-review-pipeline-seams.md
- PR handoff suggestions, VCS preamble consolidation, code-reviewer disambiguation. Executes
  CON-p3-vcs-preamble-set.

## cog release flow (runbook) — SUPERSEDED / historical

- source: docs/superpowers/plans/2026-05-29-cog-release-flow.md
- Runbook for the cocogitto tag-only release flow. SUPERSEDED by locked release-please decision
  (fhsk-dgo). Historical only; not active.

## handoff bead type (runbook)

- source: docs/superpowers/plans/2026-05-29-handoff-bead-type.md
- Replaces ephemeral handoff-prompt with persistent handoff bead type. Executes
  CON-p3-handoff-body-schema (locked fhsk-s15/57f/8xn).

## solving-a-bead skill (runbook)

- source: docs/superpowers/plans/2026-05-29-solving-a-bead.md
- Adds solving-a-bead skill + slash command with verification gates. Executes
  CON-p3-solving-a-bead-interface (locked fhsk-3xn/hj3/ypt).

## mermaid skill (runbook)

- source: docs/superpowers/plans/2026-05-30-mermaid-skill.md
- Mermaid authoring/lint/render skill. Executes CON-p3-mermaid-pipeline (locked fhsk-4bi).

## memory-curator plugin (runbook)

- source: docs/superpowers/plans/2026-06-01-memory-curator-plugin.md
- 11-task build of the memory-curator plugin. Executes CON-p3-memory-curator-mcp (locked
  fhsk-e0u).

## miniflux skill (runbook)

- source: docs/superpowers/plans/2026-06-13-miniflux-skill.md
- 12-task build of the miniflux RSS skill. Executes CON-p3-miniflux-cli (locked
  fhsk-pqw/qs9/0qz).

## ADR render/doctor Python migration (runbook) — IMPLEMENTED

- source: docs/superpowers/plans/2026-06-30-adr-render-python-frontmatter.md
- 13-task rewrite of render-adr + adr-doctor to Python PEP 723 with Starlight frontmatter
  (epic fhsk-cdr, closed). Executes CON-p3-adr-starlight-frontmatter (locked fhsk-nlw/slp/bmn).

---

Context items this pass: 23 DOCs across 21 topic groups (2 reference docs + drain-lineage group
folds 4 runbooks). All subordinate to the locked baseline + their Pass-3 SPEC contracts.
