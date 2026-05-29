# cog Tag-Only Release Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace release-please's 15-package monorepo versioning with a single repo-wide, tag-only release derived by cocogitto (`cog`), with GitHub Release notes, manual dispatch, and CI PR-title validation.

**Architecture:** `cog` becomes both the commit validator (CI, on PR titles) and the release engine (`cog bump --auto` → `vX.Y.Z` tag only, no commit to `main`). A `workflow_dispatch` workflow creates the tag + GitHub Release (`cog changelog` notes). All in-file `version` fields are removed — plugins are versioned by git SHA (machine) and the tag is the human release marker. A `Taskfile.yaml` wraps local ergonomics.

**Tech Stack:** cocogitto 7.0.0 (pinned by sha256), GitHub Actions, go-task (Taskfile), jq, jj (colocated repo).

**Spec:** `docs/superpowers/specs/2026-05-29-cog-release-flow-design.md` · **Design bead:** fhsk-9g0

**Conventions for this plan:** This is infrastructure/config work, not application code, so "tests" are concrete verification commands with expected output rather than unit tests. Commit after each task with `jj commit -m "..."` (see `references/vcs-preamble.md`; this is a colocated jj repo — use jj for all VCS mutations). Each task is independently committable.

---

## Task 1: Rewrite `cog.toml` as the release engine

**Files:**

- Modify: `cog.toml` (full replacement)

- [ ] **Step 1: Replace `cog.toml` with the release-engine config**

Replace the entire file with:

```toml
# Cocogitto configuration — https://docs.cocogitto.io/
#
# cog is BOTH the commit-message validator (CI, on PR titles via
# .github/workflows/commit-lint.yaml) AND the release engine: `cog bump --auto`
# derives the next semver from conventional commits and creates a TAG ONLY
# (no bump commit, no in-repo CHANGELOG.md). GitHub Release notes are produced
# by `cog changelog` in .github/workflows/release.yaml.
#
# cog 7 note: these are TOP-LEVEL keys, NOT nested under [settings] (cog 7
# rejects an unknown [settings] section). The built-in commit-type allow-list
# (feat fix docs style refactor perf test build ci chore revert) is used as-is:
# there is intentionally NO [commit_types] block, because an empty `feat = {}`
# entry DISABLES that type and makes `cog verify`/`cog bump` reject it. Only add
# a [commit_types] block to introduce a NEW type, and then only as a non-empty
# table, e.g. deps = { omit_from_changelog = true }.

tag_prefix = "v"
branch_whitelist = ["main"]
ignore_merge_commits = true
disable_changelog = true        # no in-repo CHANGELOG.md (no commit to main)
disable_bump_commit = true      # TAG ONLY — cog never commits to main
```

- [ ] **Step 2: Verify cog accepts the config and still validates messages**

Run: `cog --version && cog verify "feat(release): adopt cog tag-only flow" && cog verify "not a conventional commit" ; echo "exit=$?"`
Expected: prints a cog 7.x version; the first `cog verify` succeeds ("No errored commits"); the second prints an error and the final `exit=` is non-zero (proves validation still works).

- [ ] **Step 3: Verify dry-run bump parses (baseline tag may not exist yet)**

Run: `cog bump --auto --dry-run 2>&1 | head -5`
Expected: either a computed version line, or a message that there is no previous tag / nothing to bump. Either is acceptable — it confirms the config is parseable and `disable_bump_commit`/`disable_changelog` are accepted (no "unknown field" / "unknown setting [settings]" error). A config error here is a FAIL.

- [ ] **Step 4: Commit**

Run: `jj commit -m "feat(release): make cog.toml the tag-only release engine"`

---

### Task 2: Add the pinned `install-cog` composite action

**Files:**

- Create: `.github/actions/install-cog/action.yml`

- [ ] **Step 1: Create the composite action**

Create `.github/actions/install-cog/action.yml`:

