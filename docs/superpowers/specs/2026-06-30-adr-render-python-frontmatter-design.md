<!-- markdownlint-disable MD013 -->

# Migrate render-adr + adr-doctor to Python/uv with Starlight frontmatter

**Design bead:** fhsk-cdr
**Date:** 2026-06-30
**Status:** Draft — pending design-reviewer

## Problem

`dev-flow/scripts/render-adr` emits ADR markdown in a **legacy format**: an HTML
comment header, a `# <TITLE>` H1 heading, and a `**Deciders:**` line — but **no
YAML frontmatter**. Downstream consumers that build `docs/adr/*.md` as an
[Astro Starlight](https://starlight.astro.build) content collection **require** a
frontmatter `title:` field on every page. Every ADR `render-adr` generates therefore
fails the Starlight `deploy` check with
`[InvalidContentEntryDataError] title: Required` until hand-fixed.

This was discovered in the homelab repo (issue `hl-386w`) while fixing PR #1290 CI:
four freshly captured ADRs each needed a hand-added frontmatter block and the H1
dropped before the docs build went green. The render script — shared across repos via
the dev-flow plugin cache — is the root cause.

Grounding (context7 `/withastro/starlight`, `reference/frontmatter.md`): the `title`
frontmatter field is **required for every page**, is rendered as the page's H1 at the
top of the page, and is **not** derived from a body heading. Therefore the fix is to
emit `title:` in frontmatter **and drop the body `# TITLE` H1** (otherwise the page
shows two H1s).

Secondary goal (user directive): move dev-flow's ADR tooling **off shell** onto
Python run via `uv` (PEP 723 single-file scripts), consistent with the repo's existing
`uv run --script` scripts.

## Goals

- `render-adr` emits a Starlight-valid ADR: YAML frontmatter with a `title:` field,
  and no body H1.
- `render-adr` and `adr-doctor.sh` are rewritten in Python as PEP 723
  (`uv run --script`) executables backed by importable, unit-tested modules.
- `adr-doctor` gains an invariant that fails when an ADR lacks a frontmatter `title:`
  — a regression guard that runs **without** `bd` (so CI catches it, unlike INV-A22).
- All committed `docs/adr/*.md` are regenerated to the new format with **no
  unintended content change** (verified by a parity harness), and stale slug-drift
  orphans are removed.
- `adr-doctor.sh` is renamed to `adr-doctor` (drops the misleading `.sh`), and all
  references are updated.

## Non-Goals

- Migrating other `dev-flow/scripts/*` shell scripts to Python (deferred to follow-up
  beads).
- Lifting `Date`/`Status`/`Decision`/`Deciders` into frontmatter — **title-only**
  frontmatter this round; those stay as bold body lines.
- Changing the bd-as-source-of-truth model, the ADR formula, or any lifecycle
  semantics in `/adr` / `evolve-adr` / `capture-adrs`.
- Fixing the homelab repo's ADRs directly (cross-repo; happens when homelab bumps the
  plugin cache — see Cross-Repo Impact).
- Changing CI to install `bd`.

## Background / Current State

- `render-adr` (bash, ~213 lines) reads a `decision` bead via `bd show --json`,
  computes status (5-branch rule), slugifies the title, resolves supersession edges,
  and writes `docs/adr/<bd-id>-<slug>.md`. It is idempotent — re-running reproduces the
  file from bd state.
- `adr-doctor.sh` (bash, ~300 lines) is the durable lint over `docs/adr/`, wired into
  `task lint` (and thus CI). It enforces ~13 named invariants. The relevant ones:
  - **INV-A4/A5** `**Decision:** <bd-id>` header present and matches filename; required
    `## Decision` / `## Rationale` / `## Alternatives Considered` body sections.
  - **INV-A13** supersession edge coherence (reads `**Status:** Superseded by`).
  - **INV-A22** `markdown_matches_render`: re-renders each bead and **byte-compares**
    the committed file; drift = fail. **Guarded by `command -v bd`** — skipped in CI
    (CI does not install bd), enforced locally.
  - **INV-A20/A21/A23/A24** bd-description and metadata checks.
- The repo currently has **33** `docs/adr/*.md` but only **32** `decision` beads —
  `fhsk-0cd` has two files (`…-auto-bootstrap.md` and `…-auto-bootstrapping-firs.md`)
  from a slug-algorithm change; one is a stale orphan.
