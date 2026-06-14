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


def test_no_literal_newline_escapes_in_adrs() -> None:
    """Rendered ADR bodies must use real line breaks, not the literal escape \\n.

    Regression guard for the capture-adrs/render-adr bug (PR #167): composing a
    decision-bead body with `printf '%s'` and `\\n` leaves the escape literal, so
    bulleted Rationale/Alternatives/Consequences render as backslash-n. Code
    fences are skipped since they may legitimately document a `\\n`.
    """
    adr_dir = REPO_ROOT / "docs" / "adr"
    offenders = []
    for path in sorted(adr_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        in_fence = False
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence and "\\n" in line:
                offenders.append(f"{path.name}:{lineno}")
    assert not offenders, (
        "ADR bodies must use real line breaks, not the literal escape '\\n'. "
        f"Offenders: {offenders}"
    )
