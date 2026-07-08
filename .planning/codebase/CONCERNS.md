# Codebase Concerns

**Analysis Date:** 2026-07-08

## Tech Debt

**ADR index drift (fhsk-2kl):**

- Issue: `adr-doctor` INV-A12 checks for sentinel markers (`<!-- BEGIN INDEX -->` / `<!-- END INDEX -->`) in `docs/adr/README.md` but does NOT verify the index rows match actual ADR status and content.
- Files: `dev-flow/scripts/_adr_doctor.py`, `docs/adr/README.md`
- Impact: New ADRs or status changes (e.g., Accepted → Superseded) silently drift from the index. Readers see stale information. Index becomes unreliable as source of truth.
- Fix approach: Generate/validate the index table between sentinels from `bd` state via `render-adr --index` or a new `adr-doctor` check (INV-A26). Add test coverage for index freshness.

**Orphaned ADR recovery path (fhsk-cdr plan, section 1):**

- Issue: `adr-doctor` can detect orphaned decision beads (no corresponding `.md` file) but recovery requires `AskUserQuestion` (only available in main session context). Plan notes this path is "not exercised by this repo's migration" (5 ADRs all have `.md` files today).
- Files: `docs/superpowers/plans/2026-06-30-adr-render-python-frontmatter.md` (lines 671-1034)
- Impact: If an ADR bead is deleted and its `.md` is removed, `adr-doctor` fails to recover it automatically. Subagent-driven workflows can't prompt for recovery data without main-session context.
- Fix approach: Implement full `AskUserQuestion` path in `adr-doctor` for v2. Until then, document the limitation and provide manual recovery instructions (re-create bead, run `render-adr <id>`).

**Large monolithic file (terraform_mcp.py):**

- Issue: `homelab/skills/terraform/scripts/terraform_mcp.py` is 1648 lines, combining MCP client, Docker container orchestration, HCP Terraform API client, and CLI dispatch in one file.
- Files: `homelab/skills/terraform/scripts/terraform_mcp.py`
- Impact: Difficult to unit-test individual components. Mocking Docker and HTTP layers intertwined. High cognitive load for future maintainers. Changes to any layer risk unintended side effects.
- Fix approach: Split into modules: `_mcp_client.py`, `_docker_manager.py`, `_hcp_client.py`, `_cli.py`. Add integration tests for Docker spawn/cleanup. Make HTTP client injectable for testing.

## Known Bugs

**Worktree create/remove warnings on local-only repos:**

- Symptoms: Multiple "WARNING" messages when creating/removing worktrees in repos with no remote (`git remote -v` returns nothing). Warnings are appropriate but noisy for legitimate use cases (local-only repos, offline development).
- Files: `dev-flow/hooks/worktree_helpers.py` (lines 98, 148, 181, 209, 243, 262, 274), `dev-flow/hooks/tests/test_worktree_create.py`, `dev-flow/hooks/tests/test_worktree_remove.py`
- Trigger: Run `git worktree add` or `git worktree remove` in a repo with no remote, or when the remote is unreachable (offline mode).
- Workaround: Expected behavior; warnings are correct. Consider adding `--quiet` flag or environment variable (`WORKTREE_QUIET=1`) to suppress warnings if needed.

**Python 3.14 percent-escape regression fixed (fhsk-b43):**