- **`docs/adr/*.md` is NOT in the repo's rumdl gate.** `Taskfile.yaml:lint` runs
  `rumdl check --no-exclude {{.MD_FILES}}` against an **explicit file list**, and
  `MD_FILES` does not include `docs/adr/`. (The `.rumdl.toml` `exclude` patterns only
  apply in directory-scan mode; they have no effect when rumdl is handed explicit
  paths.) So nothing in this repo lints ADR markdown — dropping the body H1 has **no
  rumdl impact here**. ADR files still carry an inline
  `<!-- markdownlint-disable MD013 -->` for the benefit of downstream consumers
  (e.g. the homelab Starlight build) whose own linting may differ.
- Prior art for the target runtime already exists in-repo: `drain-watchdog`,
  `ensure-isolated-workspace`, `drain-worker-launch`,
  `solving-a-bead/scripts/validate-bead` all start with
  `#!/usr/bin/env -S uv run --script` + a `# /// script` PEP 723 metadata block. The
  testable pattern is an importable `_module.py` (e.g. `_muxdriver.py`) plus a thin
  executable wrapper, with pytest under `dev-flow/scripts/tests/` (already in
  `PYTEST_DIRS`).

## Design

### 1. New ADR file format (title-only frontmatter)

```markdown
---
title: "<TITLE>"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:<ID>; do not edit manually; use `/adr update <ID>` -->

**Date:** <DATE>
**Status:** <STATUS>
**Decision:** <ID>
**Deciders:** <DECIDERS>

<BODY>

## Addenda            (only if present)

- <addendum>

## References          (only if body refs or supersession edges exist)

- <merged refs>
```

Rules:

- The frontmatter block is the **first bytes of the file** (`---` on line 1). Remark/
  Starlight require this.
