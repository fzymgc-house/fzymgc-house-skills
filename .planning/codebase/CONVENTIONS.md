# Coding Conventions

**Analysis Date:** 2026-07-08

## Naming Patterns

**Files:**

- Python files use `snake_case` (e.g., `_adr_doctor.py`, `worktree_helpers.py`)
- Files with leading underscore indicate internal/private utilities: `_muxdriver.py`, `_adr_render.py`
- Test files follow pattern `test_<module>.py` (e.g., `test_review_gate_agents.py`)
- Markdown files use `UPPERCASE.md` for documentation (e.g., `SKILL.md`, `AGENTS.md`)

**Functions:**

- Functions use `snake_case`: `sanitize_for_output()`, `validate_safe_name()`, `run_cmd()`
- Private functions (internal use only) prefixed with underscore: `_first_non_empty()`, `_cwd_relative_invocations()`
- Test functions use descriptive names: `test_design_reviewer_verdict_regex_match_ready()`

**Variables:**

- Local variables use `snake_case`: `repo_root`, `worktree_path`, `result`
- Private module-level variables prefixed with underscore: `_MARKER`, `_EXEC_PREFIXES`, `_FILENAME_RE`

**Types:**

- Type hints used throughout: `def run_cmd(args: list[str], *, cwd: Path | str) -> subprocess.CompletedProcess`
- Union types use modern syntax: `Path | str` (not `Union[Path, str]`)
- All functions should declare parameter and return type annotations

## Code Style

**Formatting:**

- Tool: `ruff` for Python formatting and linting
- Auto-format via `task fmt` before committing
- All Markdown formatted via `rumdl`

**Linting:**

- Tool: `ruff` (runs `ruff check` and `ruff format`)
- Config: checked in CI via `.github/workflows/ci.yaml` (no local config file — uses ruff defaults)
- Markdown: `rumdl` with config at `/.rumdl.toml`
- Enforced via `task lint` gate

**Line Length:** No explicit line length limit detected; follows ruff defaults (88 chars for code)

**Whitespace & Formatting:**

- 4-space indentation (Python standard)
- Type hints with spaces: `def func(arg: str) -> int`
- Space before function/class definition and between methods
- Trailing whitespace removed by formatters

## Import Organization

**Order:**

1. Future imports: `from __future__ import annotations` (always first)
2. Standard library: `import os`, `import sys`, `from pathlib import Path`
3. Third-party: `import pytest`, `import subprocess`, etc.
4. Local imports: `import _adr_render as R` (module-relative when needed)
5. Type imports (TYPE_CHECKING block if needed)

**Path Aliases:**

- No project-wide path aliases detected (uses relative imports)
- Local module imports: `sys.path.insert(0, str(...)` pattern used in test discovery

**Style:**

- One blank line between import groups
- `from` imports preferred over bare `import` when accessing specific symbols
- Explicit relative imports for sibling modules in scripts: `import _adr_render as R`

## Error Handling

**Patterns:**

**1. Raise with descriptive messages:**

```python
if not name:
    raise ValueError(f"{label} must not be empty")

if invalid:
    raise ValueError(
        f"invalid {safe_label} '{safe_name}' "
        "(alphanumeric, dots, hyphens, underscores only; ...)"
    )
```

**2. Never-fail functions return False and warn to stderr:**

```python
def fetch_origin(repo_root: Path | str, *, is_jj: bool, run=run_cmd) -> bool:
    """Best-effort refresh... Never fails the caller: returns False and warns to stderr."""
    result = run(cmd, cwd=repo_root)
    if result.returncode != 0:
        print(f"WARNING: {label} failed...", file=sys.stderr)
        return False
    return True
```

**3. Subprocess handling never raises:**

```python
def run_cmd(args: list[str], *, cwd: Path | str) -> subprocess.CompletedProcess:
    """Run command. Never raises: returns CompletedProcess with returncode=127 on OSError."""
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=args, returncode=127, stdout="", stderr=f"{type(exc).__name__}: {exc}"
        )
```

**4. Test assertions with context:**

```python
assert not violations, (
    f"{path.relative_to(REPO_ROOT)} invokes a dev-flow script via a "
    "cwd-relative path. Use ${CLAUDE_PLUGIN_ROOT}/scripts/... "
    "Offending lines:\n  " + "\n  ".join(violations)
)
```

**Stderr for warnings:** Non-fatal issues printed to `stderr` with "WARNING:" prefix, fatal errors raised as exceptions.

## Logging

