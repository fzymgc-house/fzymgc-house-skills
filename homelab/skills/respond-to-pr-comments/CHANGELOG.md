# Changelog

## [0.6.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/respond-to-pr-comments-v0.5.0...respond-to-pr-comments-v0.6.0) (2026-02-17)


### Features

* **skills:** update model routing to prefer Sonnet 4.6 ([#16](https://github.com/fzymgc-house/fzymgc-house-skills/issues/16)) ([ddb71eb](https://github.com/fzymgc-house/fzymgc-house-skills/commit/ddb71eb64883d9e7ef8f0591c939a101590286a0))

## [0.5.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/respond-to-pr-comments-v0.4.0...respond-to-pr-comments-v0.5.0) (2026-02-16)


### Features

* **ci:** integrate release-please for automated versioning ([#11](https://github.com/fzymgc-house/fzymgc-house-skills/issues/11)) ([8ab39f0](https://github.com/fzymgc-house/fzymgc-house-skills/commit/8ab39f0902ef55b001b4de8e94e136e442981b6c))
* replace JSONL temp dirs with beads persistence in review skills ([#9](https://github.com/fzymgc-house/fzymgc-house-skills/issues/9)) ([20fd167](https://github.com/fzymgc-house/fzymgc-house-skills/commit/20fd16779b526e83e44fd512dddb9885ded1edec))
* **skills:** add pr-review-response skill, improve respond-to-pr-comments ([57c6978](https://github.com/fzymgc-house/fzymgc-house-skills/commit/57c69780041792e2ff339638fbfc1c15aca1c6e6))
* **skills:** add pr-review-response, improve respond-to-pr-comments ([1a9b23f](https://github.com/fzymgc-house/fzymgc-house-skills/commit/1a9b23fcc9147edab6e1635ac731de1ea6ff8e44))
* **skills:** add prior review history gathering to review-pr and respond-to-pr-comments ([de615f1](https://github.com/fzymgc-house/fzymgc-house-skills/commit/de615f16d391af5d3b657f1f686c934870a38f3f))
* **skills:** limit subagent concurrency to 3 ([#8](https://github.com/fzymgc-house/fzymgc-house-skills/issues/8)) ([5aac374](https://github.com/fzymgc-house/fzymgc-house-skills/commit/5aac3745001be78301d3ed4131a80b4527606c6a))


### Bug Fixes

* **pr-comments:** use correct API endpoints for reactions ([3bc74b5](https://github.com/fzymgc-house/fzymgc-house-skills/commit/3bc74b53921100a7f799d1c656cdfb6e6d03c01a))
* **pr-comments:** use databaseId for GitHub API reactions ([219668c](https://github.com/fzymgc-house/fzymgc-house-skills/commit/219668cdcec823f5919702000829adf02dc4abaa))
* replace bare except with Exception in pr_comments.py ([bee014d](https://github.com/fzymgc-house/fzymgc-house-skills/commit/bee014d389b466aa272a43f9ee5b83a54bc7ff33))
* **skills:** add integration tests and independent review to PR workflow ([#6](https://github.com/fzymgc-house/fzymgc-house-skills/issues/6)) ([0f55aff](https://github.com/fzymgc-house/fzymgc-house-skills/commit/0f55afffc997d8583bd0d2b3f4da98a07bfcc4ae))
* **skills:** correct bd list --labels to --label ([#13](https://github.com/fzymgc-house/fzymgc-house-skills/issues/13)) ([2585cc8](https://github.com/fzymgc-house/fzymgc-house-skills/commit/2585cc89b5c3afc5808eddfa33538d70c0528d86))
* **skills:** split Phase 2 into distinct steps ([#3](https://github.com/fzymgc-house/fzymgc-house-skills/issues/3)) ([a6a43de](https://github.com/fzymgc-house/fzymgc-house-skills/commit/a6a43def569a75d52d4203068334955d6d0c57a4))
