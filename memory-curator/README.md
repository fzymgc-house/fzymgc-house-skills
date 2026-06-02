# memory-curator

Wires the self-hosted memory MCP layer into Claude Code as a low-friction,
self-correcting part of every session: prior durable context surfaces at
session start, new durable knowledge is captured with discipline, and the store
stays correct over time.

## Setup (one-time)

Authentication is native MCP **OAuth** (Authentik PKCE) — there is no secret to
configure. After installing the plugin, run `/mcp`, select `memory_oauth`, and
choose **Authenticate**. A browser opens for Authentik login; the token is
stored per-user and auto-refreshes, so re-auth is only needed occasionally
(e.g. after a gateway restart).

Auth is interactive: headless/CI sessions that have never authenticated cannot
complete the browser flow and will simply have memory recall unavailable (the
session is never blocked).

## Scope convention

Memory is two-tier, keyed off repository identity (not the working directory):

- **spine** `repo:<host/org/repo>` — repo-wide durable facts, shared across
  every workspace/worktree of the repo.
- **overlay** `repo:<host/org/repo>:ws:<workspace>` — durable context local to a
  named non-default workspace. The primary checkout is spine-only.

The repo id is the normalized `origin` remote (jj-first: a jj workspace resolves
it via `jj git remote list`, since a workspace is not itself a git repo), with a
directory-basename fallback when there is no remote. Store and recall use the
same derivation, so what you store in one session is recalled in the next.

## What it does

- **Session start:** a hook computes the scope(s), asks Claude to recall this
  repo's durable memories (silent when there are none), and briefs it on the
  capture discipline. This is silent `additionalContext` and re-fires after
  compaction, so the expectations survive context loss.
- **During the session:** the `curating-memory` skill enforces durable-only
  capture, search-before-store (semantic/vector recall), and
  supersede-on-contradiction. After the first file edit, a throttled
  `PostToolUse` hook silently re-surfaces the capture reminder once per session.
- **Work completion:** the `promoting-memory` skill graduates workspace-local
  memories into the spine and cleans up.

There is no blocking session-end hook: nudging at `Stop` requires
`decision: block`, which Claude Code renders as a "Stop hook error" on every
session. Capture is instead set up front (session start) and re-surfaced
silently mid-work (`PostToolUse`), so the store stays current with zero
error-styled noise.
