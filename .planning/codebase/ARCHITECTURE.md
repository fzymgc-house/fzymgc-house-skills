<!-- refreshed: 2026-07-08 -->
# Architecture

**Analysis Date:** 2026-07-08

## System Overview

This is a **multi-platform plugin marketplace** that publishes skill workflows for both Claude Code (native plugins) and Codex (wrapper plugins). The architecture decouples skill content (single source in source plugin directories) from platform-specific distribution (Claude marketplace vs. Codex wrappers using symlinks).

```text
┌────────────────────────────────────────────────────────────────────┐
│                    Plugin Marketplace Layer                        │
│  .claude-plugin/marketplace.json     .agents/plugins/marketplace   │
│  (Claude Code installs)               (Codex installs)             │
└────────┬──────────────────────────────────────────┬────────────────┘
         │                                          │
         ▼                                          ▼
┌────────────────────────────────────────────────────────────────────┐
│              Source Plugin Directories (Single Source)              │
│  homelab/  jj/  dev-flow/  tmux/  grepping/                        │
│  Contains: skills/, commands/, hooks/, scripts/, references/       │
│  Entry point: plugin.json + SKILL.md in each skill/                │
└────────┬──────────────────────────────────────────┬────────────────┘
         │                                          │
         ▼                                          ▼
┌──────────────────────────────────┐  ┌─────────────────────────────┐
│  Claude Plugin Installation      │  │  Codex Wrapper Plugins      │
│  (Direct source references)      │  │  `plugins/<name>/`          │
│                                  │  │  Symlinks to sources        │
└──────────────────────────────────┘  └─────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **homelab** | Infrastructure skills for Terraform, skill QA, Miniflux | `homelab/plugin.json` |
| **jj** | Jujutsu VCS workflow guidance, colocated repo support | `jj/plugin.json` |
| **dev-flow** | Development workflow pipeline: spec → plan → execute → review → merge | `dev-flow/plugin.json` |
| **tmux** | Terminal multiplexer scripting and session management | `tmux/plugin.json` |
| **grepping** | Shell search skill: ripgrep/ast-grep/grep translation + nudge hooks | `grepping/plugin.json` |
| **Claude Marketplace** | Distribution point for Claude Code plugin installs | `.claude-plugin/marketplace.json` |
| **Codex Marketplace** | Distribution point for Codex plugin installs | `.agents/plugins/marketplace.json` |

## Pattern Overview

**Overall:** Plugin-based skill marketplace with **single-source skill content**, **platform-agnostic skill definitions** (SKILL.md + supporting code), and **dual marketplace distribution** (Claude direct refs, Codex symlink wrappers).

**Key Characteristics:**

- Skills dispatch agents; agents never dispatch other agents or directly invoke skills
- One repo-wide version line across all plugins (`.release-please-manifest.json`, release-please automates sync)
- No pre-commit hooks (jj does not fire git hooks reliably) — Taskfile.yaml is the single quality gate source
- Beads (bd issue tracker) as centralized task coordination across skills
- Cross-session handoff via drain beads in dev-flow autonomous mode

## Layers

**Marketplace Layer (Distribution):**

- Purpose: Enumerate plugins and their sources for each platform
- Location: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`
- Contains: Plugin metadata, source references, version
- Depends on: Source plugin plugin.json files
- Used by: Claude Code installer, Codex plugin loader

**Plugin Layer (Aggregation):**

- Purpose: Define plugin identity and package multiple skills
- Location: `homelab/plugin.json`, `jj/plugin.json`, `dev-flow/plugin.json`, `tmux/plugin.json`, `grepping/plugin.json`
- Contains: Plugin name, version (synced by release-please), description
- Depends on: Skills in subdirectories
- Used by: Marketplace, Claude/Codex installers

**Skill Layer (Entry Points):**

- Purpose: Define user-facing commands with metadata, allowed tools, dispatch agents
- Location: Each skill in a subdirectory with `SKILL.md`, supporting code (Python, references)
- Example: `dev-flow/skills/review-pr/SKILL.md` defines `/review-pr` command
- Frontmatter: `name`, `description`, `argument-hint`, `allowed-tools`, `metadata`
- Used by: Agent dispatch system, Taskfile.yaml linting

**Workflow Layer (Pipeline Execution):**

- Purpose: Orchestrate multi-step development workflows
- Example: dev-flow pipeline (spec → plan → execute → review → merge)
- Coordination: Beads (bd) epic as central junction for multi-driver execution
- Three execution drivers for the same bead graph:
  1. `subagent-driven-development` (interactive, two-stage review per task)
  2. `executing-plans` (serial in-session)
  3. `/drain` (autonomous via `/goal` re-firing until queue drains)

**Hook Layer (Cross-Cutting Automation):**

