<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-buu; do not edit manually; use `/adr update fhsk-buu` -->

# Use bd create --type drain for drain bead creation (not bd mol pour)

**Date:** 2026-05-24
**Status:** Accepted
**Decision:** fhsk-buu
**Deciders:** Sean Brandt (@seanb4t)

## Context

Each `/drain` invocation creates a typed audit-trail bead carrying the run's
`mode`/`scope`/`started_at` metadata, accumulating lesson and rejection notes,
and serving as the parent for the run. ADR `fhsk-rqh` chose `bd mol pour
formula-drain` (a versioned TOML formula) for this, on the premise — sourced
from deepwiki — that a formula step's `type` field maps to the created issue's
type and that unknown types auto-register during pour.

That premise was falsified by reading the bd source (`gastownhall/beads`
checkout `v1.0.4-215`, the version in use plus 215 commits) and by end-to-end
reproduction against bd 1.0.4.

## Decision

Create the drain bead directly with `bd create --type drain`. `/drain init`
registers the `drain` custom type via `bd config set types.custom`; no formula
file is shipped or copied. Labels are passed on the create call
(`--label phase:run --label "drain:$MODE"`); resume metadata is set with
post-create `bd update --set-metadata`.

## Rationale

Verified against bd source and by reproduction:

- `cmd/bd/cook.go` `stepTypeToIssueType()` is a closed switch over the five
  built-in types (`task`/`bug`/`feature`/`epic`/`chore`) with `default →
  TypeTask`. It never consults `types.custom`, so a formula step's `type =
  "drain"` is silently downgraded to `task` on every pour. No formula syntax
  avoids this.
- `cmd/bd/cook.go` `substituteStepVars()` substitutes only `Title`,
  `Description`, `Notes`, and `Gate.*` — never `Labels` or `Metadata`. So
  `drain:{{mode}}` lands as a literal, unsubstituted label.
- `bd mol pour` always creates a root molecule container plus the step beads
  (`created: 2`), leaving an orphan wrapper epic the harness never tracked.
- `bd create --type drain` honors `types.custom` (fails loudly with `invalid
  issue type` if unregistered), returns a flat top-level `.id`, creates exactly
  one bead, and stores shell-resolved labels. Confirmed end-to-end: the drain
  bead lands as `issue_type=drain`, status `in_progress`, correct labels,
  parent, and all three `drain_*` metadata keys, and is found by the pre-flight
  overlap scan via `bd list --type=drain`.

## Alternatives Considered

**Keep `bd mol pour` with post-pour workarounds — rejected.** Re-stamp the type
via `bd update --type drain`, capture the drain-root from
`.id_mapping["formula-drain.drain-root"]`, set the real label, and close the
orphan wrapper epic. Functional, but layers four permanent workarounds over bd
limitations across three mode blocks for zero benefit on a single-step formula.

**Fix bd upstream — out of scope.** The custom-type downgrade is a genuine bd
limitation worth reporting, but it is present even at `v1.0.4-215` and cannot
gate the drain harness. Tracked separately.

## Consequences

**Positive.** One bead per run, correct custom type, no orphan wrapper, real
labels, and a simpler `/drain init` (register type only). The harness no longer
depends on a formula file being present in the consumer repo.

**Negative.** Diverges from the `formula-adr` / `bd mol pour` pattern still used
by `/adr` and `capture-adrs` — which carry the *same* bd-1.0.4 incompatibilities
(custom-type downgrade, unsubstituted labels, wrapper epic, and `bd show --json`
array parsing in their command bodies). That shared breakage is tracked as a
separate follow-up.

**Neutral.** `bd show --json` returns a single-element array with the type under
`issue_type` (not `type`); every `jq` read in the harness uses `.[0].<field>`.
This fix is required regardless of the create-vs-pour choice.

## References

- Supersedes: fhsk-rqh
