<!-- markdownlint-disable MD013 -->

# `mermaid`: A Diagram Authoring, Lint, and Render Skill for dev-flow

**Date:** 2026-05-30
**Status:** Proposed
**Deciders:** Sean Brandt (`@seanb4t`)
**Design bead:** `fhsk-80b`
**Supersedes:** —

## Overview

Add a `mermaid` skill to the `dev-flow` plugin that helps an agent (or human) **author correct Mermaid diagrams, validate them, and render them to image formats**. The skill is three pillars:

1. **Authoring guidance** — which diagram type to use when, when to split a diagram, and a catalog of common mistakes (seeded from real failures), so diagrams are right the first time.
2. **Lint / validate** — a fast, browser-free syntax + structural check of every diagram embedded in markdown (or standalone), with clear line-anchored diagnostics and optional autofix.
3. **Render** — produce `svg` / `png` / `pdf` from a diagram or from the diagrams embedded in a markdown file.

The skill is deliberately thin orchestration over two adopted, best-in-class external tools — it does **not** re-implement a Mermaid parser or renderer. Its original, load-bearing content is the authoring guidance plus the conventions that wire the tools into the dev-flow workflow.

## Goals

- Prevent the recurring class of Mermaid mistakes observed in real use (see Grounding) — primarily *structural* errors in flowchart-style diagrams, not just gross syntax.
- Make validation **browser-free and portable**, so it runs anywhere an agent runs (Claude Code, Codex, CI) without a 1.7 GB Puppeteer/Chromium dependency.
- Make rendering to `svg`/`png`/`pdf` available **without a local install**, via `bunx`.
- Integrate as a discoverable dev-flow skill that `brainstorming` and `writing-plans` can point at when a spec/plan benefits from a diagram.
- Stay honest about the boundary between what tooling can catch (syntax, structural) and what only human discipline can catch (a diagram that is valid but *wrong*).

## Non-goals

- **Not** a Mermaid parser/renderer of our own. We adopt existing tools and own the guidance + conventions.
- **Not** tied to bd dependency graphs. An earlier framing assumed the skill would diagram bead dependency graphs; that is explicitly out of scope. This is a general-purpose diagramming skill.
- **Not** an imposed CI gate on *consumers*. This is a marketplace repo; we ship a capability and an opt-in recipe, we do not own the CI where the skill is installed (see "CI and the marketplace boundary").
- **Not** a visual-editing or diagram-from-prose generation feature.

## Grounding

### Failure taxonomy (holomush, ~20 issues)

A survey of recent `holomush/holomush` issues mentioning Mermaid shows the mistakes are almost entirely **semantic / structural drift in dependency-graph (flowchart) diagrams embedded in implementation plans**, not parser-level syntax errors. Representative classes:

| holomush issue | Failure class | Mechanically catchable? |
|---|---|---|
| #1020 | Phantom node — `T23 --> T27` left dangling after `T27` was split into `T27a`/`T27b`; Mermaid renders a disconnected box | Partially (undeclared/dangling reference) |
| #1010 | Reversed edge — `T6 --> T5` where prose says "Task 6 requires Task 5" | No — requires a source of truth |
| #2053 | Diagram contradicts the critical-path prose | No — cross-artifact semantic |
| #1932 | Edge present in the gate table but missing from the diagram (and vice versa) | No — cross-artifact semantic |
| #2549 | Critical-path nodes missing their `style`/`class` declarations | **Yes** — dangling style target |
| #2536 | Redundant/duplicate edge | **Yes** — duplicate edge |

Root cause: the dependency graph was hand-duplicated across the task table, the gate table, the critical-path prose, **and** the diagram — four copies that drift. This is a Rule 4 (no duplicate state) violation in the wild. dev-flow already mitigates the dependency-graph case by making bd dep edges the source of truth, which is why this skill does **not** re-introduce diagram-as-graph-of-record. The taxonomy instead defines *what good authoring + lint must catch or warn about*.

### Tool ecosystem (deepwiki + exa)