- Purpose: Advisory nudges (rg over grep), workflow automation (worktree isolation, ADR capture)
- Location: `dev-flow/hooks/`, `jj/hooks/`, `grepping/hooks/`, `.claude/hooks/`
- Types: PreToolUse (nudge before tool), PostToolUse (flag errors), other automation
- Example: `grepping/hooks/nudge-rg-over-grep.py` runs PreToolUse to suggest ripgrep

**Command Layer (VCS-Specific Workflows):**

- Purpose: Platform-specific shortcuts (jj-only, git-only) that complement skills
- Location: `jj/commands/`, `dev-flow/commands/`
- Used by: Agent workflows when native VCS operations are needed

**Script Layer (Utilities):**

- Purpose: Shared infrastructure for complex operations
- Location: `dev-flow/scripts/` (adr-doctor, muxdriver, adr-render), `homelab/skills/terraform/scripts/`
- Example: `_muxdriver.py` shared tmux/cmux driver logic; `_adr_doctor` validates ADR graph

**Reference Layer (Documentation):**

- Purpose: Guides, patterns, and reference material for skills
- Location: `dev-flow/references/`, `grepping/skills/grepping/references/`
- Examples: `vcs-preamble.md`, code-slop patterns, ripgrep guide

**Test Layer:**

- Purpose: Harness-independent validation of hooks, scripts, skills
- Location: Distributed co-located (`dev-flow/hooks/tests/`, `tests/`, `.claude/hooks/tests/`)
- Run via: `task test` (invokes pytest across all dirs in PYTEST_DIRS)

## Data Flow

### Primary Request Path (Skill Invocation)

1. User types `/skill-name args` in Claude Code or Codex agent
2. Skill handler reads SKILL.md frontmatter for allowed tools, metadata
3. Skill content executes (typically calls Bash, Read, Grep, or other allowed tools)
4. Skill MAY dispatch named agents (e.g., `review-pr` → `code-reviewer`, `security-auditor`, etc.)
5. Agents return findings or execution results
6. Skill optionally files beads (task records) for async follow-up

### Dev-Flow Pipeline Path (Spec → Merge)

1. `using-superpowers` entry skill enforces platform detection
2. `brainstorming` phase → `design-reviewer` gate (read-only agent)
3. `writing-plans` phase → `plan-reviewer` gate (read-only agent)
4. **Auto-fire chain:** `capture-adrs` (may dispatch `adr-extractor`, file decision beads) → `plan-to-beads` (materializes plan into bd epic)
5. **Bead epic junction** (single central coordination point):
   - `subagent-driven-development` (interactive path) OR
   - `executing-plans` (serial in-session) OR
   - `/drain` (autonomous, dispatches SDD per bead via `/goal` Stop hook)
6. `finishing-a-development-branch` → PR creation
7. `review-pr` dispatches up to 10 review agents (parallel), files findings as beads
8. `address-findings` runs fix loop until clean
9. Merge to main

### Autonomous Drain Loop (Hands-Off Execution)

`/drain epic|set|cascade <bead-id>` enters its own sentinel-driven protocol:

- While queue not empty:
  1. Load next ready bead
  2. Dispatch `subagent-driven-development` for that bead
  3. Capture lessons in bd notes
  4. Mark bead resolved
  5. Re-fire `/goal` Stop hook (no manual intervention needed)

**State Management:**

- **Beads:** Central task/decision/finding record; parent-child dependencies
- **ADR graph:** Design decisions tree (`dev-flow/scripts/adr-doctor` validates connectivity)
- **Worktrees:** Isolated git/jj workspaces per agent execution (`dev-flow/hooks/worktree_*`)
- **Session state:** Minimal delta passed in handoff prompts (not full re-snapshot)

## Key Abstractions

**Bead (bd Issue Tracker):**

- Purpose: Unified task, decision, and finding record across dev-flow pipeline
- Types: Task (work to do), Decision (ADR), Finding (PR review output)
- Graph: Parent-child dependencies, blocker relationships
- Integration: Skills query/update beads; cross-session handoff via drain bead notes

**Skill (SKILL.md):**

- Purpose: User-facing command definition with metadata and execution contract
- Structure: Frontmatter (name, description, allowed-tools, argument-hint) + body (prompt)
- Agents: Can only be dispatched BY skills, not vice versa
- Entry Point: `/skill-name` invocation → SKILL.md → execution

**Agent (*.md in dev-flow/agents/):**

- Purpose: Specialized reviewer/analyzer/fixer dispatched by skills
- Types: code-reviewer, security-auditor, fix-worker, review-gate, etc.
- Contract: Each reads findings from PR/beads, returns verdict or results
- Never entry point; never dispatches other agents

**ADR (Architecture Decision Record):**

- Purpose: Capture design decisions with rationale and status
- Graph: Organized by `adr-doctor` script into decision tree
- Integration: `capture-adrs` skill + `adr-extractor` agent materialize plan ADRs

