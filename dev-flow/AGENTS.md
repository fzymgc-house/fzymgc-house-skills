<!-- markdownlint-disable MD013 -->

# Dev-Flow Conventions

Conventions for the `dev-flow` workflow plugin. Every workflow skill (`brainstorming`, `writing-plans`, `subagent-driven-development`, `executing-plans`, `finishing-a-development-branch`, `plan-to-beads`, `bead-create-smart`, `handoff-prompt`, `capture-adrs`) and review-gate agent (`design-reviewer`, `plan-reviewer`, `adr-extractor`) MUST follow these rules.

**Design source:** [`docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`](../docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md). When this document and the spec disagree, the spec wins; file an issue against this AGENTS.md.

## Rule 1: Structure in specs/plans, implementation in code

Specs and plans describe architecture, contracts, and interfaces. Implementation is left to the implementer.

**Allowed in specs/plans (structural / load-bearing):**

| Category | Examples |
|---|---|
| Schemas | Proto definitions, SQL DDL, YAML config shapes |
| Type contracts | Type signatures, interface definitions, exact field names + orderings |
| Service boundaries | Architecture diagrams, message shapes, RPC mode declarations (streaming vs unary) |
| Naming conventions | File paths, identifier names, label namespaces |

**Not allowed:**

- Function bodies
- Algorithm implementations
- Business logic / imperative code
- Pseudo-code that reads like implementation

**Why:** Implementers (sub-agents or future sessions) need structural details verbatim — they cannot safely infer "this RPC is server-streaming" from prose. They also need implementation freedom.

**Test:** If it defines structure (shape, contract, interface), include it. If it shows *how* to compute, leave it out.

## Rule 2: 3+ trackable tasks → epic

Plans are classified at `plan-to-beads` time:

| Task count | Bead structure |
|---|---|
| 3 or more | Parent epic + child task beads. Epic linkage via `--parent <epic-id>`. |
| 1-2 | Standalone task beads. No epic. `plan-reference` description points back. |
| 0 (design-only spec) | Skip bead creation. Plan exists as a reference document. |

## Rule 3: Use bd's structured fields; description carries narrative only

Tracked beads use `bd create`'s native flags for structured data. The `--description` field carries **narrative**: Goal, Plan reference (with verbatim-read directive), Files touched (approximate), Out of scope.

| Bead field | bd flag |
|---|---|
| Title (imperative-voice) | positional or `--title` |
| Type | `--type task\|feature\|bug\|epic\|chore\|decision` |
| Parent epic | `--parent <epic-id>` |
| Priority | `--priority 0-4` |
| Labels | `--labels` (e.g. `area:jj,aspect:security,model:opus`) |
| Required skills | `--skills` (dispatch routing hint) |
| Design link | `--spec-id <path>` + `--design <string>` or `--design-file <path>` |
| Acceptance criteria | `--acceptance` (RFC2119 MUST/SHOULD) |
| Verification steps | `--notes` (concrete commands) |
| Dependencies | `--deps type:id` or `bd dep add` afterwards |
| Fanout gates | `--waits-for` + `--waits-for-gate all-children\|any-children` |
| External ref | `--external-ref` (PR/issue URL) |
| Narrative description | `--description` or `--body-file` |

**Note on bd flag naming:** `bd create` and `bd update` use `--spec-id`. `bd list` uses `--spec` (filter by spec_id prefix). Inconsistent on bd's part, but verified against bd CLI v1.0.4.

**Validation:** `bd create --validate` checks descriptions against bd's built-in section requirements per issue type. Enable project-wide via `bd config set validation.on-create warn` (or `block` for strict mode).

## Rule 4: No duplicate state

| State | Lives in |
|---|---|
| Graph topology (deps, parent epics) | bd's dep edges |
| Acceptance criteria | bd's `--acceptance` field |
| Design link | bd's `--spec-id` field |
| Verification commands | bd's `--notes` field |
| Bead status (open/in_progress/closed) | bd |
| Bead chain "structure" | bd (NOT a plan markdown section) |

