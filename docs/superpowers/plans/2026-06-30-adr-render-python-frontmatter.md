<!-- markdownlint-disable MD013 -->

# ADR render-adr + adr-doctor → Python/uv with Starlight frontmatter — Implementation Plan

> **STATUS: IMPLEMENTED (epic `fhsk-cdr`, all tasks closed).** The shipped code in
> `dev-flow/scripts/` (`_adr_render.py`, `render-adr`, `_adr_doctor.py`, `adr-doctor`,
> and the tests under `dev-flow/scripts/tests/`) is **authoritative**. A few code
> snippets below reflect an earlier plan revision whose review corrections were lost in
> the PR #183 squash/reconcile (markdown `\n`-in-code-fence edits mis-fired); the
> as-built code applied those corrections — notably: the split-refs test asserts the
> rstripped value; `adr-doctor` uses `_bd_decision_ids()` + per-bead `bd show` (not a
> `_bd_decisions` full-record read) plus a record-missing check; stdlib imports are
> hoisted to the top of each module; and the parity harness used `difflib`. Read the
> code, not these snippets, for exact behavior.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `dev-flow/scripts/render-adr` and `adr-doctor.sh` as Python PEP 723 (`uv run --script`) tools so generated ADRs carry a Starlight-valid YAML `title:` frontmatter (no body H1), and regenerate all committed ADRs to the new format.

**Architecture:** Pure, importable modules (`_adr_render.py`, `_adr_doctor.py`) hold all logic and are unit-tested without `bd`; thin PEP 723 executables (`render-adr`, `adr-doctor`) do I/O only. A one-shot dev-time parity harness proves the bash→Python port changes only `{+frontmatter, −H1}`; golden fixtures freeze the result. A new bd-free `adr-doctor` invariant (INV-A25) gates frontmatter-title presence in CI.

**Tech Stack:** Python ≥3.11 (stdlib only), `uv run --script` (PEP 723), pytest (already in `PYTEST_DIRS`), ruff, `bd` (Dolt issue tracker), jj VCS.

**Design bead:** fhsk-cdr · **Spec:** `docs/superpowers/specs/2026-06-30-adr-render-python-frontmatter-design.md`

---

## Background an implementer needs

- ADRs are `bd` `decision` beads; `docs/adr/<bd-id>-<slug>.md` is a **derived view** rendered from bd state. `render-adr <bd-id>` is idempotent — it rebuilds the file from the bead.
- The **only** intentional output change vs today: prepend `---\ntitle: "<TITLE>"\n---\n` as the first bytes, and drop the body `# <TITLE>` H1 line **plus the single blank line that followed it** (so the comment block is followed by exactly one blank line, then `**Date:**`). Everything else is byte-identical.
- `docs/adr/*.md` is **not** in the repo's rumdl gate (`Taskfile.yaml` `MD_FILES` is an explicit list without `docs/adr/`), so dropping the H1 has no rumdl impact here. `adr-doctor` is the ADR-shape gate.
- Fidelity detail: bash captures (`X="$(...)"`) strip **all trailing newlines**. The Python port mirrors this by `.rstrip("\n")` on every value read from `bd … --json` (jq `// empty` → `""` for null/missing). Output lines are modeled as a `list[str]` joined by `"".join(line + "\n" …)`, exactly mirroring `echo`/`printf '…\n'`.
- Run all commands from the worktree root: `/Volumes/Code/github.com/fzymgc-house/fzymgc-house-skills_worktrees/fix-render-adr-frontmatter`. VCS is **jj** — commit with `jj commit -m "…"` (see `references/vcs-preamble.md`). Pass `--no-pager` on `jj log`/`diff`.

## File structure

| File | Action | Responsibility |
|------|--------|----------------|
| `dev-flow/scripts/_adr_render.py` | Create | Pure render helpers + impure `load_and_render(bd_id)` (the one place that shells to `bd`). |
| `dev-flow/scripts/render-adr` | Rewrite | PEP 723 wrapper: arg parse → `load_and_render` → write file + messages. |
| `dev-flow/scripts/_adr_doctor.py` | Create | Pure check functions over file text + injected bd data; reuses `_adr_render` for INV-A22. |
| `dev-flow/scripts/adr-doctor` | Create | PEP 723 wrapper: CLI (`--explain`, `--changed-only`), file resolution, orchestration, exit codes. |
| `dev-flow/scripts/adr-doctor.sh` | Delete | Renamed to `adr-doctor`. |
| `dev-flow/scripts/tests/test_adr_render.py` | Create | Unit + golden + format-invariant tests. |
| `dev-flow/scripts/tests/test_adr_doctor.py` | Create | Per-invariant tests (incl. INV-A25). |
| `docs/adr/*.md` | Regenerate | New-format output for all 32 decision beads; delete stale orphan. |
| `Taskfile.yaml` | Modify | `adr-doctor.sh` → `adr-doctor` at the `lint` task. |
| `AGENTS.md`, `dev-flow/AGENTS.md`, `dev-flow/skills/evolve-adr/SKILL.md`, `dev-flow/skills/capture-adrs/SKILL.md`, `dev-flow/commands/adr.md` | Modify | Reference + format-snippet + Codex-compat updates. |

---

### Task 1: `_adr_render.py` — `slugify`

**Files:**

- Create: `dev-flow/scripts/_adr_render.py`
- Test: `dev-flow/scripts/tests/test_adr_render.py`
- [ ] **Step 1: Write the failing test**

Create `dev-flow/scripts/tests/test_adr_render.py`:

```python
"""Unit + golden tests for _adr_render (pure ADR rendering logic)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _adr_render as R  # noqa: E402  (sibling stdlib module on the inserted path)


def test_slugify_basic_kebab():
    assert R.slugify("Adopt Single Repo-Wide Version") == "adopt-single-repo-wide-version"


def test_slugify_drops_stop_words():
    # "for", "of", "to", "in", "on", "with", "a", "an", "the" are dropped.
    assert R.slugify("Use Active Aspects for Deferral of the Slop") == "use-active-aspects-deferral-slop"


def test_slugify_caps_at_60_then_strips_trailing_dash():
    title = "Make drain init explicit rather than auto bootstrapping first run now"
    out = R.slugify(title)
    assert len(out) <= 60
    assert not out.endswith("-")


def test_slugify_empty_when_only_stop_words_or_punct():
    assert R.slugify("the of to") == ""
    assert R.slugify("!!! ???") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named '_adr_render'`.

- [ ] **Step 3: Write minimal implementation**

Create `dev-flow/scripts/_adr_render.py`:

