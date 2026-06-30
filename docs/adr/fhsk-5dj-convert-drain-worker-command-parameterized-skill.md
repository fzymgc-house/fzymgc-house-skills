---
title: "Convert drain-with-worker command to a parameterized skill"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-5dj; do not edit manually; use `/adr update fhsk-5dj` -->

**Date:** 2026-06-13
**Status:** Accepted
**Decision:** fhsk-5dj
**Deciders:** Sean Brandt

## Context

The drain harness had a cmux-only `/drain-with-worker` slash command. Adding tmux support created a fork: duplicate the command as `drain-with-tmux-worker`, or convert the launcher to a single skill that accepts a worker-type argument. Skills are the auto-discovered, parameterizable extension surface in Claude Code; commands substitute positional `$1` while skills receive a free-form arg string parsed in prose. In this harness a skill is still typeable as `/drain-with-worker`.

## Decision

Replace `dev-flow/commands/drain-with-worker.md` with `dev-flow/skills/drain-with-worker/SKILL.md` taking an optional `[worker-type] <drain-id>` argument; `worker-type` defaults to `auto` (resolved by `_muxdriver.detect()`). The SKILL.md `allowed-tools` frontmatter replaces the raw `Bash(cmux:*)` verb permission with script-invocation permissions.

## Rationale

- Skills are the auto-discovered, description-triggered extension surface; a command is now the narrower choice.
- A single parameterized skill scales to N multiplexers without N commands.
- The `allowed-tools` frontmatter tightens the permission surface (no raw multiplexer verbs).
- Forking duplicates launch logic across two files with no convergence mechanism.

## Alternatives Considered

**Fork a separate `drain-with-tmux-worker` command** (rejected) — isolated scope and deterministic `$1` substitution, but duplicates all launch logic, diverges over time, and a third multiplexer needs a third command.

**Convert to a single parameterized skill** (chosen) — one entry point for all multiplexers; new multiplexers extend the worker-type arg. Trade-off: argument parsing is prose-interpreted by the model rather than positional `$1`, and four existing tests that read the command file must be rewritten.

## Consequences

**Positive:** one canonical entry point for all worker types; new multiplexers extend the worker-type argument, not the file count; explicit `allowed-tools` frontmatter tightens the permission surface.

**Negative:** argument parsing is prose-interpreted, so reliability depends on SKILL.md wording; four existing tests must be rewritten to target the new paths.

**Neutral:** the skill remains typeable as `/drain-with-worker`; operator UX is unchanged.
