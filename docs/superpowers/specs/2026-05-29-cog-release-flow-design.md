# Design: Replace release-please with a cog tag-only release flow

- **Design bead:** fhsk-9g0
- **Date:** 2026-05-29
- **Status:** Draft for review

## Problem

The marketplace repo uses `googleapis/release-please-action` to manage **15
independently-versioned packages** (`.release-please-manifest.json` +
`release-please-config.json`), each with its own version stream, per-package
changelog, and release PR. That machinery is heavy and, on inspection, mostly
ceremony:

- Claude Code installs/updates plugins by **git commit SHA**, not by the
  semver in `plugin.json` or `marketplace.json` (the live install tracks
  `f878d22c03b7`, not `jj@0.6.1`).
- The in-file versions are already **inconsistent** with the manifest
  (`jj/plugin.json` = `0.1.0` vs manifest `jj = 0.6.1`) and nothing breaks.
- Per-skill `# x-release-please-version` markers and per-package changelogs are
  not consumed by any installer or by the marketplace UI.

The goal is a **simpler release process** modeled on the holomush repo: a
single repo-wide version derived by **cocogitto (`cog`)** from conventional
commits, tag-only (no commits to protected `main`), with GitHub Release notes,
triggered manually. Conventional-commit validation moves to CI because this is
a colocated **jj** repo where git `commit-msg` hooks do not fire reliably.

## Decisions (locked with the user)

1. **Single repo-wide version.** Drop the 15 per-package versions and all
   per-skill markers.
2. **Tag-only + GitHub Release notes.** `cog` creates a `vX.Y.Z` tag and a
   GitHub Release; **no commit to `main`**.
3. **Manual dispatch + guard.** `task release:cut` runs the release workflow
   via `workflow_dispatch`, with an `expected_increment` guard (holomush model).
4. **CI PR-title validation.** A CI job runs `cog verify` on the PR title (the
   squash-merge commit that `cog` later reads). The local lefthook
   `commit-msg` hook is removed.
5. **Remove all in-file version fields.** Versioning is by git SHA (machine) +
   git tag (human changelog marker). Confirmed safe: every `version` field is
   optional; only `plugin.json` `name` is required; SKILL.md has no real
   version field.

## Grounding

- **plugins-reference docs (authoritative):** version resolution order is
  `plugin.json` → marketplace entry → **git commit SHA** → `unknown`. Omitting
  `version` yields SHA-based updates (every commit is a new version). Per the
  plugin-manifest schema, **`name` is the sole required field**. Source:
  official `plugins-reference.md` §"Version management" + manifest schema
  (verified via claude-code-guide against the live docs). Note: deepwiki's
  indexed copy of the marketplace schema is **stale** and still shows `version`
  as required — the official docs supersede it. This is the load-bearing claim
  for removing in-file versions, so it is grounded against the primary source,
  not deepwiki.
- **cocogitto 7 (context7 `/cocogitto/cocogitto`):** supports
  `disable_bump_commit = true` (tag only, no commit), `disable_changelog`,
  `branch_whitelist`, `tag_prefix`, and `cog changelog <range>` to produce
  release-note bodies independently of the in-repo changelog.
- **holomush prior art:** cog 7.0.0 pinned by sha256 in a composite action;
  `task release:cut` wraps `gh workflow run release.yaml`; release dispatched
  with an `expected_increment` guard; tag-only via `disable_changelog`.

## Design

### Component 1 — `cog.toml` (release engine)

Extend the existing validation-only config:

```toml
tag_prefix = "v"
branch_whitelist = ["main"]
ignore_merge_commits = true
disable_changelog = true        # no in-repo CHANGELOG.md (no commit to main)
disable_bump_commit = true      # TAG ONLY — cog never commits to main
# NO [commit_types] block — see migration note (the current all-`{}` block is
# deleted, not edited; cog's built-in defaults cover the standard types).
```

