"""dev-flow scripts must be invoked via ${CLAUDE_PLUGIN_ROOT}, not cwd-relative.

A repo-relative ``dev-flow/scripts/<script>`` invocation resolves only from this
plugin's own source tree. In a consumer repo that installs dev-flow via the
marketplace the scripts live in the plugin cache, not at
``<consumer>/dev-flow/scripts/`` — so the bare path fails (EXIT 127). The
``${CLAUDE_PLUGIN_ROOT}`` placeholder is substituted with the plugin install
directory in command, skill, and agent bodies and in frontmatter
``allowed-tools`` alike, so it resolves regardless of cwd.

Regression guard for bd fhsk-4pz (drain + adr commands/skills). Same bug class
as fhsk-7wj (solving-a-bead's validator), already guarded in
``test_solving_a_bead.py``. The check flags *invocations*, not source-tree
*documentation* pointers (e.g. evolve-adr's References manifest, which lists the
script path in prose alongside doc/spec paths) — see ``_cwd_relative_invocations``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [
    REPO_ROOT / "dev-flow" / "commands",
    REPO_ROOT / "dev-flow" / "skills",
    REPO_ROOT / "dev-flow" / "references",
    REPO_ROOT / "dev-flow" / "agents",
]

_MARKER = "dev-flow/scripts/"
# Characters that, immediately before the marker, mark it as an execution rather
# than a prose mention: line-start (""), a subshell/permission paren ``(`` — both
# ``$(...)`` and ``Bash(...)`` — a quote, or an assignment ``=``. A backtick
# (mid-sentence prose pointer) is deliberately excluded.
_EXEC_PREFIXES = frozenset({"", "(", '"', "'", "="})


def _md_files() -> list[Path]:
    # Fail loudly if a scanned dir is renamed/removed — rglob on a missing path
    # returns empty, which would otherwise let the guard vacuously pass.
    missing = [d for d in SCAN_DIRS if not d.is_dir()]
    assert not missing, f"SCAN_DIRS no longer exist: {missing}"
    files: list[Path] = []
    for d in SCAN_DIRS:
        files.extend(sorted(d.rglob("*.md")))
    assert files, "no markdown files collected — SCAN_DIRS globbing is broken"
    return files


def _cwd_relative_invocations(text: str) -> list[str]:
    """Return lines that *execute* a dev-flow script via a cwd-relative path.

    A line is flagged when ``dev-flow/scripts/`` appears in an execution
    position (preceded by one of ``_EXEC_PREFIXES``). ``probe`` is the
    indentation- and prompt-stripped line used for position analysis; the
    original ``line`` is what gets reported, so messages keep their context.
    """
    bad: list[str] = []
    for line in text.splitlines():
        probe = line.lstrip()
        if probe.startswith("$ "):  # drop a shown shell prompt
            probe = probe[2:]
        idx = probe.find(_MARKER)
        while idx != -1:
            prev = probe[idx - 1] if idx > 0 else ""
            if prev in _EXEC_PREFIXES:
                bad.append(line.strip())
                break
            idx = probe.find(_MARKER, idx + 1)
    return bad


@pytest.mark.parametrize(
    "path", _md_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_cwd_relative_dev_flow_script_invocations(path: Path) -> None:
    violations = _cwd_relative_invocations(path.read_text())
    assert not violations, (
        f"{path.relative_to(REPO_ROOT)} invokes a dev-flow script via a "
        "cwd-relative path. Use ${CLAUDE_PLUGIN_ROOT}/scripts/<script> so it "
        "resolves from a consumer's repo, not only this plugin's source tree. "
        "Offending lines:\n  " + "\n  ".join(violations)
    )
