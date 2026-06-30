"""Unit + golden tests for _adr_render (pure ADR rendering logic)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _adr_render as R  # noqa: E402  (sibling stdlib module on the inserted path)


def test_slugify_basic_kebab():
    assert (
        R.slugify("Adopt Single Repo-Wide Version") == "adopt-single-repo-wide-version"
    )


def test_slugify_drops_stop_words():
    # "for", "of", "to", "in", "on", "with", "a", "an", "the" are dropped.
    assert (
        R.slugify("Use Active Aspects for Deferral of the Slop")
        == "use-active-aspects-deferral-slop"
    )


def test_slugify_caps_at_60_then_strips_trailing_dash():
    title = "Make drain init explicit rather than auto bootstrapping first run now"
    out = R.slugify(title)
    assert len(out) <= 60
    assert not out.endswith("-")


def test_slugify_empty_when_only_stop_words_or_punct():
    assert R.slugify("the of to") == ""
    assert R.slugify("!!! ???") == ""


def test_yaml_title_escapes_backslash_then_quote():
    assert R.yaml_title(r'Path C:\ and "quoted"') == r"Path C:\\ and \"quoted\""


def test_compute_status_branches():
    assert R.compute_status("open", None, []) == "Proposed"
    assert R.compute_status("closed", "fhsk-new", []) == "Superseded by fhsk-new"
    assert R.compute_status("closed", None, ["adr:rejected"]) == "Rejected"
    assert R.compute_status("closed", None, ["adr:deprecated"]) == "Deprecated"
    assert R.compute_status("closed", None, []) == "Accepted"
    # superseded_by wins over labels; open wins over everything.
    assert R.compute_status("open", "fhsk-new", ["adr:rejected"]) == "Proposed"


def test_compute_date_prefers_created_strips_time_else_emdash():
    assert (
        R.compute_date("2026-05-22T12:00:00Z", "2026-06-01T00:00:00Z") == "2026-05-22"
    )
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
    assert main == "## Context\nbody"  # rstripped, mirroring bash $(...) capture
    assert bullets == "- a ref\n- b ref"


def test_split_body_references_no_section_returns_whole_body():
    desc = "## Context\nbody only"
    main, bullets = R.split_body_references(desc)
    assert main == desc
    assert bullets == ""


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
    out = R.build_document(
        "fhsk-7y4", _sample_bead(), superseded_by=None, supersedes_ids=[]
    )
    assert out == EXPECTED


def test_build_document_format_invariants():
    out = R.build_document(
        "fhsk-7y4", _sample_bead(), superseded_by=None, supersedes_ids=[]
    )
    assert out.startswith("---\n")
    assert out.splitlines()[1] == 'title: "Adopt Single Repo-Wide Version"'
    # No body H1 line anywhere.
    assert not any(line.startswith("# ") for line in out.splitlines())


def test_build_document_references_merge():
    bead = _sample_bead()
    bead["description"] = "## Context\nbody\n\n## References\n\n- existing ref"
    bead["notes"] = ""
    out = R.build_document(
        "fhsk-7y4", bead, superseded_by="fhsk-new", supersedes_ids=["fhsk-old"]
    )
    assert (
        "## References\n\n- existing ref\n- Supersedes: fhsk-old\n- Superseded by: fhsk-new\n"
        in out
    )
    # Exactly one References heading (no MD024 duplicate).
    assert out.count("## References") == 1
