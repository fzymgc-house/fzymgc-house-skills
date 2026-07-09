# Constraints (SPEC intel — Pass 3)

Provenance: Pass 3 ingest, MERGE mode. 20 SPEC-classified docs. Each constraint below is an
implementation contract / NFR / protocol / schema extracted from a SPEC and **subordinated**
to an already-LOCKED decision (ADR > SPEC precedence). These do NOT override any locked
decision; they record the concrete contract the locked decision implies, deduplicated against
the Pass 1 + Pass 2 baseline (which held no formal SPEC constraints).

Type legend: api-contract | schema | nfr | protocol | structural.

---

## Hooks & VCS integration

### CON-p3-hook-python-runtime (nfr / protocol) — NEW

- source: docs/superpowers/specs/2026-03-11-hook-python-migration-design.md
- Claude hooks are single-file PEP 723 `uv run` Python scripts (not bash), backed by a shared
  `worktree_helpers.py` (`sanitize_for_output`, `validate_safe_name`, `detect_repo_root`,
  `run_cmd`, `cleanup_empty_parent`), pytest-covered; `.claude/settings.json` points at the
  Python entrypoints. Generalizes the Python/uv tooling stance beyond ADR scripts (fhsk-nlw).

### CON-p3-jj-pager-safety (nfr) — NEW

- source: docs/superpowers/specs/2026-04-03-jj-plugin-hardening-design.md
- jj invocations in an agent context MUST use a non-interactive pager to avoid pager hangs;
  conflict-marker output is normalized for machine parsing.

### CON-p3-jj-workspace-collision (protocol) — NEW

- source: docs/superpowers/specs/2026-04-03-jj-plugin-hardening-design.md
- Parallel-agent jj workspaces MUST have collision detection (session-start-jj-detect hook);
  undo/op semantics are documented in jjagent memory.

### CON-p3-guard-jj-op-marker (protocol) — NEW; implements LOCKED DEC-jj-op-log-recovery-gate

- source: docs/superpowers/specs/2026-05-02-guard-jj-mutating-design.md
- PreToolUse/Bash hook blocks `jj op restore` / `jj op abandon` unless the command line carries
  the approval marker `# jj-op-approved`; defined JSON response shapes + regex patterns mirror
  the existing guard-git-mutating hook. Concrete contract for the locked op-log recovery gate.

### CON-p3-vcs-preamble-set (schema / protocol) — NEW

- source: docs/superpowers/specs/2026-05-28-wire-review-pipeline-seams-design.md;
  docs/superpowers/specs/2026-03-16-superpowers-jj-fork-design.md
- Consolidated VCS reference set shared across dev-flow skills/agents:
  `vcs-preamble.md`, `vcs-detection-preamble.md`, `vcs-equivalence.md`. Single source for
  git/jj equivalence; code-reviewer agent disambiguated between the two homonym locations.

### CON-p3-upstream-manifest (protocol) — NEW

- source: docs/superpowers/specs/2026-03-16-superpowers-jj-fork-design.md
- The dev-flow (ex-superpowers) fork tracks obra/superpowers upstream by version via
  `references/upstream-manifest.md` + a `sync-upstream`/`scan-upstream` script; jj/git VCS
  abstraction is applied per-skill via the vcs-preamble.

---

## ADR tooling

### CON-p3-adr-bd-source-of-truth (schema) — NEW; elaborates LOCKED fhsk-nlw/slp/bmn

- source: docs/superpowers/specs/2026-05-22-adr-evolution-design.md
- bd is the canonical ADR store; markdown is a derived render produced by `render-adr`;
  `adr-doctor` detects bd↔markdown drift; `formula-adr` supplies versioned scaffolding;
  `evolve-adr` skill performs lifecycle operations.

### CON-p3-adr-starlight-frontmatter (schema) — NEW; elaborates LOCKED fhsk-slp/bmn/nlw

- source: docs/superpowers/specs/2026-06-30-adr-render-python-frontmatter-design.md
- `render-adr` + `adr-doctor` are Python PEP 723 uv scripts emitting/validating Starlight-
  compatible YAML frontmatter (title in frontmatter, no body H1); INV-A25 bd-free check
  enforces frontmatter presence in CI.

---

## Review pipeline

### CON-p3-slop-pattern-catalogs (schema) — NEW; elaborates LOCKED fhsk-2us

- source: docs/superpowers/specs/2026-05-28-anti-ai-slop-review-aspect-design.md
- slop-hunter review aspect uses named pattern catalogs: `code-slop.md` (C-n IDs) and
  `prose-slop.md` (P-n IDs); ACTIVE_ASPECTS deferral suppresses co-owned patterns to avoid
  duplicate findings; named-pattern discipline + cross-aspect deferral rules govern additions.

### CON-p3-pr-review-consolidation (structural) — NEW

- source: docs/superpowers/specs/2026-05-28-consolidate-pr-review-under-dev-flow-design.md
- The pr-review plugin is consolidated under dev-flow: skills/agents/references/evals relocated
  into `dev-flow/`, Codex wrappers + symlinks and both marketplace manifests retargeted, tests
  updated. (Matches current repo layout; grepping was later re-extracted as its own plugin.)

