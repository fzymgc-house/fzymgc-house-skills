# ast-grep (sg) reference

Use `sg` when the thing you're matching is a *syntax shape*, not a text pattern — e.g. "any call to
`foo` regardless of arguments", "any `T{...}` composite literal", "every `if err != nil` block".
Text regex can't reliably match nested/balanced code; ast-grep parses with tree-sitter. Companion to
the `grepping` skill; for text search see `ripgrep.md`.

## When to escalate from rg to sg

- The match spans balanced/nested code (function bodies, call arguments, composite literals).
- You want to match a construct regardless of formatting/whitespace/line breaks.
- You want a structural **rewrite** (`-r`) instead of a text substitution that would also hit
  comments, strings, and substrings.

For "where is `X` defined / how does `Y` work", prefer `mcp__probe__search_code` over both.

## Pattern syntax

| Construct | Meaning |
|-----------|---------|
| `$A`, `$NAME` | single named metavariable (matches one AST node) |
| `$$$`, `$$$ARGS` | multi metavariable (zero or more nodes — args, statements, fields) |
| `$_` | anonymous single-node wildcard |
| literal code | matched structurally, so `{ } ( ) .` need no escaping |
| same `$A` twice | both positions must be the same text |

## Commands

```bash
sg -p 'foo($$$ARGS)' -l go            # any call to foo, any args
sg -p 'eventbus.Event{$$$}' -l go     # any Event composite literal (no brace escaping)
sg -p 'if err != nil { $$$ }' -l go   # every nil-error guard
sg -p '$A.Close()' -l go              # any .Close() call; $A is one node
sg -p 'old($A)' -r 'new($A)' -l go    # search + show rewrite diff
sg -p 'old($A)' -r 'new($A)' -l go -U # apply the rewrite in place
sg scan -c sgconfig.yml               # run a YAML ruleset (lint-style)
sg run --debug-query=ast -p 'PAT' -l go   # diagnose a pattern that won't match
```

`-l` / `--lang` is effectively required for `run`. Values are tree-sitter language names (`go`,
`rust`, `python`, `tsx`, `typescript`, `javascript`, `java`, `c`, `cpp`, …); full list at
<https://ast-grep.github.io/reference/languages.html>. For complex multi-condition matches (kind +
inside + has), use a YAML rule with `sg scan` rather than a single `-p` pattern.

## Gotchas

- The binary is `sg` / `ast-grep`. On Linux `sg` may collide with shadow-utils' `setgroups` — use
  `ast-grep` or an alias if `sg` does something surprising.
- ast-grep respects `.gitignore` and skips hidden files, like rg. Use `--no-ignore hidden` to
  include them.
- A pattern that matches nothing is usually an invalid parse for the language — run
  `--debug-query=ast` to see the tree-sitter AST it actually built.
