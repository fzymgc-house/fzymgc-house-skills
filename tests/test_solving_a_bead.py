from __future__ import annotations

import importlib.util
import json
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "dev-flow" / "skills" / "solving-a-bead" / "SKILL.md"
VALIDATE_BEAD = SKILL.parent / "scripts" / "validate-bead"


def _load() -> ModuleType:
    """Import the extensionless `validate-bead` uv script as a module. The PEP
    723 header and shebang are comments and the entrypoint is `__main__`-guarded,
    so import is inert — only the helpers and `main()` are exercised."""
    loader = SourceFileLoader("validate_bead", str(VALIDATE_BEAD))
    spec = importlib.util.spec_from_loader("validate_bead", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _proc(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["bd"], returncode, stdout, stderr)


def _show(bead: dict) -> subprocess.CompletedProcess:
    """A successful `bd show --json` — note the single-element array wrapper."""
    return _proc(0, json.dumps([bead]))


def _fake_bd(
    *,
    show: subprocess.CompletedProcess,
    deps: subprocess.CompletedProcess | None = None,
):
    """Return a stand-in for the module's `bd()` that dispatches on subcommand."""

    def _bd(args: list[str]) -> subprocess.CompletedProcess:
        if args[0] == "show":
            return show
        if args[0] == "dep":
            return deps if deps is not None else _proc(0, "[]")
        return _proc(0)

    return _bd


def _run(module, monkeypatch, argv, **bd_kwargs) -> int:
    """Invoke main(); normalize the abort path (SystemExit) and proceed path
    (plain return) to a single exit code."""
    if bd_kwargs:
        monkeypatch.setattr(module, "bd", _fake_bd(**bd_kwargs))
    try:
        return module.main(argv)
    except SystemExit as exc:
        return int(exc.code)


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return _load()


# --- pure helper: note-aware redirect target -------------------------------


def test_redirect_target_prefers_plan_over_spec(mod) -> None:
    assert "plan-to-beads" in mod.redirect_target("Spec: a.md\nPlan: b.md")


def test_redirect_target_spec_when_no_plan(mod) -> None:
    assert "writing-plans" in mod.redirect_target("Spec: a.md")


def test_redirect_target_brainstorming_when_bare(mod) -> None:
    assert "brainstorming" in mod.redirect_target("")


# --- exit-code contract for each Phase 0 gate ------------------------------


def test_usage_when_no_arg(mod, monkeypatch) -> None:
    assert _run(mod, monkeypatch, []) == mod.USAGE


def test_not_found_aborts(mod, monkeypatch, capsys) -> None:
    code = _run(mod, monkeypatch, ["x"], show=_proc(1, stderr="no issue found"))
    assert code == mod.USAGE
    assert "not found" in capsys.readouterr().out


def test_design_bead_hard_redirects(mod, monkeypatch, capsys) -> None:
    bead = {"status": "open", "labels": ["phase:design"], "notes": ""}
    code = _run(mod, monkeypatch, ["d1"], show=_show(bead))
    out = capsys.readouterr().out
    assert code == mod.REDIRECT
    assert "phase:design" in out and "brainstorming" in out


def test_design_bead_with_plan_note_routes_to_materialize(
    mod, monkeypatch, capsys
) -> None:
    bead = {
        "status": "open",
        "labels": ["phase:design"],
        "notes": "Spec: s.md\nPlan: p.md",
    }
    code = _run(mod, monkeypatch, ["d2"], show=_show(bead))
    assert code == mod.REDIRECT
    assert "plan-to-beads" in capsys.readouterr().out


def test_design_label_takes_precedence_over_status(mod, monkeypatch) -> None:
    # A closed design bead still redirects (gate 2 runs before gate 3).
    bead = {"status": "closed", "labels": ["phase:design"], "notes": ""}
    assert _run(mod, monkeypatch, ["d3"], show=_show(bead)) == mod.REDIRECT


def test_closed_status_aborts(mod, monkeypatch, capsys) -> None:
    bead = {"status": "closed", "labels": [], "notes": ""}
    code = _run(mod, monkeypatch, ["c1"], show=_show(bead))
    assert code == mod.STATUS
    assert "implementation phase is over" in capsys.readouterr().out


def test_in_review_status_aborts(mod, monkeypatch) -> None:
    bead = {"status": "in_review", "labels": [], "notes": ""}
    assert _run(mod, monkeypatch, ["r1"], show=_show(bead)) == mod.STATUS


def test_in_progress_resumes(mod, monkeypatch, capsys) -> None:
    bead = {
        "status": "in_progress",
        "title": "t",
        "issue_type": "bug",
        "labels": [],
        "notes": "",
    }
    code = _run(mod, monkeypatch, ["p1"], show=_show(bead))
    assert code == mod.PROCEED
    assert "already claimed — resuming" in capsys.readouterr().out


def test_open_proceeds_and_emits_context(mod, monkeypatch, capsys) -> None:
    bead = {
        "status": "open",
        "title": "fix the thing",
        "issue_type": "bug",
        "labels": ["model:sonnet"],
        "description": "a description",
        "notes": "verify: pytest",
    }
    code = _run(mod, monkeypatch, ["ok1"], show=_show(bead))
    out = capsys.readouterr().out
    assert code == mod.PROCEED
    assert "PROCEED: ok1 is workable." in out
    assert "fix the thing" in out and "model:sonnet" in out
    assert "a description" in out and "verify: pytest" in out


def test_unmet_blocker_aborts(mod, monkeypatch, capsys) -> None:
    bead = {"status": "open", "labels": [], "notes": ""}
    deps = _proc(0, json.dumps([{"id": "blk-1", "status": "open"}]))
    code = _run(mod, monkeypatch, ["b1"], show=_show(bead), deps=deps)
    out = capsys.readouterr().out
    assert code == mod.BLOCKED
    assert "blk-1" in out and "unmet blocker" in out


def test_closed_blocker_does_not_block(mod, monkeypatch) -> None:
    bead = {
        "status": "open",
        "title": "t",
        "issue_type": "task",
        "labels": [],
        "notes": "",
    }
    deps = _proc(0, json.dumps([{"id": "blk-1", "status": "closed"}]))
    assert _run(mod, monkeypatch, ["b2"], show=_show(bead), deps=deps) == mod.PROCEED


# --- SKILL.md <-> script contract ------------------------------------------


def test_skill_invokes_the_script() -> None:
    body = SKILL.read_text()
    assert "scripts/validate-bead" in body, "SKILL.md must call the validator"


def test_skill_documents_every_exit_code() -> None:
    body = SKILL.read_text()
    for code in ("`0`", "`1`", "`2`", "`3`", "`4`"):
        assert code in body, f"SKILL.md exit-code table missing {code}"
