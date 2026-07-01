"""Check functions for adr-doctor. Each returns a list[str] of FAIL messages
(empty == clean). Most checks are pure (no I/O, no bd); check_render_match
delegates to load_and_render which shells out to bd. The adr-doctor wrapper
orchestrates these plus the bd-backed checks. Faithful port of the former
adr-doctor.sh invariants, with a new INV-A25 frontmatter-title check.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Generic bd-id matcher (verbatim from adr-doctor.sh): any-prefix-XXXX.
BD_ID_RE = r"[a-z][a-z0-9-]*-[a-z0-9]+"
_FILENAME_RE = re.compile(rf"^{BD_ID_RE}-[a-z0-9-]+\.md$")
_DECISION_RE = re.compile(rf"^\*\*Decision:\*\*\s+({BD_ID_RE})", re.M)


def _decision_id(text: str) -> str | None:
    """The bd-id declared by a file's '**Decision:** <bd-id>' line, or None."""
    m = _DECISION_RE.search(text)
    return m.group(1) if m else None


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
    decision_id = _decision_id(text)
    if decision_id is None:
        return [f"{path}: missing **Decision:** <bd-id> header"]
    if not bn.startswith(f"{decision_id}-"):
        return [
            f"{path}: filename does not start with **Decision:** id ({decision_id}-)"
        ]
    return []


def _id_from_name(name: str) -> str | None:
    """Fallback bd-id from a filename; truncates multi-segment prefixes, so used
    only when the **Decision:** header is absent. See bd_id_for_file."""
    m = re.match(r"([a-z][a-z0-9-]*?-[a-z0-9]+)(?=-|\.)", name)
    return m.group(1) if m else None


def bd_id_for_file(path: Path) -> str | None:
    """Resolve an ADR's bd-id for bd lookups, prefix-agnostically. Prefer the
    '**Decision:** <bd-id>' line (INV-A4/A5 checks the filename starts with it);
    fall back to the ambiguous filename regex only when the header is absent."""
    return _decision_id(path.read_text()) or _id_from_name(path.name)


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
    overwrite, no VCS restore — the in-memory string comparison is the check;
    load_and_render is the documented impure entry that shells out to bd."""
    try:
        _slug, expected, _warn = R.load_and_render(bd_id)
    except R.RenderError:
        return []  # unrenderable (unknown id or no title); nothing to compare
    if path.read_text() != expected:
        return [
            f"{path}: drift between rendered output and committed file. Run: /adr render {bd_id} (INV-A22)"
        ]
    return []


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
        fails.append(
            f"{agent_path}: tools list MUST NOT include Write/Edit/NotebookEdit"
        )
    return fails


def check_hook_executable(hook_path: Path) -> list[str]:
    """Hook must be executable; shellcheck-clean if shellcheck is available."""
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
        return [
            f"{skill_path}: contains a commit/describe command — skill MUST NOT commit"
        ]
    return []