`cog bump --auto` derives the next semver from conventional commits since the
last tag and creates the `vX.Y.Z` tag and nothing else.

**Migration note (not additive):** the *current* `cog.toml` wraps its keys in a
`[settings]` table **and** lists every type as `feat = {}`, `fix = {}`, … cog 7
rejects an unknown `[settings]` section, so the rewrite moves the keys to
**top-level** and **removes the `[settings]` wrapper** (the holomush cog.toml
confirms this). Critically, the entire `[commit_types]` block is **deleted**,
not edited: cog's built-in defaults already allow the standard types
(`feat fix docs style refactor perf test build ci chore revert`), and an empty
`{}` entry *disables* a type — making `cog verify`/`cog bump` reject it (the
holomush footgun). Only re-introduce `[commit_types]` if a **new** type is
needed, and then only as a non-empty table, e.g.
`deps = { omit_from_changelog = true }`.

### Component 2 — `.github/actions/install-cog` (pinned tool)

Composite action that downloads a pinned `cog` release binary, verifies its
SHA256, and puts it on `PATH` (port of holomush's action; pin to a current
cog 7.x release). Used by both workflows below.

### Component 3 — `.github/workflows/release.yaml` (tag + Release)

- Trigger: `workflow_dispatch` with input `expected_increment`
  (`auto|major|minor|patch`); `auto` = no guard.
- `permissions: contents: write` only. The default `GITHUB_TOKEN` suffices —
  we create a **tag + Release**, never push to `main`, so no GitHub App token
  or branch-protection bypass is needed.
- Steps:
  1. `actions/checkout` with `fetch-depth: 0` (full history + tags for cog).
  2. Install cog (Component 2).
  3. Configure a bot git identity for tagging.
  4. **Preview + guard:** `cog bump --auto --dry-run`; if `expected_increment`
     != `auto`, assert the computed bump matches, else fail loudly.
  5. **Bump:** `cog bump --auto` creates the `vX.Y.Z` git tag **locally only**
     (`disable_bump_commit` = no commit). Capture the tag, then push it
     explicitly: `git push origin "$(git describe --tags --abbrev=0)"`. (CI
     runs on a git `actions/checkout`, so plain `git push` of the tag is
     correct — there is no jj/goreleaser remote-tag step here.)
  6. **Release notes:** `cog changelog <prev_tag>..vX.Y.Z` → body file →
     `gh release create vX.Y.Z --notes-file <file> --title vX.Y.Z`.

### Component 4 — `.github/workflows/commit-lint.yaml` (PR-title gate)

- Trigger: `pull_request` (`opened`, `edited`, `synchronize`,
  `reopened`) targeting `main`.
- Install cog; run `cog verify "<PR title>"`. Because PRs land via
  squash-merge, the PR title becomes the `main` commit message cog reads for
  versioning, so the title is the authoritative thing to validate.

### Component 5 — `Taskfile.yaml` (local ergonomics)

A thin convenience layer over existing gates and the release dispatch:

```yaml
version: "3"
tasks:
  lint:            # wraps existing gates
    cmds:
      - rumdl check **/*.md
      - jq empty .claude-plugin/marketplace.json plugins/*/.codex-plugin/plugin.json */plugin.json
      - uv run --with pytest pytest .claude/hooks/tests/ jj/hooks/tests/ tests/ -q --import-mode=importlib
  verify:          # validate recent commit messages locally
    cmds:
      - cog check
  release:preview:
    cmds:
      - cog bump --auto --dry-run
  release:cut:     # increment=auto|major|minor|patch
    cmds:
      - gh workflow run release.yaml -f expected_increment={{.increment | default "auto"}}
```

### Component 6 — Remove in-file versions

- `.claude-plugin/marketplace.json`: remove the top-level `version`.
- All 6 `plugin.json` (`homelab`, `jj`, `dev-flow` + the 3
  `plugins/*/.codex-plugin/plugin.json` Codex wrappers): remove `version`,
  keep `name` + `description`.
