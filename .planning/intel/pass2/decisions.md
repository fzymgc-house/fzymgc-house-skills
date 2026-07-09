# Decisions (ADR intel — Pass 2)

Synthesized from 35 ADR-classified docs in `docs/adr/` (fhsk-*). Higher-precedence
than SPEC/PRD/DOC. 31 ADRs are active LOCKED; 4 are Superseded (recorded as
historical context only, NOT active locked decisions).

Provenance: Pass 2 ingest, merge mode. Existing Pass 1 locked decisions live in
`.planning/PROJECT.md` and `.planning/intel/decisions.md` and are NOT modified here.

---

## Active LOCKED decisions (31)

### DEC-adr-fhsk-0cd — Make /drain init explicit, not auto-bootstrapping

- source: docs/adr/fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md
- status: LOCKED (Accepted)
- scope: drain harness, bd configuration, bootstrap initialization, custom type registration, formula deployment
- Decision: Bootstrap the drain harness explicitly via `/drain init` with pre-flight checks; missing assets produce a clear error rather than silent mutations on first run.

### DEC-adr-fhsk-0qz — Split curation into deterministic rules (Miniflux) + reasoning (Claude)

- source: docs/adr/fhsk-0qz-split-curation-into-deterministic-rules-miniflux-and-reasoni.md
- status: LOCKED (Accepted)
- scope: Miniflux, content curation, blocklist/keeplist rules, relevance ranking, rule proposals
- Decision: Deterministic blocklist/keeplist regex rules live server-side in Miniflux; Claude handles relevance ranking, digest prose, and rule proposals via a suggest-rules → apply-rule handoff.

### DEC-adr-fhsk-2us — ACTIVE_ASPECTS deferral for cross-aspect dedup in slop-hunter

- source: docs/adr/fhsk-2us-use-active-aspects-deferral-cross-aspect-deduplication-slop.md
- status: LOCKED (Accepted)
- scope: slop-hunter, ACTIVE_ASPECTS, cross-aspect deduplication, review orchestrator, pattern catalog
- Decision: Use ACTIVE_ASPECTS deferral in slop-hunter to suppress co-owned patterns when owning aspects are present, eliminating duplicate findings.

### DEC-adr-fhsk-3xn — Hard-block skill entry on unmet bead blocker dependencies

- source: docs/adr/fhsk-3xn-hard-block-skill-entry-unmet-bead-blocker-dependencies.md
- status: LOCKED (Accepted)
- scope: solving-a-bead, Phase 0, blocker dependencies, skill entry gate, dependency validation
- Decision: Phase 0 of solving-a-bead hard-blocks if any blocker dependency is open, guaranteeing correctness rather than emitting a soft warning.

### DEC-adr-fhsk-4bi — Adopt @probelabs/maid as primary Mermaid lint engine

- source: docs/adr/fhsk-4bi-adopt-probelabs-maid-as-primary-mermaid-lint-engine.md
- status: LOCKED (Accepted)
- scope: mermaid, linting, validation, @probelabs/maid, bunx, diagram-validation
- Decision: Use @probelabs/maid as the primary Mermaid lint engine via bunx, with optional mmdc render-validate fallback for portable, browser-free validation.

### DEC-adr-fhsk-57f — Package handoff create+resume as one conditional-workflow skill

- source: docs/adr/fhsk-57f-package-handoff-create-and-resume-as-one-conditional-workflo.md
- status: LOCKED (Accepted)
- scope: handoff skill, conditional-workflow pattern, body schema, create/resume modes
- Decision: One handoff skill with conditional create/resume modes sharing a single body-schema reference; thin `/handoff` and `/handoff-resume` entry points.

### DEC-adr-fhsk-5dj — Convert drain-with-worker command to a parameterized skill

- source: docs/adr/fhsk-5dj-convert-drain-worker-command-parameterized-skill.md
- status: LOCKED (Accepted)
- scope: drain-with-worker, skill parameterization, worker-type argument, cmux, tmux, multiplexer support
- Decision: Replace the drain-with-worker command with a parameterized skill accepting an optional worker-type argument, supporting multiple multiplexers without forking.

### DEC-adr-fhsk-8g6 — Drain finishes the branch autonomously (push + PR) at clean sentinel

- source: docs/adr/fhsk-8g6-drain-finishes-branch-autonomously-push-pr-at-clean-sentinel.md
- status: LOCKED (Accepted)
- scope: drain worker, finishing-a-development-branch, clean sentinel, PR creation, review-pr gate
- Decision: Drain workers autonomously finish branches via the non-interactive mode of finishing-a-development-branch, pushing and creating PRs without interactive menus.