**Implication:** plans do NOT contain a `## Bead chain structure` section. `plan-to-beads` reads the plan's task table directly; bd is source of truth for the graph.

**Plan task table semantics:** The plan's task table is a **one-shot input** to `plan-to-beads`. After materialization, bd is the source of truth. Editing the plan task table after materialization does not retroactively change beads — file follow-up beads manually or re-invoke `plan-to-beads --force-update`.

## Rule 5: Model selection on beads (label-driven, enforced at dispatch)

Beads carry an optional model hint via `--labels model:<haiku|sonnet|opus>`. Default is **sonnet** if no label.

| Label | When | Examples |
|---|---|---|
| `model:haiku` | Mechanical, high-volume, low-judgment | Regex rename across N files, scaffold from template, generate test boilerplate, JSON manifest edits |
| `model:sonnet` (default) | Most implementation | New feature, bug fix, refactor with judgment, normal subagent task |
| `model:opus` | Hard reasoning, architecture, cross-cutting risk | Plan-reviewer dispatch, security-sensitive code, multi-file refactors with subtle invariants, debugging distributed-state bugs |

**Enforcement (MUST):**

- `subagent-driven-development` reads bead's `model:*` label, passes as `model` to `Agent` tool invocation.
- `executing-plans` honors the current bead's label for serial-execution session model and child `Agent` calls.
- `handoff-prompt` includes the model recommendation in briefing text.
- **Absence of label = sonnet.** No fallback to "highest available"; explicit default keeps cost predictable.

**Author-time discipline:**

- `plan-to-beads` proposes model labels heuristically based on task content (mechanical patterns → haiku; architecture / security keywords → opus; default sonnet). User reviews + overrides in dry-run preview.
- `bead-create-smart` accepts an explicit model arg; defaults to sonnet if omitted.

## Rule 6: The design bead — one bead spans the whole lifecycle

A single bead tracks design work from `brainstorming` open through `plan-to-beads` materialization. The bead's **type evolves** with the work: starts as `task` during design, promotes to `epic` at materialization time for 3+ child tasks, stays as `task` for 1-2 (with optional sibling), or closes for design-only.

### Lifecycle

| Phase | Bead state | What happens |
|---|---|---|
| `brainstorming` opens | `--type=task --title="Design: <provisional>" --labels="phase:design"` | Created at session start; user opts out for throwaway exploration |
| spec drafted | `bd note <id> "Spec: <path>"` | Spec path recorded |
| design-reviewer rounds | `bd note <id> "design-review round N: <verdict> — <finding summary>"` | Each round's findings preserved as session-spanning audit trail |
| writing-plans completes | `bd note <id> "Plan: <path>"` | Plan path recorded |
| plan-reviewer rounds | `bd note <id> "plan-review round N: <verdict> — <finding summary>"` | Same pattern |
| capture-adrs files ADRs | `bd note <id> "ADRs: <bd-ids>"` | Decision-bead IDs recorded |
| `plan-to-beads` runs (3+ tasks) | `bd update <id> --type=epic --title="<feature name>"` + create children with `--parent <id>` | Bead **promotes to epic**; design-phase notes persist as epic audit trail |
| `plan-to-beads` runs (1-2 tasks) | `bd update <id> --title="<title of first plan task>"` (stays `task`); optional second `bd create` for the second task with no `--parent` | Design bead inherits first plan task's title (top-to-bottom order); review-history notes travel with it |
| `plan-to-beads` runs (0 tasks, design-only) | `bd close <id> --reason="Design-only; no implementation tracked"` | Design bead closes |

**Opt-out for ad-hoc work:** `brainstorming` offers a one-prompt opt-out at session start; default opts in for substantive prompts, out for clearly exploratory ones.