```yaml
name: Install Cocogitto
# Download the pinned cog binary, verify its SHA256, and put it on PATH.
# Pinned to the same 7.0.0 release + checksum used by the holomush repo
# (verified working in that CI). The x86_64 musl tarball nests the binary under
# x86_64-unknown-linux-musl/, so --strip-components=1 lands /usr/local/bin/cog.
description: Install the pinned cog binary and add it to PATH.

runs:
  using: composite
  steps:
    - name: Install cocogitto
      shell: bash
      run: |
        set -euo pipefail
        COG_VERSION="7.0.0"
        COG_TARBALL="cocogitto-${COG_VERSION}-x86_64-unknown-linux-musl.tar.gz"
        COG_URL="https://github.com/cocogitto/cocogitto/releases/download/${COG_VERSION}/${COG_TARBALL}"
        COG_SHA256="e03938ff2c4c86d71c00c0f3284dbbe95c5ca76fe34a51f33e945c23010d59bb"
        curl -LsSfO "$COG_URL"
        echo "${COG_SHA256}  ${COG_TARBALL}" | sha256sum -c -
        sudo tar xzf "$COG_TARBALL" --overwrite --strip-components=1 \
          -C /usr/local/bin x86_64-unknown-linux-musl/cog
        rm "$COG_TARBALL"
    - name: Verify cog
      shell: bash
      run: cog --version
```

- [ ] **Step 2: Verify the action file is valid YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/actions/install-cog/action.yml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

Run: `jj commit -m "ci(release): add sha256-pinned install-cog composite action"`

---

### Task 3: Add the `release.yaml` workflow (tag + GitHub Release)

**Files:**

- Create: `.github/workflows/release.yaml`

- [ ] **Step 1: Create the release workflow**

Create `.github/workflows/release.yaml`:

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      expected_increment:
        description: "Guard: fail if cog computes a different bump (auto = no guard)"
        required: false
        default: "auto"
        type: choice
        options:
          - auto
          - major
          - minor
          - patch

permissions:
  contents: read

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write # create the tag + GitHub Release
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
        with:
          fetch-depth: 0 # full history + tags so cog can compute the bump

      - name: Install cog
        uses: ./.github/actions/install-cog

      - name: Configure git identity for tagging
        run: |
          git config user.name "fzymgc-release[bot]"
          git config user.email "fzymgc-release[bot]@users.noreply.github.com"

      - name: Preview and guard the computed bump
        env:
          EXPECTED: ${{ inputs.expected_increment }}
        run: |
          set -euo pipefail
          echo "Computed next version (dry-run):"
          cog bump --auto --dry-run
          if [ "$EXPECTED" != "auto" ]; then
            CUR="$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo '0.0.0')"
            NEXT="$(cog bump --auto --dry-run 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | tail -n1)"
            [ -n "$NEXT" ] || { echo "::error::could not compute next version"; exit 1; }
            IFS=. read -r cmaj cmin _ <<< "$CUR"
            IFS=. read -r nmaj nmin _ <<< "$NEXT"
            if   [ "$nmaj" -gt "$cmaj" ]; then KIND=major
            elif [ "$nmin" -gt "$cmin" ]; then KIND=minor
            else KIND=patch; fi
            if [ "$KIND" != "$EXPECTED" ]; then
              echo "::error::expected '$EXPECTED' bump but cog computed '$KIND' ($CUR -> $NEXT)"
              exit 1
            fi
            echo "Guard OK: $KIND bump ($CUR -> $NEXT)"
          fi

      - name: Bump (create tag only) and push the tag
        run: |
          set -euo pipefail
          cog bump --auto
          TAG="$(git describe --tags --abbrev=0)"
          echo "TAG=$TAG" >> "$GITHUB_ENV"
          git push origin "$TAG"

      - name: Create GitHub Release with cog changelog notes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          PREV="$(git describe --tags --abbrev=0 "${TAG}^" 2>/dev/null || true)"
          if [ -n "$PREV" ]; then RANGE="${PREV}..${TAG}"; else RANGE="$TAG"; fi
          cog changelog "$RANGE" > /tmp/release-notes.md
          gh release create "$TAG" --title "$TAG" --notes-file /tmp/release-notes.md
