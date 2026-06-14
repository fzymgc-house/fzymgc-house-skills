from __future__ import annotations

import importlib.util
import re
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAIN_CMD = REPO_ROOT / "dev-flow" / "commands" / "drain.md"
DRAIN_SKILL = REPO_ROOT / "dev-flow" / "skills" / "draining-beads" / "SKILL.md"
DRAIN_WITH_WORKER_REF = REPO_ROOT / "dev-flow" / "references" / "drain-with-worker.md"
DRAIN_WITH_WORKER_SKILL = (
    REPO_ROOT / "dev-flow" / "skills" / "drain-with-worker" / "SKILL.md"
)
DRAIN_WATCHDOG = REPO_ROOT / "dev-flow" / "scripts" / "drain-watchdog"

CONDITION_MAX = 1500


def _load_watchdog() -> ModuleType:
    """Import the extensionless `drain-watchdog` uv script as a module so its
    pure helpers (classify) can be unit-tested. The PEP 723 header and shebang
    are comments, and the run loop is `__main__`-guarded, so import is inert."""
    loader = SourceFileLoader("drain_watchdog", str(DRAIN_WATCHDOG))
    spec = importlib.util.spec_from_loader("drain_watchdog", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


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


def test_worker_condition_has_jj_clause() -> None:
    tpl = _condition_template(DRAIN_CMD.read_text())
    assert "jj:jujutsu" in tpl, (
        "canonical worker condition must tell the worker to invoke jj:jujutsu "
        "before commit/rebase/topology surgery"
    )


def test_reference_delegates_refuse_early_to_launch() -> None:
    text = DRAIN_WITH_WORKER_REF.read_text()
    assert "drain-worker-launch" in text, (
        "reference must delegate validation to the script"
    )
    assert "--check" in text, "reference must mention the validate-only mode"
    # Reclaim the reference coverage the deleted prereqs/arms tests had:
    for meta in ("drain_workspace", "drain_scope", "drain_sentinel"):
        assert meta in text, f"reference must still document the {meta} guard"
    assert "drain-watchdog" in text and "--multiplexer" in text, (
        "reference must keep the (now parameterized) watchdog arm command"
    )


def test_watchdog_completion_keys_on_bead_closed() -> None:
    text = DRAIN_WATCHDOG.read_text()
    assert '== "closed"' in text, "watchdog completion = drain bead status closed"
    assert 'startswith(scope + ".")' in text, (
        "epic child probe filters by '<scope>.' prefix"
    )


def test_skill_arms_the_watchdog_script() -> None:
    text = DRAIN_WITH_WORKER_SKILL.read_text()
    assert "--drain-id" in text and "--scope" in text and "--surface" in text
    assert "--multiplexer" in text


def test_watchdog_classifies_blocked_input() -> None:
    classify = _load_watchdog().classify
    # permission prompt the bypass guard still catches
    assert classify("Do you want to proceed?\n❯ 1. Yes\n  2. No") == "blocked-input"
    # AskUserQuestion-style numbered menu
    assert (
        classify("  1. Yes, and don't ask again\n  2. No, suggest changes")
        == "blocked-input"
    )
    # trust-folder prompt ("...trust the files in this folder?")
    assert classify("Do you trust the files in this folder?") == "blocked-input"


def test_watchdog_classifies_api_error() -> None:
    classify = _load_watchdog().classify
    assert (
        classify("API Error: 429 rate_limit_exceeded, retrying in 12s") == "api-error"
    )
    assert classify("API Error (Overloaded) 529") == "api-error"
    assert classify("Connection error: fetch failed") == "api-error"
    # a status code adjacent to a JSON error body is still a real error
    assert classify('429 {"type":"error","error":{"type":"rate_limit"}}') == "api-error"


def test_watchdog_diff_line_numbers_do_not_false_positive() -> None:
    # a bare status-code-like number in the worker's own diff/listing output is
    # NOT an API error — it is a file line number (fhsk-b43)
    classify = _load_watchdog().classify
    assert classify('      429 +    uf.add_argument("--title")') == "working"
    assert classify("      529 +        rc = mfa.run_command(boom)") == "working"
    assert classify("  503  return self._retry()") == "working"


def test_watchdog_classifies_healthy_surface_as_working() -> None:
    classify = _load_watchdog().classify
    assert (
        classify("· Crunching (esc to interrupt) 12.3k tokens\nBash(jj st)")
        == "working"
    )
    assert classify("Implementing Task 3 of 12. Running tests now.") == "working"
    assert classify("") == "working"


def test_watchdog_api_error_wins_over_a_co_occurring_prompt() -> None:
    # an error and a retry prompt can co-occur; the error is the more urgent signal
    classify = _load_watchdog().classify
    assert classify("API Error: overloaded\nDo you want to retry?") == "api-error"


def test_surface_monitoring_documented_in_skill() -> None:
    text = DRAIN_SKILL.read_text()
    assert "surface-aware watchdog" in text, (
        "skill must document the surface-aware watchdog"
    )
    assert "read-screen" in text, "skill must mention scanning the worker surface"


def test_worker_condition_byte_identical() -> None:
    cmd_tpl = _condition_template(DRAIN_CMD.read_text())
    ref_tpl = _condition_template(DRAIN_WITH_WORKER_REF.read_text())
    assert cmd_tpl == ref_tpl, (
        "the worker condition embedded in the reference must be byte-identical to "
        "drain.md's canonical condition"
    )
    assert "jj:jujutsu" in ref_tpl


def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    assert m, "command must start with YAML frontmatter"
    return m.group(1)


def test_skill_frontmatter_declares_script_tools() -> None:
    fm = _frontmatter(DRAIN_WITH_WORKER_SKILL.read_text())
    assert "Bash(dev-flow/scripts/drain-worker-launch:*)" in fm
    assert "Bash(dev-flow/scripts/drain-watchdog:*)" in fm
    assert "AskUserQuestion" in fm


def test_skill_body_invokes_launch_and_watchdog() -> None:
    text = DRAIN_WITH_WORKER_SKILL.read_text()
    assert "drain-worker-launch" in text, "skill must invoke the launch script"
    assert "drain-watchdog --multiplexer" in text, (
        "skill must arm the parameterized watchdog"
    )


def test_drain_allowed_tools_gained_launch_toolset() -> None:
    fm = _frontmatter(DRAIN_CMD.read_text())
    assert "AskUserQuestion" in fm, "inline launch offer needs AskUserQuestion"
    assert "Bash(cmux:*)" in fm, "inline launch needs cmux"


def test_drain_epic_phase_d_offers_worker() -> None:
    text = DRAIN_CMD.read_text()
    assert "command -v cmux" in text, "Phase D must probe for cmux"
    assert "/drain-with-worker" in text, "Phase D must hand off to /drain-with-worker"


def test_drain_phase_d_probes_tmux_too() -> None:
    text = DRAIN_CMD.read_text()
    assert "command -v cmux || command -v tmux" in text, (
        "Phase D must probe both multiplexers"
    )


def test_drain_frontmatter_allows_tmux() -> None:
    fm = _frontmatter(DRAIN_CMD.read_text())
    assert "Bash(tmux:*)" in fm and "Bash(command -v tmux:*)" in fm


def test_agents_doc_mentions_drain_with_worker() -> None:
    agents = (REPO_ROOT / "dev-flow" / "AGENTS.md").read_text()
    assert "/drain-with-worker" in agents, "AGENTS.md must document the new command"


def test_watchdog_multiplexer_defaults_to_cmux() -> None:
    wd = _load_watchdog()
    mux = wd.resolve_mux(None)  # None = flag absent
    assert mux.name == "cmux"


def test_watchdog_read_surface_uses_tmux_argv(monkeypatch) -> None:
    wd = _load_watchdog()
    calls: list[list[str]] = []
    monkeypatch.setattr(wd, "_run", lambda cmd: calls.append(cmd) or "line\n")
    mux = wd.resolve_mux("tmux")
    wd.read_surface(mux, "%9")
    assert calls[-1] == ["tmux", "capture-pane", "-p", "-t", "%9"]


def test_watchdog_nudge_uses_tmux_argv(monkeypatch) -> None:
    wd = _load_watchdog()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        wd.subprocess, "run", lambda cmd, check=False: calls.append(cmd)
    )
    monkeypatch.setattr(wd.time, "sleep", lambda _s: None)
    mux = wd.resolve_mux("tmux")
    wd.nudge(mux, "%9")
    assert calls[0] == ["tmux", "send-keys", "-t", "%9", "-l", wd.NUDGE]
    assert calls[1] == ["tmux", "send-keys", "-t", "%9", "Enter"]


def test_tmux_plugin_registered_and_versioned() -> None:
    import json

    claude_mp = json.loads(
        (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text()
    )
    assert any(p["name"] == "tmux" for p in claude_mp["plugins"])
    codex_mp = json.loads(
        (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text()
    )
    assert any(p["name"] == "tmux" for p in codex_mp["plugins"])
    cfg = json.loads((REPO_ROOT / "release-please-config.json").read_text())
    paths = [f["path"] for f in cfg["packages"]["."]["extra-files"]]
    assert "tmux/plugin.json" in paths
    assert (REPO_ROOT / "tmux" / "skills" / "tmux" / "SKILL.md").exists()