## Rule 7: Grounding before design — codebase + dependencies first

Workflow skills MUST consult appropriate grounding sources BEFORE proposing designs, before declaring plans READY, and before materializing beads. The failure mode this prevents: designs that propose library calls that don't exist, file paths that don't match the codebase, function signatures invented from memory.

### Tool inventory

| Tool | Use for |
|---|---|
| `mcp__probe__search_code` | "Where is X defined?" / "How does Y work?" — semantic code search returning AST blocks |
| `mcp__probe__extract_code` | Pull a specific symbol or `path:line` range by name |
| `mcp__probe__grep` | Structured ripgrep with file/line metadata |
| `mcp__context7__resolve-library-id` + `query-docs` | ANY mention of a library, framework, SDK, API, CLI, cloud service — even ones in training data |
| `mcp__deepwiki__read_wiki_structure` | "What topics does this repo's docs cover?" — get an overview |
| `mcp__deepwiki__read_wiki_contents` | View the actual docs for a topic |
| `mcp__deepwiki__ask_question` | Targeted Q&A against a repo's docs |
| `mcp__exa__web_search_exa` | Current web search — news, comparison, real-world adoption signals |
| `mcp__firecrawl-mcp__firecrawl_scrape` (or `firecrawl` skill) | Page-content extraction once Exa surfaces a relevant URL |

### Tool precedence (semantic-first, then raw)

```text
probe.search_code  →  probe.extract_code  →  probe.grep  →  rg  →  Read
context7           →  deepwiki            →  exa+firecrawl  →  WebFetch
```

MUST attempt the higher-precedence tool first. MAY fall through when the higher tool is insufficient or inapplicable.

### Brainstorming MUST-use checklist

Before proposing any approach, `brainstorming` MUST:

1. **Probe the codebase** for prior art on the topic at hand.
2. **Context7 every named external dependency.** If a user says "use library X", `brainstorming` MUST call `mcp__context7__resolve-library-id "X"` then `query-docs <id> "<question>"`.
3. **Deepwiki for upstream repo conventions** when relevant. Typical pattern: `read_wiki_structure <org>/<repo>` → `read_wiki_contents` or `ask_question`.
4. **Exa + firecrawl** when the design question is "current state of the art" / "recently changed".

### Grounding-trace contract (links Rule 6 + Rule 7)

The design bead (Rule 6) serves as the grounding audit trail. `brainstorming` MUST append a `bd note` for each grounding source consulted:

- `bd note <id> "grounding/context7: <library-id> — <one-line summary>"`
- `bd note <id> "grounding/deepwiki: <repo> — <one-line summary>"`
- `bd note <id> "grounding/probe: <query> — <hit summary>"`
- `bd note <id> "grounding/exa: <query> — <result summary>"`

`plan-reviewer` reads these via `bd show <design-bead-id>` (its Bash tool covers this); absence of relevant grounding traces for libraries/concepts named in the plan triggers a NOT READY finding.

### Soft-failure reconciliation

Rule 7's "MUST use" language applies **when the tool is available**. If the tool is absent (per the spec's Plugin runtime requirements failure-mode table), the grounding step degrades — `brainstorming` proceeds with weaker grounding, and `plan-reviewer` surfaces the gap as a plan-level finding rather than treating absence as a hard error. The hard prerequisite is `bd`; everything else degrades gracefully.

## bd config setup

After cloning the repo (or after first `bd init`), enable project-wide validation:

```bash
bd config set validation.on-create warn
```

This makes every `bd create` validate descriptions against bd's built-in section requirements per issue type. Use `block` instead of `warn` for strict mode.

## See also

- Spec: [`docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`](../docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md)
- Plan: [`docs/superpowers/plans/2026-05-14-dev-flow-beads-integration.md`](../docs/superpowers/plans/2026-05-14-dev-flow-beads-integration.md)
- Plugin README: [`README.md`](README.md)