```

- [ ] **Step 2: Verify the workflow is valid YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yaml')); print('ok')"`
Expected: `ok`. If `actionlint` is installed, also run `actionlint .github/workflows/release.yaml` (expected: no errors); otherwise CI will lint it.

- [ ] **Step 3: Commit**

Run: `jj commit -m "ci(release): add manual-dispatch tag-only release workflow"`

---

### Task 4: Add the `commit-lint.yaml` workflow (PR-title gate)

**Files:**

- Create: `.github/workflows/commit-lint.yaml`

- [ ] **Step 1: Create the PR-title validation workflow**

Create `.github/workflows/commit-lint.yaml`:

```yaml
name: Commit Lint

on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
    branches: [main]

permissions:
  contents: read

jobs:
  pr-title:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
      - name: Install cog
        uses: ./.github/actions/install-cog
      - name: Verify PR title is a conventional commit
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: cog verify "$PR_TITLE"
```

- [ ] **Step 2: Verify the workflow is valid YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/commit-lint.yaml')); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

Run: `jj commit -m "ci(release): validate PR titles with cog verify"`

---

### Task 5: Add `Taskfile.yaml` for local ergonomics

**Files:**

- Create: `Taskfile.yaml`

- [ ] **Step 1: Create the Taskfile**

Create `Taskfile.yaml`:

```yaml
version: "3"

tasks:
  lint:
    desc: Run repo quality gates (markdown, JSON, hook tests)
    cmds:
      - rumdl check README.md AGENTS.md CLAUDE.md docs/plans/*.md
      - jq empty .claude-plugin/marketplace.json .agents/plugins/marketplace.json homelab/plugin.json jj/plugin.json dev-flow/plugin.json plugins/*/.codex-plugin/plugin.json
      - uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ dev-flow/hooks/tests/ tests/ -q --import-mode=importlib

  verify:
    desc: Validate commit history against conventional-commit rules
    cmds:
      - cog check

  release:preview:
    desc: Show the next version cog would compute (no side effects)
    cmds:
      - cog bump --auto --dry-run

  release:cut:
    desc: "Cut a release via GitHub Actions. Args: increment=auto|major|minor|patch"
    cmds:
      - gh workflow run release.yaml -f expected_increment={{.increment | default "auto"}}
```

- [ ] **Step 2: Verify the Taskfile parses and lists tasks**

Run: `task --list`
Expected: lists `lint`, `verify`, `release:preview`, `release:cut` with their descriptions. (Requires go-task: `brew install go-task` if `task` is not found.)

- [ ] **Step 3: Commit**

Run: `jj commit -m "build(release): add Taskfile for lint/verify/release ergonomics"`

---

### Task 6: Remove all in-file `version` fields

**Files:**

- Modify: `.claude-plugin/marketplace.json`
- Modify: `homelab/plugin.json`, `jj/plugin.json`, `dev-flow/plugin.json`
- Modify: `plugins/homelab/.codex-plugin/plugin.json`, `plugins/jj/.codex-plugin/plugin.json`, `plugins/dev-flow/.codex-plugin/plugin.json`
- Modify: 10 `SKILL.md` files (see Step 4)
- [ ] **Step 1: Remove the top-level `version` from the Claude marketplace manifest**

In `.claude-plugin/marketplace.json`, delete the line:

```json
  "version": "1.13.1",
```

(The `$schema`, `name`, then `description` lines remain; `version` is optional per the plugins-reference docs.)

- [ ] **Step 2: Remove `version` from the 3 source `plugin.json` files**

Each becomes exactly (only `name` + `description`):

