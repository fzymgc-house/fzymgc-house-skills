# Architecture Decision Records (ADRs)

This directory captures architectural decisions made during the
brainstorming and planning phases of work tracked by `dev-flow`.

## Index

<!-- BEGIN INDEX -->

| Date | bd | Title | Status |
|------|-----|-------|--------|
| 2026-05-24 | [fhsk-zds](fhsk-zds-use-drain-bead-as-cross-session-handoff-carrier-not-temp-fil.md) | Use the drain bead as the cross-session handoff carrier, not a temp file | Accepted |
| 2026-05-24 | [fhsk-eqt](fhsk-eqt-store-drain-iteration-protocol-skill-not-goal-condition.md) | Store the drain iteration protocol in the skill, not the /goal condition | Accepted |
| 2026-05-24 | [fhsk-e4i](fhsk-e4i-never-invoke-goal-from-skill-emit-condition-user-or-driver-s.md) | Never invoke /goal from a skill; emit the condition for a user or driver to submit | Accepted |
| 2026-05-24 | [fhsk-buu](fhsk-buu-use-bd-create-type-drain-drain-bead-creation-not-bd-mol-pour.md) | Use bd create --type drain for drain bead creation (not bd mol pour) | Accepted |
| 2026-05-22 | [fhsk-thw](fhsk-thw-use-goal-over-loop-autonomous-bead-queue-drains.md) | Use /goal over /loop for autonomous bead-queue drains | Accepted |
| 2026-05-22 | [fhsk-rqh](fhsk-rqh-use-bd-mol-pour-versioned-formula-drain-bead-creation.md) | Use bd mol pour with versioned formula for drain bead creation | Superseded by fhsk-buu |
| 2026-05-22 | [fhsk-ce3](fhsk-ce3-store-drain-lessons-bd-notes-rather-than-prompt-body.md) | Store drain lessons in bd notes rather than the prompt body | Accepted |
| 2026-05-22 | [fhsk-0o2](fhsk-0o2-split-drain-harness-into-formula-command-and-skill.md) | Split drain harness into formula, command, and skill | Superseded by fhsk-eqt |
| 2026-05-22 | [fhsk-0cd](fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md) | Make /drain init explicit rather than auto-bootstrapping on first run | Accepted |
| 2026-05-22 | [fhsk-0cd](fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrap.md) | Make /drain init explicit rather than auto-bootstrapping on first run | Accepted |

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