- All 10 `SKILL.md` metadata blocks: remove the `version:` line and its
  `# x-release-please-version` marker.

### Component 7 — Remove release-please + docs

- Delete `release-please-config.json`, `.release-please-manifest.json`,
  `.github/workflows/release-please.yml`.
- **Remove the `drift-check` job from `.github/workflows/check-skills.yml`.**
  That job (`jq -r '.packages | keys[]' release-please-config.json`) verifies
  every skill dir is registered as a release-please package; deleting the
  config without removing this job breaks CI on the next PR. With per-package
  versioning gone the drift-check has no purpose, so it is deleted (keep any
  other jobs in `check-skills.yml`).
- Remove the `commit-msg` hook from `lefthook.yml` (keep `pre-commit`).
- Rewrite the "Release Versioning" guidance in `AGENTS.md` (and the
  `CLAUDE.md` shim) to describe the cog tag-only flow and the
  "no in-file versions; SHA + tag" model.

## Version baseline (divergent histories)

The single repo-wide version **continues the `marketplace.json` lineage**
(`$.version`, `1.14.1` at time of writing — read the live value at cutover
rather than hardcoding, since release-please keeps advancing it until removed).
The divergent per-package histories tracked by
release-please — `homelab 1.0.0`, `dev-flow 0.9.0`, `jj 0.6.1`, and the per-skill
`0.x` streams — are **discarded**, not reconciled. They were never consumed by
plugin installs (which resolve by SHA), so collapsing them loses nothing a
consumer can observe. The repo's release identity going forward is the single
`v1.x` tag line seeded at cutover.

## Migration / cutover order

1. Merge PR #105 (jj hook fix) first — independent. (DONE: merged.)
2. Create a baseline tag `v<current marketplace.json $.version>` on `main`
   (e.g. `v1.14.1` — read the live value at cutover) so `cog bump --auto` has a
   starting point to compute the next bump from. This is the one-time adoption
   of the `v1.x` line; per-package tags/manifests are not migrated. Do this
   step **after** removing release-please so it cannot cut a competing release.
3. Land this change (cog config + workflows + Taskfile + removals) in one PR.
4. First real release: `task release:cut` → verify the tag + GitHub Release.

## Testing / verification

- `cog --version` and `cog check` run locally and in CI.
- `cog bump --auto --dry-run` on a branch with a `feat:`/`fix:` since the
  baseline tag prints the expected next version.
- `jq empty` passes on all manifests after version removal.
- `actionlint` (or `task lint:actions` if added) on the two new workflows.
- Marketplace still loads with `version` removed (plugins resolve to SHA) —
  smoke-checked by reinstalling the marketplace locally.
- `cog verify` rejects a non-conventional PR title and accepts a conventional
  one.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| In-file versions removed → `/plugin` shows SHA not semver | Intended; SHA is already what installs track. Tag/Release is the human changelog. |
| Manual release cadence means releases can be forgotten | Acceptable and intended (deliberate human action). `task release:cut` makes it one command. |
| `cog bump` finds no baseline tag and miscomputes | Cutover step 2 creates the baseline tag (current `marketplace.json` `$.version`) before the first real bump. |
| Codex wrapper schema rejects missing `version` | Codex wrappers are thin mirrors; verify Codex still loads, else keep `version` only there. |
| Tag protection rules block `GITHUB_TOKEN` tag creation | None known on this repo; if added later, mint a scoped App token (holomush pattern). |

## Out of scope

- Per-package / per-skill versioning (explicitly dropped).
- Building or publishing any artifact (no GoReleaser equivalent needed — the
  repo ships source plugins consumed by git ref).
- Changing plugin **update cadence** (remains SHA-based / every-commit under
  autoUpdate).
<!-- adr-capture: sha256=00fc568cff35c8b1; session=cli; ts=2026-05-29T12:43:19Z; adrs=fhsk-7y4,fhsk-toy,fhsk-h3z -->