```python
"""Pure ADR rendering logic for render-adr (and adr-doctor INV-A22).

The functions in the first section are pure (no I/O, no `bd`) and are unit
tested directly. `load_and_render` at the bottom is the single impure entry
that shells out to `bd`; both the render-adr wrapper and adr-doctor's
in-memory INV-A22 check call it.

Byte-fidelity contract: this is a faithful port of the former bash render-adr.
The ONLY intentional output difference is the YAML `title:` frontmatter and the
removal of the body `# <TITLE>` H1. Bash `$(...)` capture strips all trailing
newlines; we mirror that with `.rstrip("\\n")` on every value read from bd.
"""

from __future__ import annotations

import json
import re
import subprocess

# Stop-words dropped from slugs (verbatim from the former bash awk list).
_STOP_WORDS = frozenset({"a", "an", "the", "for", "of", "to", "in", "on", "with"})


def slugify(title: str) -> str:
    """lowercase, non-[a-z0-9] -> space, collapse, drop stop-words, join '-',
    cut to 60 chars, strip trailing '-'. ASCII scope: bash used byte-wise
    `tr -c 'a-z0-9'`; this is char-wise. bd ADR titles are ASCII in practice."""
    lowered = title.lower()
    spaced = re.sub(r"[^a-z0-9]", " ", lowered)
    words = [w for w in spaced.split() if w not in _STOP_WORDS]
    slug = "-".join(words)[:60]
    return slug.rstrip("-")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): add _adr_render.slugify (Python port)"`

---

### Task 2: `_adr_render.py` — field helpers

**Files:**

- Modify: `dev-flow/scripts/_adr_render.py`
- Test: `dev-flow/scripts/tests/test_adr_render.py`
- [ ] **Step 1: Write the failing tests**

Append to `dev-flow/scripts/tests/test_adr_render.py`:

```python
def test_yaml_title_escapes_backslash_then_quote():
    assert R.yaml_title(r'Path C:\ and "quoted"') == r'Path C:\\ and \"quoted\"'


def test_compute_status_branches():
    assert R.compute_status("open", None, []) == "Proposed"
    assert R.compute_status("closed", "fhsk-new", []) == "Superseded by fhsk-new"
    assert R.compute_status("closed", None, ["adr:rejected"]) == "Rejected"
    assert R.compute_status("closed", None, ["adr:deprecated"]) == "Deprecated"
    assert R.compute_status("closed", None, []) == "Accepted"
    # superseded_by wins over labels; open wins over everything.
    assert R.compute_status("open", "fhsk-new", ["adr:rejected"]) == "Proposed"


def test_compute_date_prefers_created_strips_time_else_emdash():
    assert R.compute_date("2026-05-22T12:00:00Z", "2026-06-01T00:00:00Z") == "2026-05-22"
    assert R.compute_date("", "2026-06-01T00:00:00Z") == "2026-06-01"
    assert R.compute_date("", "") == "—"


def test_normalize_labels_handles_null_array_string():
    assert R.normalize_labels(None) == []
    assert R.normalize_labels(["x", "y"]) == ["x", "y"]
    assert R.normalize_labels("solo") == ["solo"]


def test_parse_addenda_strips_prefix():
    notes = "intro\naddendum: first thing\nnoise\naddendum: second"
    assert R.parse_addenda(notes) == ["first thing", "second"]


def test_split_body_references_separates_refs_section():
    desc = "## Context\nbody\n\n## References\n\n- a ref\n- b ref"
    main, bullets = R.split_body_references(desc)
    assert main == "## Context\nbody\n"
    assert bullets == "- a ref\n- b ref"


def test_split_body_references_no_section_returns_whole_body():
    desc = "## Context\nbody only"
    main, bullets = R.split_body_references(desc)
    assert main == desc
    assert bullets == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: FAIL — `AttributeError: module '_adr_render' has no attribute 'yaml_title'`.

- [ ] **Step 3: Write minimal implementation**

Append to `dev-flow/scripts/_adr_render.py`:

```python
def yaml_title(title: str) -> str:
    """Escape a title for a YAML double-quoted scalar: backslash first, then quote."""
    return title.replace("\\", "\\\\").replace('"', '\\"')


def compute_status(status_raw: str, superseded_by: str | None, labels: list[str]) -> str:
    """5-branch status rule (verbatim order from the former bash script)."""
    if status_raw == "open":
        return "Proposed"
    if superseded_by:
        return f"Superseded by {superseded_by}"
    if "adr:rejected" in labels:
        return "Rejected"
    if "adr:deprecated" in labels:
        return "Deprecated"
    return "Accepted"


def compute_date(created_at: str, closed_at: str) -> str:
    """Decision date = created_at (fallback closed_at), date portion only, else em dash."""
    raw = created_at or closed_at
    date = raw.split("T", 1)[0]
    return date or "—"


def normalize_labels(raw) -> list[str]:
    """bd labels may be null, an array, or a string. Normalize to a list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    return [str(raw)]


def parse_addenda(notes: str) -> list[str]:
    """Lines beginning 'addendum: ' in notes, with the prefix stripped."""
    prefix = "addendum: "
    return [line[len(prefix):] for line in notes.split("\n") if line.startswith(prefix)]


def split_body_references(description: str) -> tuple[str, str]:
    """Split a body into (main, ref_bullets), mirroring the two former awk passes.

    main: all lines except the '## References' section (which runs to the next
    '## ' heading or end). ref_bullets: '- ' bullet lines inside that section.
    Both are rstripped of trailing newlines to mirror bash `$(...)` capture.
    """
    lines = description.split("\n")
    if not any(line.startswith("## References") for line in lines):
        return description, ""

    main: list[str] = []
    skip = False
    for line in lines:
        if line.startswith("## References"):
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            main.append(line)

    bullets: list[str] = []
    in_refs = False
    for line in lines:
        if line.startswith("## References"):
            in_refs = True
            continue
        if in_refs and line.startswith("## "):
            in_refs = False
        if in_refs and line.startswith("- "):
            bullets.append(line)

    return "\n".join(main).rstrip("\n"), "\n".join(bullets).rstrip("\n")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): add _adr_render field helpers (status/date/labels/addenda/refs)"`

---

### Task 3: `_adr_render.py` — `build_document` (assembly + golden)

**Files:**

- Modify: `dev-flow/scripts/_adr_render.py`
- Test: `dev-flow/scripts/tests/test_adr_render.py`
- [ ] **Step 1: Write the failing golden + invariant tests**

Append to `dev-flow/scripts/tests/test_adr_render.py`:

```python
def _sample_bead() -> dict:
    return {
        "title": "Adopt Single Repo-Wide Version",
        "status": "closed",
        "created_at": "2026-05-22T10:00:00Z",
        "closed_at": "",
        "description": "## Context\n\nWhy.\n\n## Decision\n\nDo it.\n\n## Consequences\n\nFine.",
        "metadata": {"adr_deciders": "Sean Brandt (@seanb4t)"},
        "notes": "addendum: revisited later",
        "labels": [],
    }


EXPECTED = (
    "---\n"
    'title: "Adopt Single Repo-Wide Version"\n'
    "---\n"
    "<!-- markdownlint-disable MD013 -->\n"
    "<!-- adr-render: source=bd:fhsk-7y4; do not edit manually; use `/adr update fhsk-7y4` -->\n"
    "\n"
    "**Date:** 2026-05-22\n"
    "**Status:** Accepted\n"
    "**Decision:** fhsk-7y4\n"
    "**Deciders:** Sean Brandt (@seanb4t)\n"
    "\n"
    "## Context\n\nWhy.\n\n## Decision\n\nDo it.\n\n## Consequences\n\nFine.\n"
    "\n"
    "## Addenda\n"
    "\n"
    "- revisited later\n"
)


def test_build_document_golden():
    out = R.build_document("fhsk-7y4", _sample_bead(), superseded_by=None, supersedes_ids=[])
    assert out == EXPECTED


def test_build_document_format_invariants():
    out = R.build_document("fhsk-7y4", _sample_bead(), superseded_by=None, supersedes_ids=[])
    assert out.startswith("---\n")
    assert out.splitlines()[1] == 'title: "Adopt Single Repo-Wide Version"'
    # No body H1 line anywhere.
    assert not any(line.startswith("# ") for line in out.splitlines())


def test_build_document_references_merge():
    bead = _sample_bead()
    bead["description"] = "## Context\nbody\n\n## References\n\n- existing ref"
    bead["notes"] = ""
    out = R.build_document("fhsk-7y4", bead, superseded_by="fhsk-new", supersedes_ids=["fhsk-old"])
    assert "## References\n\n- existing ref\n- Supersedes: fhsk-old\n- Superseded by: fhsk-new\n" in out
    # Exactly one References heading (no MD024 duplicate).
    assert out.count("## References") == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: FAIL — `AttributeError: … has no attribute 'build_document'`.

- [ ] **Step 3: Write minimal implementation**

Append to `dev-flow/scripts/_adr_render.py`:

```python
def build_document(
    bd_id: str,
    bead: dict,
    *,
    superseded_by: str | None,
    supersedes_ids: list[str],
) -> str:
    """Assemble the ADR markdown string from a bead dict + supersession refs.

    Pure: no I/O. Mirrors the former bash assembly byte-for-byte EXCEPT it
    prepends YAML `title:` frontmatter and omits the body `# <TITLE>` H1.
    """
    title = (bead.get("title") or "").rstrip("\n")
    status_raw = (bead.get("status") or "").rstrip("\n")
    created_at = (bead.get("created_at") or "").rstrip("\n")
    closed_at = (bead.get("closed_at") or "").rstrip("\n")
    description = (bead.get("description") or "").rstrip("\n")
    deciders = ((bead.get("metadata") or {}).get("adr_deciders") or "").rstrip("\n")
    notes = (bead.get("notes") or "").rstrip("\n")
    labels = normalize_labels(bead.get("labels"))

    date = compute_date(created_at, closed_at)
    status = compute_status(status_raw, superseded_by, labels)
    deciders_out = deciders or "—"
    addenda = parse_addenda(notes)
    body_main, body_ref_bullets = split_body_references(description)

    lines: list[str] = []
    lines.append("---")
    lines.append(f'title: "{yaml_title(title)}"')
    lines.append("---")
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append(
        f"<!-- adr-render: source=bd:{bd_id}; do not edit manually; use `/adr update {bd_id}` -->"
    )
    lines.append("")
    lines.append(f"**Date:** {date}")
    lines.append(f"**Status:** {status}")
    lines.append(f"**Decision:** {bd_id}")
    lines.append(f"**Deciders:** {deciders_out}")
    lines.append("")
    if body_main:
        lines.extend(body_main.split("\n"))

    if addenda:
        lines.append("")
        lines.append("## Addenda")
        lines.append("")
        lines.extend(f"- {entry}" for entry in addenda)

    if body_ref_bullets or supersedes_ids or superseded_by:
        lines.append("")
        lines.append("## References")
        lines.append("")
        if body_ref_bullets:
            lines.extend(body_ref_bullets.split("\n"))
        lines.extend(f"- Supersedes: {old_id}" for old_id in supersedes_ids)
        if superseded_by:
            lines.append(f"- Superseded by: {superseded_by}")

    return "".join(line + "\n" for line in lines)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: PASS (all render tests green).

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): add _adr_render.build_document with frontmatter + golden test"`

---

### Task 4: `_adr_render.py` — impure `load_and_render`

**Files:**

- Modify: `dev-flow/scripts/_adr_render.py`

- [ ] **Step 1: Write the implementation (impure; tested via the wrapper in Task 5)**

Append to `dev-flow/scripts/_adr_render.py`:

```python
class RenderError(Exception):
    """Raised with a message + intended exit code for the wrapper to surface."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.message = message
        self.code = code


def _bd_json(args: list[str], default):
    """Run `bd <args> --json`; return parsed JSON or `default` on any failure."""
    try:
        proc = subprocess.run(["bd", *args, "--json"], capture_output=True, text=True)
    except FileNotFoundError:
        return default
    if proc.returncode != 0 or not proc.stdout.strip():
        return default
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return default


def load_and_render(bd_id: str) -> tuple[str, str, str | None]:
    """Fetch the bead + supersession edges and render.

    Returns (slug, content, literal_newline_warning_or_None). Raises RenderError
    with the appropriate exit code on not-found / no-title.
    """
    bead_arr = _bd_json(["show", bd_id], default=[])
    if not bead_arr:
        raise RenderError(f"render-adr: bead {bd_id} not found", 1)
    bead = bead_arr[0]

    title = (bead.get("title") or "").rstrip("\n")
    if not title:
        raise RenderError(f"render-adr: bead {bd_id} has no title", 1)

    up = _bd_json(["dep", "list", bd_id, "--direction=up", "--type=supersedes"], default=[])
    superseded_by = (up[0].get("id") if up else None) or None
    down = _bd_json(["dep", "list", bd_id, "--direction=down", "--type=supersedes"], default=[])
    supersedes_ids = [edge["id"] for edge in down if edge.get("id")]

    warning = None
    description = (bead.get("description") or "")
    if "\\n" in description:
        warning = (
            f"render-adr: WARNING: bead {bd_id} body contains the literal escape \\n; "
            f"it will render verbatim. Fix the bead description to use real newlines "
            f"(bd update {bd_id} --body-file ...)."
        )

    slug = slugify(title) or "untitled"
    content = build_document(bd_id, bead, superseded_by=superseded_by, supersedes_ids=supersedes_ids)
    return slug, content, warning
```

