# Fix `--skills` Routing Misconception + Tighten/Retime capture-adrs

- **Design bead:** fhsk-07o
- **Date:** 2026-05-28
- **Status:** Draft for review

## Problem

Three independent defects in `dev-flow`, reported together:

1. **`--skills` does not route subagents.** Multiple skills instruct the reader
   to read a bead's `skills[]` field from JSON and map it to a `subagent_type`.
   Verified behavior: `bd create --skills "review,test"` leaves the JSON
   `skills` field **null** and appends a `## Required Skills\nreview,test` block
   to the bead **description**. There is no `skills[]` array to read, and
   `--skills` was never a dispatch mechanism. The routing logic in
   `subagent-driven-development`, `draining-beads`, and `handoff-prompt` is
   therefore unreachable as written.
2. **capture-adrs over-captures.** The `adr-extractor` worthiness criteria are
   lenient: "score < 4 — surface it anyway" lets borderline candidates through,
   and "has rejected alternatives" is trivially satisfied because `brainstorming`
   manufactures alternatives via every `AskUserQuestion`. The extractor surfaces
   process, packaging, sequencing, and refactor-mechanics decisions as if they
   were architectural ADRs.
3. **capture-adrs nudge fires too early.** The `nudge-adr-capture` hook watches
   `docs/**/(specs|plans)/*.md`, so it fires during `brainstorming` on spec
   writes — before a plan even exists. ADR capture should only be prompted after
   `writing-plans`.

## Goals

- Encode the true `--skills` semantics and give subagent dispatch a real signal:
  an `agent:<type>` label (parallel to the existing `model:<tier>` label).
- Raise the capture-adrs bar so only architecturally load-bearing decisions are
  surfaced.
- Retime the ADR nudge to fire on plans only.

## Non-Goals

- Renaming or removing the `--skills` flag (it remains a valid way to annotate
  Required Skills in the description).
- Building the specialized implementer subagent types themselves (the
  `agent:*` values are forward-looking; see Part A).
- Changing the `capture-adrs` skill's own path regex (per decision: only the
  automatic nudge is retimed; manual `/capture-adrs <spec>` still works).
- Changing how `review-pr` dispatches its review agents.

## Part A — `agent:*` routing label replaces the `--skills` misconception

### The truth to encode

`--skills <csv>` appends a `## Required Skills` block to the bead description. It
is a **human/agent-readable capability hint**, not a dispatch signal. The JSON
`skills` field is null.

### The `agent:<type>` label

Introduce an `agent:<subagent_type>` label, parallel to `model:<tier>`. It is the
**only** signal that drives `subagent_type` selection.

**Reader resolution rule (used by `subagent-driven-development`, `draining-beads`,
`handoff-prompt`):**

Resolution is a **documented lookup, not a runtime probe.** The Agent/Task tool
errors on an unregistered `subagent_type`, so the reader MUST NOT pass a value
it cannot confirm is registered. Each reader carries the known-registered set
(today: `{ general-purpose }`) and resolves as:

1. Read the `agent:*` label, if any.
2. If its value is in the reader's known-registered set, dispatch that
   `subagent_type`.
3. Otherwise (no label, or a value not in the set) dispatch `general-purpose`.

**Today every value resolves to `general-purpose`** because that is the only
registered implementer subagent type. The `agent:*` label is therefore a
forward-looking annotation with no current dispatch effect: it records the
*intended* specialist so that when such a subagent type is later registered, the
reader's known-set is extended and routing begins — no bead re-labeling needed.
This keeps the label real but never dispatches an unregistered type.

**Enumerated values (aspirational; all resolve to `general-purpose` until the
corresponding subagent type exists):**

| Label | Intended for |
|-------|--------------|
| `agent:general-purpose` | default; general implementation (also the fallback) |
| `agent:test-author` | test-writing tasks |
| `agent:infra` | infrastructure / CI / config tasks |
| `agent:debugger` | diagnosis / bugfix tasks |
| `agent:docs` | documentation tasks |

Today only `general-purpose` is registered, so every value currently resolves to
it. The label is a forward-looking hook; the reader's fallback guarantees no
broken dispatch.

**Constraint (carried from PR #102):** never set `agent:code-reviewer` (or any
`review-pr` orchestrator agent) on an implementer bead — those agents require the
orchestrator contract (`PARENT_BEAD_ID`, `PR_URL`, `ASPECT`) and are dispatched
only by `review-pr`.

### Reader changes (stop reading `skills[]`)