- **`mermaid-cli` (`mmdc`)** natively ingests markdown (`-i file.md`), extracts every ` ```mermaid ` **and** `:::mermaid` block, and validates-by-rendering. It has **no validate-only mode** and **always requires Puppeteer/Chromium** — Mermaid's Jison parser is coupled to rendering. It exits non-zero if any block fails and continues past a bad block. Output formats: `svg`, `png`, `pdf`, or rewritten `md`. Confirmed empirically via `bunx @mermaid-js/mermaid-cli --help` and against the mermaid-cli source.
- A family of **browser-free validators** built for the AI-generated-diagram problem:
  - **`probelabs/maid`** (npm `@probelabs/maid`, **ISC**): from-scratch Chevrotain parser, "render guarantee", `bunx`-able, exit `0`/`1`, autofix (`--fix`), line/column/caret/hint diagnostics, markdown + directory input, optional MCP server (`validate_mermaid`). Deep parsers cover **flowchart / pie / sequence**; other types are detected as "unknown" and **pass through as valid** (no false positive). ~5 MB, no Chromium.
  - **`tetrafolium/mermaid-check`** (Go, **Apache-2.0**): 21+ diagram types with semantic validation (undefined-reference, duplicate-identifier, strict-mode style), markdown extraction, line numbers. No browser, but a Go binary (not `bunx`).
  - **`suwa-sh/md-mermaid-lint`** (**MIT**) and **`Zabaca/mermaid-validate`** (no license — *not adoptable*): official-parser + jsdom validators.
- The existing **`documentation-generation:mermaid-expert`** agent (`wshobson/claude-code-workflows`, **MIT**) is a 43-line haiku agent with no concrete substance (no syntax reference, lint, or render). Useful only as diagram-type-selection framing; not worth lifting wholesale.

### Empirical confirmation (`maid` v1.0.1)

`bunx -y @probelabs/maid` on a flowchart with `style D …` (D undefined) and an `X -> Y` arrow emitted:

- `FL-STYLE-TARGET-UNKNOWN: Unknown node id 'D' in style statement` (warning, with line:col, caret, hint) — i.e. holomush #2549, caught mechanically.
- `FL-ARROW-INVALID: Invalid arrow syntax: -> (use --> instead)` (error, autofixable).

A `classDiagram` (outside its deep parsers) returned `Valid` (exit 0) — safe pass-through. This is the decisive evidence: `maid` catches the holomush structural classes in flowcharts (its strongest area, which is exactly where holomush bled) and does not false-error on diagram types it does not deeply parse.

Grounding traces for the above are recorded as `bd note` entries on `fhsk-80b`.

## Decisions

### D1 — Build the guidance, adopt the engines

The skill's original content is the **authoring guidance**. Linting and rendering are orchestration over adopted tools; no Mermaid parser/renderer is written here.

### D2 — Lint via `maid`; render-validate other types via `mmdc`

- Primary lint engine: **`@probelabs/maid`** (ISC), run via `bunx`. Deep structural lint on flowchart / pie / sequence; autofix available.
- For diagram types `maid` passes through (class / state / ER / gantt / C4 / …), an **optional `mmdc` render pass** is the catch-all that surfaces gross syntax errors. This reuses the renderer the skill already needs.
- No hand-rolled structural linter.

### D3 — Render via `@mermaid-js/mermaid-cli` (`mmdc`) over `bunx`, no install

- Render to `svg` / `png` / `pdf` via `bunx -y @mermaid-js/mermaid-cli` (fallback to `mmdc` on `PATH`, then `npx`). No persistent install.
- `mmdc` routes **all** output through Puppeteer/headless Chromium. The skill documents the `PUPPETEER_EXECUTABLE_PATH` escape hatch (point at a system Chrome) and degrades with a clear message when no browser is reachable. Validation does **not** depend on this path (that is `maid`'s job).

### D4 — Consume via `bunx` everywhere + optional `maid` MCP

- `bunx` invocations are the portable baseline (Claude Code, Codex, CI).
- The skill documents the **optional** `maid` MCP server (`claude mcp add -- npx -y @probelabs/maid mcp`) for an in-conversation validate/autofix loop during authoring in Claude Code.
- The plan adds the `maid` MCP to this repo's own root `.mcp.json` (alongside `context7` and `terraform`) for dogfooding while authoring here — a deliverable, not a current fact. Consumers are **not** required to run any MCP; `bunx` always works.

### D5 — CI and the marketplace boundary

This repo ships a skill; it does not own the CI where the skill is installed. Therefore:

- **No imposed gate on consumers.** The skill's docs include an opt-in recipe ("wire `bunx -y @probelabs/maid <paths>` into your pre-commit / Taskfile / CI") that a consumer adopts on their own, the same way `dev-flow` ships `adr-doctor.sh` for the consumer to wire.
- **Self-dogfood (optional, low-cost):** because validation is now Chromium-free, this repo MAY add a `maid`-lint step to its own `task lint` over its own tracked ` ```mermaid ` blocks. (Today that is essentially just `docs/dev-flow-pipeline.md`.)