### DEC-adr-fhsk-8xn — Carry session-state delta in the handoff body, not a full re-snapshot

- source: docs/adr/fhsk-8xn-carry-session-state-delta-handoff-body-not-full-re-snapshot.md
- status: LOCKED (Accepted)
- scope: handoff beads, session-state delta, bd dep edges, resume flow, stale-handoff detection
- Decision: Handoff beads carry only the session-state delta via bd dep edges, omitting non-applicable sections; full re-snapshots are rejected as maintenance burden and drift source.

### DEC-adr-fhsk-8yz — Share cmux/tmux driver logic via a _muxdriver module

- source: docs/adr/fhsk-8yz-share-cmux-tmux-driver-logic-via-muxdriver-module-not-script.md
- status: LOCKED (Accepted)
- scope: _muxdriver module, CmuxDriver, TmuxDriver, multiplexer abstraction, dev-flow/scripts, uv run --script
- Decision: Extract shared cmux/tmux driver logic into a `_muxdriver.py` stdlib module for protocol consistency across scripts, rather than duplicating script logic.

### DEC-adr-fhsk-a6v — Add tmux as a standalone plugin, not folded into dev-flow

- source: docs/adr/fhsk-a6v-add-tmux-as-standalone-plugin-rather-than-folding-into-dev-f.md
- status: LOCKED (Accepted)
- scope: tmux plugin, plugin taxonomy, marketplace registration, release automation, Codex wrapper
- Decision: Create tmux as a standalone plugin at the organizational level of jj and homelab (not co-located in dev-flow) for reusability across plugin boundaries.

### DEC-adr-fhsk-bj8 — Use agent:* label as the sole subagent dispatch signal

- source: docs/adr/fhsk-bj8-use-agent-label-as-sole-subagent-dispatch-signal.md
- status: LOCKED (Accepted)
- scope: subagent dispatch, bead labels, agent label routing, subagent-driven-development
- Decision: Replace unreachable skills[] dispatch with `agent:<type>` bead labels using a static known-set fallback to general-purpose.

### DEC-adr-fhsk-bmn — Add bd-free INV-A25 frontmatter check alongside bd-guarded INV-A22

- source: docs/adr/fhsk-bmn-add-bd-free-inv-a25-frontmatter-check-alongside-bd-guarded-i.md
- status: LOCKED (Accepted)
- scope: adr-doctor, INV-A25, INV-A22, frontmatter validation, ADR files, CI pipeline
- Decision: Introduce a bd-free INV-A25 check enforcing YAML frontmatter title presence in ADR files during CI, complementing the local bd-guarded INV-A22 content-fidelity check.

### DEC-adr-fhsk-buu — Use bd create --type drain for drain bead creation (not bd mol pour)

- source: docs/adr/fhsk-buu-use-bd-create-type-drain-drain-bead-creation-not-bd-mol-pour.md
- status: LOCKED (Accepted)
- scope: bd create, drain bead type, bead metadata, type registration
- Decision: Use `bd create --type drain` directly instead of `bd mol pour formula-drain` for audit-trail drain beads, based on verified bd source incompatibilities. Supersedes fhsk-rqh.

### DEC-adr-fhsk-ce3 — Store drain lessons in bd notes rather than the prompt body

- source: docs/adr/fhsk-ce3-store-drain-lessons-bd-notes-rather-than-prompt-body.md
- status: LOCKED (Accepted)
- scope: bd notes, drain beads, epic beads, prompt iteration, lesson storage
- Decision: Store lessons as bd notes on drain (ephemeral) or epic (persistent) beads to eliminate prompt drift and enable stable prompt iteration.

### DEC-adr-fhsk-dgo — Use release-please with in-file plugin versions (reverse cog tag-only)

- source: docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md
- status: LOCKED (Accepted)
- scope: release-please, release automation, plugin versioning, GitHub releases, CHANGELOG.md, manifest management
- Decision: Adopt release-please over cog; restore in-file plugin versions and CHANGELOG.md for consistency with sibling repos. Supersedes fhsk-toy and fhsk-7y4.
- Merge note: AGREES with existing Pass 1 LOCKED decision DEC-release-please-versioning (release-please, automated version sync). No contradiction. Advances GOV-01 (a superseding release ADR). See INGEST-CONFLICTS-pass2.md INFO.

### DEC-adr-fhsk-dtk — Gate drain worker launch behind AskUserQuestion, never auto-fire

