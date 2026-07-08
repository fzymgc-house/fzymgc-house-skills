# Context (DOC intel)

Supporting notes from DOC-classified planning docs (12). Lowest precedence — background and
implementation runbooks, subordinate to ADR/SPEC when they overlap. Keyed by topic, source-attributed.

---

## Grafana skill — token efficiency

- source: docs/plans/2025-12-24-token-efficiency-design.md
- Design rationale for cutting Grafana skill token usage via output formatting, compound workflows, and pre-baked tool schemas. Classifier flagged decision-like tone but no ADR structure (no Consequences), so treated as design context, not a locked decision.
- source: docs/plans/2025-12-24-token-efficiency-implementation.md
- Phased implementation: `--format`/`--brief` flags in `grafana_mcp.py` (PyYAML), compound workflows (investigate-logs, investigate-metrics, quick-status, find-dashboard), pre-baked reference docs and tool schemas, SKILL.md updates; targets grafana skill version 0.2.0.

---

## Terraform skill — implementation

- source: docs/plans/2025-12-29-terraform-skill-implementation.md
- Step-by-step runbook for the Terraform Cloud skill wrapping the HashiCorp MCP server via a Python gateway (Docker, HCP Terraform, workspace management, run monitoring, provider docs) plus CI wiring. Execution detail for CON-terraform-skill.

---

## Beads review integration — implementation

- source: docs/plans/2026-02-15-beads-review-integration-implementation.md
- Runbook to replace the JSONL temp-dir workflow with beads-backed persistence in review-pr and respond-to-pr-comments: allowed-tools config, agent reference files, skill docs. Executes DEC-beads-review-persistence (Draft ADR).

---

## Address review findings — implementation

- source: docs/plans/2026-02-16-address-review-findings-implementation.md
- Runbook for the new address-review-findings skill: SKILL.md structure, bd CLI reference, frontmatter, Phase 1-6 tasks, validation. Executes CON-address-review-findings.

---

## Release-please — implementation

- source: docs/plans/2026-02-16-release-please-implementation.md
- Step-by-step plan to wire release-please: config files, `.release-please-manifest.json`, `release-please.yml` + `check-skills.yml` workflows, SKILL.md metadata markers, manifest mode. Executes LOCKED DEC-release-please-manifest-versioning.

---

## Agent & plugin restructure — implementation

- source: docs/plans/2026-02-23-agent-plugin-restructure-implementation.md
- Twelve-task plan splitting fzymgc-house into homelab + pr-review plugins with 12 true agents, CI + release-please reconfig, beads tracking. Executes CON-agent-plugin-restructure — which contradicts the LOCKED release-please ADR layout (see INGEST-CONFLICTS.md).

---

## Worktree isolation fix — implementation

- source: docs/plans/2026-03-06-worktree-isolation-fix.md
- Seven-task runbook: hook scripts (`worktree-create.sh`, `worktree-remove.sh`), `.claude/settings.json`, fix-worker/verification-runner agent edits, sibling directory layout, doc updates. Executes CON-worktree-isolation-fix.

---

## jj (Jujutsu) VCS support

- source: docs/plans/2026-03-07-jj-vcs-support-design.md
- Design for adding jj VCS support: new jj plugin, VCS detection in colocated repos, pr-review adaptation, worktree helpers, command-equivalence mapping, release config. Prescriptive but path/style classified as DOC.
- source: docs/plans/2026-03-07-jj-vcs-support.md
- Implementation plan: jj plugin, VCS-aware pr-review skills/agents, workspace hooks, release config, integration testing (12 tasks). Both assume post-restructure `pr-review`/`jj` naming (subordinate to LOCKED release-please ADR under precedence).

---

## Codex marketplace — implementation

- source: docs/plans/2026-04-09-codex-marketplace-implementation.md
- Step-by-step plan to add Codex wrappers + pytest coverage for repo-local plugin management (symlinks, GitHub Actions, marketplace.json). Executes CON-codex-marketplace.

---

## jj skill — op-log recovery rule implementation

- source: docs/plans/2026-05-01-jj-skill-op-log-recovery-rule-implementation.md
- Task-by-task runbook updating SKILL.md and jj-reference.md with the recovery ladder and MUST NOT approval gates, plus markdown linting and beads lifecycle. Executes LOCKED DEC-jj-op-log-recovery-gate.
