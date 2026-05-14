# dev-flow

Development workflow skills, plus first-class beads + jj integration.

## Heritage

Originally derived from [obra/superpowers v5.0.7](https://github.com/obra/superpowers). Evolved independently with first-class jj VCS support, bead-based execution tracking, ADR capture, and adversarial in-session review gates.

Future upstream changes are reviewed via `scripts/scan-upstream` (changelog reader); cherry-picked selectively rather than auto-synced.

## Plugin runtime requirements

| Component | Purpose | Soft/Hard |
|---|---|---|
| `bd` CLI (plugin floor `v0.60.0+`; design-time install `v1.0.4`) | Workflow tracking | Hard prerequisite |
| `mcp__probe__*` | Code grounding | Soft |
| `mcp__context7__*` | Library docs grounding | Soft |
| `mcp__deepwiki__*` | Repo conventions grounding | Soft |
| `mcp__exa__*` | Web search grounding | Soft |
| `mcp__firecrawl-mcp__*` or `firecrawl` skill | Page-content extraction | Soft |

See `AGENTS.md` for Rules 1-7 (conventions).