**Framework:** `print()` to stdout/stderr (not a structured logging library)

**Patterns:**

- Warnings to stderr: `print(f"WARNING: ...", file=sys.stderr)`
- Transient issues logged with context: `print(f"INFO: {message}", file=sys.stderr)`
- Control characters sanitized via `sanitize_for_output()` before logging user-provided paths/text

**When to Log:**

- Before operations that may fail (subprocess calls, file I/O)
- After operations succeed (confirmation messages)
- Warnings for edge cases (missing files, empty output)
- Never log secrets or sensitive data (API keys, tokens, passwords)

## Comments

**When to Comment:**

- Document "why," not "what" — code should be self-documenting
- Invariants and contracts: `# Preserve \\t (0x09), \\n (0x0A), \\r (0x0D)`
- Non-obvious decisions: `# cmux requires full surface:<N> ref; bare <N> is rejected`
- Workarounds for known bugs: `# cmux 0.64.15 prints multi-token status banner`
- Verbose regex/parsing logic benefits from inline comments

**Avoid:**

- Comments restating code: don't comment `x = x + 1  # increment x`
- Obvious logic: clear code names are better than comments

## Docstrings

**Module Docstring:** Always present at file top, lists public functions/classes

Example from `worktree_helpers.py`:

```python
"""Shared helpers for the worktree-create and worktree-remove hooks.

Functions:
    sanitize_for_output(s)          — strip control chars for safe logging
    validate_safe_name(name, label) — reject path traversal/metacharacters
    run_cmd(args, *, cwd)           — thin subprocess wrapper, never raises
"""
```

**Function Docstring:** Single-line summary, then detailed description with parameter/return info

```python
def validate_safe_name(name: str, label: str) -> None:
    """Validate that *name* is safe for use as a filesystem component.

    Raises ValueError for:
    - Empty names
    - Characters outside [a-zA-Z0-9_.-]
    - Leading dot, trailing dot, or double-dot anywhere in the name
    """
```

**Return value contract:** Document what exceptions are raised, what values returned

```python
def run_cmd(args: list[str], *, cwd: Path | str) -> subprocess.CompletedProcess:
    """Run *args* as a subprocess in *cwd*.

    Returns a CompletedProcess. Never raises: returns a synthetic
    result with returncode=127 and descriptive stderr on OSError
    (executable not found, permission denied, etc.).
    """
```

## Function Design

**Size:** Prefer small functions (most functions fit on one screen)

**Parameters:**

- Positional args for required parameters
- Keyword-only args (after `*`) for optional parameters
- Type hints on all parameters
- Document complex parameters in docstring

Example:

```python
def fetch_origin(repo_root: Path | str, *, is_jj: bool, run=run_cmd) -> bool:
    """... repo_root: working directory. is_jj: use jj or git. run: optional mock."""
```

**Return Values:**

- Explicitly declare return type annotation
- Document in docstring what return value means
- Return early to avoid nesting: prefer `if not condition: return`

Example:

```python
def _decision_id(text: str) -> str | None:
    """The bd-id declared by a file's '**Decision:** <bd-id>' line, or None."""
    m = _DECISION_RE.search(text)
    return m.group(1) if m else None
```

## Module Design

**Exports:**

- Public API functions have no leading underscore
- Private implementation functions start with `_`
- Module docstring lists public API at top

**Barrel Files:** Not used (direct imports from specific modules)

**Initialization:** Files with `from __future__ import annotations` at line 1

## Patterns

**Path handling:** Use `pathlib.Path` throughout (not string paths)

```python
from pathlib import Path

repo_root: Path = Path(repo_root).resolve()
worktree_path: Path = Path(worktree_path)
```

**List comprehensions:** Used for filtering and mapping where readable

```python
words = [w for w in spaced.split() if w not in _STOP_WORDS]
bad = [line.strip() for line in text.splitlines() if condition]
```

**Type annotations:** Always use on functions; optional on simple locals

```python
def _frontmatter_block(text: str) -> str | None:  # Always use
result: dict = load_fixture("search_providers")  # Optional but good
x = 5  # OK to omit for obvious types
```

**Regex compilation:** Compile at module level with leading underscore for private patterns

```python
_FILENAME_RE = re.compile(rf"^{BD_ID_RE}-[a-z0-9-]+\.md$")
_DECISION_RE = re.compile(rf"^\*\*Decision:\*\*\s+({BD_ID_RE})", re.M)
```

---

*Convention analysis: 2026-07-08*
