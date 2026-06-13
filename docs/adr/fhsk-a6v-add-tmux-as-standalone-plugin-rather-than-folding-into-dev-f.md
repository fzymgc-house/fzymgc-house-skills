<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-a6v; do not edit manually; use `/adr update fhsk-a6v` -->

# Add tmux as a standalone plugin rather than folding into dev-flow

**Date:** 2026-06-13
**Status:** Accepted
**Decision:** fhsk-a6v
**Deciders:** Sean Brandt

## Context

The tmux usage skill needed a home. It could live inside `dev-flow/skills/` (co-located with drain) or in a new top-level `tmux/` plugin following the same structure as `homelab/`, `jj/`, and `dev-flow/`. The plugin boundary determines reusability: a `dev-flow`-internal skill is unavailable to `jj` or `homelab` skills without a cross-plugin dependency.

## Decision

Create `tmux/plugin.json`, `tmux/skills/tmux/SKILL.md`, and a Codex wrapper at `plugins/tmux/` (skills symlink only); register `tmux` in both `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`, and add `tmux/plugin.json` `$.version` to `release-please-config.json` extra-files.

## Rationale

- tmux is a general-purpose terminal multiplexer, not a drain-specific tool; it belongs at the same level as `jj` and `homelab`.
- A standalone plugin keeps tmux primitives reusable without cross-plugin dependency injection.
- The existing plugin taxonomy (one plugin per tool domain) is extended consistently.

## Alternatives Considered

**Add the tmux skill inside `dev-flow/skills/`** (rejected) — no new plugin registration, no release-please/Codex-wrapper boilerplate, but couples tmux primitives to the drain workflow plugin and makes them unavailable to `jj`/`homelab` without a cross-plugin dependency.

**Create a standalone `tmux/` plugin** (chosen) — tmux primitives reusable across all plugins without coupling; consistent with the existing one-plugin-per-tool-domain taxonomy. Trade-off: registration boilerplate across four files (two marketplace manifests, release-please config, Codex wrapper).

## Consequences

**Positive:** the tmux usage skill is available to any plugin without cross-plugin coupling; the plugin taxonomy stays consistent (one plugin per tool domain).

**Negative:** a new plugin requires registration boilerplate in four files.

**Neutral:** AGENTS.md "three source plugins" count updates to four.
