---
title: "Adopt @probelabs/maid as the primary Mermaid lint engine"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-4bi; do not edit manually; use `/adr update fhsk-4bi` -->

**Date:** 2026-05-30
**Status:** Accepted
**Decision:** fhsk-4bi
**Deciders:** Sean Brandt

## Context

The `mermaid` skill needs a lint/validate pillar. `mermaid-cli` (`mmdc`) has no validate-only mode and always requires Puppeteer/Chromium (~1.7 GB). The holomush failure taxonomy shows the structural errors that matter — dangling style targets, phantom nodes, duplicate edges — occur in flowchart diagrams, exactly where a browser-free alternative can provide deep coverage. Empirical testing confirmed `@probelabs/maid` catches the holomush structural classes and safely passes through diagram types it does not deeply parse.

## Decision

Use `@probelabs/maid` (ISC) as the primary lint engine via `bunx`, with an optional `mmdc` render-validate pass as the catch-all for diagram types maid passes through (class / state / ER / gantt / C4).

## Rationale

- maid empirically caught both holomush structural failure classes (`FL-STYLE-TARGET-UNKNOWN` for #2549, `FL-ARROW-INVALID`) in a live test, with line/column/caret diagnostics and autofix.
- Browser-free operation satisfies the portability constraint (Claude Code, Codex, CI) without a Chromium dependency.
- Safe pass-through on unknown types (a `classDiagram` returned exit 0) means no false positives on the diagram types it does not deeply parse.
- The `mmdc` render pass as a secondary catch-all handles gross syntax errors in types maid passes through, reusing the renderer already needed for the render pillar.

## Alternatives Considered

- **`@probelabs/maid` (ISC, Chevrotain parser) — chosen.** Browser-free (~5 MB), `bunx`-able, exit 0/1, autofix (`--fix`), line/column/caret diagnostics, optional MCP server, render-guarantee, safe pass-through on unknown types. Weakness: deep coverage only on flowchart / pie / sequence.
- **`tetrafolium/mermaid-check` (Apache-2.0, Go) — rejected.** 21+ diagram types with semantic validation (undefined-reference, duplicate-identifier, strict mode), no browser, line numbers; but a Go binary, not `bunx`-able, incompatible with the portable-baseline requirement.
- **Hand-rolled structural linter (Python) — rejected.** Full control, no external dependency; but reimplements a Mermaid parser (fragile, maintenance burden), violates the "adopt engines, own the guidance" principle, and does not scale across diagram types.
- **`mmdc` render-validate only (no separate lint engine) — rejected.** Single authoritative tool; but always requires Chromium (~1.7 GB), has no validate-only mode, breaks portability, and cannot run in sandboxed/offline environments.

## Consequences

**Positive.** Validation runs anywhere `bunx` runs — no Chromium installation. Autofix (`--fix`) closes the AI-generated-diagram feedback loop for common errors. The optional maid MCP server enables an in-conversation validate/autofix loop during authoring in Claude Code.

**Negative.** maid's deep coverage is limited to flowchart / pie / sequence; class / state / ER / gantt / C4 diagrams only get render-validate coverage via `mmdc`. The test suite is version-sensitive — it asserts against maid's specific error codes (e.g. `FL-STYLE-TARGET-UNKNOWN`), requiring version pinning.

**Neutral.** `tetrafolium/mermaid-check` remains a documented alternative for consumers who need broader semantic coverage and can tolerate a Go install.