- [ ] **Step 2: Run the existing tests to confirm no regression**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: PASS (no new tests; pure helpers unchanged).

- [ ] **Step 3: Commit**

Run: `jj commit -m "feat(adr): add _adr_render.load_and_render (bd I/O entry)"`

---

### Task 5: Rewrite `render-adr` as a PEP 723 wrapper

**Files:**

- Modify (full rewrite): `dev-flow/scripts/render-adr`
- Test: `dev-flow/scripts/tests/test_adr_render.py`
- [ ] **Step 1: Write the failing hermetic wrapper test (fake `bd` on PATH)**

Append to `dev-flow/scripts/tests/test_adr_render.py`:

```python
import json as _json
import os
import subprocess
import textwrap

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
RENDER_ADR = SCRIPTS_DIR / "render-adr"


def _fake_bd(tmp_path: Path, bead: dict) -> Path:
    """Create a fake `bd` executable that answers show/dep-list for one bead."""
    bd = tmp_path / "bin" / "bd"
    bd.parent.mkdir(parents=True, exist_ok=True)
    bd.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, sys
            args = sys.argv[1:]
            if args[:1] == ["show"]:
                print(json.dumps([{_json.dumps(bead)}]))
            elif args[:2] == ["dep", "list"]:
                print("[]")
            else:
                print("[]")
            """
        )
    )
    bd.chmod(0o755)
    return bd


def test_render_adr_wrapper_writes_new_format(tmp_path):
    bead = {
        "title": "Wrapper Smoke Test",
        "status": "closed",
        "created_at": "2026-06-30T00:00:00Z",
        "closed_at": "",
        "description": "## Context\nx\n\n## Decision\ny\n\n## Consequences\nz",
        "metadata": {"adr_deciders": "Sean"},
        "notes": "",
        "labels": [],
    }
    fake_bd = _fake_bd(tmp_path, bead)
    env = dict(os.environ, PATH=f"{fake_bd.parent}{os.pathsep}{os.environ['PATH']}")
    proc = subprocess.run(
        [str(RENDER_ADR), "fhsk-smk"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out_file = tmp_path / "docs" / "adr" / "fhsk-smk-wrapper-smoke-test.md"
    assert out_file.exists()
    content = out_file.read_text()
    assert content.startswith('---\ntitle: "Wrapper Smoke Test"\n---\n')
    assert "**Decision:** fhsk-smk\n" in content
    assert not any(line.startswith("# ") for line in content.splitlines())


def test_render_adr_wrapper_missing_bead_exits_1(tmp_path):
    empty_bd = tmp_path / "bin" / "bd"
    empty_bd.parent.mkdir(parents=True, exist_ok=True)
    empty_bd.write_text("#!/usr/bin/env python3\nprint('[]')\n")
    empty_bd.chmod(0o755)
    env = dict(os.environ, PATH=f"{empty_bd.parent}{os.pathsep}{os.environ['PATH']}")
    proc = subprocess.run(
        [str(RENDER_ADR), "fhsk-nope"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "not found" in proc.stderr
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -k wrapper -q`
Expected: FAIL — the current `render-adr` is bash and emits the old format (no frontmatter), so `startswith('---…')` fails (or the filename/test assertions fail).

- [ ] **Step 3: Replace `dev-flow/scripts/render-adr` entirely**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# SPDX-License-Identifier: Apache-2.0
#
# render-adr — render a decision bead to a canonical ADR markdown file.
#
# Usage:
#   dev-flow/scripts/render-adr <bd-id>
#
# Reads bd state via `bd show --json` and writes docs/adr/<bd-id>-<slug>.md
# (relative to the current directory; run from the repo root). Idempotent.
# Logic lives in the importable sibling module _adr_render.py.

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _adr_render as R  # noqa: E402  (sibling stdlib module on the inserted path)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(f"usage: {Path(sys.argv[0]).name} <bd-id>", file=sys.stderr)
        return 2
    bd_id = argv[0]

    try:
        slug, content, warning = R.load_and_render(bd_id)
    except R.RenderError as err:
        print(err.message, file=sys.stderr)
        return err.code

    if warning:
        print(warning, file=sys.stderr)

    out_dir = Path("docs/adr")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{bd_id}-{slug}.md"
    out_file.write_text(content)
    print(f"render-adr: wrote {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Make it executable and run the wrapper tests**

Run: `chmod +x dev-flow/scripts/render-adr && cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_render.py -q`
Expected: PASS (units + golden + both wrapper tests).

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): rewrite render-adr as PEP723 wrapper emitting Starlight frontmatter"`

---

### Task 6: Parity harness (one-shot, dev-time — NOT committed)

**Files:**

- Create (temp, in scratchpad — do **not** add to the repo): `/private/tmp/claude-501/.../scratchpad/parity_check.py`

This proves the port changed only `{+frontmatter, −H1}`. It shells out to the **old bash** `render-adr` from jj history, so it cannot live in the repo after the rewrite. Run it once; discard it.

- [ ] **Step 1: Recover the old bash render-adr from history**

Run:

```bash
jj --no-pager show "$(jj --no-pager log -r 'latest(::@- & description(exact:"chore(main): release 1.25.0 (#171)"))' --no-graph -T 'commit_id.short()')":dev-flow/scripts/render-adr 2>/dev/null \
  > /tmp/old-render-adr 2>/dev/null || \
  git show "$(git rev-parse HEAD~99 2>/dev/null || echo main)":dev-flow/scripts/render-adr > /tmp/old-render-adr
```

Simpler and reliable: the old script is the version at the worktree base `main` (tag v1.25.0). Use:

```bash
git -C . show "$(git rev-parse 'main')":dev-flow/scripts/render-adr > /tmp/old-render-adr && chmod +x /tmp/old-render-adr
```

Expected: `/tmp/old-render-adr` is the pre-rewrite bash script.

- [ ] **Step 2: Write the harness**

Create `…/scratchpad/parity_check.py`:

```python
"""One-shot parity harness: old bash render-adr vs new python, per decision bead.

Asserts the only differences are the added frontmatter block and the removed
`# <TITLE>` H1 (plus the single blank line that followed it). NOT committed.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path.cwd()  # run this harness from the worktree root (Step 3 cd's there)
OLD = Path("/tmp/old-render-adr")
NEW = REPO / "dev-flow" / "scripts" / "render-adr"

ids = json.loads(subprocess.check_output(
    ["bd", "list", "--all", "--type=decision", "--json"], text=True))
