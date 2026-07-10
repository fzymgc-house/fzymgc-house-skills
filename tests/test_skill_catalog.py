from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
ADOPTION_PATH = REPO_ROOT / "docs" / "adoption.md"


def _shipped_skill_names() -> list[str]:
    """Enumerate every shipped skill's directory name (the catalog token).

    Directory name == SKILL.md `name` frontmatter for all shipped skills, so
    the directory name is a stable, filesystem-derived heuristic that avoids
    parsing YAML frontmatter for a simple membership check.
    """
    skill_md_paths = sorted(
        path
        for path in REPO_ROOT.glob("*/skills/*/SKILL.md")
        if not path.relative_to(REPO_ROOT).parts[0].startswith(".")
    )
    assert skill_md_paths, "No */skills/*/SKILL.md files found — glob is broken"
    return [path.parent.name for path in skill_md_paths]


def _readme_catalog_region() -> str:
    text = README_PATH.read_text()
    match = re.search(r"## Plugins\n(.*?)\n## Installation", text, flags=re.DOTALL)
    assert match, "README.md is missing the '## Plugins' ... '## Installation' region"
    return match.group(1)


def test_every_skill_in_readme_catalog() -> None:
    assert README_PATH.exists(), f"Missing README: {README_PATH}"

    catalog_region = _readme_catalog_region()
    missing = [
        name for name in _shipped_skill_names() if f"**{name}**" not in catalog_region
    ]

    assert not missing, (
        "README.md '## Plugins' catalog is missing these shipped skills "
        f"(expected a '**<name>**' row for each): {sorted(missing)}"
    )


def test_every_skill_in_adoption_index() -> None:
    assert ADOPTION_PATH.exists(), f"Missing canonical adoption guide: {ADOPTION_PATH}"

    adoption_text = ADOPTION_PATH.read_text()
    missing = [
        name for name in _shipped_skill_names() if f"**{name}**" not in adoption_text
    ]

    assert not missing, (
        "docs/adoption.md discovery index is missing these shipped skills "
        f"(expected a '**<name>**' token for each): {sorted(missing)}"
    )
