# Testing Patterns

**Analysis Date:** 2026-07-08

## Test Framework

**Runner:**

- `pytest` for all Python test suites
- Config: `.github/workflows/ci.yaml` / `Taskfile.yaml` (no local pytest.ini or pyproject.toml)
- Import mode: `importlib` (flag: `--import-mode=importlib`)

**Assertion Library:**

- Python `assert` statements (built-in)
- `pytest` fixtures and parametrization

**Run Commands:**

```bash
task test                                # Run all harness-independent tests
uv run --with pytest --with httpx --with pyyaml pytest tests/ -q --import-mode=importlib
pytest path/to/tests/ -q                 # Run specific test directory
pytest path/to/tests/test_file.py::test_function -v  # Run single test with verbose output
```

**Coverage:**

- Not enforced via CI/local gates (no coverage target detected)
- Can run: `pytest --cov=<module>` if needed

## Test File Organization

**Location:**

- Primary: `tests/` (root-level test directory)
- Plugin-specific: `<plugin>/hooks/tests/` (e.g., `.claude/hooks/tests/`)
- Embedded: `<module>/tests/` (e.g., `homelab/skills/terraform/tests/`)

**Naming:**

- Test files: `test_<name>.py`
- Test classes (optional): `Test<Name>` (Pascal case)
- Test functions: `test_<description>` (lowercase snake_case)

**Structure:**

```text
tests/
├── test_review_gate_agents.py
├── test_plugin_script_paths.py
├── test_adr_docs.py
├── test_muxdriver.py
└── fixtures/
    ├── search_providers.json
    └── capture_fixtures.py

homelab/skills/terraform/tests/
├── test_terraform_mcp.py
├── fixtures/
│   └── search_providers.json
└── capture_fixtures.py

.claude/hooks/tests/
├── conftest.py
├── test_post_edit_format.py
└── test_warn_default_workspace.py
```

## Test Structure

**Suite Organization:**

```python
"""Tests for [module] — [purpose]."""

from __future__ import annotations

from pathlib import Path
import pytest

# Imports first (stdlib, then third-party, then local)
REPO_ROOT = Path(__file__).resolve().parents[1]

class TestModuleName:
    """Group of related tests — optional."""

    def test_specific_behavior(self) -> None:
        """Single test function with descriptive name."""
        # Arrange
        fixture = load_fixture("name")
        
        # Act
        result = parse_something(fixture)
        
        # Assert
        assert result == expected
```

**Patterns:**

**1. Module-level constants:**

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_REVIEWER = REPO_ROOT / "dev-flow" / "agents" / "design-reviewer.md"
_VERDICT_RE = r"^VERDICT: (READY|NOT READY)$"
```

**2. Test grouping with classes:**

```python
class TestParseProviderSearchMarkdown:
    """Tests for parse_provider_search_markdown function."""

    def test_parse_real_search_providers_response(self):
        """Test parsing real markdown from MCP response."""
        fixture = load_fixture("search_providers")
        entries = parse_provider_search_markdown(text)
        assert len(entries) >= 5

    def test_parse_with_target_slug_exact_match(self):
        """Test that target_slug prioritizes exact matches."""
        # ...
```

**3. Parametrized tests:**

```python
@pytest.mark.parametrize(
    "path", _md_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_cwd_relative_dev_flow_script_invocations(path: Path) -> None:
    """Test applied to each item in _md_files()."""
    violations = _cwd_relative_invocations(path.read_text())
    assert not violations
```

**4. Skipped/conditional tests:**

```python
RUFF_AVAILABLE = shutil.which("ruff") is not None

@pytest.mark.skipif(not RUFF_AVAILABLE, reason="ruff is not installed")
def test_python_file_formatted_by_ruff(tmp_path: Path) -> None:
    """Only runs if ruff is available."""
    # ...
```

## Mocking

**Framework:** `monkeypatch` (pytest built-in fixture)

**Patterns:**

**1. Environment variables:**

```python
def test_detect_precedence(monkeypatch) -> None:
    # Set env var
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1,0")
    assert mod.detect("auto").name == "tmux"
    
    # Unset env var
    monkeypatch.delenv("TMUX", raising=False)
    assert mod.detect("auto").name == "cmux"
```

**2. Function/method mocking:**

```python
def test_detect_precedence(monkeypatch) -> None:
    # Replace a function
    monkeypatch.setattr(
        mod.shutil, "which", lambda c: "/usr/bin/cmux" if c == "cmux" else None
    )
    assert mod.detect("auto").name == "cmux"
```

**3. Dependency injection (preferred over monkey-patching):**

```python
def fetch_origin(repo_root: Path | str, *, is_jj: bool, run=run_cmd) -> bool:
    """Accept run as a parameter for testing."""
    result = run(cmd, cwd=repo_root)
    # ...

# In test
def test_fetch_origin_success() -> None:
    def mock_run(args, *, cwd):
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")
    
    result = fetch_origin(repo_root, is_jj=False, run=mock_run)
    assert result is True
```

**What to Mock:**

- External commands (subprocess calls)
- Environment variables
- File system calls (use `tmp_path` fixture instead)
- Imports that are hard to set up

**What NOT to Mock:**

- Pure functions (test them directly)
- Standard library (use as-is)
- File I/O (use `tmp_path` pytest fixture for isolation)

## Fixtures and Factories

**Test Data:**

```python
# From homelab/skills/terraform/tests/test_terraform_mcp.py

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / f"{name}.json") as f:
        return json.load(f)

