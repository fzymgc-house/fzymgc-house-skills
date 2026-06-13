<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-pqw; do not edit manually; use `/adr update fhsk-pqw` -->

# Wrap Miniflux client directly, not via MCP gateway

**Date:** 2026-06-14
**Status:** Accepted
**Decision:** fhsk-pqw
**Deciders:** Sean

## Context

The homelab plugin has two skills (grafana, terraform) that proxy an MCP server over httpx. When adding Miniflux support, the choice was whether to build a Miniflux MCP server and proxy it the same way, or import the official miniflux Python client directly in the gateway script. No Miniflux MCP server exists; building one adds a runtime process and network hop with no benefit for a single self-hosted instance.

## Decision

miniflux_api.py is a direct wrapper over the official miniflux Python client with no MCP intermediary, diverging from the grafana/terraform implementation pattern while preserving the same CLI surface conventions (--format yaml|json, CLAUDE_PLUGIN_ROOT invocation, references/).

## Rationale

- No Miniflux MCP server exists; building one is out of scope per the spec Non-Goals.
- A single self-hosted instance needs no network indirection layer.
- The official miniflux pip client fully covers the required API surface.
- SKILL.md explicitly calls this out as a direct-client wrapper to avoid contributor confusion.

## Alternatives Considered

- **Direct Python client wrapper (chosen):** no extra process/hop; stable official client; simpler deployment; consistent CLI surface. Diverges structurally from grafana/terraform.
- **Build and proxy a Miniflux MCP server (rejected):** structural consistency, but no server exists; significant scope creep; needless network process; explicit Non-Goal.

## Consequences

- Positive: simpler deployment (one uv-managed script, no server); full API surface without MCP schema translation.
- Negative: implementation-level divergence means a fourth homelab skill cannot just copy the httpx-proxy pattern.
- Neutral: CLI surface remains identical to existing skills.
