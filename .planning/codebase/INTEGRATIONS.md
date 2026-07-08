# External Integrations

**Analysis Date:** 2026-07-08

## APIs & External Services

**Terraform Cloud (HCP Terraform):**

- Service: HashiCorp HCP Terraform / Terraform Cloud
- What it's used for: Infrastructure state management, workspace operations, runs, registry lookups
- SDK/Client: `terraform-mcp-server` Docker image (hashicorp/terraform-mcp-server:latest)
- Auth: `TFE_TOKEN` environment variable (HCP Terraform API token)
- Config: `.mcp.json` declares the Terraform MCP server as a Docker container
- Usage: `homelab/skills/terraform/` plugin provides operations via `terraform-mcp` client

**Firecrawl (Optional MCP Server):**

- Service: Firecrawl web scraping API
- What it's used for: Web content extraction and scraping (optional integration)
- SDK/Client: MCP server integration
- Auth: `FIRECRAWL_API_KEY` environment variable (fetched from Vault)
- Config: Sourced from `.envrc` via Vault lookup at `secret/users/<entity>/firecrawl`
- Status: Optional — integration available when key is present

**Exa (Optional MCP Server):**

- Service: Exa intelligent search API
- What it's used for: Web search integration (optional)
- SDK/Client: MCP server integration
- Auth: `EXA_API_KEY` environment variable (fetched from Vault)
- Config: Sourced from `.envrc` via Vault lookup at `secret/users/<entity>/exa`
- Status: Optional — integration available when key is present

## Data Storage

**Databases:**

- None detected — repository is skills/plugins, not a database-driven application

**File Storage:**

- Local filesystem only — `.planning/codebase/` directory for documentation
- `.beads/` directory for issue tracking (Dolt-backed local database)
- `.git/` for version control

**Caching:**

- `.pytest_cache/` - pytest cache (local, ephemeral)
- `.ruff_cache/` - ruff linter cache (local, ephemeral)
- `.rumdl_cache/` - rumdl formatter cache (local, ephemeral)

## Authentication & Identity

**Auth Provider:**

- Vault (HashiCorp) at `https://vault.fzymgc.house`
  - Implementation: OIDC login with localhost:8250 callback
  - User entity lookup via `vault token lookup` and `vault read identity/entity/id/{entity_id}`
  - Secret paths: `secret/users/<entity_name>/{firecrawl,exa,terraform}`, `secret/fzymgc-house/cluster/hcp-terraform`

**GitHub Authentication:**

- GitHub CLI (gh) with `GITHUB_TOKEN` (default GitHub Actions token)
- release-please GitHub App with app-id + private-key secrets (for release automation)
- Personal access tokens for `gh release download` commands (used in CI)

## Monitoring & Observability

**Error Tracking:**

- None detected — repository is skills/plugins, not an application

**Logs:**

- GitHub Actions workflow logs (stored in GitHub)
- Local test output via pytest
- CI lint/test output (stored in GitHub Actions artifacts)

## CI/CD & Deployment

**Hosting:**

- GitHub (github.com/fzymgc-house/fzymgc-house-skills)
- Claude Code marketplace (installed by git commit SHA)
- Codex marketplace (installed locally via .agents/plugins/marketplace.json)

**CI Pipeline:**

- GitHub Actions (workflow files in `.github/workflows/`)
  - `ci.yaml` - Lint and test on push to main and PRs
  - `commit-lint.yaml` - Conventional commit validation (via amannn/action-semantic-pull-request)
  - `release.yaml` - Automated releases via release-please

**Release Process:**

- release-please (googleapis/release-please-action) v5.0.0
  - Bumps `.release-please-manifest.json`, plugin version fields, `CHANGELOG.md`
  - Creates git tag `vX.Y.Z` and GitHub Release automatically
- Versions managed repo-wide in `.release-please-manifest.json`
- Release config: `release-please-config.json`

## Environment Configuration

**Required env vars:**

- `TFE_TOKEN` - HCP Terraform API token (for terraform skill)
- `VAULT_ADDR` - Vault server address (default: `https://vault.fzymgc.house`)

**Optional env vars:**

- `FIRECRAWL_API_KEY` - Firecrawl API key (fetched from Vault if available)
- `EXA_API_KEY` - Exa search API key (fetched from Vault if available)
- `GITHUB_TOKEN` - GitHub API token (provided by GitHub Actions)
- `RELEASE_PLEASE_APP_ID` - release-please GitHub App ID (GitHub Actions secrets)
- `RELEASE_PLEASE_PRIVATE_KEY` - release-please GitHub App private key (GitHub Actions secrets)
- `GH_TOKEN` - GitHub CLI token (used in CI for release downloads)
- `OBJC_DISABLE_INITIALIZE_FORK_SAFETY` - macOS fork safety flag (set in `.envrc`)
- `SOPS_AGE_KEY_FILE` - SOPS encryption key file (commented in `.envrc`, optional)

**Secrets location:**

- Vault server: `https://vault.fzymgc.house`
  - Per-user secrets: `secret/users/<entity_name>/{firecrawl,exa,terraform}`
  - Cluster-level secrets: `secret/fzymgc-house/cluster/hcp-terraform`
- GitHub Actions secrets (configured via repo settings):
  - `RELEASE_PLEASE_APP_ID`
  - `RELEASE_PLEASE_PRIVATE_KEY`

## Webhooks & Callbacks

**Incoming:**

- GitHub push webhook (triggers CI on branch push)
- GitHub pull request webhook (triggers CI on PR)
- GitHub workflow_dispatch webhook (manual trigger)

**Outgoing:**

- Vault OIDC callback: localhost:8250 (for local `vault login -method=oidc`)
- GitHub API calls via `gh` CLI (release downloads, token creation)
- release-please GitHub App writes (release PR creation, tag creation, Release creation)

---

*Integration audit: 2026-07-08*
