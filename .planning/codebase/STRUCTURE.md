# Codebase Structure

**Analysis Date:** 2026-07-08

## Directory Layout

```text
fzymgc-house-skills/
├── .claude/                      # Claude-specific configuration and hooks
│   ├── hooks/                    # Claude automation hooks (formatting, workspace)
│   ├── settings.json             # Claude settings (read-only reference)
│   └── settings.local.json       # Local overrides
├── .agents/                      # Codex agent configuration
│   └── plugins/
│       └── marketplace.json      # Codex marketplace manifest (wrapper plugins)
├── .claude-plugin/
│   └── marketplace.json          # Claude marketplace manifest (source plugins)
├── .mcp.json                     # MCP servers (context7, terraform)
├── .beads/                       # Beads issue tracker metadata
├── .planning/                    # GSD planning output directory
│   └── codebase/                 # Codebase analysis documents (this directory)
├── .github/                      # GitHub Actions CI/CD workflows
├── .rumdl.toml                   # Markdown linting configuration
├── Taskfile.yaml                 # Task runner (single source of quality gates)
├── release-please-config.json    # release-please configuration
├── .release-please-manifest.json # Current repo version
├── AGENTS.md                     # Shared agent instructions (cross-platform)
├── CLAUDE.md                     # Claude-specific addendum
├── README.md                     # User-facing documentation
├── CHANGELOG.md                  # Release history
│
├── homelab/                      # Infrastructure plugin
│   ├── plugin.json               # Plugin manifest
│   └── skills/
│       ├── terraform/            # Terraform Cloud operations skill
│       ├── skill-qa/             # SKILL.md validation skill
│       └── miniflux/             # Miniflux RSS reader skill
│
├── jj/                           # Jujutsu VCS plugin
│   ├── plugin.json               # Plugin manifest
│   ├── commands/                 # jj-specific commands (VCS shortcuts)
│   ├── evals/                    # Behavioral eval schemas
│   ├── hooks/                    # jj workflow automation hooks
│   └── skills/
│       └── jujutsu/              # Jujutsu workflow guidance skill
│
├── dev-flow/                     # Development workflow orchestration plugin
│   ├── plugin.json               # Plugin manifest
│   ├── agents/                   # Review/fix/verification agents (dispatched by skills)
│   │   ├── code-reviewer.md
│   │   ├── security-auditor.md
│   │   ├── pr-test-analyzer.md
│   │   ├── api-contract-checker.md
│   │   ├── spec-compliance.md
│   │   ├── code-simplifier.md
│   │   ├── slop-hunter.md
│   │   ├── comment-analyzer.md
│   │   ├── silent-failure-hunter.md
│   │   ├── type-design-analyzer.md
│   │   ├── fix-worker.md
│   │   ├── review-gate.md
│   │   ├── verification-runner.md
│   │   ├── adr-extractor.md
│   │   ├── design-reviewer.md
│   │   ├── plan-reviewer.md
│   │   └── (14 agents total)
│   ├── commands/                 # VCS-specific development commands
│   ├── evals/                    # Behavioral eval definitions
│   ├── hooks/                    # Workflow automation (worktree, ADR, isolation)
│   ├── references/               # Documentation and pattern guides
│   ├── scripts/                  # Shared utilities (adr-doctor, muxdriver, adr-render)
│   ├── .beads/                   # dev-flow-local bead formulas
│   └── skills/                   # 28 workflow skills
│       ├── using-superpowers/    # Entry skill (platform detection)
│       ├── brainstorming/        # Design phase
│       ├── writing-plans/        # Planning phase → auto-fires capture-adrs + plan-to-beads
│       ├── capture-adrs/         # ADR materialization (dispatches adr-extractor)
│       ├── plan-to-beads/        # Plan → bead epic (central coordination junction)
│       ├── subagent-driven-development/  # Interactive multi-stage review per task
│       ├── executing-plans/      # Serial in-session execution
│       ├── draining-beads/       # Autonomous execution via /goal Stop hook
│       ├── finishing-a-development-branch/  # PR creation
│       ├── review-pr/            # PR review orchestrator (dispatches up to 10 agents)
│       ├── address-findings/     # Fix loop orchestrator (fix-worker → review-gate → verification)
│       ├── respond-to-comments/  # PR comment management with bead context
│       ├── verification-before-completion/  # Pre-completion gate
│       ├── systematic-debugging/ # Structured debugging workflow
│       ├── test-driven-development/  # TDD workflow
│       ├── using-worktrees/      # Git worktree isolation guidance
│       ├── using-git-worktrees/  # Git-specific worktree details
│       ├── dispatching-parallel-agents/  # Multi-agent orchestration
│       ├── bead-create-smart/    # Intelligent bead creation
│       ├── solving-a-bead/       # Single-task workflow
│       ├── draining-beads/       # Multi-bead autonomous loop
│       ├── drain-with-worker/    # Worker-mode drain orchestration
│       ├── requesting-code-review/  # Pre-PR review request
│       ├── receiving-code-review/   # Review feedback integration
│       ├── evolve-adr/           # ADR updates and status changes
│       ├── capture-adrs/         # ADR capture from plan
│       ├── plan-to-beads/        # Plan materialization
│       ├── handoff-prompt/       # Cross-session context transfer
│       └── writing-skills/       # Skill authoring guidance
│
├── tmux/                         # Terminal multiplexer plugin
│   ├── plugin.json               # Plugin manifest
│   └── skills/
│       └── tmux/                 # tmux/cmux session and pane scripting
│
├── grepping/                     # Shell search plugin
│   ├── plugin.json               # Plugin manifest
│   ├── hooks/                    # Advisory nudges (rg over grep, rg failures)
│   └── skills/
│       └── grepping/             # ripgrep/ast-grep/grep search and translation
│
├── plugins/                      # Codex wrapper plugins (thin wrappers with symlinks)
│   ├── homelab/
│   │   ├── .codex-plugin/plugin.json  # Codex wrapper manifest
│   │   ├── .mcp.json             # Symlink to repo-root .mcp.json
│   │   └── skills/               # Symlink to ../../homelab/skills
│   ├── jj/
│   ├── dev-flow/
│   ├── tmux/
│   └── grepping/
│
├── tests/                        # Repo-wide harness-independent tests
│   ├── test_adr_docs.py
│   ├── test_plugin_script_paths.py
│   ├── test_codex_marketplace.py
│   ├── test_command_skill_collision.py
│   ├── test_review_gate_agents.py
│   ├── test_solving_a_bead.py
│   ├── test_drain_skill.py
│   ├── test_agent_guidance_docs.py
│   ├── test_drain_worker_launch.py
│   ├── test_muxdriver.py
│   └── (more pytest suites)
│
└── docs/                         # Project documentation and ADRs
    ├── dev-flow-pipeline.md      # dev-flow pipeline visual guide
    └── adr/                      # Architecture decision records
        ├── fhsk-dgo-*.md         # Release versioning strategy
        ├── fhsk-e0u-*.md         # Two-tier memory scope model
        └── (15+ ADRs total)
```

