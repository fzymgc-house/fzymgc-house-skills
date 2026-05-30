# Mermaid Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use dev-flow:subagent-driven-development (recommended) or dev-flow:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `dev-flow/skills/mermaid` skill that teaches correct Mermaid authoring and orchestrates browser-free lint (`@probelabs/maid`) plus multi-format render (`@mermaid-js/mermaid-cli`), wired into the dev-flow workflow.

**Architecture:** A reference-and-tool skill. Original content is authoring guidance (`SKILL.md` + two reference files); lint and render are documented `bunx` one-liners over two adopted external tools (no parser/renderer of our own). A network-gated pytest smoke test pins and characterizes `maid`'s behavior; small edits wire the skill into the repo's lint gate, MCP config, and the brainstorming/writing-plans pointers.

**Tech Stack:** Markdown (skill + references), `@probelabs/maid` (ISC, npm, browser-free Mermaid validator + autofix), `@mermaid-js/mermaid-cli`/`mmdc` (renderer), `bun`/`bunx`, pytest (uv), rumdl, Taskfile.

**Spec:** `docs/superpowers/specs/2026-05-30-mermaid-skill-design.md` — authoritative for design decisions D1–D7 and the scope boundary.

**Version pins (resolves the spec's open question):** the smoke test asserts against **`@probelabs/maid@1.0.1`** (codes `FL-STYLE-TARGET-UNKNOWN`, `FL-ARROW-INVALID` verified on that version). User-facing `SKILL.md` commands use the **major-pinned** `@probelabs/maid@1` and `@mermaid-js/mermaid-cli@11` so consumers get patches without surprise majors.

**Note on doc tasks:** Tasks 1–3 produce prose documents. Each task specifies the file's required frontmatter, section list, and the *load-bearing contracts* that must appear verbatim (command shapes, tables, error-code names). The implementer authors the connecting explanatory prose; the contracts are not optional and not paraphrasable. Verification for doc tasks is `rumdl check` passing plus a presence check of the required sections/contracts.

---

## File Structure

**Created:**

- `dev-flow/skills/mermaid/SKILL.md` — entry: authoring overview, when-to-use pointers, lint + render workflows, degraded-mode, CI opt-in recipe, attribution. One responsibility: be the discoverable surface and the workflow reference.
- `dev-flow/skills/mermaid/references/diagram-types.md` — "which diagram when" selection guide + minimal per-type syntax. Loaded on demand.
- `dev-flow/skills/mermaid/references/common-mistakes.md` — traps catalog mapping each failure to `maid` code vs human discipline. Loaded on demand.
- `tests/test_mermaid_skill.py` — hermetic structure checks (always run) + network-gated `maid` characterization (skips without `bun`).

**Modified:**

- `Taskfile.yaml` — add the three new markdown files to the `MD_FILES` rumdl gate.
- `.mcp.json` (repo root) — add the optional `maid` MCP server entry.
- `dev-flow/skills/brainstorming/SKILL.md` — one-line pointer to the `mermaid` skill.
- `dev-flow/skills/writing-plans/SKILL.md` — one-line pointer to the `mermaid` skill.

**Dependency order:** Task 1 → (Tasks 2, 3 parallel) → Task 4 (tests reference the skill files) → Task 5 (MD_FILES gate needs the files to exist). Tasks 6 and 7 are independent of 1–5 and may land any time.

---

### Task 1: Create the skill scaffold and SKILL.md

**Files:**

- Create: `dev-flow/skills/mermaid/SKILL.md`

- [ ] **Step 1: Create the directory and SKILL.md with this frontmatter (verbatim contract)**

```yaml
---
name: mermaid
description: >-
  Author, validate, and render Mermaid diagrams. Use when creating or editing a
  Mermaid diagram (flowchart, sequence, class, state, ER, gantt, C4, etc.) in
  markdown or a .mmd file, when a diagram fails to render or looks wrong, or when
  asked to lint/validate or export a diagram to svg/png/pdf.
allowed-tools:
  - Read
  - Grep
  - Glob
  - "Bash(bunx -y @probelabs/maid*)"
  - "Bash(bunx -y @mermaid-js/mermaid-cli*)"
  - "Bash(mmdc*)"
  - "Bash(npx -y @probelabs/maid*)"
  - "Bash(npx -y @mermaid-js/mermaid-cli*)"
metadata:
  author: fzymgc-house
---
```

The `description` states *when* to use the skill (CSO), not the internal workflow — do not summarize the lint/render steps in it.

- [ ] **Step 2: Write the body with exactly these sections**

Required sections (author prose; the fenced command blocks and the exit-code lines are verbatim contracts):

1. `# Mermaid Diagrams` + a one-paragraph Overview. Core principle: *validation is browser-free and cheap (maid); rendering needs a browser (mmdc) — validate always, render when you need an image.*
2. `## Choosing a diagram type` — one short paragraph + `See [references/diagram-types.md](references/diagram-types.md)`.
3. `## When to split a diagram` — 4–6 bullets (one concept per diagram; prefer subgraphs or separate linked diagrams over one mega-diagram; a node/edge count past ~25/40 is a smell). No tool enforces this — it is authoring judgment.
4. `## Lint / validate` — contract block:

   ````markdown
   ```bash
   # Validate every diagram in a markdown file, a directory (recursive), or stdin
   bunx -y @probelabs/maid@1 path/to/doc.md
   bunx -y @probelabs/maid@1 docs/
   cat diagram.mmd | bunx -y @probelabs/maid@1 -

   # Auto-fix common (AI-generated) mistakes in place
   bunx -y @probelabs/maid@1 --fix path/to/doc.md
   ```
   ````

   Then state the exit-code contract verbatim: `maid exits 0 when there are no errors (including when no diagrams are found) and 1 when at least one error is present; warnings do not change the exit code.` Note coverage: *deep structural checks cover flowchart, pie, and sequence; other types pass through as valid (no false positives) — use the render pass below to surface their syntax errors.*
5. `## Render (svg / png / pdf)` — contract block:

   ````markdown
   ```bash
   # A standalone diagram
   bunx -y @mermaid-js/mermaid-cli@11 -i diagram.mmd -o diagram.svg
   bunx -y @mermaid-js/mermaid-cli@11 -i diagram.mmd -o diagram.pdf

   # Every diagram embedded in a markdown file (per-block artefacts)
   bunx -y @mermaid-js/mermaid-cli@11 -i doc.md -e png

   # When Puppeteer's bundled Chromium is unavailable, point at a system Chrome
   PUPPETEER_EXECUTABLE_PATH=/path/to/chrome \
     bunx -y @mermaid-js/mermaid-cli@11 -i diagram.mmd -o diagram.svg
   ```
   ````

   State: *mmdc routes all output (even svg) through headless Chromium; if no browser is reachable it fails with a Puppeteer error — that affects rendering only, not validation.*
6. `## Common mistakes` — one paragraph + `See [references/common-mistakes.md](references/common-mistakes.md)`.
7. `## Use it in CI / pre-commit (optional)` — opt-in recipe block:

   ````markdown
   ```bash
   # Pre-commit or CI: fail the build if any tracked diagram is invalid
   bunx -y @probelabs/maid@1 docs/ README.md
   ```
   ````

   State that this is opt-in for the consumer's own pipeline; this repo ships the capability, not a gate.
8. `## Degraded mode` — 3 bullets: no `bunx`/network → lint and render unavailable, say so plainly; no browser → render unavailable, lint still works; unknown diagram type → maid passes it through, rely on the render pass.
9. `## Optional: maid MCP` — `claude mcp add -- npx -y @probelabs/maid mcp` for an in-conversation validate/fix loop in Claude Code; note `bunx` is the portable fallback.
10. `## Attribution` — credits: `@probelabs/maid` (ISC), `@mermaid-js/mermaid-cli`; diagram-type framing inspired by the MIT `mermaid-expert` agent.

- [ ] **Step 3: Verify the body is under 500 lines and lint passes**

Run: `rumdl check --no-exclude dev-flow/skills/mermaid/SKILL.md && wc -l dev-flow/skills/mermaid/SKILL.md`
Expected: rumdl reports no issues; line count < 500.

- [ ] **Step 4: Commit**

Commit using VCS-appropriate commands per `references/vcs-preamble.md`. Message: `feat(mermaid): add skill SKILL.md (authoring + lint/render workflow)`.

---

### Task 2: Write references/diagram-types.md

**Files:**

- Create: `dev-flow/skills/mermaid/references/diagram-types.md`

- [ ] **Step 1: Create the file with a table of contents (required because it exceeds 100 lines)**

First section `## Contents` listing the sections below.

- [ ] **Step 2: Write the selection guide as this contract table**

A `## Which diagram when` table with columns `Diagram | Mermaid keyword | Use when` covering at least: flowchart (`flowchart`/`graph`) — process / logic / decision / dependency; sequence (`sequenceDiagram`) — interactions / API / temporal ordering; class (`classDiagram`) — data model / OO relationships; state (`stateDiagram-v2`) — lifecycles / state machines; ER (`erDiagram`) — database schema; gantt (`gantt`) — timelines; pie (`pie`) — proportions; journey (`journey`) — user experience; C4 / architecture (`C4Context` / `architecture-beta`) — system structure; gitGraph (`gitGraph`) — branch history; timeline (`timeline`) — chronology.

- [ ] **Step 3: Add a minimal valid syntax skeleton per common type**

For flowchart, sequence, class, state, ER, gantt: a short fenced ` ```mermaid ` example (5–10 lines each) that renders. These are reference snippets the author can copy and adapt.

- [ ] **Step 4: Add a `## Validation coverage` note**

State which types `maid` deep-parses (flowchart, pie, sequence) vs. which rely on the `mmdc` render pass (everything else), cross-linking `common-mistakes.md` and `SKILL.md`'s lint section.

- [ ] **Step 5: Verify lint passes**

Run: `rumdl check --no-exclude dev-flow/skills/mermaid/references/diagram-types.md`
Expected: no issues.

- [ ] **Step 6: Commit**

Message: `feat(mermaid): add diagram-types reference (selection + syntax)`.

---

### Task 3: Write references/common-mistakes.md

**Files:**

- Create: `dev-flow/skills/mermaid/references/common-mistakes.md`

- [ ] **Step 1: Create the file with a `## Contents` table of contents**

- [ ] **Step 2: Write the traps catalog as this contract table (verbatim columns + the maid codes)**

A `## Traps` table with columns `Trap | Example | Handling`:

| Trap | Example | Handling |
|---|---|---|
| Invalid arrow | `A -> B` | `maid` `FL-ARROW-INVALID` (error; autofixable with `--fix`) |
| Dangling style/class target | `style D fill:#f00` where `D` is undefined | `maid` `FL-STYLE-TARGET-UNKNOWN` (warning) |
| Phantom node after rename/split | `T23 --> T27` after `T27` became `T27a`/`T27b` | `maid` flags the dangling reference; the *correct* target is human judgment |
| Reversed edge direction | `T6 --> T5` when "Task 6 requires Task 5" | **human discipline** — not mechanically lintable |
| Diagram contradicts prose | critical-path text lists edges the diagram lacks | **human discipline** — not mechanically lintable |
| Overcrowding | one diagram with 40+ nodes | **authoring guidance** — split (see SKILL.md "When to split") |

- [ ] **Step 3: Write the boundary section**

A `## What lint cannot catch` section that states plainly: reversed direction and diagram-vs-prose contradiction are *semantic* and require a source of truth this skill does not consult (per spec Non-goals / D6); the defense is authoring discipline — restate the dependency in prose and the diagram and read them against each other.

- [ ] **Step 4: Write the autofix note**

A `## Autofix` section: `bunx -y @probelabs/maid@1 --fix <file>` corrects common AI-generated mistakes (e.g. `->` → `-->`); review the diff — autofix is safe-by-default but should be inspected.

- [ ] **Step 5: Verify lint passes**

Run: `rumdl check --no-exclude dev-flow/skills/mermaid/references/common-mistakes.md`
Expected: no issues.

- [ ] **Step 6: Commit**

Message: `feat(mermaid): add common-mistakes reference (traps + boundary)`.

---

### Task 4: Smoke test — structure checks + maid characterization

**Files:**

- Create: `tests/test_mermaid_skill.py`

- [ ] **Step 1: Write the failing structure tests first**

```python
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "dev-flow" / "skills" / "mermaid"
SKILL = SKILL_DIR / "SKILL.md"
DIAGRAM_TYPES = SKILL_DIR / "references" / "diagram-types.md"
COMMON_MISTAKES = SKILL_DIR / "references" / "common-mistakes.md"

MAID = "@probelabs/maid@1.0.1"


def test_skill_files_exist() -> None:
    for path in (SKILL, DIAGRAM_TYPES, COMMON_MISTAKES):
        assert path.is_file(), f"missing {path}"


def test_skill_frontmatter_and_contracts() -> None:
    text = SKILL.read_text()
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    assert "name: mermaid" in text
    assert "description:" in text
    # load-bearing command contracts must be present
    assert "bunx -y @probelabs/maid@1" in text
    assert "bunx -y @mermaid-js/mermaid-cli@11" in text
    assert "PUPPETEER_EXECUTABLE_PATH" in text


def test_common_mistakes_maps_maid_codes() -> None:
    text = COMMON_MISTAKES.read_text()
    assert "FL-ARROW-INVALID" in text
    assert "FL-STYLE-TARGET-UNKNOWN" in text
    # the un-lintable boundary must be stated, not implied as covered
    assert "human discipline" in text.lower()
```

- [ ] **Step 2: Run the structure tests to verify they fail (skill files not yet created if running this task in isolation; otherwise pass)**

Run: `uv run --with pytest pytest tests/test_mermaid_skill.py -q -k "not maid"`
Expected: PASS once Tasks 1–3 are merged; FAIL with "missing …/SKILL.md" if run before them. (This task depends on Tasks 1–3.)

- [ ] **Step 3: Add the network-gated maid characterization tests**

```python
_BUNX = shutil.which("bunx") or shutil.which("bun")
needs_bunx = pytest.mark.skipif(
    _BUNX is None, reason="bun/bunx not available (e.g. hermetic CI); maid checks skipped"
)

BAD = "flowchart TD\n  A[Start] --> B[Build]\n  style D fill:#f00\n  X -> Y\n"
GOOD = "flowchart TD\n  A[Start] --> B[Build]\n  B --> C[Test]\n"


def _maid(text: str, tmp_path: Path) -> subprocess.CompletedProcess:
    f = tmp_path / "d.mmd"
    f.write_text(text)
    return subprocess.run(
        ["bunx", "-y", MAID, str(f)],
        capture_output=True,
        text=True,
        timeout=180,
    )


@needs_bunx
def test_maid_flags_known_bad(tmp_path: Path) -> None:
    res = _maid(BAD, tmp_path)
    out = res.stdout + res.stderr
    assert res.returncode == 1, f"expected exit 1, got {res.returncode}: {out}"
    assert "FL-ARROW-INVALID" in out


@needs_bunx
def test_maid_passes_known_good(tmp_path: Path) -> None:
    res = _maid(GOOD, tmp_path)
    assert res.returncode == 0, (res.stdout + res.stderr)
```

- [ ] **Step 4: Run the full file**

Run: `uv run --with pytest pytest tests/test_mermaid_skill.py -q`
Expected: structure tests PASS; maid tests PASS locally (bun present), SKIP in hermetic CI. Pristine output (only PASS/SKIP).

- [ ] **Step 5: Commit**

Message: `test(mermaid): structure checks + maid characterization (pinned 1.0.1)`.

---

### Task 5: Add the skill docs to the rumdl MD_FILES gate

**Files:**

- Modify: `Taskfile.yaml` (the `MD_FILES` var)

- [ ] **Step 1: Append the three markdown files to `MD_FILES`**

Add these three lines to the `MD_FILES: >-` block (after the `grepping` reference lines), matching the existing indentation:

```yaml
    dev-flow/skills/mermaid/SKILL.md
    dev-flow/skills/mermaid/references/diagram-types.md
    dev-flow/skills/mermaid/references/common-mistakes.md
```

(`tests/` is already in `PYTEST_DIRS`, so `tests/test_mermaid_skill.py` is gated automatically — no test-var change needed.)

- [ ] **Step 2: Verify the gate now covers the new files and still passes**

Run: `task lint`
Expected: rumdl runs over the three new files (and everything else) with no issues; `jq empty` on the plugin JSON still passes; adr-doctor still passes.

- [ ] **Step 3: Commit**

Message: `build(mermaid): gate skill docs in task lint (MD_FILES)`.

---

### Task 6: Add the maid MCP server to .mcp.json

**Files:**

- Modify: `.mcp.json` (repo root)

- [ ] **Step 1: Add the `maid` entry under `mcpServers` (alongside `context7`, `terraform`)**

```json
"maid": {
  "command": "npx",
  "args": ["-y", "@probelabs/maid", "mcp"]
}
```

Use `npx` here to match maid's documented MCP invocation (`claude mcp add -- npx -y @probelabs/maid mcp`); the lint CLI elsewhere uses `bunx`. This entry is for dogfooding in this repo and is optional for consumers.

- [ ] **Step 2: Verify the JSON is valid and the entry is present**

Run: `jq -e '.mcpServers.maid.args | index("mcp")' .mcp.json`
Expected: a non-null index (exit 0), confirming the `maid mcp` entry parsed correctly.

- [ ] **Step 3: Commit**

Message: `chore(mermaid): declare optional maid MCP in .mcp.json`.

---

### Task 7: Wire the skill pointer into brainstorming and writing-plans

**Files:**

- Modify: `dev-flow/skills/brainstorming/SKILL.md`
- Modify: `dev-flow/skills/writing-plans/SKILL.md`
- [ ] **Step 1: Add the pointer to brainstorming**

In `dev-flow/skills/brainstorming/SKILL.md`, under the `## After the Design` section (the `**Documentation:**` sub-heading, where spec writing is discussed), add one line:

```markdown
- When the spec needs a diagram, use the `dev-flow:mermaid` skill to author, lint, and render it; run `bunx -y @probelabs/maid@1 <file>` before committing.
```

- [ ] **Step 2: Add the pointer to writing-plans**

In `dev-flow/skills/writing-plans/SKILL.md`, near the "File Structure" / diagram discussion, add one line:

```markdown
> When a plan benefits from a diagram, use the `dev-flow:mermaid` skill to author and validate it (`bunx -y @probelabs/maid@1 <file>`).
```

- [ ] **Step 3: Verify both pointers are present**

Run: `grep -l "dev-flow:mermaid" dev-flow/skills/brainstorming/SKILL.md dev-flow/skills/writing-plans/SKILL.md`
Expected: both file paths printed.

- [ ] **Step 4: Commit**

Message: `docs(mermaid): point brainstorming + writing-plans at the mermaid skill`.

---

## Verification (whole-feature)

After all tasks:

- [ ] `task lint` passes (rumdl over the three new docs + everything else; jq; adr-doctor).
- [ ] `uv run --with pytest pytest tests/test_mermaid_skill.py -q` passes (structure tests PASS; maid tests PASS locally / SKIP in CI).
- [ ] `bunx -y @probelabs/maid@1 dev-flow/skills/mermaid/SKILL.md` exits 0 (the skill's own example blocks, if any are tagged ` ```mermaid `, are valid — otherwise "no diagrams found" also exits 0).
- [ ] `jq -e '.mcpServers.maid' .mcp.json` is non-null.
- [ ] `grep -rl "dev-flow:mermaid" dev-flow/skills/brainstorming/SKILL.md dev-flow/skills/writing-plans/SKILL.md` prints both files.

## Model selection (Rule 5 hints for plan-to-beads)

- Tasks 1, 2, 3 (authoring prose with load-bearing contracts) → `model:sonnet`.
- Task 4 (test authoring) → `model:sonnet`.
- Tasks 5, 6, 7 (mechanical config / one-line edits) → `model:haiku`.

## Out of scope (per spec Non-goals)

- A gateway wrapper script (`scripts/mermaid`) — deferred open question; v1 ships documented `bunx` one-liners.
- bd-dependency-graph diagramming.
- Adopting `tetrafolium/mermaid-check` (Go) for broad-type semantic coverage — recorded as an alternative, not adopted.
- Imposing a CI gate on consumers.
- Self-dogfooding a `maid`-lint of this repo's own ` ```mermaid ` blocks inside CI (spec D5 marked this *MAY*) — omitted because this repo's CI is hermetic (no `bun`); the rumdl `MD_FILES` gate covers the new docs, and contributors can run the opt-in recipe locally.
- A `dev-flow/AGENTS.md` skill-inventory line — omitted: `mermaid` is a tool/reference skill, not a Rule 1–7 workflow skill, so it does not belong in that list.
<!-- adr-capture: sha256=ec7ada5ceebf298f; session=251b9fe3; ts=2026-05-30T19:44:47Z; adrs=fhsk-4bi -->
