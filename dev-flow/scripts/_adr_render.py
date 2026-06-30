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
