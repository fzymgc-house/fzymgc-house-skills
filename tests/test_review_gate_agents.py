"""Contract tests for the dev-flow review-gate agents (design-reviewer, plan-reviewer).

These tests verify the VERDICT-line regex contract that calling skills
(`brainstorming`, `writing-plans`) use to branch on reviewer output.

Agent behavior itself is LLM-driven and validated via live dogfood; these tests
lock the parseable contract only.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_FLOW = REPO_ROOT / "dev-flow"
DESIGN_REVIEWER = DEV_FLOW / "agents" / "design-reviewer.md"
PLAN_REVIEWER = DEV_FLOW / "agents" / "plan-reviewer.md"
REVIEW_DESIGN_CMD = DEV_FLOW / "commands" / "review-design.md"
REVIEW_PLAN_CMD = DEV_FLOW / "commands" / "review-plan.md"

VERDICT_RE = r"^VERDICT: (READY|NOT READY)$"


def _first_non_empty(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def test_design_reviewer_verdict_regex_match_ready() -> None:
    sample_output = "VERDICT: READY\n\n## Strengths\n- well-grounded\n"
    match = re.match(VERDICT_RE, _first_non_empty(sample_output))
    assert match
    assert match.group(1) == "READY"


def test_design_reviewer_verdict_regex_match_not_ready() -> None:
    sample_output = "VERDICT: NOT READY\n\n## Findings\n1. ...\n"
    match = re.match(VERDICT_RE, _first_non_empty(sample_output))
    assert match
    assert match.group(1) == "NOT READY"


def test_verdict_regex_tolerates_leading_blank_lines() -> None:
    sample_output = "\n\nVERDICT: READY\n"
    match = re.match(VERDICT_RE, _first_non_empty(sample_output))
    assert match
    assert match.group(1) == "READY"


def test_verdict_regex_rejects_malformed() -> None:
    # Missing colon
    assert not re.match(VERDICT_RE, "VERDICT READY")
    # Lowercase
    assert not re.match(VERDICT_RE, "verdict: ready")
    # Extra prefix
    assert not re.match(VERDICT_RE, "## VERDICT: READY")
    # Trailing junk on the verdict line
    assert not re.match(VERDICT_RE, "VERDICT: READY with notes")
    # Unknown verdict token
    assert not re.match(VERDICT_RE, "VERDICT: MAYBE")


def test_design_reviewer_agent_file_exists() -> None:
    assert DESIGN_REVIEWER.is_file(), (
        f"design-reviewer agent missing at {DESIGN_REVIEWER}"
    )


def test_plan_reviewer_agent_file_exists() -> None:
    assert PLAN_REVIEWER.is_file(), f"plan-reviewer agent missing at {PLAN_REVIEWER}"


def test_design_reviewer_declares_verdict_contract() -> None:
    text = DESIGN_REVIEWER.read_text()
    assert "VERDICT: READY" in text
    assert "VERDICT: NOT READY" in text
    assert "^VERDICT: (READY|NOT READY)$" in text


def test_plan_reviewer_declares_verdict_contract() -> None:
    text = PLAN_REVIEWER.read_text()
    assert "VERDICT: READY" in text
    assert "VERDICT: NOT READY" in text
    assert "^VERDICT: (READY|NOT READY)$" in text


def test_design_reviewer_frontmatter_tools() -> None:
    text = DESIGN_REVIEWER.read_text()
    required_tools = [
        "Read",
        "Grep",
        "Glob",
        "mcp__probe__search_code",
        "mcp__probe__extract_code",
        "mcp__probe__grep",
        "mcp__context7__resolve-library-id",
        "mcp__context7__query-docs",
        "mcp__deepwiki__read_wiki_structure",
        "mcp__deepwiki__read_wiki_contents",
        "mcp__deepwiki__ask_question",
    ]
    for tool in required_tools:
        assert tool in text, f"design-reviewer missing tool: {tool}"
    # design-reviewer MUST NOT have Bash (spec § Skill Inventory)
    # Look for it as a tools-list entry, not in prose.
    assert "\n  - Bash\n" not in text, "design-reviewer must not declare Bash"


def test_plan_reviewer_frontmatter_tools() -> None:
    text = PLAN_REVIEWER.read_text()
    required_tools = [
        "Read",
        "Grep",
        "Glob",
        "Bash",
        "mcp__probe__search_code",
        "mcp__probe__extract_code",
        "mcp__probe__grep",
        "mcp__context7__resolve-library-id",
        "mcp__context7__query-docs",
        "mcp__deepwiki__read_wiki_structure",
        "mcp__deepwiki__read_wiki_contents",
        "mcp__deepwiki__ask_question",
    ]
    for tool in required_tools:
        assert tool in text, f"plan-reviewer missing tool: {tool}"


def test_review_design_command_exists() -> None:
    assert REVIEW_DESIGN_CMD.is_file()
    text = REVIEW_DESIGN_CMD.read_text()
    assert "design-reviewer" in text


def test_review_plan_command_exists() -> None:
    assert REVIEW_PLAN_CMD.is_file()
    text = REVIEW_PLAN_CMD.read_text()
    assert "plan-reviewer" in text
