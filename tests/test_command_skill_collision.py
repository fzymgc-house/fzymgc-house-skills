"""Guard against the command/skill name-collision loop (bead fhsk-hcb, PR #124).

Claude Code merges custom commands into the skills namespace, so a
`dev-flow/commands/<X>.md` command and a `dev-flow/skills/<X>/SKILL.md` skill
both register as `dev-flow:<X>`. For plugin-packaged entries the command shadows
the skill, so a thin wrapper whose body says "invoke the <X> skill" resolves
`Skill(dev-flow:<X>)` back to itself and loops, never reaching the skill body.

A skill already provides its own `/<X>` slash command (the directory name), takes
arguments via `$ARGUMENTS`, and declares an autocomplete hint via
`argument-hint` — so a same-named command is pure redundancy. The fix removed the
`solving-a-bead` and `capture-adrs` command wrappers; this test asserts the
invariant holds for good: no dev-flow command may share a name with a skill.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = REPO_ROOT / "dev-flow" / "commands"
SKILLS = REPO_ROOT / "dev-flow" / "skills"


def _skill_names() -> set[str]:
    return {p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists()}


def test_no_command_shares_a_name_with_a_skill() -> None:
    skill_names = _skill_names()
    collisions = sorted(c.stem for c in COMMANDS.glob("*.md") if c.stem in skill_names)
    assert not collisions, (
        "dev-flow commands collide with same-named skills; in Claude Code's "
        "merged command/skill namespace the command shadows the skill and thin "
        "wrappers loop. A skill already provides its own /<name> slash command, "
        "so drop the command and let the skill be the entry point. Offenders: "
        f"{collisions}"
    )
