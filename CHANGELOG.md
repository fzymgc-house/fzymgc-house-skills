# Changelog

## [2.0.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.25.0...v2.0.0) (2026-06-30)


### ⚠ BREAKING CHANGES

* **homelab:** remove unused grafana skill ([#181](https://github.com/fzymgc-house/fzymgc-house-skills/issues/181))

### Features

* **adr:** migrate render-adr + adr-doctor to Python/uv with Starlight frontmatter ([#184](https://github.com/fzymgc-house/fzymgc-house-skills/issues/184)) ([32bd353](https://github.com/fzymgc-house/fzymgc-house-skills/commit/32bd353ff25294d2529f60107863b706782ad2cc))
* **homelab:** remove unused grafana skill ([#181](https://github.com/fzymgc-house/fzymgc-house-skills/issues/181)) ([acdfee0](https://github.com/fzymgc-house/fzymgc-house-skills/commit/acdfee04ed1fbc78077a0403155b2041102fc972))

## [1.25.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.24.4...v1.25.0) (2026-06-14)


### Features

* **miniflux:** add Miniflux RSS feed management & curation skill (fhsk-8k8) ([#174](https://github.com/fzymgc-house/fzymgc-house-skills/issues/174)) ([6137627](https://github.com/fzymgc-house/fzymgc-house-skills/commit/613762740d180f4c3144f0977d6bb6203db98eff))


### Bug Fixes

* **dev-flow:** resolve drain/adr scripts via ${CLAUDE_PLUGIN_ROOT} ([#172](https://github.com/fzymgc-house/fzymgc-house-skills/issues/172)) ([ea5cdc4](https://github.com/fzymgc-house/fzymgc-house-skills/commit/ea5cdc48279ed0f73733457d63542ac3411052e0))
* **drain:** detect cmux by session, not PATH — symmetric mux selection (fhsk-3v3) ([#173](https://github.com/fzymgc-house/fzymgc-house-skills/issues/173)) ([02750c5](https://github.com/fzymgc-house/fzymgc-house-skills/commit/02750c58abc3d095d0b75b167b7c6f1b2781042d))
* **drain:** skip direnv gate in non-direnv repos (missing .envrc misread as blocked) ([#170](https://github.com/fzymgc-house/fzymgc-house-skills/issues/170)) ([1c1e44b](https://github.com/fzymgc-house/fzymgc-house-skills/commit/1c1e44b6973941196e70ef90cd4cf7245cb09ff7))
* **drain:** stop watchdog api-error false-positive on diff line numbers (fhsk-b43) ([#175](https://github.com/fzymgc-house/fzymgc-house-skills/issues/175)) ([39957db](https://github.com/fzymgc-house/fzymgc-house-skills/commit/39957db3cdf72180346119420d5162b76d581626))

## [1.24.4](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.24.3...v1.24.4) (2026-06-14)


### Bug Fixes

* **capture-adrs:** prevent literal \n in ADR bodies ([#168](https://github.com/fzymgc-house/fzymgc-house-skills/issues/168)) ([73ca96b](https://github.com/fzymgc-house/fzymgc-house-skills/commit/73ca96b5697e30a812038b9ba14dbd601b3df408))

## [1.24.3](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.24.2...v1.24.3) (2026-06-13)


### Bug Fixes

* **drain:** make drain-worker-launch direnv probe shell-agnostic (fish) ([#163](https://github.com/fzymgc-house/fzymgc-house-skills/issues/163)) ([d0c709b](https://github.com/fzymgc-house/fzymgc-house-skills/commit/d0c709b2d130f9762ac004a2e86a04ebafd037e6))

## [1.24.2](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.24.1...v1.24.2) (2026-06-13)


### Bug Fixes

* **drain:** escape literal % in drain-watchdog argparse help (Python 3.14) ([#159](https://github.com/fzymgc-house/fzymgc-house-skills/issues/159)) ([2f5d562](https://github.com/fzymgc-house/fzymgc-house-skills/commit/2f5d56279bb5f037e5d271ed13c97e8d59c0e5aa))
* **drain:** make drain-worker-launch direnv gate idempotent ([#158](https://github.com/fzymgc-house/fzymgc-house-skills/issues/158)) ([#161](https://github.com/fzymgc-house/fzymgc-house-skills/issues/161)) ([1fb66c5](https://github.com/fzymgc-house/fzymgc-house-skills/commit/1fb66c5b39bf14930a6ef6cc009819f675dab2d8))

## [1.24.1](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.24.0...v1.24.1) (2026-06-13)


### Bug Fixes

* **drain:** extract surface:&lt;N&gt; token in CmuxDriver.parse_ref (cmux 0.64.15) ([#155](https://github.com/fzymgc-house/fzymgc-house-skills/issues/155)) ([de10412](https://github.com/fzymgc-house/fzymgc-house-skills/commit/de104121e71d59e4d2b485b14d8fc27a27e39430))

## [1.24.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.23.0...v1.24.0) (2026-06-13)


### Features

* **drain:** tmux support for the /drain worker (parameterized skill + _muxdriver + tmux plugin) ([#151](https://github.com/fzymgc-house/fzymgc-house-skills/issues/151)) ([feb124b](https://github.com/fzymgc-house/fzymgc-house-skills/commit/feb124bf900775834367050800893025171fd939))

## [1.23.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.22.1...v1.23.0) (2026-06-13)


### Features

* **drain:** auto-finish branch (push + PR) at clean sentinel without prompting ([#146](https://github.com/fzymgc-house/fzymgc-house-skills/issues/146)) ([b24464d](https://github.com/fzymgc-house/fzymgc-house-skills/commit/b24464d9173489b32df1d658d10aed801392a4ce))


### Bug Fixes

* **drain:** write .beads/redirect when ensure-isolated-workspace creates a jj workspace ([#149](https://github.com/fzymgc-house/fzymgc-house-skills/issues/149)) ([3e4d3f0](https://github.com/fzymgc-house/fzymgc-house-skills/commit/3e4d3f0037da2f1f3b5073f55470366dc9c876ad))

## [1.22.1](https://github.com/fzymgc-house/fzymgc-house-skills/compare/v1.22.0...v1.22.1) (2026-06-10)


### Bug Fixes

* **worktrees:** set up .beads/redirect when creating jj workspaces (fhsk-0sq) ([#144](https://github.com/fzymgc-house/fzymgc-house-skills/issues/144)) ([9fd7574](https://github.com/fzymgc-house/fzymgc-house-skills/commit/9fd7574ffbff7bfa4facc775e1dcda2fff7f40a7))
