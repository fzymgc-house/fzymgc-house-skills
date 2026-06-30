---
title: "Rewrite ADR scripts as Python PEP 723 uv run --script modules"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-nlw; do not edit manually; use `/adr update fhsk-nlw` -->

**Date:** 2026-06-30
**Status:** Accepted
**Decision:** fhsk-nlw
**Deciders:** Sean Brandt (@seanb4t)

## Context

render-adr (~213 lines of bash) and adr-doctor.sh (~300 lines of bash) are dev-flow's ADR tooling. The bash INV-A22 render-match overwrites the committed file in place and then restores it via `git checkout` / `jj restore` — a destructive step with restore-failure edge cases. The repo already ships several `uv run --script` PEP 723 executables (drain-watchdog, ensure-isolated-workspace, validate-bead) with importable `_module.py` companions tested under dev-flow/scripts/tests/. The user directed moving dev-flow tooling off shell onto Python/uv.

## Decision

render-adr and adr-doctor.sh are rewritten as PEP 723 `uv run --script` executables backed by importable pure-function modules (`_adr_render.py`, `_adr_doctor.py`); CLI contracts and exit codes are unchanged. adr-doctor.sh is renamed to adr-doctor.

## Rationale

- A pure `render()` returning a string lets INV-A22 compare in memory, eliminating the destructive overwrite-and-restore dance.
- Importable modules allow per-invariant unit tests with injected bd data, no live bd required.
- Consistent with drain-watchdog, ensure-isolated-workspace, and other `uv run --script` tools already in PYTEST_DIRS.

## Alternatives Considered

- **Python PEP 723 uv run --script with pure modules (chosen):** in-memory render-match; unit-testable without bd; matches the repo pattern.
- **Minimal bash patch adding only frontmatter emission (rejected):** does not address the destructive INV-A22 dance or enable bd-free unit testing.
- **Packaged Python module (pyproject.toml) (rejected):** build/install overhead inconsistent with the single-file script pattern.
- **Migrate all dev-flow scripts to Python at once (rejected/deferred):** out of scope for this bead.

## Consequences

- Positive: INV-A22 restore-failure edge cases eliminated; ADR tooling is unit-testable in CI; uv is already a repo dependency.
- Negative: uv must be on PATH wherever adr-doctor/render-adr run; the Codex-compatibility note in evolve-adr/SKILL.md becomes stale and must be updated.
- Neutral: adr-doctor.sh is renamed to adr-doctor and all references are updated.