- `title:` is a YAML **double-quoted scalar**. Escape order: backslash first
  (`\` → `\\`), then double-quote (`"` → `\"`). bd titles are single-line, so no
  newline handling is needed.
- The body **`# <TITLE>` H1 is removed**. No other element moves.
- The two HTML comments and the `Date/Status/Decision/Deciders` block follow the
  frontmatter unchanged, so `adr-doctor`'s `**Decision:**` / `**Status:**` greps keep
  matching.

This is the only intentional difference from current output. Everything below the
metadata block (body, addenda, references, the verbatim-body backstop warning for the
literal `\n` escape) is preserved exactly.

### 2. Code structure

| File | Action | Role |
|------|--------|------|
| `dev-flow/scripts/_adr_render.py` | Create | Pure render library. No I/O, no `bd`. |
| `dev-flow/scripts/render-adr` | Rewrite | PEP 723 `uv run --script` wrapper (filename unchanged). |
| `dev-flow/scripts/_adr_doctor.py` | Create | Pure check library over file text + injected bd data. |
| `dev-flow/scripts/adr-doctor` | Create (rename) | PEP 723 `uv run --script` wrapper. Replaces `adr-doctor.sh`. |
| `dev-flow/scripts/adr-doctor.sh` | Delete | Renamed. |
| `dev-flow/scripts/tests/test_adr_render.py` | Create | Unit + golden + format-invariant tests. (The parity harness is dev-time only and NOT committed — see Migration §3.) |
| `dev-flow/scripts/tests/test_adr_doctor.py` | Create | Per-invariant unit tests. |

`_adr_render.py` public surface (illustrative, not binding):

- `slugify(title: str) -> str` — exact port of the bash pipeline: lowercase,
  non-alnum → space, collapse, drop stop-words
  (`a an the for of to in on with`), join with `-`, cut to 60 chars, strip trailing
  `-`. **Must produce byte-identical slugs** so filenames don't churn. **Scope
  caveat:** the bash pipeline (`tr -c 'a-z0-9' ' '`) operates **byte-wise**, while a
  natural Python port (`re.sub(r'[^a-z0-9]', ' ', s)` after `.lower()`) operates
  **char-wise** — for a non-ASCII title the two diverge. bd ADR titles are ASCII in
  practice, so the parity claim is scoped to ASCII; the parity harness (Migration §3)
  diffs old-vs-new filenames per bead and will surface any non-ASCII divergence rather
  than silently mismatching. Port the byte-level behavior if a non-ASCII title appears.
- `yaml_title(title: str) -> str` — escaping per §1.
- `compute_status(status_raw, superseded_by, labels) -> str` — the 5-branch rule
  (Proposed / Superseded by / Rejected / Deprecated / Accepted).
- `render(bead: dict, superseded_by: str|None, supersedes: list[dict]) -> str` — builds
  the full file content string.

`render-adr` wrapper responsibilities (I/O only): parse `<bd-id>`, call
`bd show --json` / `bd dep list … --type=supersedes --json` (incoming + outgoing),
emit the literal-`\n` backstop warning to stderr, call `render(...)`, `mkdir -p
docs/adr`, write `docs/adr/<id>-<slug>.md`, print `render-adr: wrote <path>`. CLI
contract (args, exit codes 0/1/2, stdout/stderr messages) is **unchanged**.

`_adr_doctor.py` separates **pure file-text checks** (decision header, required
sections, frontmatter title, supersession status line) from **bd-backed checks**
(context/consequences sections, status-label coherence, deciders metadata,
render-match). bd-backed checks receive injected data / a small gateway so unit tests
need no live `bd`.

**INV-A22 render-match without the destructive dance.** The current bash INV-A22
re-renders **in place** (overwriting the committed file) then restores it via
`git checkout HEAD` / `jj restore`. The Python port drops that: because `render()` is a
pure function returning the file content as a **string**, the `adr-doctor` wrapper
computes the expected content **in memory** (call the same `bd` fetch the wrapper uses,
then `render(...)`) and string-compares it to the committed file's bytes. No in-place
overwrite, no VCS restore — eliminating the destructive step and its restore-failure
edge cases. (This sidesteps the never-implemented `render-adr --to-stdout` mode the
2026-05-22 ADR-evolution plan once contemplated; the pure `render()` makes it
unnecessary.)

The `adr-doctor` wrapper preserves the existing CLI:
`--explain`, `--changed-only <files…>`, exit codes (0 clean / 1 fail / 2 missing
prereq), and the `FAIL:` / `adr-doctor: all checks passed.` output lines.

### 3. adr-doctor invariants

Port **all** existing invariants with identical semantics and messages:
INV-A2 (skill must not commit), INV-A4/A5 (decision header + sections),
INV-A12 (README present + index sentinels + no `legacy/` subdir),
INV-A13 (supersession edges), INV-A14/A15 (adr-extractor agent frontmatter),
INV-A20/A21 (bd description `## Context` / `## Consequences`),
INV-A22 (`markdown_matches_render`, bd-guarded),
INV-A23 (status/label coherence), INV-A24 (deciders metadata),
plus `hook_executable` and shellcheck-of-hook (shellcheck still applies to the
remaining shell hook `nudge-adr-capture`).

Add **new INV-A25 `frontmatter_title_present`**: every `<bd-id>-<slug>.md` (excluding
`README.md`) MUST begin with a YAML frontmatter block (`---` … `---`) whose first
keys include a non-empty `title:`. Runs in **both** full and `--changed-only` modes and
**without bd**, so CI enforces it. This is the guard that would have caught the
original Starlight failure pre-merge.

### 4. Migration / correction

The new `render-adr` is the migration tool (authoritative, idempotent). Migration is a
deterministic regeneration, not a bespoke correction pass:

1. **Regenerate:** run `render-adr <id>` for every `decision` bead
   (`bd list --all --type=decision --json | jq -r '.[].id'`). Produces 32 new-format
   files.
2. **De-dup / orphan removal:** delete any `docs/adr/*.md` (except `README.md`) that
   does not correspond to a current `render-adr` output filename — this removes the
   stale `fhsk-0cd-…-bootstrapping-firs.md`.
3. **Parity harness (one-shot, dev-time only — NOT committed):** for each bead, render
   with the **old bash** script (from git history) and the **new Python** script and
   assert the unified diff contains only (a) added frontmatter `---` / `title:` / `---`
   lines and (b) a removed `# <TITLE>` line — nothing else. This proves the port is
   behavior-faithful beyond the intended format change. The harness shells out to the
   old bash script, so it **cannot** run after that script is deleted — it is therefore
   run **once during implementation and discarded**, never committed as a pytest. What
   **is** committed and CI-run is `test_adr_render.py`: golden fixtures (fixture bead
   JSON → expected new-format markdown) plus the format-invariant assertions. The
   harness validates the regeneration; the golden fixtures freeze the result.
4. **Commit** the regenerated tree in the same change as the script rewrite.

No separate long-lived "correction script" is warranted: a future format change re-runs
`render-adr` over all beads the same way. If a bulk re-render convenience is wanted
later, it is a trivial `for id in $(bd list …); do render-adr "$id"; done` loop and can
be a follow-up bead, not part of this spec.

### 5. Ripple (reference updates)

- `Taskfile.yaml` — `./dev-flow/scripts/adr-doctor.sh` → `./dev-flow/scripts/adr-doctor`.
  **Do NOT add `docs/adr/*.md` to `MD_FILES`** — keeping ADR markdown out of the repo's
  rumdl gate is the status quo (see Background); the `adr-doctor` invariants, not rumdl,
  govern ADR file shape. Adding it would be unplanned scope and would pull MD041 into
  play.
- `dev-flow/AGENTS.md`, `AGENTS.md` — mentions of `adr-doctor` (prose; update `.sh` if
  the literal filename appears).
- `dev-flow/skills/evolve-adr/SKILL.md` — references to `adr-doctor.sh` and the
  `render-adr <id>` command lines (command name unchanged; only `.sh` references in
  prose need fixing). If any rendered-format example shows the old H1-first layout,
  update it to the frontmatter layout. **Also** fix the `### Codex compatibility`
  paragraph (~line 213): "`render-adr` is a plain bash script. These work in Codex with
  no special glue." is stale after the port — `render-adr`/`adr-doctor` now require
  `uv` on `PATH` (same as the repo's other `uv run --script` tools); update the prose
  to state the `uv` dependency.
- `dev-flow/skills/capture-adrs/SKILL.md` and the `/adr` command — update any literal
  rendered-format snippet to the new layout; command invocations of `render-adr` are
  unchanged.
- Historical `docs/superpowers/specs/*` and `plans/*` are **left as-is** (point-in-time
  records).

### 6. Cross-Repo Impact

The homelab repo consumes `render-adr`/`adr-doctor` through the dev-flow plugin cache
(pinned by commit SHA). It will pick up the new format when it bumps the cache. Its
already-hand-fixed ADRs (frontmatter present) will then re-render consistently; any
that drift surface via its own `adr-doctor`/Starlight build. No action in this repo's
PR. Worth a one-line heads-up in the PR description for homelab maintainers.

## Testing

- **`test_adr_render.py`:**
  - Unit: `slugify` (stop-words, 60-char cut, trailing-dash strip, unicode/punctuation),
    `yaml_title` (embedded `"` and `\`), `compute_status` (all 5 branches).
  - Golden: fixture bead JSON → exact expected markdown (new format), including
    addenda and merged References.
  - Format invariants: output starts with `---\n`, contains exactly one `title:`, no
    body `#` H1, frontmatter title equals bead title.
- **`test_adr_doctor.py`:** synthetic ADR fixtures that trip each invariant (including
  **INV-A25**: a file with no frontmatter, and one with empty `title:`) and verify
  pass on clean fixtures. bd-backed checks tested with injected data.
- **Integration:** `task lint` passes — `adr-doctor` **full pass** over the regenerated
  `docs/adr/` tree (this, not rumdl, is the ADR-shape gate; rumdl's `MD_FILES` does not
  include `docs/adr/`), plus rumdl over its curated `MD_FILES` set and ruff over the new
  `.py`. `task test` passes (new pytest files under `dev-flow/scripts/tests/`).
  `task fmt` clean. The new-format frontmatter presence is enforced by `adr-doctor`
  INV-A25 (bd-free), which runs in CI.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Python port silently changes ADR output beyond frontmatter/H1 | Parity harness diffs old-bash vs new-python per bead, asserting only the two intended deltas; golden fixtures freeze the format. |
| Dropping the body H1 trips a markdown linter (e.g. MD041 "first heading must be top-level") | **No impact in this repo:** `docs/adr/` is not in rumdl's `MD_FILES`, so the repo never lints ADR markdown. For downstream consumers that DO lint (e.g. homelab), markdownlint/rumdl's `front_matter_title` default treats a frontmatter `title:` as satisfying MD041; the inline `<!-- markdownlint-disable MD013 -->` remains, and `MD041` can be added there if a consumer needs it. Starlight itself does not run markdownlint — it requires the frontmatter `title`, which the new format provides. |
| `slugify` port diverges → filename churn / orphaned files | Byte-identical port (ASCII scope — see Design §2 byte-vs-char caveat) asserted by golden slug tests + the parity harness diffing per-bead filenames; orphan-removal step cleans pre-existing drift (`fhsk-0cd`). |
| INV-A22 drift merges silently because CI lacks bd | New bd-free INV-A25 covers the frontmatter regression class in CI; INV-A22 remains the local full-fidelity gate. |
| `uv` unavailable in some execution context | Same risk as existing `uv run --script` scripts already shipped; no new exposure. PEP 723 metadata pins `requires-python`. |

## Open Questions

None outstanding. (Frontmatter scope, runtime style, migration approach, and the
`adr-doctor.sh` → `adr-doctor` rename are all resolved.)
<!-- adr-capture: sha256=c64b3d0d8731c1bf; session=cli; ts=2026-06-30T15:49:47Z; adrs=fhsk-slp,fhsk-nlw,fhsk-bmn -->
