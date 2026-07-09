# Constraints (SPEC intel)

Technical constraints from SPEC-classified planning docs. Lower precedence than ADR, higher than PRD/DOC.
All five are Draft status. One (agent/plugin restructure) contradicts a LOCKED ADR — see INGEST-CONFLICTS.md.

---

## CON-terraform-skill

- source: docs/plans/2025-12-29-terraform-skill-design.md
- type: protocol / api-contract
- status: Draft

Wrap the HashiCorp Terraform MCP server behind a `terraform_mcp.py` gateway (`uv run`) so only `terraform/SKILL.md` loads into context, not the 30+ MCP tool definitions.

- Session management: reuse a Docker subprocess; MCP client speaks stdio JSON-RPC to the Docker container.
- HCP Terraform API fallback for operations the MCP server doesn't cover; provider documentation lookup.
- Secure token handling: `TFE_TOKEN` passed via environment variable to the subprocess.
- Non-goals (hard scope limits): no destructive ops (create/delete workspaces, apply runs), no variable management, no private registry module/provider management, no full MCP tool exposure.

---

## CON-address-review-findings

- source: docs/plans/2026-02-16-address-review-findings-design.md
- type: protocol / schema
- status: Draft

New `address-review-findings` skill dedicated to processing review-pr finding beads (splits that concern out of respond-to-pr-comments, which retains arbitrary human-comment handling).

- 6-phase workflow over the beads data model established by the beads-review integration.
- Bead types: finding beads, work beads (for non-trivial fixes), deferred-work beads.
- Steps: dependency analysis, triage logic, quality gates, PR comment posting.
- Builds on DEC-beads-review-persistence (Draft ADR); consistent with it, not contradictory.

---

## CON-agent-plugin-restructure

- source: docs/plans/2026-02-23-agent-plugin-restructure-design.md
- type: architecture / protocol
- status: Draft
- CONFLICT: contradicts LOCKED DEC-release-please-manifest-versioning on directory layout (auto-resolved, ADR wins — see INGEST-CONFLICTS.md)

Split the single `fzymgc-house` plugin into a two-plugin marketplace:

- `homelab/` (renamed from fzymgc-house): grafana, terraform, skill-qa skills.
- `pr-review/` (new): 12 true Claude Code agents (code-reviewer, silent-failure-hunter, pr-test-analyzer, type-design-analyzer, comment-analyzer, security-auditor, api-contract-checker, spec-compliance, code-simplifier, fix-worker, review-gate, verification-runner).
- Primary driver: native worktree isolation for fix-worker agents. Includes agent input/output contracts, worktree merge protocols, communication boundaries.

Under precedence, the LOCKED release-please ADR's `fzymgc-house/skills/*` package layout wins in synthesized intel. This restructure is recorded as subordinate pending a superseding ADR.

---

## CON-worktree-isolation-fix

- source: docs/plans/2026-03-06-worktree-isolation-fix-design.md
- type: protocol
- status: Draft

Fix pr-review fix agents' two failure modes (never committing; editing the base repo instead of the worktree).

- Sibling worktree layout: `<repo-root>_worktrees/<agent>-<id>/` instead of nested `.claude/worktrees/` (which confused LSP).
- Implemented via WorktreeCreate/WorktreeRemove hooks in `.claude/settings.json` (`worktree-create.sh`, `worktree-remove.sh`).
- fix-worker gains an explicit commit step; all agents gain worktree-awareness instructions.
- verification-runner receives context about what was fixed and why.

---

## CON-codex-marketplace

- source: docs/plans/2026-04-09-codex-marketplace-design.md
- type: schema / api-contract
- status: Draft (high classifier confidence)

Add a repo-local Codex marketplace layer exposing existing Claude plugins without forking skill content.

- Codex manifest at `.agents/plugins/marketplace.json`; thin wrappers under `plugins/<name>/.codex-plugin/plugin.json` with symlinks (`skills -> ../../<plugin>/skills`, `agents -> ...`, `.mcp.json -> ../../.mcp.json`).
- Hard constraints: Claude stays first-class (`.claude-plugin` manifests/paths unchanged); skills remain single-source (wrappers point at source dirs, no duplication); Codex lacks Claude-style named agents, so agent-dispatch workflows keep prompt files accessible and document the workaround; CI test catches marketplace drift.
- Assumes post-restructure plugin names (`homelab`, `pr-review`, `jj`, `superpowers`) — subordinate to the LOCKED release-please ADR's naming under precedence (see INGEST-CONFLICTS.md INFO).