# Usage
def test_parse_real_search_providers_response(self):
    fixture = load_fixture("search_providers")
    text = fixture["result"]["content"][0]["text"]
    entries = parse_provider_search_markdown(text)
```

**Location:**

- Fixture files: `<test_dir>/fixtures/` (JSON, YAML, or other data files)
- Fixture functions: In same test file or `conftest.py` for shared fixtures

**Patterns:**

- Factories return realistic test data (e.g., complete JSON responses)
- Fixtures are committed to repo (not generated at test time)
- Large fixtures stored as separate files (not inline in test code)

**Built-in pytest fixtures used:**

- `tmp_path` (Path): Temporary directory unique to test
- `monkeypatch`: Monkey-patch environment/functions

## Common Patterns

**1. Subprocess testing:**

```python
def run_hook(data: dict | None = None, raw: str | None = None) -> subprocess.CompletedProcess:
    """Run the hook as a subprocess with the given JSON input."""
    if raw is not None:
        stdin_input = raw
    elif data is not None:
        stdin_input = json.dumps(data)
    else:
        stdin_input = ""
    
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin_input,
        capture_output=True,
        text=True,
    )

def test_python_file_runs_ruff(tmp_path: Path) -> None:
    py_file = tmp_path / "example.py"
    py_file.write_text("x=1\n")
    
    data = {"tool_input": {"file_path": str(py_file)}}
    result = run_hook(data)
    
    assert result.returncode == 0
```

**2. File I/O testing:**

```python
def test_python_file_formatted_by_ruff(tmp_path: Path) -> None:
    """Use tmp_path to test file modifications."""
    py_file = tmp_path / "example.py"
    py_file.write_text("x=1\n")  # Unformatted
    
    run_hook({"tool_input": {"file_path": str(py_file)}})
    
    content = py_file.read_text()
    assert "x = 1" in content  # Formatted by ruff
```

**3. Regex pattern testing:**

```python
VERDICT_RE = r"^VERDICT: (READY|NOT READY)$"

def test_verdict_regex_rejects_malformed() -> None:
    assert not re.match(VERDICT_RE, "VERDICT READY")  # Missing colon
    assert not re.match(VERDICT_RE, "verdict: ready")  # Lowercase
    assert not re.match(VERDICT_RE, "## VERDICT: READY")  # Extra prefix
```

**4. Exception testing:**

```python
import pytest

def test_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_safe_name("", "label")

def test_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="not inside a git/jj repository"):
        detect_repo_root(cwd="/tmp")
```

**5. Async testing (not used in this codebase):** Not detected.

**6. Error testing - contract verification:**

```python
def test_design_reviewer_declares_verdict_contract() -> None:
    """Verify the agent file declares the regex contract."""
    text = DESIGN_REVIEWER.read_text()
    assert "VERDICT: READY" in text
    assert "VERDICT: NOT READY" in text
    assert "^VERDICT: (READY|NOT READY)$" in text  # The regex itself
```

## Test Organization by Type

**Unit Tests:**

- Scope: Single function or method
- Location: `tests/test_<module>.py` or `<module>/tests/test_<module>.py`
- Approach: Fast, isolated, no I/O or subprocess (or mocked)
- Examples: `test_review_gate_agents.py`, `test_muxdriver.py`

**Integration Tests:**

- Scope: Multiple components working together
- Location: Same `tests/` directories, named `test_<integration>.py`
- Approach: Use real fixtures (JSON files), subprocess calls, file I/O
- Examples: `homelab/skills/terraform/tests/test_terraform_mcp.py` (calls parse functions with real API response fixtures)

**Contract Tests:**

- Scope: Verify interface/output format contracts
- Location: `tests/test_review_gate_agents.py`
- Approach: Regex matching, file existence, schema validation
- Example: `test_design_reviewer_declares_verdict_contract()` verifies the agent output format

**E2E Tests:**

- Not used: Behavioral evals (`dev-flow/evals`, `jj/evals`) require Claude harness; not run in `task test`
- These are schema-validated but not executed: `uv run check-jsonschema --schemafile dev-flow/evals/evals.schema.json dev-flow/evals/evals.json`

## Coverage

**Requirements:** Not enforced (no coverage target or gate detected)

**View Coverage:** Can run manually:

```bash
pytest --cov=<module> --cov-report=term-missing tests/
```

**Note:** CI (`Taskfile.yaml` `task test`) does not enforce coverage. Coverage gaps noted but not gated.

## Dependencies

**Test runtime:** Installed via `uv run --with pytest --with httpx --with pyyaml pytest ...` (from `Taskfile.yaml`)

**Installed dependencies:**

- `pytest` — test runner
- `httpx` — HTTP client (used in fixture loading for MCP tests)
- `pyyaml` — YAML parsing

**No test-specific lock file detected:** Uses `uv` to manage test dependencies dynamically.

---

*Testing analysis: 2026-07-08*
