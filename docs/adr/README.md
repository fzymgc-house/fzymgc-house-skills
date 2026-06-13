# Architecture Decision Records (ADRs)

This directory captures architectural decisions made during the
brainstorming and planning phases of work tracked by `dev-flow`.

## Index

<!-- BEGIN INDEX -->

| Date | bd | Title | Status |
|------|-----|-------|--------|
| 2026-06-13 | [fhsk-a6v](fhsk-a6v-add-tmux-as-standalone-plugin-rather-than-folding-into-dev-f.md) | Add tmux as a standalone plugin rather than folding into dev-flow | Accepted |
| 2026-06-13 | [fhsk-8yz](fhsk-8yz-share-cmux-tmux-driver-logic-via-muxdriver-module-not-script.md) | Share cmux/tmux driver logic via a _muxdriver module, not script duplication | Accepted |
| 2026-06-13 | [fhsk-5dj](fhsk-5dj-convert-drain-worker-command-parameterized-skill.md) | Convert drain-with-worker command to a parameterized skill | Accepted |
| 2026-06-10 | [fhsk-8g6](fhsk-8g6-drain-finishes-branch-autonomously-push-pr-at-clean-sentinel.md) | Drain finishes the branch autonomously (push + PR) at the clean sentinel | Accepted |
| 2026-06-09 | [fhsk-dgo](fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md) | Use release-please with in-file plugin versions (reverse cog tag-only) | Accepted |
| 2026-06-02 | [fhsk-p07](fhsk-p07-replace-blocking-stop-hook-capture-nudge-silent-sessionstart.md) | Replace blocking Stop-hook capture nudge with silent SessionStart briefing and throttled PostToolUse nudge | Accepted |
| 2026-06-01 | [fhsk-e0u](fhsk-e0u-use-two-tier-spine-overlay-memory-scope-model.md) | Use two-tier spine/overlay memory scope model | Accepted |
| 2026-05-30 | [fhsk-4bi](fhsk-4bi-adopt-probelabs-maid-as-primary-mermaid-lint-engine.md) | Adopt @probelabs/maid as the primary Mermaid lint engine | Accepted |
| 2026-05-29 | [fhsk-ypt](fhsk-ypt-treat-bug-bead-suggested-fixes-as-non-authoritative-hypothes.md) | Treat bug bead suggested fixes as non-authoritative hypotheses | Accepted |
| 2026-05-29 | [fhsk-toy](fhsk-toy-use-tag-only-cog-releases-no-commit-main.md) | Use tag-only cog releases with no commit to main | Superseded by fhsk-dgo |
| 2026-05-29 | [fhsk-s15](fhsk-s15-use-custom-bd-type-handoffs-not-label-or-note.md) | Use a custom bd type for handoffs, not a label or note | Accepted |
| 2026-05-29 | [fhsk-hj3](fhsk-hj3-leave-bead-progress-at-hand-off-delegate-closure-merge.md) | Leave bead in_progress at hand-off; delegate closure to merge | Accepted |
| 2026-05-29 | [fhsk-h3z](fhsk-h3z-validate-conventional-commits-at-pr-title-boundary-ci.md) | Validate conventional commits at the PR-title boundary in CI | Accepted |
| 2026-05-29 | [fhsk-8xn](fhsk-8xn-carry-session-state-delta-handoff-body-not-full-re-snapshot.md) | Carry session-state delta in the handoff body, not a full re-snapshot | Accepted |
| 2026-05-29 | [fhsk-7y4](fhsk-7y4-adopt-single-repo-wide-version-replacing-per-package-streams.md) | Adopt single repo-wide version replacing per-package streams | Superseded by fhsk-dgo |
| 2026-05-29 | [fhsk-57f](fhsk-57f-package-handoff-create-and-resume-as-one-conditional-workflo.md) | Package handoff create and resume as one conditional-workflow skill | Accepted |
| 2026-05-29 | [fhsk-3xn](fhsk-3xn-hard-block-skill-entry-unmet-bead-blocker-dependencies.md) | Hard-block skill entry on unmet bead blocker dependencies | Accepted |
| 2026-05-28 | [fhsk-bj8](fhsk-bj8-use-agent-label-as-sole-subagent-dispatch-signal.md) | Use agent:* label as the sole subagent dispatch signal | Accepted |
| 2026-05-28 | [fhsk-2us](fhsk-2us-use-active-aspects-deferral-cross-aspect-deduplication-slop.md) | Use ACTIVE_ASPECTS deferral for cross-aspect deduplication in slop-hunter | Accepted |
| 2026-05-25 | [fhsk-dtk](fhsk-dtk-gate-drain-worker-launch-behind-askuserquestion-never-auto-f.md) | Gate drain worker launch behind AskUserQuestion, never auto-fire | Accepted |
| 2026-05-24 | [fhsk-zds](fhsk-zds-use-drain-bead-as-cross-session-handoff-carrier-not-temp-fil.md) | Use the drain bead as the cross-session handoff carrier, not a temp file | Accepted |
| 2026-05-24 | [fhsk-eqt](fhsk-eqt-store-drain-iteration-protocol-skill-not-goal-condition.md) | Store the drain iteration protocol in the skill, not the /goal condition | Accepted |
| 2026-05-24 | [fhsk-e4i](fhsk-e4i-never-invoke-goal-from-skill-emit-condition-user-or-driver-s.md) | Never invoke /goal from a skill; emit the condition for a user or driver to submit | Accepted |
| 2026-05-24 | [fhsk-buu](fhsk-buu-use-bd-create-type-drain-drain-bead-creation-not-bd-mol-pour.md) | Use bd create --type drain for drain bead creation (not bd mol pour) | Accepted |
| 2026-05-22 | [fhsk-thw](fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md) | Use /goal over /loop for autonomous bead-queue drains | Accepted |
| 2026-05-22 | [fhsk-rqh](fhsk-rqh-use-bd-mol-pour-versioned-formula-drain-bead-creation.md) | Use bd mol pour with versioned formula for drain bead creation | Superseded by fhsk-buu |
| 2026-05-22 | [fhsk-ce3](fhsk-ce3-store-drain-lessons-bd-notes-rather-than-prompt-body.md) | Store drain lessons in bd notes rather than the prompt body | Accepted |
| 2026-05-22 | [fhsk-0o2](fhsk-0o2-split-drain-harness-into-formula-command-and-skill.md) | Split drain harness into formula, command, and skill | Superseded by fhsk-eqt |
| 2026-05-22 | [fhsk-0cd](fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md) | Make /drain init explicit rather than auto-bootstrapping on first run | Accepted |

<!-- END INDEX -->

## Writing guidelines

ADRs are captured by the `capture-adrs` skill
(`dev-flow/skills/capture-adrs/SKILL.md`) automatically after
`plan-reviewer` returns READY. Each ADR pairs a markdown file with a
`bd` decision bead. Filename convention: `<bd-id>-<slug>.md`.

For the worthiness criteria and supersession discipline, see the spec
at
`docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
§ "ADR Capture Subsystem".
