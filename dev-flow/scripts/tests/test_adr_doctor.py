"""Per-invariant tests for _adr_doctor (pure checks over ADR file text)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _adr_doctor as D  # noqa: E402

BD_ID_RE = D.BD_ID_RE

GOOD = (
    "---\n"
    'title: "A Decision"\n'
    "---\n"
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
