---
title: "Use env-then-file config resolution for Miniflux credentials"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-qs9; do not edit manually; use `/adr update fhsk-qs9` -->

**Date:** 2026-06-14
**Status:** Accepted
**Decision:** fhsk-qs9
**Deciders:** Sean

## Context

The gateway script needs a Miniflux URL and API key at runtime. The homelab plugin runs in agent contexts where secrets may be injected as env vars (CI, container) or stored in a user dotfile. Both must be supported without forcing one.

## Decision

resolve_config() reads MINIFLUX_URL and MINIFLUX_API_KEY from the environment first; if either is absent it falls back to ~/.config/miniflux/config.yaml (XDG_CONFIG_HOME honored); missing/incomplete config raises ConfigError with an actionable message naming both sources.

## Rationale

- Matches the two-source pattern used by grafana and terraform skills.
- Env-first lets CI/container contexts inject credentials without filesystem side-effects.
- XDG compliance keeps dotfiles out of the home root.
- All three paths (env-wins, file-fallback, missing) are unit-tested.

## Alternatives Considered

- **Env-first, YAML dotfile fallback (chosen):** works headless and interactive; actionable error. Two code paths; partial-override edge case.
- **Env vars only (rejected):** simpler, but no persistent dotfile for interactive use.
- **Config file only (rejected):** single path, but no CI override; incompatible with injection patterns.

## Consequences

- Positive: works identically in headless CI and interactive desktop; ConfigError guides the fix.
- Negative: partial-override edge case (one var set, one missing) must be handled to avoid a half-configured client.
- Neutral: minimal config schema (url + api_key); no versioning concern.