- source: docs/adr/fhsk-dtk-gate-drain-worker-launch-behind-askuserquestion-never-auto-f.md
- status: LOCKED (Accepted)
- scope: /drain-with-worker, /drain, AskUserQuestion, --dangerously-skip-permissions worker, allowed-tools contract
- Decision: Require AskUserQuestion confirmation for /drain-with-worker launches, preventing silent auto-fire of privileged workers.
- Merge note: complementary with fhsk-8g6 — dtk gates worker LAUNCH; fhsk-8g6 governs autonomous behavior AFTER launch. Different phases; not contradictory.

### DEC-adr-fhsk-e0u — Use two-tier spine/overlay memory scope model

- source: docs/adr/fhsk-e0u-use-two-tier-spine-overlay-memory-scope-model.md
- status: LOCKED (Accepted)
- scope: memory-curator plugin, scope model, repository/jj workspaces, durable facts
- Decision: Adopt a two-tier scope model for the memory-curator plugin — spine (repo-wide) and overlay (workspace-local) — to share durable facts while isolating in-flight context.

### DEC-adr-fhsk-e4i — Never invoke /goal from a skill; emit the condition

- source: docs/adr/fhsk-e4i-never-invoke-goal-from-skill-emit-condition-user-or-driver-s.md
- status: LOCKED (Accepted)
- scope: /goal, skill design, agent behavior, user-only built-ins, drain command
- Decision: Skills must emit /goal conditions for a user or driver to submit, never invoke /goal directly (agents lack the tool access).
- Merge note: complementary with fhsk-thw — thw makes /goal the drain primitive; e4i governs HOW skills interact with /goal. Consistent.

### DEC-adr-fhsk-eqt — Store the drain iteration protocol in the skill, not the /goal condition

- source: docs/adr/fhsk-eqt-store-drain-iteration-protocol-skill-not-goal-condition.md
- status: LOCKED (Accepted)
- scope: drain iteration protocol, dev-flow:draining-beads skill, /goal condition, prompt caching, cold-boot reliability
- Decision: Move the 12-step iteration protocol into the dev-flow skill, away from the /goal condition, to avoid 4K-character truncation risk.

### DEC-adr-fhsk-h3z — Validate conventional commits at the PR-title boundary in CI

- source: docs/adr/fhsk-h3z-validate-conventional-commits-at-pr-title-boundary-ci.md
- status: LOCKED (Accepted)
- scope: conventional commits, PR title validation, CI workflow, lefthook, jj operations, squash-merge
- Decision: Move conventional-commit validation from a local git hook to a CI workflow on the PR title for reliable enforcement across jj and git VCS clients.

### DEC-adr-fhsk-hj3 — Leave bead in_progress at hand-off; delegate closure to merge

- source: docs/adr/fhsk-hj3-leave-bead-progress-at-hand-off-delegate-closure-merge.md
- status: LOCKED (Accepted)
- scope: bead lifecycle, solving-a-bead, finishing-a-development-branch, PR/merge workflow
- Decision: Bead closure occurs at merge time, not at fix commit; Phase 4 leaves the bead in_progress and suggests finishing-a-development-branch.

### DEC-adr-fhsk-nlw — Rewrite ADR scripts as Python PEP 723 uv run --script modules

- source: docs/adr/fhsk-nlw-rewrite-adr-scripts-as-python-pep-723-uv-run-script-modules.md
- status: LOCKED (Accepted)
- scope: render-adr, adr-doctor, ADR tooling, PEP 723, uv run --script, Python modules
- Decision: Rewrite ADR tooling (render-adr, adr-doctor.sh) as PEP 723 `uv run --script` Python modules to enable in-memory render matching and unit testing without a live bd.

### DEC-adr-fhsk-p07 — Replace blocking Stop-hook capture nudge with silent SessionStart + throttled PostToolUse

- source: docs/adr/fhsk-p07-replace-blocking-stop-hook-capture-nudge-silent-sessionstart.md
- status: LOCKED (Accepted)
- scope: memory-curator plugin, Stop hook, SessionStart briefing, PostToolUse hook, session capture
- Decision: Remove the blocking Stop hook that emits error-styled output; replace it with a silent SessionStart briefing and a throttled PostToolUse capture nudge.

### DEC-adr-fhsk-pqw — Wrap Miniflux client directly, not via MCP gateway

- source: docs/adr/fhsk-pqw-wrap-miniflux-client-directly-not-via-mcp-gateway.md
- status: LOCKED (Accepted)
- scope: Miniflux, MCP gateway, Python client wrapper, homelab plugin
- Decision: Wrap the Miniflux client directly without an MCP intermediary, diverging from the existing homelab MCP-gateway pattern.