### CON-p3-dev-flow-rules (structural) — NEW; governing contract

- source: docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md
- dev-flow structural Rules 1–7 (spec/plan discipline, bead lifecycle, model selection,
  grounding tools) govern every dev-flow skill and review-gate agent; ADR-capture subsystem
  (capture-adrs, adr-extractor, nudge-adr-capture) is wired into the workflow.

### CON-p3-skills-routing (protocol) — NEW; elaborates LOCKED fhsk-bj8/p07

- source: docs/superpowers/specs/2026-05-28-skills-routing-and-adr-capture-fixes-design.md
- Subagent dispatch uses `agent:<type>` bead labels (static known-set fallback to
  general-purpose); capture-adrs worthiness criteria tightened; nudge-adr-capture fires only on
  plan beads.

---

## Drain harness

### CON-p3-drain-sentinel-protocol (protocol) — NEW; elaborates LOCKED fhsk-thw/zds/e4i/eqt/0cd

- source: docs/superpowers/specs/2026-05-22-drain-skill-design.md;
  docs/superpowers/specs/2026-05-24-drain-goal-handoff-redesign-design.md
- Drain harness = /drain command + draining-beads skill + `bd create --type drain` bead
  (fhsk-buu). Uses sentinel predicates + halt conditions; skills EMIT the /goal condition
  (never invoke /goal); iteration protocol lives in the skill (not the condition, to dodge 4K
  truncation); cold-boot worker reads a condition pointer + durable bead state (no temp file);
  explicit `/drain init` pre-flight, post-flight finalization.

### CON-p3-drain-watchdog (protocol) — NEW; elaborates LOCKED fhsk-dtk/5dj/8g6

- source: docs/superpowers/specs/2026-05-25-drain-with-worker-design.md
- drain-with-worker launches an autonomous worker pane via a `drain-watchdog` Python script
  with surface (screen) monitoring for stall detection; bead-prerequisite validation runs
  before launch; launch is gated behind AskUserQuestion (fhsk-dtk).

### CON-p3-mux-driver-protocol (api-contract) — NEW; elaborates LOCKED fhsk-8yz/a6v/5dj

- source: docs/superpowers/specs/2026-06-13-tmux-drain-worker-design.md
- Multiplexer abstraction contract — methods `spawn`, `send_text`, `send_enter`, `read_screen`
  — implemented by `CmuxDriver` and `TmuxDriver` in a shared `_muxdriver.py` stdlib uv module;
  drain-watchdog / drain-worker-launch parameterized over the driver; tmux ships as a
  standalone plugin.

---

## Skills & plugins

### CON-p3-solving-a-bead-interface (api-contract) — NEW; elaborates LOCKED fhsk-3xn/hj3/ypt

- source: docs/superpowers/specs/2026-05-29-solving-a-bead-design.md
- solving-a-bead skill + `/solving-a-bead` command: phased workflow (Phase 0 blocker
  hard-block → claim → triage → TDD → verify → hand-off), validation gates, skill frontmatter +
  command `allowed-tools`/`argument-hint` interface; bead left in_progress at hand-off.

### CON-p3-handoff-body-schema (schema) — NEW; elaborates LOCKED fhsk-s15/57f/8xn

- source: docs/superpowers/specs/2026-05-29-handoff-bead-type-design.md
- handoff is a custom bd type with a `references/body-schema.md` contract; one conditional
  create/resume skill with thin `/handoff` + `/handoff-resume` entry points; session-state
  delta carried via bd dependency edges (no full re-snapshot).

### CON-p3-memory-curator-mcp (api-contract) — NEW; elaborates LOCKED fhsk-e0u

- source: docs/superpowers/specs/2026-06-01-memory-curator-plugin-design.md
- memory-curator plugin = MCP OAuth server + SessionStart (recall) / Stop (capture) hooks +
  `scope.py` two-tier (spine/overlay) scope derivation; curating-memory + promoting-memory
  skills; registered in both marketplaces with a Codex wrapper.

### CON-p3-miniflux-cli (api-contract) — NEW; elaborates LOCKED fhsk-pqw/qs9/0qz

- source: docs/superpowers/specs/2026-06-13-miniflux-skill-design.md
- miniflux homelab skill wraps the Miniflux Python client directly (no MCP gateway) via
  `miniflux_api.py` CLI; env-then-file credential resolution; reference set
  feeds/entries/curation/digest/health; deterministic rules server-side, reasoning in Claude.

### CON-p3-mermaid-pipeline (api-contract) — NEW; elaborates LOCKED fhsk-4bi

- source: docs/superpowers/specs/2026-05-30-mermaid-skill-design.md
- mermaid skill validates via `@probelabs/maid` (bunx) with `mmdc` render-validate fallback,
  browser-free; diagram-types + common-mistakes references; optional MCP wiring.

---

Total NEW constraints this pass: 19. All subordinate to the locked baseline; none overrides a
locked decision. See `INGEST-CONFLICTS-pass3.md` for the precedence resolution log.
