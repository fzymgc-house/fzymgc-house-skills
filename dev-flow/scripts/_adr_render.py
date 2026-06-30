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

import re

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
