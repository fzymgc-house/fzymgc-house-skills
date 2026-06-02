"""memory-curator is registered in both marketplaces with a resolvable wrapper."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    with path.open() as fh:
        return json.load(fh)


def test_claude_marketplace_includes_memory_curator():
    mp = load(REPO_ROOT / ".claude-plugin" / "marketplace.json")
    entry = next(p for p in mp["plugins"] if p["name"] == "memory-curator")
    assert entry["source"] == "./memory-curator"


def test_codex_marketplace_includes_memory_curator():
    mp = load(REPO_ROOT / ".agents" / "plugins" / "marketplace.json")
    entry = next(p for p in mp["plugins"] if p["name"] == "memory-curator")
    assert entry["source"] == {"source": "local", "path": "./plugins/memory-curator"}


def test_wrapper_symlinks_resolve():
    wrapper = REPO_ROOT / "plugins" / "memory-curator"
    assert (wrapper / ".mcp.json").resolve().is_file()
    assert (wrapper / "hooks" / "hooks.json").resolve().is_file()
    assert (wrapper / "skills" / "curating-memory" / "SKILL.md").resolve().is_file()
