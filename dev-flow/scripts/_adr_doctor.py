"""Pure check functions for adr-doctor. Each returns a list[str] of FAIL
messages (empty == clean). The adr-doctor wrapper orchestrates these plus the
bd-backed checks. Faithful port of the former adr-doctor.sh invariants, with a
new INV-A25 frontmatter-title check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Generic bd-id matcher (verbatim from adr-doctor.sh): any-prefix-XXXX.
BD_ID_RE = r"[a-z][a-z0-9-]*-[a-z0-9]+"
_FILENAME_RE = re.compile(rf"^{BD_ID_RE}-[a-z0-9-]+\.md$")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _adr_render as R  # noqa: E402  (sibling module on the inserted path)


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


def check_description_sections(bd_id: str, description: str) -> list[str]:
    """INV-A20/A21: bd description must have '## Context' and '## Consequences'."""
    fails = []
    if not re.search(r"^## Context", description, re.M):
        fails.append(f"{bd_id}: bd description missing '## Context' heading (INV-A20)")
    if not re.search(r"^## Consequences", description, re.M):
        fails.append(
            f"{bd_id}: bd description missing '## Consequences' heading (INV-A21)"
        )
    return fails


def check_status_label_coherent(bd_id: str, status: str) -> list[str]:
    """INV-A23: a bead carrying adr:deprecated must be closed. (Caller passes
    only deprecated-labelled beads.)"""
    if status != "closed":
        return [
            f"{bd_id}: has adr:deprecated label but bd status={status} (must be closed) (INV-A23)"
        ]
    return []


def check_deciders_present(bd_id: str, deciders: str) -> list[str]:
    """INV-A24: closed decision bead must carry adr_deciders metadata."""
    if not deciders:
        return [
            f"{bd_id}: closed decision bead lacks adr_deciders metadata. Run: /adr migrate --apply (INV-A24)"
        ]
    return []


def check_render_match(path: Path, bd_id: str) -> list[str]:
    """INV-A22: committed file must equal a fresh in-memory render. No in-place
    overwrite, no VCS restore — render() is pure and returns a string."""
    try:
        _slug, expected, _warn = R.load_and_render(bd_id)
    except R.RenderError:
        return []  # bd doesn't know this id; nothing to compare
    if path.read_text() != expected:
        return [
            f"{path}: drift between rendered output and committed file. Run: /adr render {bd_id} (INV-A22)"
        ]
    return []
