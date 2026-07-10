---
phase: 05-governance-reconciliation-reuse-hardening
reviewed: 2026-07-10T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - docs/adoption.md
  - docs/adr/fhsk-dgo-use-release-please-file-plugin-versions-reverse-cog-tag-only.md
  - docs/adr/fhsk-o9o-use-release-please-file-plugin-versions-across-six-shipped-m.md
  - docs/adr/fhsk-wdk-record-shipped-5-plugin-root-layout-superseding-design-plan.md
  - docs/adr/README.md
  - tests/test_skill_catalog.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-07-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Five of the six files are governance artifacts (four ADR-related markdown
files, one adoption guide) rendered/authored around the release-please
six-manifest reconciliation and the shipped 5-plugin root layout. Their
generated frontmatter/structure was treated as ground truth per the phase
brief; a factual cross-check confirmed the six-manifest list in `fhsk-o9o`
matches `release-please-config.json` exactly, the ADR index (`docs/adr/README.md`)
correctly reflects both new ADRs and the `fhsk-dgo` → `fhsk-o9o` supersession,
and the 5-plugin catalog in `docs/adoption.md` matches the actual on-disk
plugin roots (`homelab`, `jj`, `dev-flow`, `tmux`, `grepping`). No factual
inconsistencies were found in the docs.

The substantive review target, `tests/test_skill_catalog.py`, is a real drift
gate: it enumerates `*/skills/*/SKILL.md` on disk (verified to correctly
exclude the developer's local, gitignored `.claude/skills/*` symlink farm,
and to correctly avoid double-counting the `plugins/<name>/skills` Codex
wrapper symlinks, which sit one directory level too deep to match the glob)
and asserts every shipped skill name is mentioned in both `README.md`'s
`## Plugins` region and the whole of `docs/adoption.md`. The glob enumeration
and directory-name-as-catalog-token heuristic were spot-checked against all
32 shipped `SKILL.md` files and hold today. However, the two "membership"
assertions are implemented asymmetrically and both check only one direction
of the invariant (disk → docs, never docs → disk), which weakens the gate's
ability to catch real drift in ways detailed below.

## Warnings

### WR-01: Adoption-index completeness check is unbounded, unlike the README check — false-pass risk if the Discovery Index table drifts

**File:** `tests/test_skill_catalog.py:49-60`
**Issue:** `test_every_skill_in_readme_catalog` scopes its search to the `##
Plugins` … `## Installation` region via `_readme_catalog_region()` (lines
28-32), so a skill name is only counted as "present" if it appears inside the
actual catalog table. `test_every_skill_in_adoption_index`, by contrast,
searches the _entire_ `docs/adoption.md` text (`adoption_text = ADOPTION_PATH.read_text()`,
line 52) with no equivalent bounding to the `## Discovery index` section.
This means a skill's `**name**` token satisfies the assertion whether it
appears in its Discovery Index table row or anywhere else in the file — e.g.
in the "Troubleshooting" prose, an install-path code block, or a future
sentence like "if **grepping** fails to install…". If a maintainer ever
deletes or mis-edits a Discovery Index row for a skill whose name still
happens to be mentioned elsewhere in the doc (which is plausible given the
doc explicitly discusses `grepping`, `jujutsu`, `tmux`, etc. by name outside
the table already), CI would pass even though the actual discovery contract
the doc claims to enforce (adoption.md:38-41: "This table is the enforced
discovery contract") is broken. This is currently a latent risk, not an
active failure, but it is a real gap in the drift gate the phase brief asked
to assess.
**Fix:** Bound the adoption-index search the same way the README search is
bounded:

```python
def _adoption_index_region() -> str:
    text = ADOPTION_PATH.read_text()
    match = re.search(
        r"## Discovery index\n(.*?)\n## Troubleshooting", text, flags=re.DOTALL
    )
    assert match, "docs/adoption.md is missing the '## Discovery index' ... '## Troubleshooting' region"
    return match.group(1)


def test_every_skill_in_adoption_index() -> None:
    assert ADOPTION_PATH.exists(), f"Missing canonical adoption guide: {ADOPTION_PATH}"

    index_region = _adoption_index_region()
    missing = [
        name for name in _shipped_skill_names() if f"**{name}**" not in index_region
    ]
    ...
```

### WR-02: Catalog checks only verify disk → docs, never docs → disk — stale/orphaned entries are never caught

**File:** `tests/test_skill_catalog.py:35-60`
**Issue:** Both `test_every_skill_in_readme_catalog` and
`test_every_skill_in_adoption_index` compute `missing` as skills present on
disk but absent from the docs. Neither test computes the converse: catalog
rows/entries that no longer correspond to any `*/skills/*/SKILL.md` on disk
(e.g. a skill directory renamed or deleted without updating the README table
or the adoption Discovery Index). Such stale rows will never fail CI under
the current test, so the "drift gate" only catches under-documentation, not
over-documentation/staleness — a real skill catalog could silently
accumulate phantom entries for skills that no longer exist, which is exactly
the kind of governance drift this phase is meant to reconcile against.
**Fix:** Add a reverse check per surface, extracting bolded `**name**` tokens
from each bounded region and asserting they're a subset of
`_shipped_skill_names()`:

```python
def _bolded_names(region: str) -> set[str]:
    return set(re.findall(r"\*\*([a-z0-9][a-z0-9-]*)\*\*", region))

def test_readme_catalog_has_no_stale_skills() -> None:
    shipped = set(_shipped_skill_names())
    stale = _bolded_names(_readme_catalog_region()) - shipped
    assert not stale, f"README.md '## Plugins' catalog references skills no longer on disk: {sorted(stale)}"
```

(Adjust the regex to exclude non-skill bold tokens such as backtick'd agent
names if adopted for the adoption index too.)

## Info

### IN-01: Directory-name-as-catalog-token heuristic is documented but not enforced

**File:** `tests/test_skill_catalog.py:12-18`
**Issue:** The docstring for `_shipped_skill_names()` states "Directory name
== SKILL.md `name` frontmatter for all shipped skills" and uses this as
justification for avoiding YAML parsing. This was spot-checked and holds for
all 32 currently shipped skills, but nothing in the test enforces it going
forward — if a future skill's frontmatter `name:` diverges from its
directory name, `_shipped_skill_names()` would silently use the wrong token
for the README/adoption membership checks (validating the directory name's
presence in the docs rather than the name a consumer would actually
reference), and the mismatch itself would go undetected.
**Fix:** Either add a cheap assertion that cross-checks frontmatter `name:`
against directory name for each discovered `SKILL.md` (a single-line regex
read, no full YAML parser needed), or explicitly accept the risk with a
`# noqa`-style comment pointing at an issue/bead tracking the assumption.

---

_Reviewed: 2026-07-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
