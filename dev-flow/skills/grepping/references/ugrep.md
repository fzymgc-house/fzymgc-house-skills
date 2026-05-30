# ugrep → rg

ugrep is a fast, grep-*compatible* drop-in (it accepts grep's flags) with extras. Companion to the
`grepping` skill; for rg's own flags see `ripgrep.md`, for the grep dialects see `grep.md`.

Because ugrep is grep-compatible, its **defaults are grep-like** — which differ from rg:

| Behavior | ugrep | rg |
|----------|-------|-----|
| Recursive | opt-in: `-r` / `-R` (`-R` follows symlinks) | default |
| Respect `.gitignore` | opt-in: `--ignore-files` | default |
| Hidden files | searched unless excluded | skipped unless `--hidden` |
| PCRE | `-P` | `-P` |
| Fixed string | `-F` | `-F` |
| Boolean query | `--bool` / `-%` (`AND`/`OR`/`NOT`) | a single regex with `|`, or multiple `-e` |
| Fuzzy match | `-Z` (edit distance) | (none — rg is exact) |
| Interactive TUI | `ug --query` | (none) |
| Search archives/compressed | `-z` (tar, zip, gz, …) | `-z` = gz/bz2/xz of plain files only |

## Translations

| ugrep / grep | rg |
|--------------|-----|
| `ugrep -rn --ignore-files 'pat'` | `rg -n 'pat'` |
| `ugrep -Rn 'pat' .` | `rg -n -L 'pat'` (follow symlinks) |
| `ugrep -rn -tgo 'pat'` (ugrep also has `-t`) | `rg -n -t go 'pat'` |
| `ug --query 'pat'` | (no rg equivalent; use `rg` piped to `fzf`) |

## When ugrep wins over rg

Reach for ugrep specifically for: fuzzy matching (`-Z`), boolean AND/OR/NOT queries (`--bool`),
searching inside archives/compressed files, or the interactive `ug --query` TUI. For everything
else, `rg` is the default and the one the tool-precedence rules in AGENTS.md assume.
