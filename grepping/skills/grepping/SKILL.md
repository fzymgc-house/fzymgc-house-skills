---
name: grepping
description: >-
  Use when searching code or text from the shell with grep, egrep, fgrep, ugrep, ripgrep (rg), or
  ast-grep (sg) — especially when a search unexpectedly returns nothing, an rg flag errors
  (unrecognized flag, regex parse error, "missing value for flag -r"), or you are translating
  grep/BSD-grep muscle memory (\| alternation, -r recursive, -E, --include) to rg. Also when a
  text regex cannot express a structural, syntax-aware match and you need ast-grep.
---

# Grepping

## Overview

**Reach for `rg` (ripgrep) by default for text search. Reach for `sg` (ast-grep) when you need to
match code *structure*, not text.** Most search failures in practice are grep muscle memory leaking
into rg: rg uses Rust regex (ERE-like, **not** grep's BRE), is recursive by default, and respects
`.gitignore`. The flags you remember from `grep`/`egrep`/BSD grep are often wrong — sometimes they
error, and sometimes (worse) they silently corrupt the search.

For "where is this symbol defined / how does this work" questions, prefer `mcp__probe__search_code`
first — it returns whole AST blocks. `rg` is for raw text matches; `sg` is for structural matches;
`probe` is for semantic symbol lookup. This skill covers `rg` and `sg`.

**Stance:** `rg` and `ast-grep` are the tools this plugin pushes; `grep`/`egrep`/`fgrep`/`ugrep`
are a fallback (a box without rg, or a ugrep-only feature like fuzzy/archive search). For
symbol lookup ("where is X / how does Y work"), `probe` outranks all of them when it is available.
Two hooks guard this skill non-blockingly:

- **PreToolUse** (`nudge-rg-over-grep`): when a grep-family tool leads a Bash command, nudges
  toward `rg`/`ast-grep`. When the search looks symbol-shaped **and** the probe MCP is configured,
  nudges toward `mcp__probe__search_code` first.
- **PostToolUse** (`nudge-rg-failure`): after an `rg` command completes, detects failure patterns
  (flag errors, `\|` alternation, suspect flags like `-rn`/`--include=`) and nudges to load this
  skill before retrying.

Both are advisory-only — they never block.

## Tool selection

| Goal | Tool |
|------|------|
| Find text / a regex anywhere in the tree | `rg` |
| Find a code shape (`if err != nil { return $A }`, a call with any args) | `sg` (ast-grep) |
| Structural find-and-**rewrite** across a codebase | `sg -p ... -r ...` |
| "Where is `Foo` defined / how does `Bar` work" | `mcp__probe__search_code` |
| You typed `grep`/`egrep`/`fgrep`/`ugrep` out of habit | translate to `rg` (below) |

## rg quick reference

```bash
rg 'pat'                       # recursive from cwd, respects .gitignore, skips binaries
rg -i 'pat'                    # case-insensitive    (-S = smart-case: case-insens unless pat has uppercase)
rg -n 'pat'                    # show line numbers
rg -F 'literal.string'         # fixed string — no regex (use for code with { } ( ) . * etc.)
rg -w 'word'                   # whole-word match
rg -l 'pat'                    # only file names that match  (--files-without-match = files that DON'T)
rg -A3 -B1 'pat'               # 3 lines after, 1 before  (-C2 = 2 lines both sides)
rg -t go 'pat'                 # only Go files            (rg --type-list shows built-ins)
rg -g '*.proto' 'pat'          # glob filter             (-g '!*_test.go' to EXCLUDE)
rg -o 'ver=\d+'                # print only the match
rg -o -r '$1' 'ver=(\d+)'      # print only capture group 1 (replacement uses $1, not \1)
rg -P 'foo(?=bar)'             # PCRE2: lookaround / backrefs / \K — REQUIRES -P
rg -U 'foo[\s\S]*bar'          # multiline (OFF by default); --multiline-dotall lets . span lines
rg --hidden --no-ignore 'pat'  # also search dotfiles and .gitignored files
rg -0 -l 'pat' | xargs -0 ...  # NUL-separated file list for safe piping
```

Defaults to remember: **recursive, `.gitignore`-aware, skips hidden files and binaries, multiline
OFF.** No pager (don't pass `--no-pager`; that's a git/jj flag).

## Common mistakes — ranked by how often they actually bite

These are the real, frequency-ranked failure modes. The first two are **silent**: no error, just
wrong or empty output, so you wrongly conclude "the code isn't there."

| Mistake | What happens | Fix |
|---------|--------------|-----|
| `rg 'A\|B'` (BRE alternation habit) | **Silent.** `\|` matches a *literal* pipe; the OR never happens, so you get nothing | `rg 'A|B'` — bare `|`, no backslash |
| `rg -rn 'pat'` / `rg -nr 'pat'` | **Silent corruption.** rg's `-r` is `--replace`; it eats `n` as the replacement and rewrites output | Drop `-r`. rg is already recursive: `rg -n 'pat'` |
| `rg 'pat' dir -r` (trailing `-r`) | Hard error: `missing value for flag -r` | Drop `-r` |
| `rg -nR 'pat'` | `unrecognized flag -R` | Drop `-R` (recursion is default) |
| `rg --include='*.go' 'pat'` | `unrecognized flag --include` | `rg -g '*.go' 'pat'` or `rg -t go 'pat'` |
| `rg -E 'A|B'` (extended-regex habit) | `unknown encoding: A|B` — rg's `-E` is `--encoding` | Drop `-E`; rg is ERE-like already |
| `rg 'Foo{'` / `rg 'pkg.Type{'` | `regex parse error: repetition quantifier...` — `{` is a regex metachar | `rg -F 'Foo{'` or escape: `rg 'Foo\{'` |
| `rg '...\K...'`, lookaround, backrefs | `unrecognized escape sequence` / `look-around not supported` | Add `-P`: `rg -P '...\K...'` |
| `rg -t proto 'pat'` | `unrecognized file type: proto` | `rg --type-add 'proto:*.proto' -t proto` or `-g '*.proto'` |
| `rg --no-pager 'pat'` | `unrecognized flag --no-pager` | Omit it — rg has no pager |
| `rg 'pat' && nothing found` | maybe a `-g`/`-t` filter excluded everything | re-run with `--debug`, or check `--no-ignore --hidden` |

**Rule of thumb:** if rg "finds nothing" for something you're sure exists, suspect `\|`, a stray
`-r`, or a `.gitignore`/type filter — in that order — before concluding the code is absent.

## grep-family → rg

`rg` is not flag-compatible with grep. The everyday translations:

| grep / egrep / fgrep | rg |
|----------------------|-----|
| `grep -r 'pat' .` | `rg 'pat'` (recursion + dir are default) |
| `grep -rn --include='*.go' 'pat' .` | `rg -n -t go 'pat'` |
| `egrep 'A\|B'` (or `grep -E 'A|B'`) | `rg 'A|B'` |
| `fgrep 'x'` (or `grep -F 'x'`) | `rg -F 'x'` |
| `grep -P 'foo(?=bar)'` | `rg -P 'foo(?=bar)'` |
| `grep -o 'pat'` | `rg -o 'pat'` |
| `grep -c 'pat'` | `rg -c 'pat'` |
| `grep -v 'pat'` | `rg -v 'pat'` |
| `grep -l 'pat'` | `rg -l 'pat'` |
| `grep -L 'pat'` | `rg --files-without-match 'pat'` |
| `grep -A3 -B1 'pat'` | `rg -A3 -B1 'pat'` (same) |
| `grep -w 'word'` | `rg -w 'word'` |
| `grep -i 'pat'` | `rg -i 'pat'` (or `-S` for smart-case) |

Per-tool references (load only the one you need):

- [references/ripgrep.md](references/ripgrep.md) — rg's regex dialect, full flag list, the flags
  that are booby-trapped for grep users.
- [references/grep.md](references/grep.md) — exhaustive grep/egrep/fgrep → rg table and
  BSD-vs-GNU-vs-Mac grep differences.
- [references/ugrep.md](references/ugrep.md) — ugrep → rg, and when ugrep wins.
- [references/ast-grep.md](references/ast-grep.md) — ast-grep (`sg`) pattern and command reference.

## ast-grep (`sg`) essentials

Use `sg` when the thing you're matching is a *syntax shape*, not a text pattern — e.g. "every call
to `foo` regardless of arguments", "every `T{...}` composite literal", "every `if err != nil`
block". Text regex can't reliably match nested/balanced code; ast-grep parses with tree-sitter.

```bash
sg -p 'foo($$$ARGS)' -l go            # any call to foo, any args   ($$$ = zero-or-more nodes)
sg -p 'eventbus.Event{$$$}' -l go     # any Event composite literal (no { } escaping needed)
sg -p 'if err != nil { $$$ }' -l go   # every nil-error guard
sg -p '$A.Close()' -l go              # any .Close() call; $A is a single-node metavariable
sg -p 'old($A)' -r 'new($A)' -l go    # search AND rewrite (prints diff; add -U to apply)
sg run --debug-query=ast -p 'pat' -l go   # see how your pattern parses when it won't match
```

Metavariables: `$NAME` matches one node, `$$$NAME` matches a sequence (zero or more). Same name
twice means the same text must appear in both spots. `-l/--lang` is effectively required for `run`.

`sg` gotchas:

- The binary is `sg`/`ast-grep`. On Linux `sg` may collide with shadow-utils' `setgroups` — use
  `ast-grep` or an alias if `sg` does something surprising.
- ast-grep respects `.gitignore` and skips hidden files, like rg. Use `--no-ignore hidden` to
  include them.
- If a pattern matches nothing, it's usually an invalid parse for the language — run
  `--debug-query=ast` to see what tree-sitter actually built.

Full ast-grep reference: [references/ast-grep.md](references/ast-grep.md).

## When NOT to use rg

- Matching balanced/nested code (function bodies, composite literals, call arguments) → `sg`.
- "Where is `X` defined / how does `Y` work" → `mcp__probe__search_code` (whole AST blocks).
- Renaming a symbol across a codebase by *meaning* rather than text → `sg -p ... -r ...`, not
  `rg ... | sed` (which will also hit comments, strings, and substrings).
