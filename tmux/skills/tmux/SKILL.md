---
name: tmux
description: tmux terminal-multiplexer usage. Use when spawning or driving tmux sessions/windows/panes from a script or agent, capturing pane output, targeting panes by id, or when the user mentions tmux. Covers detection, spawning, send-keys, capture-pane, and lifecycle.
---

# tmux usage

Practical tmux primitives for scripting and agent automation. Examples below are
illustrative; for the drain worker's operational launch sequence see
`dev-flow/scripts/drain-worker-launch`.

## Detect whether you are inside tmux

```bash
[ -n "$TMUX" ] && echo "inside tmux"
```

`$TMUX` is set inside a tmux pane. Use it to decide between `new-window` (you are
inside a session) and a detached `new-session` (you are not).

## Spawn a surface and capture its pane id

Always target panes by their **pane id** (`%N`), never by index — indices
renumber when panes close.

```bash
# Inside an existing session: a new window, print its pane id
pane=$(tmux new-window -P -F '#{pane_id}')      # -> %12

# No session yet: a detached, named session sized for a TUI
pane=$(tmux new-session -d -s mywork -x 220 -y 50 -P -F '#{pane_id}')  # -> %12
```

A detached `new-session` defaults to **80×24**, which cramps a full-screen TUI;
set `-x`/`-y` explicitly.

## Drive a pane

`send-keys` sends literal text *or* a key. Send text and the submit separately —
a fast/long send can race the program's input handling:

```bash
tmux send-keys -t %12 -l 'echo hello'   # -l = literal text, no submit
tmux send-keys -t %12 Enter             # submit (C-m also works)
```

## Read a pane

```bash
tmux capture-pane -p -t %12             # print visible pane to stdout
tmux capture-pane -p -S -200 -t %12     # include 200 lines of scrollback
```

## Lifecycle

```bash
tmux list-sessions -F '#{session_name}'
tmux list-panes -t mywork -F '#{pane_id} #{pane_active}'
tmux kill-pane -t %12
tmux kill-session -t mywork
```

## Windows, layouts, copy-mode (brief)

```bash
tmux new-window -t mywork -n build       # named window in a session
tmux select-layout -t mywork tiled       # even-horizontal | even-vertical | tiled | main-vertical
tmux copy-mode -t %12                     # enter copy/scroll mode
```