**Worktree (git/jj isolation):**

- Purpose: Isolated workspace per agent fix/verification run
- Layout: Sibling directory (`<repo>_worktrees/<name>/`)
- Automation: Hooks ensure cleanup, prevent stale worktrees

## Entry Points

**User-Facing Skills:**

- Location: `homelab/skills/*/SKILL.md`, `jj/skills/*/SKILL.md`, `dev-flow/skills/*/SKILL.md`, etc.
- Examples: `/review-pr`, `/using-superpowers`, `/writing-plans`, `/terraform`, `/tmux`, `/grepping`
- Triggers: Direct invocation or dispatch by orchestrator skills

**CLI Entry (Marketplace Installation):**

- Claude Code: `claude plugin install homelab@fzymgc-house-skills`
- Codex: Via `.agents/plugins/marketplace.json` + local Codex install

**Programmatic Entry (Agent Dispatch):**

- Skills dispatch agents by name (e.g., `review-pr` → `code-reviewer`, `security-auditor`)
- Agents read context from PR/beads, return structured output
- No reverse dispatch; no agent-to-skill entry

## Architectural Constraints

- **Single Version Line:** One `.release-please-manifest.json` version bumped for all plugins. Release-please syncs to all plugin.json `$.version` fields and marketplace files via `extra-files` config.
- **No Git Hooks (jj consideration):** When `jj root` succeeds, use jj for mutating VCS operations. Git hooks don't fire reliably with jj; quality gates run via `task lint`/`task test` instead.
- **Marketplace Duplication:** Claude and Codex marketplaces are distinct (different schemas), but both reference the same source plugins to avoid duplication.
- **Skill-to-Agent Dispatch:** Skills are entry points; agents are dispatch targets. Never agent-to-skill or agent-to-agent dispatch. Review orchestrators (review-pr, address-findings) are skills, not agents.
- **Bead Coordination:** All async work (multi-session, multi-agent) coordinates via bd epic/ready beads, not temp files or session memory.
- **Worktree Isolation:** Agent fix/verification runs happen in isolated worktrees (sibling layout, not nested). Hooks enforce cleanup to prevent stale directories.
- **Cross-Platform Compatibility:** Codex compatibility guidance in `dev-flow/skills/using-superpowers/references/codex-tools.md` for agent dispatch (spawn_agent vs. named agents).

## Anti-Patterns

### Duplicating Skill Content Between Claude and Codex

**What happens:** Symlink-based wrapper plugins (`plugins/<name>/`) instead reference skill sources, but if a developer copies SKILL.md to Codex wrapper instead of symlinking, two versions diverge.

**Why it's wrong:** When skill updates, only one version gets the fix. PR review says "update /review-pr" but which version? Marketplace confusion.

**Do this instead:** Keep skill SKILL.md and supporting code in source plugin directories (`homelab/`, `jj/`, etc.). Codex wrappers symlink back (e.g., `plugins/dev-flow/skills -> ../../dev-flow/skills`). Single source of truth.

### Agent-to-Agent Dispatch

**What happens:** A review agent (e.g., `security-auditor`) tries to dispatch another agent or invoke a skill directly.

**Why it's wrong:** Agent dispatch hierarchy becomes a dag, not a tree. Tracing execution flow becomes impossible. Termination guarantees fail (cycles, unbounded depth).

**Do this instead:** Agents return findings/results to their dispatching skill. Skills coordinate multi-agent workflows. Review orchestrators like `review-pr` are skills that dispatch agents, not agents that dispatch agents.

### Mixing Temp Files with Bead State

**What happens:** Skill stores work-in-progress in `/tmp` or session temp, expects it to survive across agent re-invocation or drain loop iterations.

**Why it's wrong:** Sessions can be interrupted, archived, or re-invoked with fresh context. Temp files don't survive restarts.

**Do this instead:** Use drain beads to carry cross-session state. Beads persist in local bd DB and survive session boundaries. Lessons/notes in bead comments carry iteration protocol.

### Pre-Commit Hooks for VCS Operations

**What happens:** Developer relies on `.git/hooks/pre-commit` to enforce quality gates.

**Why it's wrong:** When using jj (even with colocated git), hooks don't fire. Developers bypass gates unintentionally.

**Do this instead:** Taskfile.yaml is the single source of truth. Run `task lint` / `task test` manually or in CI. CI runs the same gates, so local and CI agree.

### Hard-Coding Platform Detection in Skills

**What happens:** Skill directly checks `git rev-parse` vs. `jj root` without asking user which VCS to use.

**Why it's wrong:** jj/git colocated repos can fail to detect correctly. User intends one but skill auto-selects wrong one.

**Do this instead:** Entry skill `using-superpowers` enforces platform detection via user confirmation or environment. Skills downstream assume platform is confirmed.

---

*Architecture analysis: 2026-07-08*
