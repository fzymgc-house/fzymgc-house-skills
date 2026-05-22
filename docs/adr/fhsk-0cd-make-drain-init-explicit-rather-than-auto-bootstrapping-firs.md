<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-0cd; do not edit manually; use `/adr update fhsk-0cd` -->

# Make /drain init explicit rather than auto-bootstrapping on first run

**Date:** 2026-05-22
**Status:** Accepted
**Decision:** fhsk-0cd
**Deciders:** Sean Brandt (@seanb4t)

**Date:** 2026-05-22
**Status:** Accepted
**Deciders:** Sean Brandt (@seanb4t)

## Context

The drain harness requires per-repo state: a custom type `drain` registered in `bd config get types.custom` and a formula file copied into the repo's `.beads/formulas/formula-drain.toml`. These mutations could happen automatically on the first `/drain` invocation or require an explicit one-shot bootstrap command.

## Decision

Bootstrap is explicit via `/drain init`, idempotent, and per-repo. Subsequent `/drain epic|set|cascade|resume` invocations run read-only pre-flight checks; missing assets produce a clear "run /drain init first" error rather than triggering silent mutation.

## Rationale

- deepwiki confirmed `bd mol pour` auto-registers unknown types silently via `ensureSubgraphCustomTypes`. Without explicit init, the first drain run would mutate `.beads/config.yaml` invisibly — auditable only by diffing `bd config` before and after.
- Operator visibility goal: `bd types` lists `drain` and `bd formula list` shows `formula-drain` before any drain runs, so the harness state is discoverable via standard bd queries.
- Spec non-goal: "Bootstrap is explicit (`/drain init`) and per-repo; nothing mutates `.beads/` without operator action." Explicit init is the only design consistent with this non-goal.
- `${CLAUDE_PLUGIN_ROOT}` cp requires explicit `allowed-tools` declaration anyway; auto-bootstrap would need the same gate, making it no simpler than an explicit init command.

## Alternatives Considered

**Auto-bootstrap on first `/drain` invocation — rejected.** Strengths: zero operator friction; harness is self-configuring. Weaknesses: mutates `.beads/` mid-run without explicit operator consent; combined with `bd mol pour`'s silent auto-registration, the actual bd state changes during the first run are invisible to anyone not actively diffing config; violates the spec non-goal that nothing should mutate `.beads/` without operator action.

## Consequences

**Positive.** All `.beads/` mutations are operator-initiated and explicit. `bd types` and `bd formula list` reflect drain state before the first run. Defense-in-depth post-pour `bd show $DRAIN_ID --json | jq '.type'` verification catches any auto-registration surprises.

**Negative.** New-repo onboarding requires `/drain init`; pre-flight refusal is the failure mode if omitted. Codex users cannot use `${CLAUDE_PLUGIN_ROOT}` cp; a manual fallback recipe is documented in the skill.

**Neutral.** `/drain init` is idempotent — re-running in an already-initialized repo is safe and produces no duplicate entries.

## References

- Spec: `docs/superpowers/specs/2026-05-22-drain-skill-design.md` §Architecture — Bootstrap — /drain init, §Non-goals
- Design bead: `fhsk-a67`
- bd auto-registration behavior: deepwiki query against `gastownhall/beads` confirmed `ensureSubgraphCustomTypes` / `EnsureCustomTypeInTx` path.
