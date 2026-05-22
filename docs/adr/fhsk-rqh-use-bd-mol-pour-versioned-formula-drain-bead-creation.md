<!-- markdownlint-disable MD013 -->

# Use bd mol pour with versioned formula for drain bead creation

**Date:** 2026-05-22
**Status:** Accepted
**Decision:** fhsk-rqh
**Deciders:** Sean Brandt (@seanb4t)

## Context

Each `/drain` invocation creates a typed audit-trail bead that carries the run's mode/scope/started_at metadata, accumulates lesson and rejection notes, and serves as the parent for any per-iteration audit children. Three approaches were considered for bead creation: ad-hoc `bd create` with explicit flags, a versioned bd formula via `bd mol pour`, or reusing the built-in `TypeEvent` ("system-internal audit trail beads").

## Decision

Use `bd mol pour formula-drain` with a versioned TOML formula at `dev-flow/.beads/formulas/formula-drain.toml`. The drain bead carries custom type `drain` set via the formula's `[[steps]]` `type` field. Variable substitution (`{{mode}}`, `{{scope}}`, `{{started_at}}`) handles per-run customization.

## Rationale

- deepwiki (`gastownhall/beads`) confirmed the formula schema and that the per-step `type` field maps to `IssueType`; `ensureSubgraphCustomTypes` auto-registers unknown types during pour so the drain bead lands as type `drain` regardless of pre-registration state.
- Formula `version` field enables schema migration without breaking existing drain beads (forward compat).
- `bd mol pour --dry-run` enables testing without side effects (confirmed in `bd mol pour --help`).
- `TypeEvent` semantics ("system-internal audit trail") are conceptually misaligned with operator-initiated drain runs; reusing it would pollute system-event queries.

## Alternatives Considered

**Ad-hoc `bd create` with explicit flags — rejected.** Strengths: no formula infrastructure required; immediate. Weaknesses: no version control for bead structure; label consistency depends on command-line discipline; no dry-run validation path; harder to evolve bead schema.

**Reuse `TypeEvent` (built-in audit type) — rejected.** Strengths: no custom type registration required. Weaknesses: `TypeEvent` semantics are "system-internal audit trail" — conceptually misaligned with operator-initiated runs; would appear alongside system events in bd queries.

## Consequences

**Positive.** Drain bead structure is version-controlled and testable via `--dry-run`. `bd formula list` surfaces the formula before any run. Consistent labels (`drain:{{mode}}`, `phase:run`) enable label-based overlap detection (`drain:*` glob).

**Negative.** bd JSON envelope path (`.id` vs `.data.id`) must be revisited at bd v2.0 upgrade. Formula must be present in `.beads/formulas/` — `/drain init` copy step is required.

**Neutral.** Auto-registration means `/drain init` is for predictability + operator visibility, not a hard correctness gate.

## References

- Spec: `docs/superpowers/specs/2026-05-22-drain-skill-design.md` §Architecture — Drain bead + formula-drain.toml
- Design bead: `fhsk-a67`
- Reference formula: `/Users/sean/gascity/.beads/formulas/mol-witness-patrol.formula.toml` (exemplar)
