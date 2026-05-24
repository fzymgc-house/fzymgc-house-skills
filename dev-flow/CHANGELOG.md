# Changelog

## [0.6.2](https://github.com/fzymgc-house/fzymgc-house-skills/compare/dev-flow-v0.6.1...dev-flow-v0.6.2) (2026-05-24)


### Bug Fixes

* **adr:** replace bd mol pour formula-adr with bd create -t decision (bd 1.0.4 fixes) ([#89](https://github.com/fzymgc-house/fzymgc-house-skills/issues/89)) ([00d3f3f](https://github.com/fzymgc-house/fzymgc-house-skills/commit/00d3f3fd392e96ce63be1e0a9879443aeb6b1076))
* **drain:** replace bd mol pour with bd create -t drain (bd 1.0.4 fixes) ([#87](https://github.com/fzymgc-house/fzymgc-house-skills/issues/87)) ([a539bed](https://github.com/fzymgc-house/fzymgc-house-skills/commit/a539bedb8b657c4616c77d04d210213fc7c3f766))

## [0.6.1](https://github.com/fzymgc-house/fzymgc-house-skills/compare/dev-flow-v0.6.0...dev-flow-v0.6.1) (2026-05-24)


### Bug Fixes

* **drain:** scope pre-flight [#7](https://github.com/fzymgc-house/fzymgc-house-skills/issues/7) to overlapping chains, drop no-op label query ([#85](https://github.com/fzymgc-house/fzymgc-house-skills/issues/85)) ([ece8611](https://github.com/fzymgc-house/fzymgc-house-skills/commit/ece86117f45a2fbf7f62bbd017c21cfc2239f8f1))

## [0.6.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/dev-flow-v0.5.0...dev-flow-v0.6.0) (2026-05-22)


### Features

* **adr:** /adr harness + bd-as-truth ADR system + migrate legacy 5 ADRs ([#83](https://github.com/fzymgc-house/fzymgc-house-skills/issues/83)) ([45ae3b8](https://github.com/fzymgc-house/fzymgc-house-skills/commit/45ae3b8fa0099fcedcb1b7683c256119637b73ef))

## [0.5.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/dev-flow-v0.4.0...dev-flow-v0.5.0) (2026-05-22)


### Features

* **drain:** /drain harness — slash command + draining-beads skill + formula ([#79](https://github.com/fzymgc-house/fzymgc-house-skills/issues/79)) ([6d88744](https://github.com/fzymgc-house/fzymgc-house-skills/commit/6d88744fa49b6e9428daf26d6ebd8ff75485dcbb))

## [0.4.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/dev-flow-v0.3.0...dev-flow-v0.4.0) (2026-05-14)


### Features

* **dev-flow:** Phase 1 — foundation rename superpowers/ → dev-flow/ ([#67](https://github.com/fzymgc-house/fzymgc-house-skills/issues/67)) ([67c47c0](https://github.com/fzymgc-house/fzymgc-house-skills/commit/67c47c01c89c88bbbcc039d1edb9054fb317d547))
* **dev-flow:** Phase 2 — codify Rules 1-7 in dev-flow/AGENTS.md ([#68](https://github.com/fzymgc-house/fzymgc-house-skills/issues/68)) ([5a8a79c](https://github.com/fzymgc-house/fzymgc-house-skills/commit/5a8a79cb2fd99339398932d512c793d679ad11da))
* **dev-flow:** Phase 3 — lift plan-to-beads, bead-create-smart, handoff-prompt ([#69](https://github.com/fzymgc-house/fzymgc-house-skills/issues/69)) ([dc31c7d](https://github.com/fzymgc-house/fzymgc-house-skills/commit/dc31c7d5aabd50553e9551c999a219451573960b))
* **dev-flow:** Phase 4 — ADR capture subsystem (skill + agent + hook + doctor) ([#70](https://github.com/fzymgc-house/fzymgc-house-skills/issues/70)) ([d6df93b](https://github.com/fzymgc-house/fzymgc-house-skills/commit/d6df93b006742cb66c6824928dc59b8afea0b3f7))
* **dev-flow:** Phase 5 — design-reviewer + plan-reviewer agents ([#71](https://github.com/fzymgc-house/fzymgc-house-skills/issues/71)) ([7921c69](https://github.com/fzymgc-house/fzymgc-house-skills/commit/7921c69a1633a7916165cdedb3fd203508277205))

## [0.3.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/superpowers-v0.2.1...superpowers-v0.3.0) (2026-04-02)

### Features

* **superpowers:** sync upstream obra/superpowers v5.0.7 ([#40](https://github.com/fzymgc-house/fzymgc-house-skills/issues/40)) ([faae322](https://github.com/fzymgc-house/fzymgc-house-skills/commit/faae322eacc8ae0456b2b06ff5eaadec6378e951))

## [0.2.1](https://github.com/fzymgc-house/fzymgc-house-skills/compare/superpowers-v0.2.0...superpowers-v0.2.1) (2026-03-28)

### Bug Fixes

* **superpowers:** add missing run-hook.cmd polyglot wrapper ([4c9c6ac](https://github.com/fzymgc-house/fzymgc-house-skills/commit/4c9c6acdb2f4b05a6ab821a9c3ce730a97947a20))
* **superpowers:** add run-hook.cmd to upstream manifest ([b0083e0](https://github.com/fzymgc-house/fzymgc-house-skills/commit/b0083e015e786686ec3b15718ae492dacfb27420))

## [0.2.0](https://github.com/fzymgc-house/fzymgc-house-skills/compare/superpowers-v0.1.0...superpowers-v0.2.0) (2026-03-16)

### Features

* **superpowers:** fork obra/superpowers with jj VCS support ([#34](https://github.com/fzymgc-house/fzymgc-house-skills/issues/34)) ([1acccca](https://github.com/fzymgc-house/fzymgc-house-skills/commit/1acccca02d75627a8f7f68e0649d0406789b2b9b))
