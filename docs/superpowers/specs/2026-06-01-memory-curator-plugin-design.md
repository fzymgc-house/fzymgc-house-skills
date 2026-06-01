# memory-curator plugin — design

- **Bead:** fhsk-ga7
- **Issue:** GH#131
- **Status:** design (pending design-reviewer gate)
- **Date:** 2026-06-01
- **Revised:** 2026-06-01 — integration target's auth model changed from a static
  scoped LiteLLM key to native MCP **OAuth** (Authentik PKCE) per the GH#131
  update comment. Sections below reflect the OAuth model; the superseded
  static-key facts are noted where relevant.

## Problem

The self-hosted memory layer (a deployed MCP server reached through the LiteLLM
gateway) is useful only if a human drives it by hand. We want a client-side
Claude Code plugin that makes the memory layer a native, trustworthy part of
every session: prior context surfaces automatically at session start, new
durable knowledge is captured with discipline, and the store stays correct over
time — without the user remembering to invoke anything.

The memory **service** is out of scope and must not be modified (it owns the
tools and storage). This is purely the client-side plugin.

## Integration target (facts, not requirements)

- Memory MCP server is reached **only** through the LiteLLM gateway at
  `https://litellm.fzymgc.house/mcp/memory_oauth` (streamable-HTTP). The route
  name is `memory_oauth` (underscore — LiteLLM rejects `-`) and is kept stable.
- **Auth: native MCP OAuth** — the user authenticates to **Authentik** via PKCE;
  LiteLLM delegates upstream (`delegate_auth_to_upstream`) and the memory server
  validates the Authentik JWT (401 on unauthenticated/invalid). **There is no
  static key and no secret on disk.** (Superseded: the original
  `x-litellm-api-key: Bearer <key>` static key on `/mcp/memory` with a Vault
  `claude_code_memory` field — that route is retired.)
- One-time interactive registration (reference): `claude mcp add --transport http
  --callback-port 8765 memory_oauth https://litellm.fzymgc.house/mcp/memory_oauth`
  then `/mcp` → `memory_oauth` → Authenticate → browser → Authentik. Per the
  GH#131 update comment the route requests `offline_access` so the token
  auto-refreshes; re-auth only occasionally (e.g. gateway restart). (Refresh
  behavior is the service's claim — if it does not hold, the only effect is more
  frequent re-auth, which the degradation path already handles.)
- **Auth is interactive (browser).** Headless/CI Claude Code cannot complete the
  flow today (a non-interactive service-token path is a planned service-side
  follow-up). The plugin assumes an interactive session and must degrade
  gracefully (no crash, clear message) when the server isn't authenticated.
- Tools (unchanged): `store_memory(content, scope, source, category, tags?,
  repo?, workspace?, worktree_path?, base_dir?)`, `search_memory(query, scope,
  k?)` (semantic; requires a query), `list_memory(scope, limit?)` (no query;
  session bootstrap), `get_memory(id)`, `update_memory(id, content)`,
  `delete_memory(id)`, `delete_all(scope)`.
- A record carries `content`, `scope`, `repo`/`workspace`/`worktree_path`/
  `base_dir`, `source` (`user-said` | `agent-inferred`), `category`, `tags`,
  `created_at`, and now **`actor`** = the verified caller identity from the
  validated token (set **server-side**, not client-supplied; recall/display may
  surface it).
- The service's `scope` is a structured colon-delimited string (the upstream
  jsonschema hints `tier:repo`, e.g. `eval-2026-05:project:selfhosted-cluster`).
- Design intent of the store: **explicit and zero-junk** — only deliberately
  chosen durable facts; correctability (edit/supersede) is first-class.

## Decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Scope model | **Two-tier**: repo spine `repo:<id>` (shared across all workspaces) + workspace overlay `repo:<id>:ws:<workspace>` for **named non-default workspaces only** (primary checkout is spine-only — no `ws:default`). Recall merges both; store defaults to spine |
| Scope derivation | jj-first remote resolution (jj-colocated- and workspace-stable); basename/store-pointer fallback. Workspace name from `jj log -r @ -T working_copies` (jj) or worktree dir basename (git) |
| Auth | Native MCP **OAuth** (Authentik PKCE). Plugin only registers the `memory_oauth` HTTP server (no headers) with a fixed callback port; Claude Code's OAuth flow handles the rest. **No secret on disk** — the "never commit a secret" constraint is satisfied by construction |
| Session-start recall | uv command hook computes spine+overlay scopes locally and emits `additionalContext` **instructing Claude to call `list_memory`** over its own OAuth-authenticated connection (model-mediated — hooks can't access the OAuth token). The hook itself makes no network call |
| Session-end capture | `Stop` hook, block-once nudge guarded by `stop_hook_active` (only mechanism to prompt Claude at stop; interjects ≤1 extra turn) |
| Plugin layers | Both Claude source plugin + Codex wrapper, registered in both marketplaces |

## Architecture

A new source plugin `memory-curator/` plus a thin Codex wrapper
`plugins/memory-curator/`. Three parts:

1. **MCP wiring** — bundled `.mcp.json` registering the `memory_oauth` OAuth
   HTTP server (no headers; fixed callback port).
2. **Hooks (uv-python)** — `SessionStart` recall (scope + instruction) + `Stop`
   capture-nudge, sharing one scope-derivation module. Neither hook makes a
   network call or touches credentials.
3. **Two model-invoked skills:**
   - `curating-memory` — capture-time discipline (junk taxonomy,
     search-before-store, supersede-on-contradiction, tier selection).
   - `promoting-memory` — work-completion workflow: review a workspace overlay
     and promote repo-wide facts to the spine, then clean up.

The shared scope-derivation module is the linchpin: the recall hook computes the
two-tier scope pair (spine + workspace overlay), surfaces both into context, and
both the recall instruction and the curation skill consume those same scopes —
so store↔recall provably agree. Scope derivation is purely local (git/jj) and
auth-independent; only the actual tool calls require OAuth, and those run through
Claude's authenticated MCP connection, never through a hook.

```text
memory-curator/
  plugin.json
  .mcp.json
  hooks/
    hooks.json
    session-start-memory-recall        # uv script
    session-end-memory-capture         # uv script (Stop matcher)
    lib/
      __init__.py
      scope.py                         # shared scope derivation (local git/jj only)
    tests/
      __init__.py
      test_scope.py
      test_session_start_memory_recall.py
      test_session_end_memory_capture.py
  skills/
    curating-memory/
      SKILL.md
    promoting-memory/
      SKILL.md
  README.md                            # setup + scope convention docs
plugins/memory-curator/                  # Codex wrapper
  .codex-plugin/plugin.json              # only wrapper-local real file
  .mcp.json -> ../../memory-curator/.mcp.json   # symlinks back to source
  hooks    -> ../../memory-curator/hooks
  skills   -> ../../memory-curator/skills
```

## Component: MCP wiring (`memory-curator/.mcp.json`)

```json
{
  "mcpServers": {
    "memory_oauth": {
      "type": "http",
      "url": "https://litellm.fzymgc.house/mcp/memory_oauth",
      "oauth": { "callbackPort": 8765 }
    }
  }
}
```

- Server name **`memory_oauth`** (must match the registered route exactly;
  underscore required) → tools surface as `mcp__memory_oauth__store_memory`, etc.
- **No headers, no secret.** The server uses OAuth: on first use it returns 401,
  Claude Code flags it in `/mcp`, and the user runs `/mcp` → `memory_oauth` →
  Authenticate (one-time browser/Authentik PKCE flow). The token auto-refreshes.
  The "never commit a secret" constraint is satisfied by construction — there is
  nothing to wire from Vault/env.
- `oauth.callbackPort` pins the redirect URI to `http://localhost:8765/callback`
  to match Authentik's pre-registered redirect. **Implementer-verify** the exact
  `.mcp.json` field name/shape (`oauth.callbackPort`) against the installed
  Claude Code version (Open item #1); the CLI equivalent is `--callback-port`.
- README documents the one-time `/mcp` Authenticate step as the only setup, and
  notes that headless/CI sessions cannot authenticate yet (see degradation in
  §session-start recall).

## Component: scope derivation (`hooks/lib/scope.py`)

Produces a **two-tier scope pair** from the current cwd:

- **spine** = `repo:<repo-id>` — repo-wide durable facts, shared across every
  workspace/worktree of the repo.
- **overlay** = `repo:<repo-id>:ws:<workspace>` — durable context local to this
  line of work (this workspace/worktree).

`<repo-id>` is repo-stable (same from any workspace); `<workspace>` is
per-workspace-stable. Both halves must be deterministic so store↔recall agree
(requirement #5). Two sub-derivations:

> **Contract vs. reference.** The binding contract is: (1) the two invariants
> above (spine workspace-invariant, overlay per-workspace, both deterministic),
> (2) jj-first ordering, and (3) the six test scenarios at the end of this
> section. The specific commands below are a *verified reference path* (confirmed
> live, see Grounding traces) — the implementer SHOULD adjust the exact parsing
> to match actual jj 0.41 / git output rather than treat the command strings as
> immutable, as long as the invariants and scenarios hold.

### Repo identity `<repo-id>` (workspace-invariant)

Keys off **repository identity (the `origin` remote), never the working
directory**, so all workspaces of one repo share the same `<repo-id>`.

**Critical, verified fact:** a jj workspace (a `<repo>_worktrees/<name>` sibling)
is **not itself a git repo** — `git remote get-url origin` fails with "not a git
repository" there; only the colocated *default* workspace has `.git`. jj
workspaces share the `.jj/repo` store (the workspace's `.jj/repo` is a pointer
file to the default workspace's store), and `jj git remote list` works from any
of them and returns the same `origin`. Therefore derivation is **jj-first**.

1. **If `jj root` succeeds (jj repo, incl. any workspace):** read the remote via
   `jj git remote list`, take `origin`'s URL. Identical from default and every
   `_worktrees/<name>` workspace (shared store). Normalize (strip scheme,
   credentials, trailing `.git`) → `<host/org/repo>`.
2. **Else if `git remote get-url origin` succeeds (pure git, incl. git
   worktree):** git worktrees share `origin` natively. Normalize → `<host/org/repo>`.
3. **Fallback (no remote):** resolve the *primary* root (not the current
   worktree), use its basename:
   - jj repo → resolve the workspace's `.jj/repo` pointer to the shared store,
     strip trailing `/.jj/repo` → default workspace root. (Verified:
     `mermaid-skill`'s `.jj/repo` reads `../../../fzymgc-house-skills/.jj/repo`
     → `fzymgc-house-skills`, identical from every workspace.)
   - pure git worktree → parent of `git rev-parse --git-common-dir`.
4. If nothing resolves → `<repo-id>` is `None`; caller degrades silently.

### Workspace name `<workspace>` → overlay (non-default workspaces only)

**The primary checkout is spine-only.** It sits on trunk — the baseline the
spine already represents — so it is not a divergent line of work and has no
overlay. An overlay exists only for a *named, non-default* workspace, which is
where divergent durable facts need isolation. This keeps a `ws:default` junk
drawer from ever existing and yields a clean model: the main checkout shows the
canonical spine; each worktree layers its own context on top.

1. **jj:** `jj log -r @ --no-graph -T 'working_copies'` → e.g.
   `worktree-mermaid-skill@`; take the name via `split('@')[0]` (not
   `rstrip('@')`, which would corrupt a name legitimately containing `@`).
   (Verified live. The
   implementer confirms it returns exactly the current workspace when multiple
   workspaces sit on the same commit — disambiguate via `jj workspace root` if
   needed.) If the name is `default` → **no overlay**.
2. **git worktree:** the primary/main worktree → **no overlay**; a linked
   worktree → basename of `git rev-parse --show-toplevel`.
3. If the workspace resolves to `default` / the primary checkout, or cannot be
   resolved → `<workspace>` is `None`, i.e. **no overlay** (spine-only). Never
   fabricate a `ws:default` bucket.

### Output

Returns `(spine, overlay)` where `overlay` is `None` for the primary checkout.
Canonical example from the `mermaid-skill` jj workspace:

- spine = `repo:github.com/fzymgc-house/fzymgc-house-skills`
- overlay = `repo:github.com/fzymgc-house/fzymgc-house-skills:ws:worktree-mermaid-skill`

From the default checkout: same spine, **overlay = `None`** (spine-only; recall
and store both operate on the spine alone).

Unit-tested across: default workspace (asserts `overlay is None`), jj
workspace+remote (`jj git remote list` path, distinct overlay), pure git
linked-worktree+remote, remote-less jj workspace (`.jj/repo` pointer),
remote-less git worktree (`git-common-dir`), non-repo cwd — asserting (a) spine
identical across all workspaces of one repo, (b) overlay distinct per named
workspace, and (c) **no overlay for the primary checkout**. Exact
`jj git remote list` / `working_copies` / `.jj/repo` parsing is verified against
jj 0.41 during implementation.

The richer record fields (`worktree_path`, `base_dir`, `workspace`) MAY also be
populated by the curation skill on store for provenance, but the `scope` string
(spine or overlay) remains the single grouping key store and recall agree on.

## Component: session-start recall (`hooks/session-start-memory-recall`)

`SessionStart` matcher `startup|clear|compact` (mirroring the jj plugin).

**Model-mediated by necessity.** Under OAuth the hook has no credential to call
the endpoint (confirmed: hooks cannot read Claude Code's MCP OAuth token). So the
hook does **no network call** — it computes scopes locally and emits an
instruction for Claude to call `list_memory` over its own authenticated MCP
connection. This is a deliberate trade-off: scope *derivation* stays deterministic
(the property that makes store↔recall agree), but recall *firing* is now
model-mediated rather than hook-driven. There is no supported alternative given
OAuth + the hook credential boundary.

Contract:

1. Read hook stdin JSON for `cwd`.
2. Derive `(spine, overlay)` via `scope.py` (local git/jj only). If `spine` is
   `None` → exit 0 silently (not a repo).
3. Emit `additionalContext` via the structured JSON form on stdout — matching
   `dev-flow/hooks/nudge-rg-over-grep`:
   `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
   "<text>"}}`. The `<text>`:
   - States the scope(s): **always** `Memory spine scope: <spine>`; add
     `Memory workspace scope: <overlay>` **only when an overlay exists**. These
     also tell the curation skill where to store.
   - **Instructs Claude** to call `mcp__memory_oauth__list_memory` once per scope
     (spine, and overlay if present), merge/dedupe (spine wins), and surface the
     results in two labelled groups ("Repo-wide" / "This workspace") — **silently
     skipping any group that returns nothing** (no "nothing found" noise).
   - **Degradation instruction:** if the `memory_oauth` server is not
     authenticated (the tool call returns 401/403), Claude should note *once*
     that memory recall is unavailable and the user can authenticate via `/mcp`,
     then continue without blocking. Never treat unauthenticated as an error that
     derails the session.
4. **Headless guard:** if the session is non-interactive (no browser OAuth
   possible), the hook MAY suppress the recall instruction to avoid a guaranteed
   401 round-trip, emitting only the scope line(s). Detection mechanism is
   **implementer-verified** (Open item #5) — do not hard-code an unverified env
   var name.
5. The hook never makes a network call and never handles credentials, so it
   cannot itself fail on auth; any local error (e.g. scope derivation) → single
   stderr line, exit 0.

Because recall is an instruction Claude executes, the silence and
unauthenticated-degradation requirements are satisfied by Claude following the
emitted instruction, not by the hook inspecting tool output.

## Component: session-end capture (`hooks/session-end-memory-capture`)

`Stop` hook (command-type). **Mechanism note:** the only channel by which a hook
can make Claude *act* at session end is the Stop hook's
`{"decision": "block", "reason": "<text>"}` form — Claude receives `reason` as a
prompt and takes one more turn instead of stopping. There is no non-blocking
"nudge-to-act" path, and `SessionEnd` is cleanup-only (cannot prompt Claude). So
this hook deliberately **interjects exactly once** before the session stops,
guarded against looping.

Contract:

1. Read stdin JSON, including `stop_hook_active`.
2. **Loop guard (correct direction):** if `stop_hook_active` is `true`, Claude is
   already continuing because this hook blocked on a prior turn — `exit 0` with
   no output to **allow** the stop. Firing again here would loop forever.
3. Otherwise (`stop_hook_active` false): derive `(spine, overlay)`. If `spine` is
   `None`, `exit 0` (nothing to scope; don't interject). Else emit:

   ```json
   {"decision": "block",
    "reason": "Before stopping: evaluate whether anything durable was learned
   this session and capture it per the curating-memory skill — repo-wide facts
   to spine <spine>[, work-local facts to overlay <overlay>]. If nothing durable
   was learned, simply stop."}
   ```

   The overlay clause is included only when an overlay exists (primary checkout →
   spine-only wording). The "if nothing durable, simply stop" sentence keeps the
   single interjection cheap when there's nothing to store.
4. The hook never judges durability itself — it hands that to the skill. Net
   effect: at most one extra turn per session end.

This blocks the *first* stop attempt by design (that is the only way to prompt
capture); the `stop_hook_active` guard guarantees it never blocks a second time.

`hooks.json` registration: the `Stop` event takes **no `matcher`** (Stop events
ignore matchers), so register a bare hooks array:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command",
  "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/session-end-memory-capture\"",
  "timeout": 10}]}]}}
```

(The `SessionStart` recall entry uses `"matcher": "startup|clear|compact"` as the
`jj` plugin does.) Both entries live in **one** `memory-curator/hooks/hooks.json`
— a single file with both a `SessionStart` and a `Stop` key under `hooks`,
mirroring `jj/hooks/hooks.json`'s structure — not separate files.

## Component: curation skill (`skills/curating-memory/SKILL.md`)

Model-invoked. Encodes the discipline the issue requires:

- **Junk taxonomy.**
  - STORE (durable): decisions, preferences, conventions, gotchas,
    project-specific facts that outlive the session.
  - DON'T STORE: transient state, current activity/progress, secrets, API keys,
    timestamps, one-off tool output, anything re-derivable.
- **Search before store.** Always `search_memory` first (across **both** the
  spine and the workspace overlay) to avoid duplicates; if a near-duplicate
  exists, update it instead of adding.
- **Supersede on contradiction.** When new info conflicts with an existing
  memory, `update_memory` (preferred) or `delete_memory` the stale record so the
  store stays correct — this correctability is the whole point. Supersede
  *within a tier*; do **not** treat a spine fact and a divergent workspace fact
  as a contradiction — they are parallel truths by design (this is exactly why
  the overlay exists).
- **Tier selection (spine vs overlay).** Default to the **spine** — most durable
  facts (conventions, preferences, architecture decisions, repo-wide gotchas)
  are repo-wide and should follow the user into every workspace. Store to the
  **overlay** only when a fact is genuinely local to *this* line of work and
  would be wrong or premature elsewhere (e.g. an in-flight design decision on a
  feature branch that contradicts main until merged). Promotion of overlay facts
  to the spine when the work merges is its own workflow — see the
  `promoting-memory` skill.
- **Scope usage.** Store under the `Memory spine scope` / `Memory workspace
  scope` lines surfaced at session start. Set `source` to `user-said` vs
  `agent-inferred` honestly. Do **not** set `actor` — it is assigned server-side
  from the validated OAuth token; treat it as read-only provenance on recall.
- **Tools** are the `memory_oauth` server's: `mcp__memory_oauth__store_memory`,
  `…__search_memory`, `…__update_memory`, `…__delete_memory`, etc.
- **Unauthenticated handling.** If a memory tool returns 401/403, the server
  isn't authenticated — tell the user once they can authenticate via `/mcp`
  (`memory_oauth` → Authenticate) and skip the store; never lose the user's
  durable fact silently (restate it so they can re-store after authenticating).
- Triggers: when the user states a durable preference/decision/convention; on
  the session-end nudge; and before each memory-tool call, apply the junk
  taxonomy + search-before-store checks (the discipline gates the call, rather
  than the call invoking the skill).

## Component: promotion skill (`skills/promoting-memory/SKILL.md`)

Model-invoked workflow for graduating a workspace overlay into the repo spine
when a line of work completes (merges, lands, or is abandoned). This is the
counterpart to capture-time tier selection: `curating-memory` decides where a
*new* fact goes; `promoting-memory` reconciles an *existing* overlay against the
spine at the natural end of the work.

Triggers:

- The user asks to "promote memories", "merge workspace memories", "clean up
  this workspace's memories", or finishes/merges a line of work.
- Naturally pairs with `dev-flow:finishing-a-development-branch` — that skill's
  completion path SHOULD point here (a soft reference, not a hard dependency;
  memory-curator must not require dev-flow). The session-end capture nudge MAY
  also mention promotion when an overlay is non-empty.

Workflow:

1. Derive `(spine, overlay)` via the same `scope.py`. If `overlay` is `None`
   (primary checkout), there is nothing workspace-local to promote — exit.
2. `mcp__memory_oauth__list_memory(overlay)` — enumerate this workspace's local
   memories (all `memory_oauth` tools; 401/403 → server unauthenticated, tell the
   user to `/mcp` Authenticate and stop). If empty, report "nothing to promote".
3. For each overlay memory, decide with the user (or per clear criteria):
   - **Promote** — the fact is now true repo-wide. `search_memory(spine, …)`
     first for a duplicate/contradiction; then `store_memory(spine, …)` (or
     `update_memory` the spine record on contradiction, applying
     supersede-on-contradiction), and `delete_memory` the overlay copy.
   - **Keep** — still genuinely work-local (rare once work has merged); leave in
     the overlay.
   - **Drop** — no longer relevant (the work was abandoned, or it was transient
     after all); `delete_memory`.
4. Offer `delete_all(overlay)` as a teardown once the workspace is being retired,
   after promotions are done.

Promotion is **deliberate and model/user-mediated** — there is no automatic
merge-triggered migration (auto-promotion would need merge detection and risks
graduating junk). This keeps the spine zero-junk and the human in the loop.

## Registration + Codex parity

- **Claude:** add `memory-curator` to `.claude-plugin/marketplace.json`
  (`source: ./memory-curator`).
- **Codex:** `plugins/memory-curator/` wrapper — `.codex-plugin/plugin.json`
  (real file) plus **symlinks** back to source for everything else:
  `hooks → ../../memory-curator/hooks`, `skills → ../../memory-curator/skills`,
  and `.mcp.json → ../../memory-curator/.mcp.json`. (Verified pattern:
  `plugins/homelab/.mcp.json` is itself a symlink — `→ ../../.mcp.json` — so
  symlinking the MCP config, not copying it, is the established convention.)
  Register in `.agents/plugins/marketplace.json` with the same policy/category
  shape as the others.
- Do not duplicate skill/hook/MCP trees — the Codex wrapper symlinks to source;
  only `.codex-plugin/plugin.json` is wrapper-local.

## Quality gates

`Taskfile.yaml` uses **explicit path lists** (not globs) in its `vars`, so each
must be edited by name — a plan author must not assume new paths are picked up
automatically:

- `PYTEST_DIRS`: add `memory-curator/hooks/tests/`. (ruff runs repo-wide via
  `ruff check .`, so the lib/hook python is covered without a list edit.)
- `MD_FILES`: add `memory-curator/skills/*/SKILL.md` and
  `memory-curator/README.md`.
- `PLUGIN_JSON`: add `memory-curator/plugin.json`. The Codex wrapper's
  `.codex-plugin/plugin.json` is already covered by the existing
  `plugins/*/.codex-plugin/plugin.json` glob; the two `marketplace.json` files
  are already listed.
- **`.mcp.json` is *not* currently jq-validated** (it is absent from
  `PLUGIN_JSON`). Optionally extend the `jq empty` step to include
  `memory-curator/.mcp.json` (and the wrapper symlink) so the MCP config is
  syntax-checked; the plan should decide explicitly rather than rely on a
  non-existent gate.
- Hook tests follow `jj/hooks/tests/` patterns (stdin JSON fixtures, monkeypatch
  subprocess/HTTP, assert stdout/exit code).

## Testing strategy

- `test_scope.py`: each scenario above with fabricated git/jj layouts
  (monkeypatch `subprocess` calls to `git`/`jj`). Must assert: (a) jj-first
  ordering — a jj workspace resolves `<repo-id>` via `jj git remote list`, never
  `git remote` (which fails there); (b) **spine identical** across default
  workspace + jj workspace + git worktree of one repo; (c) **overlay distinct**
  per workspace, and `default` for the primary checkout; (d) remote-less
  `.jj/repo`-pointer and `git-common-dir` fallbacks.
- `test_session_start_memory_recall.py`: the hook makes **no network call** — it
  emits `additionalContext` JSON containing the scope line(s) and a `list_memory`
  instruction. Assert: named workspace → two scope lines + instruction naming
  both scopes; primary checkout → one spine line + instruction naming spine only
  (no overlay); non-repo (`spine is None`) → exit 0, no output; the emitted text
  includes the silence and 401-degradation instructions. (No `memory_client`
  test — there is no client; recall is model-mediated.)
- `test_session_end_memory_capture.py`: `stop_hook_active: true` → exit 0, no
  output (loop guard); `stop_hook_active: false` + named workspace → `decision:
  block` with reason naming spine + overlay; primary checkout → reason names
  spine only; `spine is None` → exit 0 (no interjection).

## Considered alternatives

### Hook-spawned headless `claude -p` for deterministic recall (deferred)

Instead of model-mediated recall, the SessionStart hook could shell out to a
separate headless `claude -p` (Haiku) invocation that calls `list_memory` and
returns results, which the hook then injects as `additionalContext`. This would
restore **deterministic, pre-loaded** recall (memories in context before the
main model's first turn) rather than relying on the main model to follow an
instruction.

**Why it works:** MCP OAuth tokens are stored **per-user, not per-session**
(`~/.claude/.credentials.json` / `~/.claude.json`) and a separate `claude -p`
process reuses them with automatic refresh — so after the one-time interactive
`/mcp` auth, a headless child can call the tool with no browser. (Verified via
claude-code-guide against code.claude.com/docs.) It also conditionally improves
the headless story: a machine that authed once can recall in later headless runs.

**Why it is NOT the default (deferred):**

- **Per-start latency on the critical path.** A Haiku + MCP-connect + tool-call
  (~2–8s) runs at *every* session start, including the common no-memories case
  that yields zero benefit. Model-mediated recall adds ~0 hook latency.
- **Uncertain failure mode.** If no token exists or refresh fails, docs don't
  confirm whether the child fast-fails or hangs for a browser; would require a
  hard `timeout … </dev/null` wrapper to guarantee non-blocking startup.
- **Recursion hazard.** The child re-fires SessionStart hooks; needs an env
  sentinel guard (e.g. `MEMORY_CURATOR_RECALL_CHILD=1` → hook exits early).
- **Breaks Claude/Codex hook parity.** Hooks are symlink-shared with the Codex
  wrapper, which has no `claude` binary; a `claude`-shelling hook becomes
  host-specific (would need host detection + no-op elsewhere).
- **CLI flag-surface coupling.** Depends on `claude -p` flags
  (`--mcp-config`/`--strict-mcp-config`, permission mode, output format, tool
  restriction) whose exact names vary by version and need verification.

**Revisit when:** pre-loaded determinism is judged worth the startup tax —
ideally paired with a **disk cache** (inject cached results instantly per scope,
refresh in the background) so the latency is paid only on a cache miss, and
after the headless fast-fail behavior is confirmed. Until then, model-mediated
recall is the contract.

## Non-goals

- No changes to the memory service.
- No knowledge-graph / temporal auto-extraction behavior (rejected alternative).
- No automatic storing by hooks — capture is always model-mediated through the
  curation skill (preserves the zero-junk, explicit-store intent).
- No non-interactive / service-token auth path — OAuth here is interactive only;
  headless/CI support is a planned service-side follow-up, out of scope for the
  plugin (which degrades gracefully instead).
- No hook-side memory calls — hooks cannot hold the OAuth credential; all tool
  calls go through Claude's authenticated MCP connection.

## Open items for the plan/implementer

1. Verify the `.mcp.json` OAuth field name/shape — the design assumes
   `"oauth": {"callbackPort": 8765}` (CLI equivalent `--callback-port`) per the
   claude-code-guide grounding, but confirm against the installed Claude Code
   version's actual `.mcp.json` schema before relying on it. Confirm a
   plugin-bundled OAuth HTTP server with no headers triggers the `/mcp`
   Authenticate flow on 401.
2. Verify `jj git remote list` output parsing and the `.jj/repo` pointer-file
   resolution on jj 0.41 (the remote-less fallback anchor). Confirmed at design
   time that `jj git remote list` returns `origin` from inside a jj workspace
   and that `git remote` fails there.
3. Confirm the production scope-string conventions (spine `repo:<host/org/repo>`
   and overlay `repo:<host/org/repo>:ws:<workspace>`) are acceptable to the
   deployed service. The upstream jsonschema only *hints* a `tier:repo` shape
   (e.g. `eval-2026-05:project:selfhosted-cluster`); confirm whether the service
   **enforces** any format or merely stores the string verbatim. This matters:
   if it silently accepts any string, a convention mismatch causes a quiet
   scope-miss (recall returns nothing) rather than a hard error — so the
   store/recall convention must be locked and documented in README, not just
   assumed compatible.
4. Verify `jj log -r @ -T 'working_copies'` reliably returns the *current*
   workspace name (confirmed live in a single-workspace-per-commit case);
   disambiguate via `jj workspace root` if multiple workspaces share `@`'s
   commit.
5. Verify the headless/non-interactive detection mechanism for the recall hook's
   optional 401-avoidance guard (the claude-code-guide suggested an env like
   `CLAUDE_INTERACTIVE` but this is **unconfirmed** — do not hard-code it). If no
   reliable signal exists, the hook simply emits the recall instruction always
   and Claude handles the 401 per the degradation instruction.

## References / Grounding traces

Recorded as `bd note`s on design bead **fhsk-ga7** (run `bd show fhsk-ga7`).
Each claim below was verified live during brainstorming, not assumed:

- **Plugin MCP config mechanics** (claude-code-guide → code.claude.com/docs):
  plugins declare MCP via `.mcp.json` at plugin root or `mcpServers` in
  `plugin.json`; HTTP transport supported (`type: "http"`, `url`, `headers`)
  with `${VAR}` interpolation; hooks may call MCP tools via `type: "mcp_tool"`
  but **only with static/templated args — not values computed by shelling out**
  (which is why recall is a command hook + instruction, not an `mcp_tool` hook).
- **OAuth + hook credential boundary** (claude-code-guide →
  code.claude.com/docs/mcp-servers, /hooks): a plugin HTTP server with no headers
  triggers Claude Code's OAuth flow on 401/403 (flagged in `/mcp`); `.mcp.json`
  reportedly supports `oauth.callbackPort` to pin the redirect port (Open item
  #1 — verify schema); **hooks cannot read the MCP OAuth token** (no documented
  interface; env exposes only `CLAUDE_PROJECT_DIR`/`CLAUDE_PLUGIN_ROOT`/
  `CLAUDE_PLUGIN_DATA`). This is the architectural basis for model-mediated
  recall.
- **Stop hook contract** (claude-code-guide → code.claude.com/docs/hooks):
  the only way to make Claude act at session end is `{"decision":"block",
  "reason":…}`; `SessionEnd` is cleanup-only and cannot prompt; `stop_hook_active`
  is the loop guard (true ⇒ already continuing ⇒ allow stop). Basis for the
  block-once capture design.
- **Auth model (current)** — GH#131 update comment (2026-06-01): endpoint
  `https://litellm.fzymgc.house/mcp/memory_oauth`; native MCP OAuth via Authentik
  PKCE (`delegate_auth_to_upstream`, upstream JWT validation); no static key/
  secret; records gain a server-set `actor` field; interactive-only (headless
  follow-up pending). PRs `selfhosted-cluster` #1133–#1137.
- **Auth model (SUPERSEDED)** (`selfhosted-cluster:docs/operations/
  litellm-mcp-clients.md`): the original static-key route `/mcp/memory` with
  header `x-litellm-api-key: Bearer sk-…` and Vault `claude_code_memory` is
  retired — retained here only to mark what changed.
- **Memory tool/scope shape** (`selfhosted-cluster:services/memory-mcp/tools.go`):
  confirmed `store_memory`/`search_memory`/`update_memory`/`delete_all`; `scope`
  is a structured colon-delimited string (schema hint `tier:repo`). Basis for
  Open item #3. (Tool *set* unchanged by the auth update; `actor` field added.)
- **jj workspace resolution** (verified live in this repo's 8 workspaces): a jj
  workspace (`<repo>_worktrees/<name>`) is **not** a git repo — `git remote`
  fails there; `jj git remote list` returns the shared `origin` from any
  workspace; `.jj/repo` is a pointer to the default workspace's store;
  `jj log -r @ -T 'working_copies'` yields the current workspace name. Basis for
  the jj-first derivation and the spine/overlay split.

Degraded-mode note: context7 was used for Claude Code docs; no grounding tool was
unavailable. All external-service facts trace to the sibling `selfhosted-cluster`
repo or its committed docs.