## Directory Purposes

**Root Configuration:**

- `.claude-plugin/marketplace.json`: Claude Code plugin distribution manifest; lists all 5 source plugins
- `.agents/plugins/marketplace.json`: Codex plugin distribution manifest; lists wrapper plugins in `plugins/`
- `.mcp.json`: MCP server configuration (context7, terraform) — shared by all plugins
- `.beads/`: Local bd issue tracker database and metadata
- `.planning/codebase/`: GSD mapping output (ARCHITECTURE.md, STRUCTURE.md, etc.)

**Marketplace Distribution:**

- **Claude:** Direct references to source plugin directories (`homelab/`, `jj/`, etc.)
- **Codex:** Thin wrapper plugins in `plugins/<name>/` with symlinks back to source content

**Source Plugin Directories (Single Source):**
Each plugin directory (`homelab/`, `jj/`, `dev-flow/`, `tmux/`, `grepping/`) contains:

- `plugin.json`: Plugin identity and version (synced by release-please)
- `skills/`: User-facing command definitions (SKILL.md + supporting code)
- `commands/` (optional): VCS-specific shortcuts
- `hooks/` (optional): Workflow automation (PreToolUse, PostToolUse, etc.)
- `scripts/` (optional): Shared utilities
- `references/` (optional): Documentation and guides
- `evals/` (optional): Behavioral eval definitions
- `agents/` (dev-flow only): Review/fix/verification orchestrators

**dev-flow Structure (Most Complex Plugin):**

- `agents/`: Named agents dispatched by skills (not entry points)
  - Review agents: code-reviewer, security-auditor, type-design-analyzer, etc.
  - Fix/quality agents: fix-worker, review-gate, verification-runner
  - Specialized: adr-extractor, slop-hunter, comment-analyzer, api-contract-checker
- `skills/`: 28 workflow skills implementing the pipeline (spec → plan → execute → review → merge)
- `hooks/`: Worktree isolation, ADR nudges, workflow automation
- `scripts/`: adr-doctor (validates ADR graph), muxdriver (shared tmux/cmux driver), adr-render (ADR templates)
- `references/`: vcs-preamble.md, code-slop patterns, prose-slop patterns, drain protocol specs

