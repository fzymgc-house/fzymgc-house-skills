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


def yaml_title(title: str) -> str:
    """Escape a title for a YAML double-quoted scalar: backslash first, then quote."""
    return title.replace("\\", "\\\\").replace('"', '\\"')


def compute_status(
    status_raw: str, superseded_by: str | None, labels: list[str]
) -> str:
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
    return [
        line[len(prefix) :] for line in notes.split("\n") if line.startswith(prefix)
    ]


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

    up = _bd_json(
        ["dep", "list", bd_id, "--direction=up", "--type=supersedes"], default=[]
    )
    superseded_by = (up[0].get("id") if up else None) or None
    down = _bd_json(
        ["dep", "list", bd_id, "--direction=down", "--type=supersedes"], default=[]
    )
    supersedes_ids = [edge["id"] for edge in down if edge.get("id")]

    warning = None
    description = bead.get("description") or ""
    if "\\n" in description:
        warning = (
            f"render-adr: WARNING: bead {bd_id} body contains the literal escape \\n; "
            f"it will render verbatim. Fix the bead description to use real newlines "
            f"(bd update {bd_id} --body-file ...)."
        )

    slug = slugify(title) or "untitled"
    content = build_document(
        bd_id, bead, superseded_by=superseded_by, supersedes_ids=supersedes_ids
    )
    return slug, content, warning
