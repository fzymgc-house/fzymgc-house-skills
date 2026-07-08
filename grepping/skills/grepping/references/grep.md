# grep / egrep / fgrep → rg

Covers GNU grep, BSD grep (macOS `/usr/bin/grep`), and the `egrep` / `fgrep` aliases. Companion to
the `grepping` skill; for rg's own flags and gotchas see `ripgrep.md`.

## Regex dialect is the root of most surprises

| Tool | Default dialect | Notes |
|------|-----------------|-------|
| `grep` (BRE) | Basic regex | `+ ? { } ( ) |` are **literal** unless escaped (`\+`, `\|`, `\{`) |
| `egrep` / `grep -E` (ERE) | Extended regex | `+ ? { } ( ) |` are operators; no backslash needed |
| `fgrep` / `grep -F` | Fixed strings | No regex at all |
| `rg` | Rust `regex` (ERE-like) | Like ERE: `|` `+` `?` `{}` `()` are operators. **No** backrefs/lookaround without `-P` |
| `rg -P` | PCRE2 | Backreferences, lookaround, `\K` |
| `ugrep` | ERE by default | grep-compatible; `-P` = PCRE2; `-F`/`-G`/`-E` switch dialects like grep |

**The #1 silent bug:** carrying BRE `\|` into rg. In rg, `\|` is a *literal pipe* — the alternation
never fires and the search returns nothing. Use a bare `|`. The mirror image: leaving `(`/`)`/`{`
unescaped in rg when you mean them literally — rg treats them as operators and either parse-errors
(`{`, unbalanced `()`) or matches the wrong thing. Use `-F` or escape with `\`.

## Full flag translation

| Intent | grep (GNU) | rg |
|--------|-----------|-----|
| Recursive | `-r` / `-R` (`-R` follows symlinks) | default (in rg, `-r`/`-R` mean other things — see `ripgrep.md`) |
| Recurse + follow symlinks | `-R` | `rg -L` |
| Extended regex | `-E` / `egrep` | default (rg's `-E` is `--encoding`!) |
| Fixed string | `-F` / `fgrep` | `-F` |
| PCRE | `-P` | `-P` / `--pcre2` |
| Case-insensitive | `-i` | `-i` (or `-S` smart-case) |
| Line numbers | `-n` | `-n` (default on a tty) |
| Count matches | `-c` | `-c` |
| Invert match | `-v` | `-v` |
| Whole word / line | `-w` / `-x` | `-w` / `-x` |
| Only matching part | `-o` | `-o` |
| Files **with** matches | `-l` | `-l` |
| Files **without** matches | `-L` | `--files-without-match` |
| After / before / around | `-A`/`-B`/`-C` | `-A`/`-B`/`-C` (same) |
| Suppress filename | `-h` | `-I` (in rg, `-h` is help) |
| Quiet (exit status only) | `-q` | `-q` |
| Include glob | `--include=GLOB` | `-g GLOB` |
| Exclude glob / dir | `--exclude=GLOB` / `--exclude-dir=D` | `-g '!GLOB'` / `-g '!D/'` |
| By file type | (none) | `-t go` / `-T go` (negate); `--type-list`, `--type-add` |
| Search hidden files | (searches all) | `--hidden` |
| Search ignored files | (searches all) | `--no-ignore` (or `-uu`) |
| NUL-separated output | `-Z` / `--null` | `-0` / `--null` |
| NUL-separated input | `-z` | `--null-data` (rg's `-z` is `--search-zip`) |
| Max matches | `-m N` | `-m N` |
| Replace in output | `-o` + `sed` | `-r 'REPL'` (captures `$1`, not `\1`) |
| Multiline | `-z` (GNU hack) | `-U` / `--multiline`; `--multiline-dotall` |

## BSD grep (macOS) vs GNU grep

macOS ships BSD grep as `/usr/bin/grep`. Differences that bite when copying Linux commands:

| Feature | GNU grep | BSD grep (macOS) |
|---------|----------|------------------|
| `-P` PCRE | supported | **not supported** (`grep: invalid option -- P`) |
| `--include` / `--exclude` | long form works | works; `--exclude-dir` differs in older versions |
| `\d` `\w` `\s` in `-E` | works (GNU ext) | **not** in BSD ERE — use `[0-9]`, `[[:digit:]]`, etc. |
| `-o` only-matching | supported | supported (modern) |
| Color | `--color=auto` | `--color=auto` (modern) / older needs `--color` |
| `-z` NUL data | supported | supported (modern) |

If a script must run on both, either install GNU grep (`brew install grep`, exposed as `ggrep`) or
**just use `rg`** — identical across platforms, no BSD/GNU split.

Note: on this machine `grep` is aliased to **ugrep**, so `grep --version` reports ugrep. The BSD
caveats above apply to the stock `/usr/bin/grep`, not the alias. See `ugrep.md`.