### D6 — Scope boundary stated explicitly

Two holomush failure classes are **not** mechanically lintable without the source-of-truth tie-in that is out of scope (Non-goals): reversed edge *direction* (#1010) and diagram-vs-prose *contradiction* (#2053, #1932). These are addressed by the **authoring guidance** as human discipline, and the common-mistakes reference labels them as such rather than implying lint covers them.

### D7 — A skill, not just a doc

The deliverable is a discoverable dev-flow skill (`SKILL.md` + references), not a loose reference page, because the authoring guidance is real, reusable value and the skill surface is how an agent finds and applies it.

## Architecture and interfaces

### Layout

```text
dev-flow/skills/mermaid/
├── SKILL.md                    # authoring guidance + when-to-use + lint/render workflow + degradation + CI recipe
└── references/
    ├── diagram-types.md        # per-type syntax + "which diagram when" selection guide (table of contents at top)
    └── common-mistakes.md      # traps catalog; each item tagged maid-catches (code) vs human-discipline
```

No gateway script in v1: lint and render are documented `bunx` one-liners (the homelab "document the invocation" idiom), keeping the skill's surface to guidance + conventions. A thin wrapper script is an explicit open question (see Risks) if render ergonomics later justify it.

### Files

**Created** (the skill itself):

- `dev-flow/skills/mermaid/SKILL.md`
- `dev-flow/skills/mermaid/references/diagram-types.md`
- `dev-flow/skills/mermaid/references/common-mistakes.md`

**Modified** (integration + dogfooding):

- `dev-flow/skills/brainstorming/SKILL.md` — one-line pointer to the `mermaid` skill
- `dev-flow/skills/writing-plans/SKILL.md` — same pointer
- `Taskfile.yaml` — add `dev-flow/skills/mermaid/SKILL.md` to the `MD_FILES` rumdl gate; wire the lint smoke test into the test surface
- `.mcp.json` (repo root) — add the optional `maid` MCP entry for dogfooding
- `dev-flow/AGENTS.md` — *optional* — list the skill in the dev-flow skill inventory if it warrants a workflow-line reference (it is a tool/reference skill, not a Rule 1–7 workflow skill, so this may be omitted)

### SKILL.md frontmatter (contract)

- `name: mermaid`
- `description`: third person, "Use when…", names the triggers (authoring/creating/validating/linting/rendering Mermaid diagrams; flowcharts, sequence, etc.) per CSO; describes *when*, not the internal workflow.
- `allowed-tools`: `Read`, `Grep`, `Glob`, and the `bunx`/`mmdc`/`maid` Bash invocation patterns. (Exact allow-list finalized in the plan.)

### Command shapes (interfaces)

```bash
# Lint a markdown file, a directory (recursive), or stdin
bunx -y @probelabs/maid path/to/doc.md
bunx -y @probelabs/maid docs/
cat diagram.mmd | bunx -y @probelabs/maid -

# Autofix common (AI-generated) mistakes
bunx -y @probelabs/maid --fix path/to/doc.md

# Render: a standalone diagram, or every block in a markdown file
bunx -y @mermaid-js/mermaid-cli -i diagram.mmd -o diagram.svg
bunx -y @mermaid-js/mermaid-cli -i doc.md -e png            # per-block artefacts
bunx -y @mermaid-js/mermaid-cli -i diagram.mmd -o out.pdf

# Render with a system Chrome when Puppeteer's bundled browser is unavailable
PUPPETEER_EXECUTABLE_PATH=/path/to/chrome bunx -y @mermaid-js/mermaid-cli -i diagram.mmd -o out.svg
```

Exit-code contract relied upon: `maid` exits `0` on no errors (including "no diagrams found") and `1` on at least one error; warnings do not fail. `mmdc` exits non-zero if any block fails to render.

### Traps catalog mapping (contract excerpt)

`common-mistakes.md` maps each failure to its handling:

| Trap | Example | Handling |
|---|---|---|
| Bad arrow | `A -> B` | `maid` `FL-ARROW-INVALID` (error, autofixable) |
| Dangling style target | `style D …`, `D` undefined | `maid` `FL-STYLE-TARGET-UNKNOWN` (warning) |
| Phantom node after rename/split | `T23 --> T27` (now `T27a`) | `maid` flags the dangling reference; **direction/intent is human discipline** |
| Reversed edge direction | `T6 --> T5` vs "6 requires 5" | **human discipline** (not lintable here) |
| Diagram vs prose contradiction | critical-path text ≠ edges | **human discipline** |
| Overcrowding | one mega-diagram | **authoring guidance** — when to split |

## dev-flow integration

- `brainstorming` and `writing-plans` gain a one-line pointer: "When a spec or plan benefits from a diagram, use the `mermaid` skill; run `bunx -y @probelabs/maid` on the file before committing." No auto-fire, no gate.
- The Codex wrapper picks the skill up automatically through the existing `plugins/dev-flow/skills` symlink; the `bunx` baseline keeps it functional in Codex.
- Attribution: the skill credits `@probelabs/maid` (ISC) and `@mermaid-js/mermaid-cli`, and notes diagram-type-selection framing inspired by `mermaid-expert` (MIT).

## Testing

- A smoke test asserting `bunx -y @probelabs/maid` flags a known-bad fixture (e.g., the dangling-style flowchart) and passes a known-good one, gated on network/`bunx` availability (skip with a clear reason when offline), added to `Taskfile` test wiring. Because the assertion keys on `maid`'s error *codes* / messages (e.g. `FL-STYLE-TARGET-UNKNOWN`), the test is version-sensitive — the plan resolves this together with the version-pinning open question (see Risks) by pinning the `maid` version the test asserts against.
- `rumdl` lint on `SKILL.md` and the references; `SKILL.md` added to the curated `MD_FILES` gate.
- The skill is reference-and-tool, not a discipline-enforcing skill, so behavioral evals are minimal; a small number of triggering evals MAY be added to `dev-flow/evals`.

## Risks and open questions

| Risk / question | Disposition |
|---|---|
| `maid` deep coverage is flowchart/pie/sequence only | Accepted: that is where holomush bled; other types get the `mmdc` render-validate catch-all (D2). |
| `bunx`/network unavailable in a sandbox | Lint/render degrade with a clear message; tests skip with a reason. |
| `mmdc` needs Chromium even for SVG | Documented; `PUPPETEER_EXECUTABLE_PATH` escape hatch; render is best-effort, validation is not affected. |
| Pinning vs floating tool versions | Open: pin `@probelabs/maid@<v>` / `@mermaid-js/mermaid-cli@<v>` in the documented commands for reproducibility, vs float for freshness. Decide in the plan. |
| Thin wrapper script later | Open: add `scripts/mermaid` only if render ergonomics (format/out/block selection, browser detection) justify it; v1 ships documented `bunx` one-liners. |
| `maid` MCP in this repo's `.mcp.json` | Additive and optional; `bunx` remains the portable path for consumers. |

## References

- Design bead `fhsk-80b` (grounding traces).
- `holomush/holomush` issues: #1020, #1010, #2053, #1932, #2549, #2536 (Mermaid failure taxonomy).
- `probelabs/maid` (ISC) — browser-free Mermaid validator + autofix + MCP.
- `tetrafolium/mermaid-check` (Apache-2.0) — broad-coverage Go validator (alternative).
- `@mermaid-js/mermaid-cli` (`mmdc`) — renderer; markdown ingestion confirmed via `--help` and deepwiki.
- `wshobson/claude-code-workflows` `documentation-generation:mermaid-expert` (MIT) — diagram-type framing only.
- `dev-flow/AGENTS.md` Rules 1, 4, 7 (structure-in-specs, no-duplicate-state, grounding-before-design).
