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
