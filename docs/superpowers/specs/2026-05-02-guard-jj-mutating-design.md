# guard-jj-mutating Hook

Date: 2026-05-02
Bead: `fhsk-406`
Companion to: `fhsk-5qh` (PR #50, prose rule landed 2026-05-01)

## Problem

The jj skill's SKILL.md prose rule (PR #50) says agents MUST NOT run
`jj op restore` or `jj op abandon` without explicit user approval,
because both rewind the global op log and can silently lose edits in
sibling workspaces (`jj workspace update-stale` may resurrect pre-rewind
content). The rule is currently honor-system: an agent that ignores the
prose can still wreck a sibling workspace.

This spec adds the enforcement layer — a PreToolUse/Bash hook that
blocks `jj op restore` and `jj op abandon` invocations unless the agent
appends an in-line approval marker, mirroring the
`# jj-exempt`-promotes-to-ASK pattern already established by
`guard-git-mutating`.

## Scope

### In scope

- New file `jj/hooks/guard-jj-mutating` (Python, `uv run --script`)
- New file `jj/hooks/tests/test_guard_jj_mutating.py`
- One added entry in `jj/plugin.json` PreToolUse/Bash array

### Out of scope (explicit non-goals)

- Environment-variable bypass (e.g., `JJ_OP_APPROVE=1`) — single
  approval mechanism keeps audit trail in shell history; env vars hide
  intent
- Blocking the broader `jj op` family — safe siblings (`log`, `show`,
  `revert`, `diff`) stay silent; matches SKILL.md prose scope (line 264)
  exactly
- Shared module extraction (`jj/hooks/_common.py`) — defer until a third
  hook lands; YAGNI for two hooks
- Auto-edit of SKILL.md — recovery ladder is the canonical source; hook
  only points at it
- Detect & block jj operations from MCP tools or other matchers —
  PreToolUse/Bash matcher only; covers all shell-routed invocations,
  which is the realistic surface

## Design

### Response model

Mirrors `guard-git-mutating`'s four-tier vocabulary, restricted to the
`jj op` policy:

| Condition | Response | Mechanism |
|---|---|---|
| `# jj-op-approved` substring in command | **ASK** (human prompted) | `permissionDecision: "ask"` JSON to stdout |
| Matched command, no marker, in jj repo | **DENY** | `permissionDecision: "deny"` JSON + `systemMessage` to stdout (fallback `exit 2` only on broken pipe) |
| Not a matched command, OR not in a jj repo, OR malformed input | **ALLOW** silently | `sys.exit(0)` |

Marker check happens **before** the jj-repo check. If an agent appends
the marker, the human prompt fires regardless of `.jj/` presence — the
marker signals intent and the human can decide. Mirrors the equivalent
order in `guard-git-mutating`.

### Detection regex

```python
JJ_OP_BLOCKED_RE = re.compile(
    r"\bjj\b(?:\s+-\S+(?:\s+\S+)?)*\s+(?:op|operation)\s+(?:restore|abandon)\b"
)
```

Matches:

- `jj op restore`, `jj op abandon`
- Long form `jj operation restore`, `jj operation abandon`
- With intervening flags, single-token (`--at-op=abc`) or two-token
  (`--repo /x`, `-R /tmp`) form: `jj --repo /x op restore`,
  `jj --at-op=abc op abandon`, `jj -R /tmp op restore`
- In compound shell context: `jj op restore && echo ok`, `$(jj op restore)`,
  `prev_cmd; jj op abandon`

The flag fragment mirrors `GIT_CMD_RE`'s `(?:-\S+(?:\s+\S+)?\s+)*` in
`guard-git-mutating`, which optionally consumes one value token per flag.
Regex backtracking handles the ambiguity when a "flag" has no value and
the next token is the subcommand (e.g. `jj --quiet op restore`): the
engine first tries to consume `op` as the flag's value, fails to match
the subcommand, then backtracks to leave `op` for the subcommand group.

Same shell-context tolerance as `GIT_CMD_RE` in `guard-git-mutating`.

### Approval marker syntax

`# jj-op-approved` — distinct from the existing `# jj-exempt` marker.
Rationale: `jj-exempt` makes a categorization claim ("this git command
is fine in a jj repo"); `jj-op-approved` makes a permission claim ("the
user approved rewinding the op log"). Conflating them weakens the audit
trail when someone greps shell history.

Detection is a simple substring check (`"# jj-op-approved" in command`),
matching the precedent. The marker is permissive about location in the
command line — appearing anywhere in the string is sufficient.

### Execution flow

1. Read JSON from stdin; defensive try/except for
   `JSONDecodeError | OSError | AttributeError` → `sys.exit(0)`
2. Extract `command = tool_input["command"]` with
   `isinstance(tool_input, dict)` guard
3. If `command` empty → `sys.exit(0)`
4. **Marker check**: if `"# jj-op-approved" in command` → emit ASK JSON,
   return
5. Read `cwd` from input; walk up max 50 dirs looking for `.jj/`; if not
   found → `sys.exit(0)`
6. Run `JJ_OP_BLOCKED_RE.search(command)`; if no match → `sys.exit(0)`
7. **DENY**: emit JSON to stdout with `permissionDecision: "deny"`,
   `permissionDecisionReason`, and top-level `systemMessage`; wrap the
   `json.dump` in `try/except OSError` and fall back to `sys.exit(2)` on
   broken pipe (mirrors `guard-git-mutating` lines 258–263)

### Response shapes

**ASK** (marker present):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "jj-op-approved: agent is requesting to rewind the global jj op log (jj op restore/abandon). Review and approve or deny."
  }
}
```

**DENY** (matched command, no marker, in jj repo):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "BLOCKED: jj op restore/abandon rewinds the global op log and can silently lose edits in sibling workspaces. Use `jj op revert <op-id>` for surgical recovery (see jj skill recovery ladder)."
  },
  "systemMessage": "jj op restore/abandon was blocked. These commands rewind the global op log and may silently lose edits in sibling workspaces via `jj workspace update-stale`. Prefer `jj op revert <op-id>` for surgical recovery. If the user has explicitly approved this op-log rewind, append `# jj-op-approved` to the command (escalates to ASK)."
}
```

### Plugin wiring

Append to existing PreToolUse/Bash array in `jj/plugin.json`:

```json
"PreToolUse": [
  {
    "matcher": "Bash",
    "hooks": [
      { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-git-mutating", "timeout": 5 },
      { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard-jj-mutating", "timeout": 5 }
    ]
  }
]
```

Both guards run on every Bash invocation. Ordering doesn't matter
because they match disjoint command sets (git-mutating subcommands vs
`jj op restore|abandon`).

## Tests

`jj/hooks/tests/test_guard_jj_mutating.py`, mirroring the class layout
of `test_guard_git_mutating.py`:

| Class | Cases |
|---|---|
| `TestBlocked` | `jj op restore`, `jj op abandon`, `jj operation restore`, `jj operation abandon`, with `--at-op=` flag, with `--repo /x` flag, in compound (`jj op restore && echo ok`), in subshell (`$(jj op restore)`) — all in a jj repo, all expect exit 0 + stdout JSON with `permissionDecision: "deny"` and `systemMessage` containing "jj op revert" |
| `TestApprovedMarker` | Each blocked form **with** `# jj-op-approved` appended → expect exit 0 + stdout JSON with `permissionDecision: "ask"` |
| `TestAllowed` | `jj op log`, `jj op show`, `jj op revert <id>`, `jj op diff`, `jj status`, `jj new`, `git status`, plain `ls` — all expect exit 0 + no stdout |
| `TestNotInJjRepo` | `jj op restore` in a tmpdir with no `.jj/` → exit 0 (silent allow; jj itself will reject) |
| `TestEdgeCases` | Empty stdin, malformed JSON, `tool_input: null`, `tool_input: "not-a-dict"`, missing `cwd`, command without `tool_input` key → all exit 0 (closes the same gaps `qpw.4` filed against the git hook) |

Pytest fixtures: reuse the `jj_repo` fixture pattern from
`test_session_start_jj_detect.py` (creates a real `jj init` tmpdir).

CI: already covered by `check-skills.yml:77` —
`pytest .claude/hooks/tests/ jj/hooks/tests/ tests/`. New file picked up
automatically.

## Acceptance criteria (from bead `fhsk-406`)

- ✅ Hook blocks `jj op restore` and `jj op abandon` by default with
  message pointing to recovery ladder
- ✅ Unit tests under `hooks/tests/`
- ✅ Hook is wired into `jj/plugin.json` (the plugin's hook
  registration)

## References

- Bead `fhsk-406` — this work
- Bead `fhsk-5qh` (closed) — companion prose rule, PR #50
- Bead `fhsk-804` (open) — multi-workspace concurrency doctrine, related
- `jj/hooks/guard-git-mutating` — analog hook, structural template
- `jj/hooks/tests/test_guard_git_mutating.py` — test layout template
- `jj/skills/jujutsu/SKILL.md` (lines 245–280) — recovery ladder
- jj-vcs/jj#9208 — upstream issue documenting the global-op-log blast
  radius
