---
title: "Replace blocking Stop-hook capture nudge with silent SessionStart briefing and throttled PostToolUse nudge"
---
<!-- markdownlint-disable MD013 -->
<!-- adr-render: source=bd:fhsk-p07; do not edit manually; use `/adr update fhsk-p07` -->

**Date:** 2026-06-02
**Status:** Accepted
**Decision:** fhsk-p07
**Deciders:** Sean Brandt

## Context

The memory-curator plugin originally used a `Stop` hook (`session-end-memory-capture`) that emitted `{"decision":"block","reason":...}` to nudge end-of-session memory capture. The original design spec named this "the only mechanism to prompt Claude at stop." In practice Claude Code renders ANY Stop-hook block as `Stop hook error: <reason>` in the transcript — on every session, including successful ones — because the harness does not distinguish an intentional block from a crashed hook. The effect is a scary, error-styled line at every single session end. The label is harness-rendered and cannot be overridden from the hook (`suppressOutput`/`systemMessage` do not remove it), and `decision:block` is the only way to make Claude act at `Stop`, so the only available levers are reduce-frequency or eliminate.

## Decision

Remove the blocking `Stop` hook entirely. Move the capture discipline into the `SessionStart` recall hook's silent `additionalContext` (which already re-fires on the `compact` matcher), and add a throttled `PostToolUse` hook (matcher `Edit|Write|NotebookEdit`, once per session via a `session_id` marker file in tempdir) that silently re-surfaces the capture reminder mid-work. `additionalContext` is injected silently and read on the following model turn, so neither mechanism produces error-styled output. Also document that `search_memory` is semantic/vector-backed so callers query it with natural-language descriptions.

## Rationale

- The "Stop hook error" label is harness-rendered for any `decision:block` and cannot be suppressed by the hook; blocking is the only way to act at `Stop`. Reduce-frequency or eliminate are the only options.
- `SessionStart` and `PostToolUse` both support `hookSpecificOutput.additionalContext`, injected silently (no chat message, no error styling) and read on the next model turn. Unlike `Stop`, both have a following turn, so the nudge is actually effective.
- `SessionStart` already matches `compact`, so folding the capture briefing there covers fresh sessions and post-compaction continuations in one edit.
- A `PostToolUse` nudge scoped to mutating tools and throttled to once per session lands the reminder when durable facts are actually being created, compensating for `SessionStart` context fading over a long session — without per-edit spam.
- Trades a guaranteed end-of-session forcing function for zero error-styled UX, an explicit user preference.

## Alternatives Considered

### Conditional Stop block (rejected)

Keep blocking but only when the transcript (`transcript_path`) shows substantive activity. Reduces frequency but still emits the "error" label whenever it fires, and a heuristic cannot reliably detect whether anything *durable* was learned.

### Time-throttled Stop block (rejected)

Stamp a state file and skip re-blocking within N minutes. A blunt clock proxy uncorrelated with durability; still produces periodic error-styled lines.

### Stop block with suppressOutput / systemMessage (rejected)

Neither field removes the harness `Stop hook error` prefix; they only affect adjacent output. The scary label remains.

## Consequences

**Positive:**

- Zero error-styled output at any point in the session lifecycle.
- Capture expectations survive compaction via the `SessionStart` re-fire on `compact`.
- The `PostToolUse` nudge is timely (fires after the first repo mutation), silent, and throttled to once per session.

**Negative:**

- No guaranteed end-of-session capture sweep — capture now depends on the model acting on silently-injected reminders plus the reactive `curating-memory` skill.
- A durable fact stated in a pure-conversation session with no tool use relies solely on the `SessionStart` briefing (no `PostToolUse` fire).

**Neutral:**

- `PostToolUse` throttle state is a per-session marker file in tempdir keyed by `session_id`; sessions without a `session_id` receive no nudge (`SessionStart` still covers them).