ids = [b["id"] for b in ids]

failures = []
for bd_id in ids:
    title = json.loads(subprocess.check_output(["bd", "show", bd_id, "--json"], text=True))[0]["title"]
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        subprocess.run([str(OLD), bd_id], cwd=d1, check=True, capture_output=True)
        subprocess.run([str(NEW), bd_id], cwd=d2, check=True, capture_output=True)
        old = next((Path(d1) / "docs" / "adr").glob("*.md")).read_text()
        new_files = list((Path(d2) / "docs" / "adr").glob("*.md"))
        new = new_files[0].read_text()
        # Transform old -> expected new: drop "# <TITLE>\n\n", prepend frontmatter.
        expected = re.sub(rf"^# {re.escape(title)}\n\n", "", old, count=1, flags=re.M)
        expected = f'---\ntitle: "{title}"\n---\n' + expected
        if new != expected:
            failures.append(bd_id)
            print(f"--- PARITY MISMATCH {bd_id} ---")
            subprocess.run(["diff", "-u", "-"], input=expected + "\0" + new, text=True)

print(f"checked {len(ids)} beads, {len(failures)} mismatches: {failures}")
sys.exit(1 if failures else 0)
```

Note: set `REPO` to the literal worktree root path before running (the `[?]` is a reminder to hard-code it, since the harness lives in scratchpad, not the repo tree). The frontmatter-title in `expected` uses the **raw** title; if any bead title contains `"` or `\`, replace the f-string with `R.yaml_title(title)` imported from the new module.

- [ ] **Step 3: Run the harness**

Run: `cd <worktree-root> && uv run --with pytest python …/scratchpad/parity_check.py` (or plain `python3`).
Expected: `checked 32 beads, 0 mismatches: []` and exit 0. If any mismatch prints, fix `_adr_render` until clean — this is the authoritative faithfulness gate.

- [ ] **Step 4: Discard the harness**

Run: `rm -f …/scratchpad/parity_check.py /tmp/old-render-adr`
(No commit — nothing repo-tracked changed in this task.)

---

### Task 7: Regenerate all ADRs + remove orphan

**Files:**

- Regenerate: `docs/adr/*.md`
- Delete: `docs/adr/fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md` (stale slug-drift orphan)
- [ ] **Step 1: Regenerate every decision bead**

Run from the worktree root:

```bash
for id in $(bd list --all --type=decision --json | jq -r '.[].id'); do
  dev-flow/scripts/render-adr "$id"
done
```

Expected: 32 `render-adr: wrote docs/adr/<id>-<slug>.md` lines, no errors.

- [ ] **Step 2: Remove orphaned ADR files not produced by a current render**

Run:

```bash
# Compute the canonical set the renderer just (re)wrote, then delete any other *.md.
keep=$(for id in $(bd list --all --type=decision --json | jq -r '.[].id'); do
  title=$(bd show "$id" --json | jq -r '.[0].title')
  slug=$(dev-flow/scripts/render-adr "$id" >/dev/null; basename "$(ls docs/adr/${id}-*.md | head -1)")
  echo "$slug"
done)
for f in docs/adr/*.md; do
  bn=$(basename "$f")
  [ "$bn" = "README.md" ] && continue
  printf '%s\n' "$keep" | grep -qxF "$bn" || { echo "removing orphan: $f"; rm -f "$f"; }
done
```

Expected: `removing orphan: docs/adr/fhsk-0cd-make-drain-init-explicit-rather-than-auto-bootstrapping-firs.md` (and nothing else, unless other drift exists). Confirm exactly one keeper remains for `fhsk-0cd`: `ls docs/adr/fhsk-0cd-*.md` shows a single file.

- [ ] **Step 3: Inspect the diff**

Run: `jj --no-pager diff --git --stat docs/adr/ | tail -5` then spot-check one file: `jj --no-pager diff --git docs/adr/fhsk-7y4-*.md`
Expected: every changed file shows `+---`/`+title:`/`+---` added at top and the `-# <TITLE>` line (plus its trailing blank) removed; one file deleted. No other content churn.

- [ ] **Step 4: Commit**

Run: `jj commit -m "docs(adr): regenerate all ADRs with Starlight title frontmatter; drop H1; remove fhsk-0cd orphan"`

---

### Task 8: `_adr_doctor.py` — pure file-text checks + INV-A25

**Files:**

- Create: `dev-flow/scripts/_adr_doctor.py`
- Test: `dev-flow/scripts/tests/test_adr_doctor.py`
- [ ] **Step 1: Write the failing tests**

Create `dev-flow/scripts/tests/test_adr_doctor.py`:

```python
"""Per-invariant tests for _adr_doctor (pure checks over ADR file text)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _adr_doctor as D  # noqa: E402

BD_ID_RE = D.BD_ID_RE

GOOD = (
    '---\n'
    'title: "A Decision"\n'
    '---\n'
    "<!-- markdownlint-disable MD013 -->\n"
    "\n"
    "**Decision:** fhsk-abc\n"
    "\n"
    "## Decision\nd\n## Rationale\nr\n## Alternatives Considered\na\n"
)


def test_frontmatter_title_present_passes_on_good(tmp_path):
    f = tmp_path / "fhsk-abc-a-decision.md"
    f.write_text(GOOD)
    assert D.check_frontmatter_title(f) == []  # INV-A25: no failures


def test_frontmatter_title_missing_fails(tmp_path):
    f = tmp_path / "fhsk-abc-a-decision.md"
    f.write_text(GOOD.replace('---\ntitle: "A Decision"\n---\n', "", 1))
    fails = D.check_frontmatter_title(f)
    assert len(fails) == 1
    assert "frontmatter" in fails[0].lower()


def test_frontmatter_title_empty_fails(tmp_path):
    f = tmp_path / "fhsk-abc-a-decision.md"
    f.write_text(GOOD.replace('title: "A Decision"', 'title: ""'))
    fails = D.check_frontmatter_title(f)
    assert len(fails) == 1


def test_decision_header_matches_filename(tmp_path):
    f = tmp_path / "fhsk-abc-a-decision.md"
    f.write_text(GOOD)
    assert D.check_decision_header(f) == []
    bad = tmp_path / "fhsk-xyz-mismatch.md"
    bad.write_text(GOOD)  # header says fhsk-abc but filename says fhsk-xyz
    assert D.check_decision_header(bad) != []


def test_validator_sections_required(tmp_path):
    f = tmp_path / "fhsk-abc-a-decision.md"
    f.write_text(GOOD.replace("## Rationale\nr\n", ""))
    fails = D.check_validator_sections(f)
    assert any("## Rationale" in m for m in fails)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_doctor.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named '_adr_doctor'`.