`homelab/plugin.json`:

```json
{
  "name": "homelab",
  "description": "Infrastructure skills for homelab cluster (Grafana, Terraform)"
}
```

`jj/plugin.json`:

```json
{
  "name": "jj",
  "description": "Jujutsu (jj) VCS workflow guidance for colocated and standalone repos"
}
```

`dev-flow/plugin.json`:

```json
{
  "name": "dev-flow",
  "description": "Development workflow skills with git and jj VCS support (fork of obra/superpowers v5.0.2)"
}
```

- [ ] **Step 3: Remove `version` from the 3 Codex wrapper `plugin.json` files**

In each of `plugins/homelab/.codex-plugin/plugin.json`, `plugins/jj/.codex-plugin/plugin.json`, `plugins/dev-flow/.codex-plugin/plugin.json`, delete the `"version": "...",` line (the 3rd line, between `"name"` and `"description"`). Leave every other field unchanged. The Codex marketplace (`.agents/plugins/marketplace.json`) pins plugins by `source.path` and carries no per-plugin version or schema ref, so this is safe. (Fallback: if Codex tooling later rejects the missing field, restore `version` in only these three files.)

- [ ] **Step 4: Remove the `version` marker line from all 10 SKILL.md files**

Each affected SKILL.md has, inside its `metadata:` block, exactly one line of the form `version: 0.1.0 # x-release-please-version`. Delete that single line in each file. Find them with:

Run: `rg -l "x-release-please-version" --glob '!docs/**'`
Expected list (10 files): `homelab/skills/grafana/SKILL.md`, `homelab/skills/terraform/SKILL.md`, `homelab/skills/skill-qa/SKILL.md`, `jj/skills/jujutsu/SKILL.md`, `dev-flow/skills/handoff-prompt/SKILL.md`, `dev-flow/skills/using-worktrees/SKILL.md`, `dev-flow/skills/requesting-code-review/SKILL.md`, `dev-flow/skills/finishing-a-development-branch/SKILL.md`, `dev-flow/skills/plan-to-beads/SKILL.md`, `dev-flow/skills/bead-create-smart/SKILL.md`.

For each file, remove the `version: ... # x-release-please-version` line. If the `metadata:` block becomes `metadata:\n  author: fzymgc-house` (author remains), that is fine; if a block would be left empty, leave `metadata:` with its remaining key(s) — do not remove `author`.

- [ ] **Step 5: Verify no version markers remain and all JSON is valid**

Run: `rg -n "x-release-please-version" --glob '!docs/**' ; echo "markers_exit=$?"`
Expected: no matches, `markers_exit=1`.

Run: `jq empty .claude-plugin/marketplace.json homelab/plugin.json jj/plugin.json dev-flow/plugin.json plugins/*/.codex-plugin/plugin.json && echo "json ok"`
Expected: `json ok` (all manifests still valid).

Run: `python3 -c "import json; d=json.load(open('homelab/plugin.json')); assert 'version' not in d and d['name']=='homelab'; print('ok')"`
Expected: `ok`.

- [ ] **Step 6: Verify SKILL.md frontmatter still parses**

Run: `rg -L -c "^---$" jj/skills/jujutsu/SKILL.md homelab/skills/grafana/SKILL.md`
Expected: each file still shows 2 `---` fence lines (frontmatter intact).

Run: `rumdl check jj/skills/jujutsu/SKILL.md homelab/skills/grafana/SKILL.md homelab/skills/terraform/SKILL.md homelab/skills/skill-qa/SKILL.md dev-flow/skills/handoff-prompt/SKILL.md dev-flow/skills/using-worktrees/SKILL.md dev-flow/skills/requesting-code-review/SKILL.md dev-flow/skills/finishing-a-development-branch/SKILL.md dev-flow/skills/plan-to-beads/SKILL.md dev-flow/skills/bead-create-smart/SKILL.md`
Expected: `Success: No issues found`.

