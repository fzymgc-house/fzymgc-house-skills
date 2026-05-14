from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_README = REPO_ROOT / "docs" / "adr" / "README.md"


def test_adr_readme_exists() -> None:
    assert ADR_README.exists(), f"missing {ADR_README}"


def test_adr_readme_has_index_sentinels() -> None:
    text = ADR_README.read_text()
    assert "<!-- BEGIN INDEX -->" in text or "## Index" in text
    assert "## Writing guidelines" in text


def test_adr_readme_has_both_index_markers() -> None:
    text = ADR_README.read_text()
    # The capture-adrs skill rewrites between these sentinels.
    assert "<!-- BEGIN INDEX -->" in text
    assert "<!-- END INDEX -->" in text