- [ ] **Step 3: Write minimal implementation**

Create `dev-flow/scripts/_adr_doctor.py`:

```python
"""Pure check functions for adr-doctor. Each returns a list[str] of FAIL
messages (empty == clean). The adr-doctor wrapper orchestrates these plus the
bd-backed checks. Faithful port of the former adr-doctor.sh invariants, with a
new INV-A25 frontmatter-title check.
"""

from __future__ import annotations

import re
from pathlib import Path

# Generic bd-id matcher (verbatim from adr-doctor.sh): any-prefix-XXXX.
BD_ID_RE = r"[a-z][a-z0-9-]*-[a-z0-9]+"
_FILENAME_RE = re.compile(rf"^{BD_ID_RE}-[a-z0-9-]+\.md$")


def _frontmatter_block(text: str) -> str | None:
    """Return the YAML between a leading '---' line and the next '---', or None."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end]


def check_frontmatter_title(path: Path) -> list[str]:
    """INV-A25: file must open with frontmatter carrying a non-empty title:."""
    text = path.read_text()
    block = _frontmatter_block(text)
    if block is None:
        return [f"{path}: missing YAML frontmatter block (INV-A25)"]
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', block, re.M)
    if not m or not m.group(1).strip():
        return [f"{path}: frontmatter missing non-empty title: (INV-A25)"]
    return []


def check_decision_header(path: Path) -> list[str]:
    """INV-A4/A5: '**Decision:** <bd-id>' present and filename starts with it."""
    bn = path.name
    if not _FILENAME_RE.match(bn):
        return []
    text = path.read_text()
    m = re.search(rf"^\*\*Decision:\*\*\s+({BD_ID_RE})", text, re.M)
    if not m:
        return [f"{path}: missing **Decision:** <bd-id> header"]
    decision_id = m.group(1)
    if not bn.startswith(f"{decision_id}-"):
        return [f"{path}: filename does not start with **Decision:** id ({decision_id}-)"]
    return []


def check_validator_sections(path: Path) -> list[str]:
    """INV-A4: required body sections present."""
    bn = path.name
    if not _FILENAME_RE.match(bn):
        return []
    text = path.read_text()
    fails = []
    for hdr in ("## Decision", "## Rationale", "## Alternatives Considered"):
        if hdr not in text:
            fails.append(f"{path}: missing {hdr} header")
    return fails


def check_readme(adr_dir: Path) -> list[str]:
    """INV-A12: README present, index sentinels present, no legacy/ subdir."""
    fails = []
    readme = adr_dir / "README.md"
    if not readme.is_file():
        fails.append(f"missing {readme}")
    else:
        body = readme.read_text()
        if "<!-- BEGIN INDEX -->" not in body:
            fails.append(f"{readme}: missing <!-- BEGIN INDEX --> sentinel")
        if "<!-- END INDEX -->" not in body:
            fails.append(f"{readme}: missing <!-- END INDEX --> sentinel")
    if (adr_dir / "legacy").is_dir():
        fails.append(f"{adr_dir / 'legacy'} must not exist (dev-flow has no legacy ADR migration)")
    return fails
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_doctor.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): add _adr_doctor pure file-text checks incl INV-A25 frontmatter-title"`

---

### Task 9: `_adr_doctor.py` — bd-backed checks (incl. in-memory INV-A22)

**Files:**

- Modify: `dev-flow/scripts/_adr_doctor.py`
- Test: `dev-flow/scripts/tests/test_adr_doctor.py`
- [ ] **Step 1: Write the failing tests (injected bd data; no live bd)**

Append to `dev-flow/scripts/tests/test_adr_doctor.py`:

```python
def test_description_sections_required():
    assert D.check_description_sections("fhsk-abc", "## Context\nx\n## Consequences\ny") == []
    fails = D.check_description_sections("fhsk-abc", "## Decision\nonly")
    assert any("## Context" in m for m in fails)
    assert any("## Consequences" in m for m in fails)


def test_status_label_coherent():
    assert D.check_status_label_coherent("fhsk-abc", "closed") == []
    assert D.check_status_label_coherent("fhsk-abc", "open") != []


def test_deciders_present():
    assert D.check_deciders_present("fhsk-abc", "Sean") == []
    assert D.check_deciders_present("fhsk-abc", "") != []


def test_render_match_in_memory(monkeypatch, tmp_path):
    # Stub _adr_render.load_and_render to return a known content; compare to file.
    import _adr_render as R

    content = '---\ntitle: "T"\n---\nbody\n'
    monkeypatch.setattr(R, "load_and_render", lambda bd_id: ("t", content, None))
    good = tmp_path / "fhsk-abc-t.md"
    good.write_text(content)
    assert D.check_render_match(good, "fhsk-abc") == []
    bad = tmp_path / "fhsk-xyz-t.md"
    bad.write_text(content + "drift\n")
    assert D.check_render_match(bad, "fhsk-xyz") != []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_doctor.py -k "description or status_label or deciders or render_match" -q`
Expected: FAIL — those functions don't exist yet.

- [ ] **Step 3: Write minimal implementation**

Append to `dev-flow/scripts/_adr_doctor.py`:

```python
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _adr_render as R  # noqa: E402


def check_description_sections(bd_id: str, description: str) -> list[str]:
    """INV-A20/A21: bd description must have '## Context' and '## Consequences'."""
    fails = []
    if not re.search(r"^## Context", description, re.M):
        fails.append(f"{bd_id}: bd description missing '## Context' heading (INV-A20)")
    if not re.search(r"^## Consequences", description, re.M):
        fails.append(f"{bd_id}: bd description missing '## Consequences' heading (INV-A21)")
    return fails


def check_status_label_coherent(bd_id: str, status: str) -> list[str]:
    """INV-A23: a bead carrying adr:deprecated must be closed. (Caller passes
    only deprecated-labelled beads.)"""
    if status != "closed":
        return [f"{bd_id}: has adr:deprecated label but bd status={status} (must be closed) (INV-A23)"]
    return []


def check_deciders_present(bd_id: str, deciders: str) -> list[str]:
    """INV-A24: closed decision bead must carry adr_deciders metadata."""
    if not deciders:
        return [f"{bd_id}: closed decision bead lacks adr_deciders metadata. Run: /adr migrate --apply (INV-A24)"]
    return []


def check_render_match(path: Path, bd_id: str) -> list[str]:
    """INV-A22: committed file must equal a fresh in-memory render. No in-place
    overwrite, no VCS restore — render() is pure and returns a string."""
    try:
        _slug, expected, _warn = R.load_and_render(bd_id)
    except R.RenderError:
        return []  # bd doesn't know this id; nothing to compare
    if path.read_text() != expected:
        return [f"{path}: drift between rendered output and committed file. Run: /adr render {bd_id} (INV-A22)"]
    return []
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_doctor.py -q`
Expected: PASS (all `_adr_doctor` tests).

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): add _adr_doctor bd-backed checks incl in-memory INV-A22"`