**Testing:**
Harness-independent pytest suites distributed co-located:

- `tests/`: Repo-wide tests (marketplace validation, bead structure, plugin paths)
- `.claude/hooks/tests/`: Claude hook tests
- `jj/hooks/tests/`: jj workflow hook tests
- `dev-flow/hooks/tests/`: Worktree/ADR/isolation hook tests
- `dev-flow/scripts/tests/`: adr-doctor, muxdriver tests
- `homelab/skills/terraform/tests/`: Terraform skill tests
- `homelab/skills/miniflux/tests/`: Miniflux skill tests

## Key File Locations

**Entry Points:**

- `dev-flow/skills/using-superpowers/SKILL.md`: Platform detection entry (Claude vs. Codex, git vs. jj)
- `homelab/skills/terraform/SKILL.md`: Terraform operations entry
- `jj/skills/jujutsu/SKILL.md`: jj workflow entry
- `tmux/skills/tmux/SKILL.md`: tmux scripting entry
- `grepping/skills/grepping/SKILL.md`: Shell search entry

**Configuration:**

- `Taskfile.yaml`: Quality gate source (fmt, lint, test); CI invokes the same tasks
- `.rumdl.toml`: Markdown linting rules and file exclusions
- `.mcp.json`: MCP server configuration (shared across all plugins)
- `.github/workflows/ci.yaml`: CI pipeline (runs same Taskfile tasks as local development)
- `.github/workflows/commit-lint.yaml`: Conventional commit validation on PR title
- `.github/workflows/release.yaml`: release-please automation (tag, release, version sync)

**Core Logic - Pipeline:**

- `dev-flow/skills/writing-plans/SKILL.md`: Plan phase → auto-fires capture-adrs + plan-to-beads
- `dev-flow/skills/plan-to-beads/SKILL.md`: Materializes plan into bd epic (central junction)
- `dev-flow/skills/subagent-driven-development/SKILL.md`: Interactive multi-stage review per task
- `dev-flow/skills/executing-plans/SKILL.md`: Serial in-session execution driver
- `dev-flow/skills/draining-beads/SKILL.md`: Autonomous execution sentinel and protocol
- `dev-flow/skills/review-pr/SKILL.md`: PR review orchestrator (dispatches 10 agents, files beads)
- `dev-flow/skills/address-findings/SKILL.md`: Fix loop (fix-worker → review-gate → verification)

**Core Logic - Utilities:**

- `dev-flow/scripts/_adr_doctor`: Validates ADR graph connectivity and decision tree
- `dev-flow/scripts/_muxdriver.py`: Shared tmux/cmux driver logic (used by tmux skill, agents)
- `dev-flow/scripts/_adr_render.py`: ADR template rendering for capture
- `dev-flow/hooks/worktree_helpers.py`: Worktree isolation utilities
- `homelab/skills/terraform/scripts/`: Terraform Cloud API integration scripts

**Testing:**

- `tests/test_plugin_script_paths.py`: Validates all script paths in plugin manifests
- `tests/test_codex_marketplace.py`: Validates Codex marketplace schema
- `tests/test_review_gate_agents.py`: PR review agent dispatch logic
- `tests/test_drain_skill.py`: Autonomous drain loop protocol
- `dev-flow/evals/evals.json`: Behavioral eval definitions (schema-validated)
- `jj/evals/evals.json`: jj workflow eval definitions

**Documentation:**

- `AGENTS.md`: Canonical cross-platform agent instructions and rules
- `CLAUDE.md`: Claude-specific addendum and compatibility shim
- `dev-flow-pipeline.md`: Visual pipeline guide with flow diagram and three execution drivers
- `docs/adr/`: Architecture decision records (15+) covering release strategy, memory scoping, drain protocol, etc.

## Naming Conventions

**Files:**

- Skill definitions: `skills/<skill-name>/SKILL.md` (kebab-case directory, SKILL.md file)
- Agents: `agents/<agent-name>.md` (kebab-case markdown files)
- Scripts: `scripts/_<script_name>.py` (leading underscore for internal utilities)
- Hooks: `hooks/<hook_purpose>.py` (descriptive names, tests in `hooks/tests/`)
- References: `references/<topic>.md` (topic-specific guides)
- ADRs: `docs/adr/fhsk-<id>-<title-kebab-case>.md` (fhsk prefix for repo ID, 4-char unique ID)

**Directories:**