- **`subagent-driven-development/SKILL.md`** — the bullet at ~L56 (`skills[]` is a
  routing hint), the `subagent_type` mapping at ~L60, the flowchart nodes at
  ~L75/95/96 ("Read labels (model:\*) + skills[]"), and the worked examples at
  ~L171/201 (`skills: infra,test`). Replace every "map `skills[]` to
  `subagent_type`" with the `agent:*` resolution rule above. The flowchart node
  becomes "Read labels (`model:*`, `agent:*`)". Examples use
  `labels: model:sonnet, agent:infra` and reframe Required Skills as a
  description hint.
- **`draining-beads/SKILL.md`** — L135 ("subagent_type from the bead's
  `skills[]`") → "subagent_type from the bead's `agent:*` label (general-purpose
  fallback)".
- **`handoff-prompt/SKILL.md`** — L7 (frontmatter "routes via the bead's
  `--skills`"), L73 ("`--skills` list — the dispatch routing hint"), L237
  ("Routed dispatch via the bead's `--skills` field") → all reference the
  `agent:*` label as the routing signal; `--skills`/Required Skills is a
  capability hint only. **Leave L130 unchanged** — the briefing-template line
  "Required skills (per bead `--skills`)" is already correct framing (it surfaces
  the capability hint to the new session; it is not a routing claim).

### Setter changes (`--skills` stays a hint, add `agent:*` for routing)

- **`plan-to-beads/SKILL.md`** — L137 and the Rule 3 flag inventory at ~L259:
  add `--labels agent:<type>` as the routing mechanism; keep `--skills
  <csv>` documented as "appends a `## Required Skills` block to the description
  (capability hint, not routing)". Note the `agent:code-reviewer` prohibition.
- **`bead-create-smart/SKILL.md`** — the inputs-table row at ~L62 (currently
  "Required skills | `--skills` | … | Dispatch routing hints (e.g. `jj,proto`)")
  AND the example command at ~L118. Reframe both: `--skills` appends a
  `## Required Skills` capability hint to the description; add an `agent:<type>`
  label row for routing.
- **`dev-flow/AGENTS.md`** — the Rule 3 flag-inventory table at ~L58 (currently
  "Required skills | `--skills` (dispatch routing hint)"). This is the canonical
  rule doc every skill cites; reframe the `--skills` row to "capability hint
  (appends `## Required Skills` to the description)" and add an `agent:<type>`
  routing row. If `AGENTS.md` is not updated, skills that cite Rule 3 re-import
  the misconception.

## Part B — Tighten capture-adrs worthiness

### `dev-flow/agents/adr-extractor.md` (§ Worthiness criteria, L25–43)

Replace the current 4-criteria + "surface borderline anyway" block with a
stricter gate:

- **Surface a candidate only if it passes ALL criteria (score == 4).** Borderline
  (< 4) candidates go to the `dropped` array with a reason; they are NOT
  surfaced. Remove "Score < 4 is borderline — surface it anyway."
- **Criterion 1 — Architecturally load-bearing.** The decision must constrain
  *future code*: system structure, public interfaces / APIs, data model,
  cross-component contracts, or trust / dependency boundaries. If reversing it
  would only churn process or files (not code behavior or structure), it is not
  architectural.
- **Explicit exclusion list (auto-drop, never surface):** process / workflow
  sequencing ("do X before Y"); packaging, versioning, or release-tooling
  mechanics; file organization, moves, or refactor mechanics; naming / slug
  conventions; documentation or wording choices; tooling / config changes that
  do not alter runtime behavior.
- **Criterion 2 — Rejected alternatives are necessary but NOT sufficient.** A
  decision presented with alternatives by a `brainstorming` `AskUserQuestion`
  prompt is not architectural merely because alternatives were listed. The
  alternatives must reflect a genuine structural fork, not a routine choice.

Keep criteria 3 (load-bearing for future contributors) and 4 (not already
captured). Update the schema comment so `worthiness_score` of 4 is the only
surfaced value and the prose at ~L112 ("prioritize by score descending") reflects
that only 4s are returned as candidates.

### Canonical spec mirror

`docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
§ "ADR Capture Subsystem" defines the worthiness contract the `capture-adrs`
skill cites. Update that section to match the tightened criteria above so the
spec and the agent do not diverge.

## Part C — Retime the nudge (plans only)

### `dev-flow/hooks/nudge-adr-capture`

Change the `WATCHED_REGEX` default from the `(specs|plans)` form to plans only:

```bash
WATCHED_REGEX="${WATCHED_GLOBS:-^(.*/)?docs/(superpowers/)?plans/.+\.md$}"
```

Update the header comments (lines ~21–29) that document the watched globs to say
plans only. The hook no longer fires on `docs/**/specs/*.md`.

### `dev-flow/hooks/tests/test_nudge_adr_capture.{sh,py}`

Grounded mechanics (verified): the `.sh` harness has 15 cases; the `.py` is a
thin wrapper asserting `"passed=15 failed=0"`. The **firing** cases (9
no-marker, 11 stale-marker, 13 malformed-marker) create real files via the
`make_spec()` helper, which writes under `docs/specs/`. The path-only cases (2
`docs/specs`, 4 `docs/superpowers/specs`, 7 worktree `docs/specs`) already
expect silent (`0 ""`) because no real file exists at those paths.

After the plans-only regex change, the firing cases would break (a `docs/specs`
file is no longer watched → silent → the `expect ... nudge` assertions fail).
Required edits:

1. **Repoint `make_spec()` to `docs/plans/`** (rename to `make_plan` for
   clarity). Cases 9/11/13 then exercise firing on a *watched* plan path. Their
   marker semantics (no-marker → nudge, stale → nudge, malformed → nudge,
   fresh/opt-out → silent) are path-independent and continue to hold.
2. **Reframe the spec-path comments** on cases 2/4/7 from "reaches marker logic
   / should match" to "spec path → no longer watched → silent." Their expected
   output stays `0 ""`.
3. **Add one case**: a real spec file (created under `docs/specs/`) with no
   marker → **silent**, proving specs are no longer watched even when the file
   exists and lacks a marker. This is the assertion that would have caught the
   bug.
4. **Update the `.py` count** assertion from `passed=15` to the new total
   (16 with the one added case) so the wrapper stays accurate.

### Out of scope for Part C

The `capture-adrs` skill's own path-resolution regex
(`^(.*/)?docs/(superpowers/)?(specs|plans)/.+\.md$`) is unchanged: a user may
still manually run `/capture-adrs <spec-path>`. Only the automatic hook is
retimed.

## Files touched

- **A:** `dev-flow/skills/subagent-driven-development/SKILL.md`,
  `dev-flow/skills/draining-beads/SKILL.md`,
  `dev-flow/skills/handoff-prompt/SKILL.md`,
  `dev-flow/skills/plan-to-beads/SKILL.md`,
  `dev-flow/skills/bead-create-smart/SKILL.md`,
  `dev-flow/AGENTS.md` (Rule 3 flag-inventory table)
- **B:** `dev-flow/agents/adr-extractor.md`,
  `docs/superpowers/specs/2026-05-14-dev-flow-beads-integration-design.md`
- **C:** `dev-flow/hooks/nudge-adr-capture`,
  `dev-flow/hooks/tests/test_nudge_adr_capture.sh`,
  `dev-flow/hooks/tests/test_nudge_adr_capture.py`

## Verification

- **`--skills` claims gone:** a grep across `dev-flow/` (`.md` + `AGENTS.md`)
  for `skills[]` and for `--skills` near "dispatch"/"routing" returns no routing
  framing (including the `AGENTS.md` Rule 3 row and the `bead-create-smart`
  inputs table); the `agent:*` documented-lookup rule (with the known-registered
  set) appears in all three readers; the `agent:code-reviewer` prohibition is in
  `plan-to-beads`; `handoff-prompt` L130 is unchanged.
- **Nudge timing:** the hook test suite passes with spec paths silent and plan
  paths firing — `uv run --with pytest pytest dev-flow/hooks/tests/test_nudge_adr_capture.py`
  and the `.sh` harness.
- **Worthiness:** `adr-extractor.md` no longer contains "surface it anyway"; the
  exclusion list is present; the spec § "ADR Capture Subsystem" matches.
- **Repo gates:** `rumdl check --no-exclude` clean on touched markdown; the full
  test suite (`.claude/hooks/tests/`, `jj/hooks/tests/`, `dev-flow/hooks/tests/`,
  `tests/`) passes; `jq` clean on any touched JSON (none expected).
- **Behavioral sanity:** dispatching from a bead with `agent:test-author` (type
  absent) resolves to `general-purpose` without error.

## Risks

- **`agent:*` reader fallback omitted** → a bead labeled with an unregistered
  agent type would fail dispatch. Mitigated by stating the
  "resolve-if-available-else-general-purpose" rule in every reader and the
  behavioral-sanity check.
- **Worthiness over-correction** → tightening could drop a genuinely
  architectural decision. Mitigated because the four criteria are conjunctive
  and the exclusion list targets only non-code-structural categories; a real
  structural fork still scores 4.
- **Hook-test drift** → if the `.sh` and `.py` harnesses encode the spec-firing
  expectation differently, one may be missed. Verification runs both.