---

### Task 10: `adr-doctor` PEP 723 wrapper; delete `adr-doctor.sh`

**Files:**

- Create: `dev-flow/scripts/adr-doctor`
- Delete: `dev-flow/scripts/adr-doctor.sh`
- [ ] **Step 1: Write the `adr-doctor` wrapper**

Create `dev-flow/scripts/adr-doctor`:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# SPDX-License-Identifier: Apache-2.0
#
# adr-doctor — durable health check for docs/adr/. Python port of the former
# adr-doctor.sh. Orchestrates pure checks (_adr_doctor.py) + bd-backed checks.
#
# Usage:
#   dev-flow/scripts/adr-doctor [--explain] [--changed-only <file> ...]
#
# Exit codes: 0 clean; 1 on any check failure; 2 on missing prerequisites.

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _adr_doctor as D  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"


def _have_bd() -> bool:
    return shutil.which("bd") is not None


def _bd_decisions(*extra: str) -> list[dict]:
    try:
        out = subprocess.check_output(
            ["bd", "list", "--all", "--type=decision", *extra, "--json"], text=True
        )
        return json.loads(out)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return []


def _bd_show(bd_id: str) -> dict | None:
    try:
        arr = json.loads(subprocess.check_output(["bd", "show", bd_id, "--json"], text=True))
        return arr[0] if arr else None
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, IndexError):
        return None


def main(argv: list[str]) -> int:
    explain = False
    changed_only = False
    changed_files: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--explain":
            explain = True
        elif arg == "--changed-only":
            changed_only = True
        elif changed_only:
            changed_files.append(arg)
        i += 1

    def note(msg: str) -> None:
        if explain:
            print(f"→ {msg}", file=sys.stderr)

    # Note: the Python port no longer needs `jq` (the former bash prereq).
    if not ADR_DIR.is_dir():
        print(f"missing {ADR_DIR}", file=sys.stderr)
        return 2

    # Resolve ADR file set.
    if changed_only:
        adr_files = [
            Path(f) for f in changed_files
            if f and (("/docs/adr/" in f) or f.startswith("docs/adr/")) and f.endswith(".md")
            and Path(f).is_file()
        ]
    else:
        adr_files = sorted(p for p in ADR_DIR.glob("*.md"))

    fails: list[str] = []

    note("readme + sentinels + no-legacy (INV-A12)")
    fails += D.check_readme(ADR_DIR)

    for f in adr_files:
        if f.name == "README.md":
            continue
        note(f"file checks: {f.name}")
        fails += D.check_frontmatter_title(f)   # INV-A25
        fails += D.check_decision_header(f)      # INV-A4/A5
        fails += D.check_validator_sections(f)   # INV-A4
        if _have_bd():
            bd_id = _id_from_name(f.name)
            if bd_id and _bd_show(bd_id) is not None:
                fails += D.check_render_match(f, bd_id)  # INV-A22 (bd-guarded)

    if _have_bd():
        note("bd description + metadata checks (INV-A20/A21/A24)")
        for bead in _bd_decisions():
            desc = (bead.get("description") or "")
            if desc:
                fails += D.check_description_sections(bead["id"], desc)
        for bead in _bd_decisions("--status=closed"):
            deciders = (bead.get("metadata") or {}).get("adr_deciders") or ""
            fails += D.check_deciders_present(bead["id"], deciders)
        note("status/label coherence (INV-A23)")
        for bead in _bd_decisions("--label", "adr:deprecated"):
            fails += D.check_status_label_coherent(bead["id"], bead.get("status", ""))

    # Full-pass-only checks (skipped in --changed-only mode).
    if not changed_only:
        note("agent_frontmatter (INV-A14/A15)")
        fails += D.check_agent_frontmatter(REPO_ROOT / "dev-flow" / "agents" / "adr-extractor.md")
        note("hook_executable + shellcheck")
        fails += D.check_hook_executable(REPO_ROOT / "dev-flow" / "hooks" / "nudge-adr-capture")
        note("forbid_skill_commits (INV-A2)")
        fails += D.check_forbid_skill_commits(
            REPO_ROOT / "dev-flow" / "skills" / "capture-adrs" / "SKILL.md"
        )
        if _have_bd():
            note("supersession_edges (INV-A13)")
            fails += _check_supersession_edges(adr_files)

    for msg in fails:
        print(f"FAIL: {msg}", file=sys.stderr)
    if fails:
        print(f"{len(fails)} check(s) failed.", file=sys.stderr)
        return 1
    print("adr-doctor: all checks passed.")
    return 0


def _id_from_name(name: str) -> str | None:
    import re
    m = re.match(rf"({D.BD_ID_RE})", name)
    return m.group(1) if m else None