### DEC-adr-fhsk-qs9 — Use env-then-file config resolution for Miniflux credentials

- source: docs/adr/fhsk-qs9-use-env-then-file-config-resolution-miniflux-credentials.md
- status: LOCKED (Accepted)
- scope: Miniflux, configuration resolution, credentials, environment variables, XDG config, homelab plugin
- Decision: Environment variables take precedence over the XDG config file for Miniflux URL and API-key resolution.

### DEC-adr-fhsk-s15 — Use a custom bd type for handoffs, not a label or note

- source: docs/adr/fhsk-s15-use-custom-bd-type-handoffs-not-label-or-note.md
- status: LOCKED (Accepted)
- scope: bd, handoff workflow, custom types, work-handoff persistence, issue tracking
- Decision: Register a custom bd type for handoffs to enable independent querying, a distinct lifecycle, and support for untracked exploration cases.

### DEC-adr-fhsk-slp — Adopt YAML title frontmatter in ADR files, drop body H1

- source: docs/adr/fhsk-slp-adopt-yaml-title-frontmatter-adr-files-drop-body-h1.md
- status: LOCKED (Accepted)
- scope: ADR rendering, render-adr script, adr-doctor tooling, Starlight docs build, YAML frontmatter
- Decision: Add YAML frontmatter with a title field to all ADR files and remove the body H1 to comply with Starlight documentation requirements.

### DEC-adr-fhsk-thw — Use /goal over /loop for autonomous bead-queue drains

- source: docs/adr/fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md
- status: LOCKED (Accepted)
- scope: dev-flow, autonomous-drains, bead-queue, /goal, /loop, holomush, bd-notes
- Decision: Adopt /goal as the sole autonomous-drain primitive in dev-flow, eliminating prompt drift from /loop's timer-based approach.

### DEC-adr-fhsk-ypt — Treat bug bead suggested fixes as non-authoritative hypotheses

- source: docs/adr/fhsk-ypt-treat-bug-bead-suggested-fixes-as-non-authoritative-hypothes.md
- status: LOCKED (Accepted)
- scope: bug beads, suggested fixes, Phase 2 triage, systematic-debugging skill, root-cause analysis
- Decision: Demote bug-bead suggested fixes to non-authoritative hypotheses and route them through systematic-debugging to enforce root-cause-first discipline.

### DEC-adr-fhsk-zds — Use the drain bead as the cross-session handoff carrier, not a temp file

- source: docs/adr/fhsk-zds-use-drain-bead-as-cross-session-handoff-carrier-not-temp-fil.md
- status: LOCKED (Accepted)
- scope: drain bead, cross-session handoff, jj workspace, cold-boot sequence, metadata fields
- Decision: The drain bead — extended with `drain_workspace` and `drain_sentinel` metadata — serves as the durable cross-session handoff carrier for /goal workers instead of temp files.

---

## Superseded ADRs (4) — historical context only, NOT active locked decisions

### fhsk-0o2 — Split drain harness into formula, command, and skill

- source: docs/adr/fhsk-0o2-split-drain-harness-into-formula-command-and-skill.md
- status: SUPERSEDED (locked:false). Supersedes fhsk-eqt; back-references fhsk-eqt.
- Historical: proposed splitting the drain harness into formula scaffolding, a command entry point with a Stop-hook body, and a canonical-reference skill.

### fhsk-7y4 — Adopt single repo-wide version replacing per-package streams

- source: docs/adr/fhsk-7y4-adopt-single-repo-wide-version-replacing-per-package-streams.md
- status: SUPERSEDED by fhsk-dgo (locked:false).
- Historical: replace per-package semver release-please streams with a single repo-wide version derived from conventional commits. Directionally consistent with the shipped one-repo-wide-version reality, but the active locked decision is fhsk-dgo.

### fhsk-rqh — Use bd mol pour with versioned formula for drain bead creation

- source: docs/adr/fhsk-rqh-use-bd-mol-pour-versioned-formula-drain-bead-creation.md
- status: SUPERSEDED by fhsk-buu (locked:false).
- Historical: proposed `bd mol pour` with a versioned TOML formula; superseded after verified bd source incompatibilities (see fhsk-buu).

### fhsk-toy — Use tag-only cog releases with no commit to main

- source: docs/adr/fhsk-toy-use-tag-only-cog-releases-no-commit-main.md
- status: SUPERSEDED by fhsk-dgo (locked:false).
- Historical: configured cog to create only git tags and GitHub Releases without committing to main; rejected in favor of release-please PRs per fhsk-dgo.
