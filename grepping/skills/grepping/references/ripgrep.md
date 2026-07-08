# ripgrep (rg) reference

`rg` is the default text-search tool in this skill — every other tool here maps onto it. Companion
to the `grepping` skill; see `grep.md` / `ugrep.md` / `ast-grep.md` for translating from those tools.

## Regex dialect

- rg uses the Rust `regex` crate — **ERE-like**: `|` `+` `?` `*` `{}` `()` are operators, no
  backslash needed. (This is why a grep-habit `\|` *breaks* in rg: there it means a literal pipe.)
- **No** backreferences or lookaround by default. Add `-P` / `--pcre2` for backrefs, lookaround,
  and `\K`.
- `{` and `(` are metacharacters. To match them literally, use `-F` (fixed string) or escape
  (`\{`, `\(`). An unescaped `{` often yields `regex parse error: repetition quantifier...`.
- `\d` `\w` `\s` work (unlike BSD grep's ERE).

## Defaults

Recursive · respects `.gitignore`/`.ignore` · skips hidden files and binaries · **multiline OFF** ·
no pager (don't pass `--no-pager` — that's a git/jj flag).

| Want | Flag |
|------|------|
| Include dotfiles | `--hidden` |
| Include `.gitignore`d files | `--no-ignore` |
| Escalate both (+ binaries) | `-u` (= `--no-ignore`) · `-uu` (+`--hidden`) · `-uuu` (+binary) |
| Multiline | `-U` / `--multiline`; `--multiline-dotall` lets `.` span newlines |

## Flag reference

| Purpose | rg |
|---------|-----|
| Case-insensitive / smart / force-sensitive | `-i` / `-S` / `-s` |
| Line numbers | `-n` (default on a tty) |
| Count matches | `-c` |
| Invert match | `-v` |
| Whole word / whole line | `-w` / `-x` |
| Only the matched part | `-o` |
| Files with / without matches | `-l` / `--files-without-match` |
| After / before / around | `-A N` / `-B N` / `-C N` |
| Suppress filename | `-I` (note: `-h` is help, not no-filename) |
| Quiet (exit status only) | `-q` |
| Fixed string (no regex) | `-F` |
| PCRE2 (backrefs, lookaround, `\K`) | `-P` / `--pcre2` |
| Glob include / exclude | `-g GLOB` / `-g '!GLOB'` |
| By file type | `-t go` / `-T go` (negate) · `--type-list` · `--type-add 'name:*.ext'` |
| Replace in output | `-r 'REPL'` — captures are `$1`, **not** `\1` |
| Max matches | `-m N` |
| NUL-separated output (for `xargs -0`) | `-0` / `--null` |
| NUL-separated **input** | `--null-data` (note: `-z` is `--search-zip`) |

## Flags booby-trapped for grep users

| You probably mean | rg reality |
|-------------------|-----------|
| `-r` = recursive | `-r` = `--replace` (consumes the next token as the replacement string) |
| `-R` = recursive | `-R` is not a flag → `unrecognized flag -R` (recursion is default; `-L` follows symlinks) |
| `-E` = extended regex | `-E` = `--encoding` (consumes the next token as an encoding name) |
| `-z` = NUL-separated input | `-z` = `--search-zip`; for NUL input use `--null-data` |
| `--include=` / `--exclude=` | not flags → use `-g GLOB` / `-g '!GLOB'` |
| `--no-pager` | not a flag (that's git/jj); rg has no pager |

Recursion is the default, so the single most common mistake is a reflexive `-r`/`-R`/`-rn`. Drop it.

## File types

`rg --type-list` shows built-ins. Add one inline for an unknown extension:
`rg --type-add 'proto:*.proto' -t proto 'pat'` (or just `rg -g '*.proto' 'pat'`).
