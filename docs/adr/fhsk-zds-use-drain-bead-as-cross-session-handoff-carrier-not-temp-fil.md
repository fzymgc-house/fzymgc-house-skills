---
title: "Use the drain bead as the cross-session handoff carrier, not a temp file"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-zds; do not edit manually; use `/adr update fhsk-zds` -->

**Date:** 2026-05-24
**Status:** Accepted
**Decision:** fhsk-zds
**Deciders:** Sean Brandt (@seanb4t)

## Context

A `/goal` worker is a fresh Claude session that inherits no controller context. The design needs a durable carrier to convey workspace, sentinel, mode, scope, and lessons to a cold worker. Controller and worker run in the same jj workspace but as separate sessions.

## Decision

The drain bead is the cross-session handoff carrier. It gains two metadata fields — `drain_workspace` (absolute jj workspace root) and `drain_sentinel` — stamped during the setup phase, alongside the existing `drain_mode`/`drain_scope`/`drain_started_at` and the `lesson:`/`rejection:`/`halt:` notes. The worker recovers everything via `bd show <drain-id> --json`.

## Rationale

- The bead is already the durable, session- and workspace-agnostic store for lessons and rejections — extending it is consistent.
- It avoids introducing a temp-file lifecycle and a gitignore entry.
- The worker reads durable state via a single `bd show`, already part of the cold-boot sequence.

## Alternatives Considered

- **Temp file (`.drain/<drain-id>.md`) as the handoff carrier:** directly readable, arbitrarily large, no schema change — but needs a gitignore entry and explicit creation/cleanup, and is weaker on session-agnostic durability. Rejected as the primary carrier (retained only as the Approach B protocol-delivery fallback).

## Consequences

- Positive: a single durable state store; no file cleanup; `drain_workspace` paves the way for a future cmux/tmux driver.
- Negative: the bead schema expands; pre-existing drain beads lack the new fields until re-initialized.
- Neutral: whether `drain_workspace` is absolute or workspace-relative is deferred to when cmux/tmux dispatch lands.
