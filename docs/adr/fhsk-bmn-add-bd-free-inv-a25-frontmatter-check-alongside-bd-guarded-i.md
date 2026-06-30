---
title: "Add bd-free INV-A25 frontmatter check alongside bd-guarded INV-A22"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-bmn; do not edit manually; use `/adr update fhsk-bmn` -->

**Date:** 2026-06-30
**Status:** Accepted
**Decision:** fhsk-bmn
**Deciders:** Sean Brandt (@seanb4t)

## Context

adr-doctor's INV-A22 (render-match) is guarded by `command -v bd` and silently skipped in CI because CI does not install bd. That gap let the missing-frontmatter regression merge into homelab undetected. Installing bd in CI is explicitly a Non-Goal.

## Decision

A bd-free INV-A25 `frontmatter_title_present` is added to adr-doctor: every `<bd-id>-<slug>.md` (excluding README.md) must begin with a YAML frontmatter block carrying a non-empty `title:`. It runs in both full and `--changed-only` modes without bd, so CI enforces it.

## Rationale

- Separates format-presence enforcement (bd-free, CI) from content-fidelity enforcement (INV-A22, local) — each layer covers what its execution context can verify.
- Directly closes the gap that let the Starlight regression merge undetected.
- A bd-free check is simpler, faster, and reproducible across all CI environments.

## Alternatives Considered

- **Add bd-free INV-A25 (chosen):** runs in CI without bd; guards the exact regression class; cheap to evaluate.
- **Install bd in CI (rejected):** explicitly a Non-Goal; adds a non-trivial CI dependency.
- **Rely solely on local INV-A22 (rejected):** leaves CI blind to frontmatter regressions; the original failure proves this insufficient.

## Consequences

- Positive: CI catches missing/empty frontmatter title before merge; a clear two-tier invariant model (format presence in CI, full fidelity locally).
- Negative: INV-A22 remains local-only; CI still cannot detect render-content drift.
- Neutral: INV-A25 applies only to `<bd-id>-<slug>.md` files, excluding README.md.