def _check_supersession_edges(adr_files: list[Path]) -> list[str]:
    import re
    fails = []
    for f in adr_files:
        if f.name == "README.md":
            continue
        text = f.read_text()
        m = re.search(rf"^\*\*Status:\*\*\s+Superseded by\s+({D.BD_ID_RE})", text, re.M)
        if not m:
            continue
        superseder = m.group(1)
        this_m = re.search(rf"^\*\*Decision:\*\*\s+({D.BD_ID_RE})", text, re.M)
        if not this_m:
            continue
        this_id = this_m.group(1)
        try:
            dep = subprocess.check_output(["bd", "dep", "list", superseder], text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            dep = ""
        if not re.search(rf"{re.escape(this_id)}.*via supersedes", dep):
            fails.append(f"{f}: Status says superseded by {superseder}, but bd dep edge missing")
    return fails


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: Add the three full-pass file checks to `_adr_doctor.py`**

Append to `dev-flow/scripts/_adr_doctor.py`:

```python
import shutil
import subprocess


def check_agent_frontmatter(agent_path: Path) -> list[str]:
    """INV-A14/A15: adr-extractor.md model must be sonnet; tools must not include
    Write/Edit/NotebookEdit."""
    if not agent_path.is_file():
        return [f"agent file missing: {agent_path}"]
    text = agent_path.read_text()
    parts = text.split("---")
    fm = parts[1] if len(parts) >= 3 else ""
    fails = []
    if not re.search(r"^model:\s+sonnet\s*$", fm, re.M):
        fails.append(f"{agent_path}: model must be sonnet")
    if re.search(r"^\s+-\s+(Write|Edit|NotebookEdit)\s*$", fm, re.M):
        fails.append(f"{agent_path}: tools list MUST NOT include Write/Edit/NotebookEdit")
    return fails


def check_hook_executable(hook_path: Path) -> list[str]:
    """Hook must be executable; shellcheck-clean if shellcheck is available."""
    import os
    fails = []
    if not (hook_path.is_file() and os.access(hook_path, os.X_OK)):
        fails.append(f"{hook_path}: not executable")
        return fails
    if shutil.which("shellcheck"):
        proc = subprocess.run(["shellcheck", str(hook_path)], capture_output=True)
        if proc.returncode != 0:
            fails.append(f"{hook_path}: shellcheck failed")
    return fails


def check_forbid_skill_commits(skill_path: Path) -> list[str]:
    """INV-A2: capture-adrs SKILL.md must not contain a commit/describe command."""
    if not skill_path.is_file():
        return []
    text = skill_path.read_text()
    pattern = r"(^\s*\$\s*(jj commit|jj describe|git commit|git add)|^\s*`(jj commit|jj describe|git commit|git add)`)"
    if re.search(pattern, text, re.M):
        return [f"{skill_path}: contains a commit/describe command — skill MUST NOT commit"]
    return []
```

- [ ] **Step 3: Delete the old shell script and make the new one executable**

Run:

```bash
rm -f dev-flow/scripts/adr-doctor.sh
chmod +x dev-flow/scripts/adr-doctor
```

- [ ] **Step 4: Run the full check + the doctor tests**

Run: `cd dev-flow/scripts && uv run --with pytest pytest tests/test_adr_doctor.py -q`
Then from worktree root: `dev-flow/scripts/adr-doctor`
Expected: tests PASS; `adr-doctor: all checks passed.` (exit 0) against the regenerated tree. If a `FAIL:` appears, fix the underlying ADR/bead — the new format should be clean.

- [ ] **Step 5: Commit**

Run: `jj commit -m "feat(adr): port adr-doctor to PEP723 Python; delete adr-doctor.sh"`

---

### Task 11: Update `Taskfile.yaml`

**Files:**

- Modify: `Taskfile.yaml:71`

- [ ] **Step 1: Update the lint reference**

Change line 71 from `- ./dev-flow/scripts/adr-doctor.sh` to `- ./dev-flow/scripts/adr-doctor`. Do **not** add `docs/adr/*.md` to `MD_FILES`.

- [ ] **Step 2: Verify lint runs the new script**

Run: `task lint 2>&1 | tail -20`
Expected: `adr-doctor: all checks passed.` appears; ruff + rumdl + jq + evals all pass.

- [ ] **Step 3: Commit**

Run: `jj commit -m "build(adr): point Taskfile lint at adr-doctor (renamed from .sh)"`

---

### Task 12: Update documentation references

**Files:**

- Modify: `AGENTS.md`, `dev-flow/AGENTS.md`, `dev-flow/skills/evolve-adr/SKILL.md`, `dev-flow/skills/capture-adrs/SKILL.md`, `dev-flow/commands/adr.md`

- [ ] **Step 1: Fix `.sh` filename references and the rendered-format examples**

Run to find every literal reference and rendered-format snippet:

```bash
rg -n 'adr-doctor\.sh' AGENTS.md dev-flow/AGENTS.md dev-flow/skills/evolve-adr/SKILL.md dev-flow/skills/capture-adrs/SKILL.md dev-flow/commands/adr.md
rg -n '^# .*\n\*\*Date' -U dev-flow/skills/evolve-adr/SKILL.md dev-flow/skills/capture-adrs/SKILL.md dev-flow/commands/adr.md
```

For each `adr-doctor.sh` hit, replace with `adr-doctor`. For any embedded ADR-format example showing the old `# <TITLE>` H1 header, update it to the frontmatter layout (`---` / `title:` / `---` then the comment block, no body H1).

- [ ] **Step 2: Fix the evolve-adr Codex-compatibility paragraph**

In `dev-flow/skills/evolve-adr/SKILL.md` (the `### Codex compatibility` section, ~line 212-213), replace the sentence "`render-adr` is a plain bash script. These work in Codex with no special glue." with text stating that `render-adr` and `adr-doctor` are Python PEP 723 scripts run via `uv` (`#!/usr/bin/env -S uv run --script`), so Codex needs `uv` on `PATH` — the same dependency as the repo's other `uv run --script` tools.

- [ ] **Step 3: Verify no stale references remain**

Run: `rg -n 'adr-doctor\.sh|plain bash script' AGENTS.md dev-flow/ ':!docs/superpowers/specs' ':!docs/superpowers/plans'`
Expected: no hits outside historical specs/plans.

- [ ] **Step 4: Commit**

Run: `jj commit -m "docs(adr): update adr-doctor/render-adr references for Python port + new format"`

---

### Task 13: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Format**

Run: `task fmt`
Expected: ruff + rumdl reformat cleanly; `jj --no-pager diff --stat` shows only formatting (if any).

- [ ] **Step 2: Lint**

Run: `task lint`
Expected: all gates green, including `adr-doctor: all checks passed.` and ruff over the new `.py` files.

- [ ] **Step 3: Test**

Run: `task test`
Expected: pytest green across `PYTEST_DIRS`, including `dev-flow/scripts/tests/test_adr_render.py` and `test_adr_doctor.py`.

- [ ] **Step 4: Changed-only smoke**

Run: `dev-flow/scripts/adr-doctor --changed-only docs/adr/fhsk-7y4-*.md; echo "exit=$?"`
Expected: `adr-doctor: all checks passed.` and `exit=0` (frontmatter + decision-header + sections checks run; bd-backed full-pass checks skipped).

- [ ] **Step 5: Commit any formatting + final state**

Run: `jj commit -m "test(adr): verify task fmt/lint/test green for ADR Python migration"` (only if Step 1 produced changes; otherwise skip).

---

## Self-review notes (for the author)

- **Spec coverage:** frontmatter format (Tasks 3,7), drop H1 (Tasks 3,7), Python/uv PEP 723 (all script tasks), INV-A25 (Task 8), in-memory INV-A22 (Task 9), regenerate + orphan removal (Task 7), parity harness one-shot/uncommitted (Task 6), rename + reference updates (Tasks 10–12), Codex-compat fix (Task 12), no `docs/adr` in `MD_FILES` (Task 11). All covered.
- **Cross-repo:** homelab impact is documented in the spec; no task here (out of scope). Call it out in the PR description.
<!-- adr-capture: sha256=6e84e9f699993020; session=cli; ts=2026-06-30T15:49:47Z; adrs=fhsk-slp,fhsk-nlw,fhsk-bmn -->