- Skill groups: `skills/<category>/` → `skills/<skill-name>/` (no intermediate nesting)
- Plugin layout: Always `skills/`, `commands/`, `hooks/`, `scripts/`, `references/`, `agents/` at plugin root
- Codex wrappers: `plugins/<plugin-name>/` (mirrors source structure via symlinks)
- Test co-location: Parallel `tests/` directories at each functional level (hooks/tests/, scripts/tests/, etc.)

**Functions/Symbols:**

- Python: snake_case for functions; CamelCase for classes
- Bash: snake_case; prefix with plugin name or purpose (e.g., `nudge_rg_over_grep`)
- SKILL.md frontmatter: kebab-case for `name`, `argument-hint`; SCREAMING_SNAKE_CASE for environment vars

**Environment Variables:**

- Configuration: `FZYMGC_*` prefix for homelab-specific, `CLAUDE_*` for Claude-specific
- Internal: Avoid global state; pass context via bead notes and session handoff prompts

## Where to Add New Code

**New Workflow Skill (Most Common):**

1. Create: `dev-flow/skills/<skill-name>/SKILL.md` with frontmatter (name, description, allowed-tools, metadata)
2. Body: Prompt for skill execution (orchestrates agents or CLI operations)
3. Agents to dispatch (optional): List in skill body, dispatch by name
4. Tests: `dev-flow/skills/<skill-name>/tests/test_<functionality>.py` (if harness-independent)
5. References: `dev-flow/references/<topic>.md` if complex workflow patterns

**New Review/Verification Agent:**

1. Create: `dev-flow/agents/<agent-name>.md` with contract (inputs, outputs, verdict format)
2. Dispatch: Referenced by orchestrator skills (review-pr, address-findings, etc.)
3. Integration: Update orchestrator skill to dispatch in parallel or sequence
4. Test: Agent logic validated via orchestrator skill tests (integration test)

**New Hook (Automation or Advisory):**

1. Create: `<plugin>/hooks/<hook_name>.py` with PreToolUse/PostToolUse trigger
2. Logic: Scan tool invocation, emit nudge or enforce workflow
3. Tests: `<plugin>/hooks/tests/test_<hook_name>.py`
4. Examples: `dev-flow/hooks/nudge_adrs.py` (advisory), `dev-flow/hooks/ensure_isolated_workspace.py` (enforce)

**New Plugin Skill (Rare):**

1. Create: `<new-plugin>/plugin.json` with name, version (use repo-wide version), description
2. Skills directory: `<new-plugin>/skills/<skill-name>/SKILL.md`
3. Update marketplaces: Add to `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`
4. Create wrapper: `plugins/<new-plugin>/` with symlinks
5. Testing: Add new plugin dirs to Taskfile.yaml PYTEST_DIRS if adding harness-independent tests

**New Infrastructure Script (Utilities):**

1. Location: `dev-flow/scripts/_<utility>.py` (underscore prefix for internal)
2. Tests: `dev-flow/scripts/tests/test_<utility>.py`
3. Usage: Import by skills/agents when needed; export via `if __name__ == "__main__"` for CLI use

**New ADR (Architecture Decision):**

1. Create: `docs/adr/fhsk-<id>-<title-kebab-case>.md` with YAML frontmatter
2. Title frontmatter: `title: [decision title]`
3. Status: `status: [Accepted|Proposed|Superseded]`
4. Validate: `adr-doctor` checks graph connectivity during `task lint`

## Special Directories

**`.beads/`:**

- Purpose: Local bd issue tracker database and metadata
- Generated: Yes (by `bd` CLI on first use)
- Committed: Yes (beads history is git-tracked; optional Dolt remote for sync)

**`dev-flow/.beads/formulas/`:**

- Purpose: Named bead creation templates (formula library)
- Generated: No (pre-defined patterns)
- Committed: Yes

**`.claude/hooks/` (Claude-specific):**

- Purpose: Claude Code automation hooks (post-edit formatting, workspace warnings)
- Generated: No (developer configuration)
- Committed: Yes (for team consistency)

**`plugins/` (Codex Wrapper Layer):**

- Purpose: Thin wrappers with symlinks to source plugins for Codex distribution
- Generated: No (manually set up once)
- Committed: Yes (symlink structure is git-committed)

**`.planning/codebase/` (GSD Output):**

- Purpose: Codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by `/gsd-map-codebase` agent)
- Committed: Yes (reference documentation for next phases)

**`.pytest_cache/`, `.ruff_cache/`, `.rumdl_cache/`:**

- Purpose: Tool cache directories
- Generated: Yes (auto-generated on first tool run)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-07-08*
