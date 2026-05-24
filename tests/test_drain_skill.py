from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAIN_CMD = REPO_ROOT / "dev-flow" / "commands" / "drain.md"
DRAIN_SKILL = REPO_ROOT / "dev-flow" / "skills" / "draining-beads" / "SKILL.md"

CONDITION_MAX = 1500


def _condition_template(text: str) -> str:
    m = re.search(r"^##\s+Worker condition.*?```text\n(.*?)\n```", text, re.S | re.M)
    assert m, (
        "drain.md must define a '## Worker condition' section with a ```text template"
    )
    return m.group(1)


def test_worker_condition_under_limit() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    worst = tpl.replace("<DRAIN_ID>", "fhsk-" + "x" * 24).replace(
        "<SENTINEL>",
        "All beads in the cascade-reachable set from {"
        + ", ".join(["fhsk-xxxxxx"] * 12)
        + "} are closed.",
    )
    assert len(worst) < CONDITION_MAX, (
        f"worker condition is {len(worst)} chars (limit {CONDITION_MAX})"
    )


def test_worker_condition_points_to_durable_carriers() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    assert "<DRAIN_ID>" in tpl and "<SENTINEL>" in tpl
    assert "bd show <DRAIN_ID>" in tpl
    assert ("dev-flow:draining-beads" in tpl) or (".drain/<DRAIN_ID>.md" in tpl)


def test_phase_d_emits_not_fires() -> None:
    text = DRAIN_CMD.read_text()
    assert "Fire `/goal`" not in text, "Phase D must EMIT the condition, not fire it"
    assert "<PROMPT_BODY>" not in text, "the inline iteration-body payload must be gone"


def test_drain_stamps_workspace_and_sentinel() -> None:
    text = DRAIN_CMD.read_text()
    assert text.count("drain_workspace=") >= 3, (
        "epic/set/cascade must each stamp drain_workspace"
    )
    assert text.count("drain_sentinel=") >= 3, (
        "epic/set/cascade must each stamp drain_sentinel"
    )


def test_iteration_body_removed_from_command() -> None:
    assert "## Iteration body" not in DRAIN_CMD.read_text(), (
        "12-step body must move to the skill"
    )


def test_skill_carries_protocol_and_goal_guidance() -> None:
    text = DRAIN_SKILL.read_text()
    assert "Using `/goal` correctly" in text
    assert "Atomic claim" in text and "Two-stage review" in text
    assert ("user-only" in text.lower()) or ("cannot self-invoke" in text.lower())


def test_skill_has_no_stale_crossrefs() -> None:
    assert "embedded in `commands/drain.md`" not in DRAIN_SKILL.read_text()


def test_worker_mode_present() -> None:
    text = DRAIN_CMD.read_text()
    assert "worker <drain-id>" in text, "argument-hint/dispatch must list worker mode"
    assert "## Worker mode" in text
