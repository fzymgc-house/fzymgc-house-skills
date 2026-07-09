## Conflict Detection Report

### BLOCKERS (0)

No unresolved blockers.

- No LOCKED-vs-LOCKED contradiction: the two locked ADRs cover disjoint scopes (release versioning vs jj op-log recovery).
- No cross-ref cycles (implementation->design graph is an acyclic DAG, depth < 50).
- No UNKNOWN / low-confidence classifications.
- Mode is `new`; no existing locked CONTEXT.md decisions to contradict.

### WARNINGS (0)

No competing acceptance variants. The ingest set contains 0 PRD-classified docs, so no requirement has divergent acceptance criteria to reconcile.

### INFO (2)

[INFO] Auto-resolved: LOCKED ADR > SPEC on plugin/skill directory layout
  Found: docs/plans/2026-02-23-agent-plugin-restructure-design.md (SPEC, Draft) renames the `fzymgc-house` plugin to `homelab` and splits a new `pr-review` plugin, moving review-pr from a skill to true agents.
  Note: docs/plans/2026-02-16-release-please-design.md (ADR, LOCKED, Approved) hard-codes release-please package paths under `fzymgc-house/skills/{grafana,terraform,review-pr,respond-to-pr-comments,address-review-findings,skill-qa}` and version files `fzymgc-house/plugin.json` / `.claude-plugin/marketplace.json`. Same scope: plugin/skill directory layout. Precedence ADR > SPEC and the ADR is LOCKED, so the ADR layout wins in synthesized intel; the restructure is recorded as subordinate in constraints.md (CON-agent-plugin-restructure). Recommend authoring a superseding ADR before adopting the `homelab`/`pr-review` paths.

[INFO] Auto-resolved: lower-precedence docs assume post-restructure naming
  Found: docs/plans/2026-04-09-codex-marketplace-design.md (SPEC), docs/plans/2026-03-07-jj-vcs-support-design.md and docs/plans/2026-03-07-jj-vcs-support.md (DOC) all reference the restructured `homelab` / `pr-review` / `jj` plugin names.
  Note: These conflict with the LOCKED release-please ADR's `fzymgc-house` naming on the same directory-layout scope. Under precedence they are subordinated to the LOCKED ADR; recorded for transparency and traced in constraints.md / context.md. Resolution is the same superseding-ADR path noted above.
