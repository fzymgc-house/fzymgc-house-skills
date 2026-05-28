from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
CLAUDE_PATH = REPO_ROOT / "CLAUDE.md"
AGENTS_DIR = REPO_ROOT / "dev-flow" / "agents"


def test_claude_doc_is_symlink_to_agents_doc() -> None:
    assert CLAUDE_PATH.is_symlink(), "CLAUDE.md must be a symlink"
    assert not AGENTS_PATH.is_symlink(), "AGENTS.md must be the canonical file"
    assert CLAUDE_PATH.resolve() == AGENTS_PATH.resolve(), (
        "CLAUDE.md must point to AGENTS.md"
    )


def test_review_agents_read_agents_before_claude() -> None:
    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    assert agent_files

    checked = 0
    for agent_file in agent_files:
        text = agent_file.read_text()
        # Only worktree-isolated review agents carry a VCS preamble; the
        # read-only artifact reviewers (adr-extractor, design-reviewer,
        # plan-reviewer) do not and are out of scope for this assertion.
        if "vcs-detection-preamble" not in text and "vcs-equivalence" not in text:
            continue
        checked += 1
        assert "Read `AGENTS.md`" in text, f"{agent_file} must read AGENTS.md"
        if "CLAUDE.md" in text:
            assert text.index("AGENTS.md") < text.index("CLAUDE.md"), (
                f"{agent_file} must reference AGENTS.md before CLAUDE.md"
            )

    assert checked >= 13, f"expected >=13 review agents, checked {checked}"
