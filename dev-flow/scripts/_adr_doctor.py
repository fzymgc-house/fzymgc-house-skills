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
        return [
            f"{path}: filename does not start with **Decision:** id ({decision_id}-)"
        ]
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
        fails.append(
            f"{adr_dir / 'legacy'} must not exist (dev-flow has no legacy ADR migration)"
        )
    return fails