- Symptoms: `drain-watchdog` crashes with argparse error on Python 3.14+ if `%` appears literally in help text.
- Files: `dev-flow/skills/drain-with-worker/SKILL.md` (references fix in PR #159)
- Trigger: Run drain worker on Python 3.14+.
- Status: **FIXED** in PR #159 — escape `%` as `%%` in argparse help strings.

**Miniflux exception construction (from fhsk-8k8 notes):**

- Symptoms: Tests that raise Miniflux exceptions (`ClientError`, `AccessUnauthorized`, `ResourceNotFound`) with string arguments crash at construction time.
- Files: `homelab/skills/miniflux/tests/test_miniflux_api.py`, any future tests that mock miniflux exceptions
- Cause: Miniflux exception classes expect a `requests.Response` object in `__init__`, not a string. They call `.json()` and `.status_code` on the Response, which strings don't have.
- Workaround: Build a mock Response with `.status_code`, `.headers={'Content-Type':'application/json'}`, and `.json()` → `{'error_message': '<msg>'}`.

## Security Considerations

**Temporary environment file for Docker credentials:**

- Risk: `terraform_mcp.py` writes `TFE_TOKEN` to a temporary `.env` file (`tempfile.NamedTemporaryFile`) for Docker `--env-file`. Temp files are written to `/tmp` (or `$TMPDIR`), which may have overly permissive default mode (0o600 on most systems, but 0o644 in some container runtimes).
- Files: `homelab/skills/terraform/scripts/terraform_mcp.py` (lines 215-251)
- Current mitigation: File is deleted immediately after container spawns (line 277). Cleanup runs in `except Exception` (line 246) and `cleanup()` (line 276). File is `delete=False` to allow explicit unlink.
- Recommendations: (1) Explicitly set mode to `0o600` after creation: `os.chmod(self._env_file_path, 0o600)`. (2) Use `tempfile.NamedTemporaryFile(delete=True, mode='w')` in a `with` statement so cleanup is guaranteed even if container spawn raises. (3) Consider passing secrets via `docker run -e TFE_TOKEN=$TFE_TOKEN` directly (avoids file) if container supports it.

**Secrets in process list (mitigated):**

- Risk: Before writing to `.env` file, tokens in shell invocation are visible in `ps`.
- Current mitigation: Docker `--env-file` approach already avoids passing `-e TFE_TOKEN=...` on the command line. No secrets in argv.

## Performance Bottlenecks

**Terraform MCP Docker spawn latency:**

- Problem: Each `get_client()` call spawns a new Docker container (`docker run --rm hashicorp/terraform-mcp-server:0.3.3`). Docker startup + image pull (if not cached) adds 2-5+ seconds per operation.
- Files: `homelab/skills/terraform/scripts/terraform_mcp.py` (line 238, `subprocess.Popen`)
- Cause: No container reuse; each skill invocation creates a fresh container.
- Improvement path: Implement container pooling or use a persistent daemon. Cache container image in CI. Measure startup time and warn if it exceeds threshold.

**Worktree test timeouts:**

- Problem: Many worktree tests set `timeout=30` or `timeout=60` for subprocess operations. Filesystem-heavy operations (git clone, jj operations) may timeout on slow machines or under CI load.
- Files: `dev-flow/hooks/tests/test_worktree_create.py`, `dev-flow/hooks/tests/test_worktree_remove.py`, `dev-flow/hooks/tests/test_ensure_isolated_workspace.py`
- Cause: Fixed hardcoded timeouts don't adapt to system load or CI resource constraints.
- Improvement path: Make timeouts configurable via environment variable (e.g., `WORKTREE_TEST_TIMEOUT=90`). Add test-level retry logic for transient failures. Monitor CI run times to detect slowness trends.

## Fragile Areas

**Worktree creation/removal hook chain (fhsk-0sq, fhsk-3v3, fhsk-b43):**

- Files: `dev-flow/hooks/worktree-create`, `dev-flow/hooks/worktree-remove`, `dev-flow/hooks/worktree_helpers.py`
- Why fragile: Multiple interdependent VCS operations (git, jj, bd) run in sequence. Cleanup must handle partial failures. Recent fixes (PR #144, #173, #175) show tight coupling between beads redirect, workspace creation, and mux detection.
- Safe modification: Add integration tests that exercise full chains (create → modify → remove) with failure injection at each step. Verify cleanup state after each failure. Test with both git and jj repos.
- Test coverage: Already well-covered by `test_worktree_create.py` and `test_worktree_remove.py`, but add end-to-end scenario tests.

**Drain worker shell compatibility (fhsk-163, fhsk-158):**

- Files: `dev-flow/skills/drain-with-worker/SKILL.md`, `dev-flow/scripts/drain-worker-launch`, tests in `tests/test_drain_worker_launch.py`
- Why fragile: Direnv probe assumes bash/zsh syntax; recent fix for fish shell (PR #163) shows assumptions about shell syntax. Argparse `%` escaping changes across Python versions (PR #159).
- Safe modification: Abstract shell detection into helper function. Add tests for each supported shell (bash, zsh, fish, sh). Pin Python version constraint (≥3.11) in scripts.
- Test coverage: Add platform-specific tests for shells (skip if shell not installed). Test on Python 3.11, 3.12, 3.13, 3.14 in CI.

**ADR render → adr-doctor parity (fhsk-cdr, plan section "Background"):**

- Files: `dev-flow/scripts/_adr_render.py`, `dev-flow/scripts/_adr_doctor.py`, `dev-flow/scripts/tests/test_adr_render.py`
- Why fragile: Python port of bash script must preserve exact byte-for-byte fidelity except for frontmatter/H1 removal. Plan notes that plan snippets may have "lost corrections in PR #183 squash" — the code is authoritative, not the plan.
- Safe modification: (1) Run the parity harness (`difflib`-based comparison) before any changes to `_adr_render.py`. (2) Golden fixtures (`test_adr_render.py`) freeze expected output for all 32 ADRs. (3) If modifying rendering logic, update golden fixtures AND verify parity harness passes.
- Test coverage: 100% parity test coverage. Any new feature (e.g., `--index`) must include golden fixture + parity tests.

**Miniflux API client exception handling (fhsk-8k8 notes):**

- Files: `homelab/skills/miniflux/scripts/miniflux_api.py`, `homelab/skills/miniflux/tests/test_miniflux_api.py`
- Why fragile: Miniflux library exception classes (`ClientError`, `AccessUnauthorized`, `ResourceNotFound`) have non-standard constructors (require `requests.Response`). Plan notes "implementer subagents must construct mock Response objects with `.status_code`, `.headers`, `.json()`" or tests crash.
- Safe modification: Add a fixture in `conftest.py` that builds valid mock Response objects. Document exception construction in code comments. Add type stubs if miniflux library doesn't provide them.
- Test coverage: Verify all exception paths call the exception correctly. Test error messages (via `.get_error_reason()`).

## Scaling Limits

**ADR decision base size (32 beads):**

- Current capacity: 32 decision ADRs, all with `.md` files.
- Limit: If ADR count grows to 100+, `adr-doctor` linear scan of all beads may become slow. Index drift detection (fhsk-2kl) adds O(n) index validation.
- Scaling path: (1) Index validation: cache last-computed index hash, re-validate only if ADR set changed. (2) `render-adr` batching: add `--all` or `--changed` flag to regenerate multiple ADRs in one pass. (3) Consider moving ADR metadata to a separate `.json` file for O(1) lookups.

**Worktree sibling directory layout:**

- Current capacity: Repo directory + unlimited worktrees in `<repo>_worktrees/` sibling directory.
- Limit: Filesystem may have inode or path-length limits. Very deep nested paths or many worktrees may hit OS limits.
- Scaling path: Document recommended max worktrees (e.g., 50 per machine). Add health check to warn if `.worktree list` exceeds threshold. Clean up stale worktrees periodically.

**Docker container pool (Terraform MCP):**

- Current capacity: One container per `get_client()` call; containers are short-lived and exit immediately.
- Limit: Rapid successive calls spawn many containers, consuming resources and slowing down. No pooling/reuse.
- Scaling path: Implement container lifecycle manager: keep N warm instances, reuse them across calls, garbage-collect idle containers after timeout.

## Dependencies at Risk

**Python 3.11+ requirement (PEP 723 scripts):**

- Risk: All `uv run --script` tools require Python ≥3.11. Older systems (RHEL 7 EOL, Ubuntu 20.04 LTS) have Python 3.8-3.9. Users on those systems cannot run scripts.
- Impact: `render-adr`, `adr-doctor`, `terraform_mcp.py`, `miniflux_api.py` all fail to run.
- Migration plan: (1) Document minimum Python version (3.11) in README. (2) Add CI matrix test for Python 3.11, 3.12, 3.13, 3.14 to catch deprecations early. (3) If supporting older Python needed, backport to bash or pin older stdlib APIs.

**Miniflux library version pinning:**

- Risk: `homelab/skills/miniflux/scripts/miniflux_api.py` imports `from miniflux import Client, ...` without version constraints. Plan notes library behavior (exception classes, API methods) changed between versions (e.g., `OPML export → export_feeds()` method name).
- Impact: Silent behavior changes or API breakage if miniflux library is upgraded.
- Migration plan: Pin miniflux version in PEP 723 inline script deps (e.g., `miniflux==7.0.0`). Add version-specific tests. Document API assumptions in code.

**Docker image version (Terraform MCP):**

- Risk: `DOCKER_IMAGE = "hashicorp/terraform-mcp-server:0.3.3"` is hardcoded. If Docker image is removed or updated, script breaks.
- Impact: CI/skill invocations fail if the image is no longer available.
- Migration plan: (1) Pin image digest (SHA256) instead of tag for reproducibility. (2) Add CI check to verify image is accessible (`docker pull ...` dry-run). (3) Document upgrade path for new image versions.

**httpx proxy detection (terraform_mcp.py):**

- Risk: Script relies on httpx auto-detecting `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` from environment. Proxy config may differ across systems/CI runners.
- Impact: Unexpected proxy routing or timeouts if proxy environment is misconfigured.
- Migration plan: Add `--proxy` CLI flag to explicitly set proxy URL. Document proxy setup. Add tests with mock proxy scenarios.

## Missing Critical Features

**ADR index regeneration command:**

- Problem: No automation to regenerate or validate `docs/adr/README.md` index from bd state. Users must manually edit the index, leading to drift (fhsk-2kl).
- Blocks: Automation of ADR lifecycle (new ADRs auto-added to index, status changes auto-reflected).

**Persistent Terraform MCP container pool:**

- Problem: Each skill invocation spawns a new Docker container, adding startup latency. No container reuse.
- Blocks: Efficient high-throughput Terraform operations (batch `apply`, multiple `plan` runs in sequence).

**Behavioral eval execution in CI:**

- Problem: Behavioral evals (`dev-flow/evals/`, `jj/evals/`) are schema-validated but never executed. They require Claude agent harness, which is not available in CI.
- Blocks: Early detection of eval failures, regression testing of agent behavior, confidence in skill quality before release.

## Test Coverage Gaps

**Terraform MCP Docker container lifecycle (high-risk area):**

- What's not tested: (1) Container spawn failure (docker not found, image pull fails). (2) Container termination via SIGTERM/SIGKILL timeouts. (3) Env file cleanup on crash. (4) Process zombie scenarios (uncleaned defunct processes).
- Files: `homelab/skills/terraform/scripts/terraform_mcp.py`, `homelab/skills/terraform/tests/test_terraform_mcp.py`
- Risk: Real production failures (zombie containers, leaked temp files, stuck processes) may not be caught until deployed.
- Priority: **High** — container lifecycle is critical for resource cleanup and system stability.

**Cross-shell compatibility (drain worker):**

- What's not tested: (1) dash/sh (POSIX shell, common in Alpine/minimal images). (2) ksh (legacy systems). (3) Shell with aliases/functions in rc files that interfere. (4) Non-standard `direnv` installations.
- Files: `dev-flow/scripts/drain-worker-launch`, `tests/test_drain_worker_launch.py`
- Risk: Drain worker fails silently on systems with unexpected shell.
- Priority: **Medium** — affects niche deployments but not common desktop use cases.

**Error recovery in worktree operations:**

- What's not tested: (1) Partial failure (git succeeds, jj fails). (2) Cleanup failures (rm fails due to permission, symlink points stale). (3) Concurrent worktree operations (race condition).
- Files: `dev-flow/hooks/worktree-create`, `dev-flow/hooks/worktree-remove`
- Risk: Orphaned worktrees, stale beads redirects, corrupted jj state.
- Priority: **High** — high-frequency operation with complex cleanup logic.

**ADR orphan recovery (adr-doctor):**

- What's not tested: (1) Orphaned bead with no `.md` file (can't trigger in this repo since all 32 have files). (2) `AskUserQuestion` fallback path (needs main session context). (3) Bead with invalid bd-id format (fhsk-51g fix for hyphenated prefixes).
- Files: `dev-flow/scripts/_adr_doctor.py`, `dev-flow/scripts/tests/test_adr_doctor.py`
- Risk: Hidden failures in edge cases discovered only in production.
- Priority: **Medium** — edge case, but could strand data if not handled.

**Miniflux API error paths:**

- What's not tested: (1) API timeouts (feed refresh stuck). (2) Partial failures (some entries fail to update). (3) Large OPML imports (memory/time limits). (4) Concurrent feed operations.
- Files: `homelab/skills/miniflux/scripts/miniflux_api.py`, `homelab/skills/miniflux/tests/test_miniflux_api.py`
- Risk: Silent partial failures or hung operations.
- Priority: **Medium** — Miniflux is new; error surface not fully explored.

---

*Concerns audit: 2026-07-08*
