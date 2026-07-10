# Requirements: fzymgc-house-skills

**Defined:** 2026-07-08 (retrospective bootstrap)
**Core Value:** Skills are single-source, discoverable, and reusable across the org's projects with low friction to adopt

> No PRD existed in the ingest set (3 ADR, 5 SPEC, 12 DOC; 0 PRD). Requirements below are
> **derived** from decisions/constraints/context and framed around cross-project reuse.
> Checked boxes (`[x]`) are retrospective — confirmed shipped by the 2026-07-08 codebase map.
> Unchecked boxes are forward-looking (open work).

## v1 Requirements

### Infrastructure Skills (INFRA)

- [x] **INFRA-01**: Terraform Cloud skill wraps the HashiCorp Terraform MCP server behind a `uv`-run gateway so only `SKILL.md` loads into context (not 30+ tool defs); read-only ops plus provider-doc lookup; `TFE_TOKEN` passed via env
- [x] **INFRA-02**: skill-qa validates a `SKILL.md` file against skill best-practice checks

### Developer Tooling Skills (TOOL)

- [x] **TOOL-01**: tmux skill drives multiplexer sessions/windows/panes from a script or agent (detection, send-keys, capture-pane, lifecycle)
- [x] **TOOL-02**: grepping skill provides rg/ast-grep/grep search guidance with advisory PreToolUse/PostToolUse nudge hooks (grep→rg, rg-failure)

### PR Review Pipeline (REV)

- [x] **REV-01**: review-pr orchestrator dispatches specialized review agents and records findings as child beads under a PR-review parent bead (persistent across sessions, label-discriminated)
- [x] **REV-02**: address-findings processes finding beads through triage and a fix loop (fix-worker → review-gate → verification-runner) until clean, filing work/deferred beads as needed
- [x] **REV-03**: respond-to-comments manages human PR-comment handling using prior review state queried from beads
- [x] **REV-04**: Fix/verification agents run in isolated sibling worktrees (`<repo>_worktrees/<agent>-<id>/`) and commit their changes without editing the base repo

### Version Control Workflows (VCS)

- [x] **VCS-01**: A `jj` plugin provides Jujutsu workflow guidance with correct VCS detection in colocated git+jj repos and jj-aware pipeline adaptation
- [x] **VCS-02**: The op-log-rewind class (`jj op restore`/`jj op abandon`) is gated MUST NOT behind explicit user approval, with a canonical recovery ladder (read-only inspect → `jj undo` → `jj op revert`)

### Release & Versioning (REL)

- [x] **REL-01**: release-please (manifest mode, GitHub Action) automates version bumps and CHANGELOG from conventional-commit PR titles
- [x] **REL-02**: A single repo-wide version line is synced across all plugin/marketplace manifests on release (no hand-bumping); a CI drift check keeps release config in sync with the actual plugin directories

### Distribution & Reuse (DIST)

- [x] **DIST-01**: Any org repo can install a plugin by name from the Claude marketplace manifest (`.claude-plugin/marketplace.json`)
- [x] **DIST-02**: The same single-source plugins install via the Codex marketplace layer (`.agents/plugins/marketplace.json`) through thin `plugins/<name>/` symlink wrappers
- [x] **DIST-03**: Skill content stays single-source in the source plugin directories (wrappers symlink back, no duplication); a CI test catches marketplace drift

### Governance & Reuse Hardening (GOV) — forward-looking

- [x] **GOV-01**: A superseding ADR records the shipped plugin layout (`homelab`/`jj`/`dev-flow`/`tmux`/`grepping`) and marks the release-please ADR's `fzymgc-house/skills/*` package layout superseded
- [ ] **GOV-02**: Cross-project adoption is documented so a new org repo can discover and install a skill following minimal, explicit steps

## v2 Requirements

None captured. Move forward-looking GOV items or new skill proposals here as they emerge.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Terraform destructive ops (create/delete workspaces, apply/discard runs, variable + private-registry mgmt) | Terraform skill is deliberately read-only for safety |
| Full MCP tool-definition exposure into context | Gateway pattern exists to keep only SKILL.md loaded |
| Duplicated skill content in the Codex wrapper layer | Wrappers symlink back to source; single source of truth |
| Pre-commit git hooks as quality gates | jj does not fire git hooks reliably; Taskfile.yaml is the gate source |
| Per-skill independent version lines | Superseded by one repo-wide version line |
| grafana skill (early design docs) | Relocated/removed from the marketplace tree; not part of current v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| TOOL-01 | Phase 1 | Complete |
| TOOL-02 | Phase 1 | Complete |
| REV-01 | Phase 2 | Complete |
| REV-02 | Phase 2 | Complete |
| REV-03 | Phase 2 | Complete |
| REV-04 | Phase 2 | Complete |
| VCS-01 | Phase 3 | Complete |
| VCS-02 | Phase 3 | Complete |
| REL-01 | Phase 4 | Complete |
| REL-02 | Phase 4 | Complete |
| DIST-01 | Phase 4 | Complete |
| DIST-02 | Phase 4 | Complete |
| DIST-03 | Phase 4 | Complete |
| GOV-01 | Phase 5 | Complete |
| GOV-02 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓
- Retrospective (shipped): 15 · Forward-looking (open): 2

---

*Requirements defined: 2026-07-08*
*Last updated: 2026-07-08 after retrospective bootstrap*
