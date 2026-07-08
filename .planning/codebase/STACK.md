# Technology Stack

**Analysis Date:** 2026-07-08

## Languages

**Primary:**

- Python 3 - Test suites, utility scripts, hook implementations
- Markdown - Documentation and skill definitions
- YAML - Configuration files and CI/CD workflows
- JSON - Plugin manifests and configuration

**Secondary:**

- Shell (Bash) - Scripts and CLI utilities
- Go - Task runner binary (external tool)

## Runtime

**Environment:**

- Linux (Ubuntu 22.04 in CI)
- macOS (Darwin with direnv support for local development)
- Docker - Terraform MCP server container runtime

**Package Manager:**

- **uv** (Python package manager) - Installed via astral.sh/uv
  - Lockfile: Not checked in (uses inline dependencies via `uv run --with`)
  - Version: Latest from astral.sh

## Frameworks

**Build/Task Management:**

- **Task** (go-task/task) v3.50.0+ - Single source of truth for quality gates
  - Config: `Taskfile.yaml` at repo root
  - Commands: `task fmt`, `task lint`, `task test`

**Testing:**

- **pytest** - Python test runner
  - Config: None (inline in Taskfile)
  - Invoked via: `uv run --with pytest --with httpx --with pyyaml pytest`
  - Test dirs: `tests/`, `.claude/hooks/tests/`, `jj/hooks/tests/`, `dev-flow/hooks/tests/`, `dev-flow/scripts/tests/`, `homelab/skills/*/tests/`

**Linting:**

- **ruff** v0.15.2 - Python linting and formatting
  - Invoked via: `uv tool install ruff@0.15.2`
  - Config: Inline in Taskfile (check + format)
- **rumdl** v0.1.43 - Markdown linting
  - Config: `.rumdl.toml` - line length 140, excludes dev-flow upstream content and .git
- **jq** - JSON validation and linting
  - Validates all plugin.json and marketplace.json files
- **check-jsonschema** v0.37-v0.38 - Schema validation
  - Validates evals files against `dev-flow/evals/evals.schema.json`

**VCS:**

- **git** - Primary version control
- **jj** (Jujutsu) v0.42.0+ - Alternative VCS with colocated git support
  - Installed in CI for test execution

## Key Dependencies

**Testing & Validation:**

- **pytest** - Test framework (installed via uv)
- **httpx** - HTTP client for tests (installed via uv)
- **pyyaml** - YAML parsing for tests (installed via uv)

**Infrastructure:**

- **terraform-mcp-server** Docker image (`hashicorp/terraform-mcp-server:latest`)
  - Runs in Docker container for HCP Terraform/TFE operations
  - Requires `TFE_TOKEN` environment variable

**Development Tools (External, not packaged):**

- Task v3.50.0+ - Task runner for Taskfile execution
- rumdl v0.1.43 - Markdown linter
- ruff v0.15.2 - Python linter/formatter
- jq - JSON processor
- jj v0.42.0+ - Jujutsu VCS (for testing)

## Configuration

**Environment:**

- direnv (`.envrc`) - Automatic environment loading on directory change
  - Exports: `VAULT_ADDR`, `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `TFE_TOKEN`
  - Paths: Adds `scripts/` directory to PATH
  - Vault integration: Fetches secrets from `https://vault.fzymgc.house`

**Build & Quality:**

- `Taskfile.yaml` - Single source of truth for all quality gates (fmt, lint, test)
- `.rumdl.toml` - Markdown linting configuration
- `.release-please-manifest.json` - Release versioning state
- `release-please-config.json` - Release automation config

**Plugin Management:**

- `.claude-plugin/marketplace.json` - Claude Code marketplace manifest (v2.0.1)
- `.agents/plugins/marketplace.json` - Codex marketplace manifest
- Individual plugin manifests: `homelab/plugin.json`, `jj/plugin.json`, `dev-flow/plugin.json`, `tmux/plugin.json`, `grepping/plugin.json`

**MCP Servers:**

- `.mcp.json` - Declares Terraform MCP server (Docker-based)

## Platform Requirements

**Development:**

- Task v3.50.0+ (installed via `taskfile.dev/install.sh`)
- uv (Python package manager, installed via `astral.sh/uv/install.sh`)
- rumdl v0.1.43 (Markdown linter)
- ruff v0.15.2 (Python linter, installed via uv tool)
- jq (JSON processor, system package)
- jj v0.42.0+ (optional, for testing jj workflows)
- direnv (recommended, for `.envrc` support)
- Vault CLI (recommended, for fetching secrets from `https://vault.fzymgc.house`)

**CI/CD (GitHub Actions):**

- Ubuntu runner (ubuntu-latest)
- GitHub Actions v7 checkout
- release-please GitHub App (with private key + app ID)
- GitHub CLI (gh) with token authentication

**Production:**

- GitHub releases hosted at <https://github.com/fzymgc-house/fzymgc-house-skills>
- Installed into Claude Code or Codex by git commit SHA
- Optional: Docker daemon for Terraform MCP server (when using homelab plugin)
- Vault server at `https://vault.fzymgc.house` (for API keys)

---

*Stack analysis: 2026-07-08*