- [ ] **Step 7: Commit**

Run: `jj commit -m "refactor(release): remove in-file version fields (SHA + tag are authoritative)"`

---

### Task 7: Remove release-please machinery, the drift-check job, and the commit-msg hook; update docs

**Files:**

- Delete: `release-please-config.json`
- Delete: `.release-please-manifest.json`
- Delete: `.github/workflows/release-please.yml`
- Modify: `.github/workflows/check-skills.yml` (remove the `drift-check` job)
- Modify: `lefthook.yml` (remove the `commit-msg` block)
- Modify: `AGENTS.md` (rewrite "Release Versioning")
- Modify: `CLAUDE.md` (rewrite "Release Versioning" + the commit-msg validation line)
- [ ] **Step 1: Delete the release-please files**

Run: `rm -f release-please-config.json .release-please-manifest.json .github/workflows/release-please.yml`

- [ ] **Step 2: Remove the `drift-check` job from `check-skills.yml`**

In `.github/workflows/check-skills.yml`, delete the entire `drift-check:` job (the block from `drift-check:` through the end of its final `exit 1` / `fi` line, up to but not including `test:`). Keep the `name`, `on`, `permissions` headers and the `test:` and `lint:` jobs unchanged. The job is removed because it validated that every skill dir was registered as a release-please package — with per-package versioning gone, it reads a file that no longer exists (`release-please-config.json`) and would fail every PR.

- [ ] **Step 3: Verify `check-skills.yml` is valid and no longer references release-please**

Run: `python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/check-skills.yml')); print(sorted(d['jobs']))"`
Expected: `['lint', 'test']` (no `drift-check`).

Run: `rg -n "release-please" .github/workflows/check-skills.yml ; echo "exit=$?"`
Expected: no matches, `exit=1`.

- [ ] **Step 4: Remove the `commit-msg` hook from `lefthook.yml`**

In `lefthook.yml`, delete the trailing block:

```yaml
commit-msg:
  commands:
    conventional-commit:
      run: cog verify --file {1}
```

Keep the entire `pre-commit:` section unchanged. (Validation now happens on PR titles in CI; the local git `commit-msg` hook does not fire reliably in this jj repo anyway.)

- [ ] **Step 5: Verify `lefthook.yml` is valid and has no commit-msg hook**

Run: `python3 -c "import yaml; d=yaml.safe_load(open('lefthook.yml')); assert 'commit-msg' not in d; assert 'pre-commit' in d; print('ok')"`
Expected: `ok`.

- [ ] **Step 6: Rewrite the "Release Versioning" section in `AGENTS.md`**

Replace the current section (the block starting `### Release Versioning` through the `- \`.release-please-manifest.json\`` line, i.e. lines that mention release-please and the in-sync files) with:

```markdown
### Release Versioning

Releases are cut with cocogitto (`cog`), tag-only. There are **no in-file
version numbers** — plugins are versioned by git commit SHA (how Claude Code
and Codex actually resolve installs) and each release is a single repo-wide
`vX.Y.Z` git tag (the human-facing marker). Do not add `version` fields back to
`marketplace.json`, `plugin.json`, `.codex-plugin/plugin.json`, or `SKILL.md`.

To cut a release: `task release:cut` (optionally `increment=major|minor|patch`
to guard the computed bump). This dispatches `.github/workflows/release.yaml`,
which runs `cog bump --auto` to create the tag and a GitHub Release with notes
from `cog changelog`. `cog` never commits to `main`
(`disable_bump_commit`/`disable_changelog`). Conventional-commit validation
runs in CI on the PR title (`.github/workflows/commit-lint.yaml`).
```

- [ ] **Step 7: Rewrite the matching guidance in `CLAUDE.md`**

In `CLAUDE.md`:

- Replace the line `Validation is enforced by \`cog verify\` in the commit-msg hook.` with:
  `Conventional-commit validation runs in CI on the PR title (\`.github/workflows/commit-lint.yaml\`); there is no local commit-msg hook (jj does not fire git hooks reliably).`
- Replace the `### Release Versioning` section (the release-please paragraph + the two bullet lists) with the same replacement text used for `AGENTS.md` in Step 6.
- [ ] **Step 8: Verify docs are consistent and lint-clean**

Run: `rg -n "release-please" AGENTS.md CLAUDE.md ; echo "exit=$?"`
Expected: no matches, `exit=1`.

Run: `rumdl check AGENTS.md CLAUDE.md`
Expected: `Success: No issues found`.

- [ ] **Step 9: Verify the repo-wide release-please references are gone**

Run: `rg -n "release-please" --glob '!docs/**' --glob '!**/CHANGELOG.md' ; echo "exit=$?"`
Expected: no matches, `exit=1` (historical references under `docs/` and generated `CHANGELOG.md` files are intentionally left untouched).

- [ ] **Step 10: Commit**

Run: `jj commit -m "chore(release): remove release-please, drift-check job, and commit-msg hook"`

---

### Task 8: Cutover — baseline tag and first release (post-merge, operational)

> Run this task **after** Tasks 1–7 have merged to `main`. It is operational (creates a real tag and Release), not a code change, so it has no commit step of its own.

**Files:** none (operates on git tags + GitHub).

- [ ] **Step 1: Confirm release-please is gone from `main`**

Run: `git ls-files | rg -n "release-please-config.json|.release-please-manifest.json|workflows/release-please.yml" ; echo "exit=$?"`
Expected: no matches, `exit=1` (the deletions are merged, so release-please cannot cut a competing release during cutover).

- [ ] **Step 2: Create the baseline tag from the last marketplace version**

The repo-wide version continues the marketplace lineage. Read the value release-please last shipped (from the last `chore: release main` merge / the deleted manifest's history) and tag it. At time of writing that value is `1.13.1`; confirm the actual last released version before tagging.

Run: `git tag v1.13.1 && git push origin v1.13.1` (substitute the confirmed last version).
Expected: the tag is created and pushed; `git describe --tags --abbrev=0` prints `v1.13.1`.

- [ ] **Step 3: Preview the next computed bump**

Run: `task release:preview`
Expected: `cog bump --auto --dry-run` prints a next version greater than the baseline (driven by `feat:`/`fix:` commits merged since the baseline), with no config errors.

- [ ] **Step 4: Cut the first real release**

Run: `task release:cut` (or `task release:cut increment=minor` to assert a specific bump).
Expected: the `Release` workflow dispatches; it creates the new `vX.Y.Z` tag and a GitHub Release whose notes are the grouped `cog changelog` output.

- [ ] **Step 5: Verify the release landed**

Run: `gh release list --limit 3` and `gh release view "$(git describe --tags --abbrev=0 origin/main 2>/dev/null || gh release list --limit 1 --json tagName --jq '.[0].tagName')"`
Expected: the new release appears with conventional-commit-grouped notes; the corresponding `vX.Y.Z` tag exists on the remote and `main` has **no** new commit from the release (tag-only confirmed).

---

## Notes for the implementer

- This is a jj repo: use `jj commit`/`jj describe` and `jj git push` (never `git commit`). The release **workflow** runs in CI on a plain git checkout, so the git commands inside the YAML are correct there.
- `cog`, `jq`, `rumdl`, `uv` are expected locally (used by existing gates). `task` (go-task) is new — `brew install go-task` if absent. `actionlint` is optional locally; CI lints workflows.
- Tasks 1–7 are one PR. Task 8 is the post-merge cutover and is intentionally separate.
<!-- adr-capture: sha256=34d62ed09e1a5947; session=cli; ts=2026-05-29T12:43:19Z; adrs=fhsk-7y4,fhsk-toy,fhsk-h3z -->
