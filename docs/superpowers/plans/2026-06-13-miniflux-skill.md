# Miniflux Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `homelab/skills/miniflux` skill that lets Claude manage and curate Miniflux RSS feeds (feed management, reading/triage, AI curation, health/maintenance) through a `uv`-run Python CLI wrapping the official `miniflux` Python client.

**Architecture:** A single gateway script (`miniflux_api.py`) exposes raw passthrough commands and compound workflows (`digest`, `triage`, `health-audit`, `suggest-rules`). Command handlers are pure `cmd_*(client, args) -> data` functions tested with a mocked `miniflux.Client`; `main()` resolves config, builds the client, dispatches, and prints `format_output`. Curation follows a rules + reasoning split: deterministic blocklist/keeplist regex live in Miniflux (applied by the script), relevance ranking and digest prose are Claude's job. This mirrors the existing `grafana`/`terraform` skills **structurally** (PEP 723 shebang, `--format yaml|json`, `references/`) but wraps the client directly with no MCP intermediary.

**Tech Stack:** Python ≥3.11, `uv` (PEP 723 inline deps), `miniflux` pip client, `pyyaml`, `pytest`. Spec: `docs/superpowers/specs/2026-06-13-miniflux-skill-design.md`. Design bead: `fhsk-8k8`.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `homelab/skills/miniflux/scripts/miniflux_api.py` | Gateway CLI: config, client factory, formatting, error handling, all `cmd_*` handlers, argparse + `main()` |
| `homelab/skills/miniflux/tests/test_miniflux_api.py` | pytest suite: config resolution, formatting, every handler (mocked client), error paths |
| `homelab/skills/miniflux/SKILL.md` | Skill frontmatter + workflow guidance + rules-vs-reasoning instructions |
| `homelab/skills/miniflux/references/feeds.md` | Feed + category CRUD, OPML, discover |
| `homelab/skills/miniflux/references/entries.md` | Entry filtering, reading, triage, bulk ops |
| `homelab/skills/miniflux/references/curation.md` | blocklist/keeplist/scraper/rewrite rules + suggest-rules flow |
| `homelab/skills/miniflux/references/digest.md` | Digest workflow + ranking guidance |
| `homelab/skills/miniflux/references/health.md` | Health audit (errored/disabled/stale feeds) |
| `Taskfile.yaml` (modify) | Add miniflux test dir to `PYTEST_DIRS`; add `--with miniflux` to `test` |

All handlers return JSON-serializable data; `main()` is the only place that prints. The `miniflux` client is imported once at module top (for `Client` + exception classes); handler tests inject a `MagicMock` client, so they need no live instance.

---

## Task 1: Script skeleton — config resolution & output formatting

**Files:**

- Create: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Create: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Create `homelab/skills/miniflux/tests/test_miniflux_api.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "pyyaml", "miniflux"]
# ///
"""Tests for miniflux_api.py (handlers tested with a mocked client)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import miniflux_api as mfa


class TestResolveConfig:
    def test_env_takes_precedence(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MINIFLUX_URL", "https://env.example.org")
        monkeypatch.setenv("MINIFLUX_API_KEY", "env-key")
        cfg = mfa.resolve_config(config_path=tmp_path / "nope.yaml")
        assert cfg == {"url": "https://env.example.org", "api_key": "env-key"}

    def test_file_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MINIFLUX_URL", raising=False)
        monkeypatch.delenv("MINIFLUX_API_KEY", raising=False)
        path = tmp_path / "config.yaml"
        path.write_text("url: https://file.example.org\napi_key: file-key\n")
        cfg = mfa.resolve_config(config_path=path)
        assert cfg == {"url": "https://file.example.org", "api_key": "file-key"}

    def test_missing_config_raises(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MINIFLUX_URL", raising=False)
        monkeypatch.delenv("MINIFLUX_API_KEY", raising=False)
        with pytest.raises(mfa.ConfigError) as exc:
            mfa.resolve_config(config_path=tmp_path / "missing.yaml")
        assert "MINIFLUX_URL" in str(exc.value)


class TestFormatOutput:
    def test_yaml_default(self):
        out = mfa.format_output({"a": 1}, "yaml")
        assert yaml.safe_load(out) == {"a": 1}

    def test_json(self):
        out = mfa.format_output({"a": 1}, "json")
        assert json.loads(out) == {"a": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'miniflux_api'`

- [ ] **Step 3: Write the minimal script skeleton**

Create `homelab/skills/miniflux/scripts/miniflux_api.py`:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["miniflux", "pyyaml"]
# ///
"""Miniflux gateway script.

Wraps the official `miniflux` Python client to manage and curate RSS feeds.
Config resolves from MINIFLUX_URL / MINIFLUX_API_KEY env vars, falling back to
~/.config/miniflux/config.yaml (keys: url, api_key).

Run with --help for the command list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when Miniflux connection config cannot be resolved."""


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "miniflux" / "config.yaml"


def resolve_config(config_path: Path | None = None) -> dict[str, str]:
    """Resolve {url, api_key} from env, then a YAML config file."""
    url = os.environ.get("MINIFLUX_URL")
    api_key = os.environ.get("MINIFLUX_API_KEY")
    if url and api_key:
        return {"url": url, "api_key": api_key}

    path = config_path or default_config_path()
    file_cfg: dict[str, Any] = {}
    if path.exists():
        file_cfg = yaml.safe_load(path.read_text()) or {}

    url = url or file_cfg.get("url")
    api_key = api_key or file_cfg.get("api_key")
    if not url or not api_key:
        raise ConfigError(
            "Miniflux config missing. Set MINIFLUX_URL and MINIFLUX_API_KEY, "
            f"or create {path} with `url:` and `api_key:` keys."
        )
    return {"url": url, "api_key": api_key}


def format_output(data: Any, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

Commit per `references/vcs-preamble.md`:
`docs`? No — code. Use: `feat(miniflux): add gateway script skeleton with config + formatting (fhsk-8k8)`

---

## Task 2: Client factory & error-translating dispatch

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestRunCommand:
    def test_success_prints_formatted(self, capsys):
        rc = mfa.run_command(lambda: {"ok": True}, "json")
        out = capsys.readouterr().out
        assert rc == 0
        assert json.loads(out) == {"ok": True}

    def test_unauthorized_maps_to_api_key_hint(self, capsys):
        import miniflux

        def boom():
            raise miniflux.AccessUnauthorized("unauthorized")

        rc = mfa.run_command(boom, "yaml")
        err = capsys.readouterr().err
        assert rc == 1
        assert "MINIFLUX_API_KEY" in err

    def test_client_error_surfaces_message(self, capsys):
        import miniflux

        def boom():
            raise miniflux.ResourceNotFound("feed not found")

        rc = mfa.run_command(boom, "yaml")
        err = capsys.readouterr().err
        assert rc == 1
        assert "feed not found" in err

    def test_connection_error_maps_to_url_hint(self, capsys):
        def boom():
            raise ConnectionError("refused")

        rc = mfa.run_command(boom, "yaml")
        err = capsys.readouterr().err
        assert rc == 1
        assert "MINIFLUX_URL" in err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestRunCommand -v`
Expected: FAIL — `AttributeError: module 'miniflux_api' has no attribute 'run_command'`

- [ ] **Step 3: Implement client factory + run_command**

Add imports near the top of `miniflux_api.py` (below `import yaml`):

```python
import sys

import miniflux
from miniflux import AccessUnauthorized, ClientError
```

Add after `format_output`:

```python
def make_client(config: dict[str, str]) -> "miniflux.Client":
    return miniflux.Client(config["url"], api_key=config["api_key"])


def run_command(call, fmt: str) -> int:
    """Execute a no-arg callable, format its result, translate errors."""
    try:
        result = call()
    except AccessUnauthorized:
        print(
            "Authentication failed (401). Check MINIFLUX_API_KEY / config api_key.",
            file=sys.stderr,
        )
        return 1
    except ClientError as e:
        status = getattr(e, "status_code", "?")
        print(f"Miniflux API error (HTTP {status}): {e}", file=sys.stderr)
        return 1
    except (ConnectionError, OSError) as e:
        print(
            f"Cannot reach Miniflux: {e}. Check MINIFLUX_URL / config url.",
            file=sys.stderr,
        )
        return 1
    print(format_output(result, fmt))
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestRunCommand -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add client factory and error-translating dispatch (fhsk-8k8)`

---

## Task 3: Feed & category raw commands

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestFeedCommands:
    def test_list_feeds_projects_fields(self):
        client = MagicMock()
        client.get_feeds.return_value = [
            {
                "id": 42,
                "title": "Example",
                "feed_url": "https://ex.org/feed",
                "category": {"id": 7, "title": "Tech"},
                "parsing_error_count": 0,
                "disabled": False,
            }
        ]
        out = mfa.cmd_list_feeds(client, _ns())
        assert out == [
            {
                "id": 42,
                "title": "Example",
                "feed_url": "https://ex.org/feed",
                "category": "Tech",
                "parsing_error_count": 0,
                "disabled": False,
            }
        ]

    def test_list_categories(self):
        client = MagicMock()
        client.get_categories.return_value = [{"id": 7, "title": "Tech"}]
        out = mfa.cmd_list_categories(client, _ns())
        assert out == [{"id": 7, "title": "Tech"}]

    def test_create_feed_returns_id(self):
        client = MagicMock()
        client.create_feed.return_value = 99
        out = mfa.cmd_create_feed(client, _ns(url="https://x/feed", category=7, crawler=True))
        client.create_feed.assert_called_once_with(
            "https://x/feed", category_id=7, crawler=True
        )
        assert out == {"created_feed_id": 99}

    def test_delete_feed(self):
        client = MagicMock()
        out = mfa.cmd_delete_feed(client, _ns(feed_id=42))
        client.delete_feed.assert_called_once_with(42)
        assert out == {"deleted_feed_id": 42}
```

Add this helper near the top of the test file (after imports):

```python
def _ns(**kwargs):
    """Build a throwaway args namespace for handler tests."""
    from argparse import Namespace

    return Namespace(**kwargs)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestFeedCommands -v`
Expected: FAIL — `AttributeError: ... has no attribute 'cmd_list_feeds'`

- [ ] **Step 3: Implement the feed/category handlers**

Add to `miniflux_api.py`:

```python
def _feed_category_name(feed: dict[str, Any]) -> str | None:
    cat = feed.get("category")
    return cat.get("title") if isinstance(cat, dict) else None


def cmd_list_feeds(client, args) -> list[dict[str, Any]]:
    return [
        {
            "id": f["id"],
            "title": f.get("title"),
            "feed_url": f.get("feed_url"),
            "category": _feed_category_name(f),
            "parsing_error_count": f.get("parsing_error_count", 0),
            "disabled": f.get("disabled", False),
        }
        for f in client.get_feeds()
    ]


def cmd_list_categories(client, args) -> list[dict[str, Any]]:
    return [{"id": c["id"], "title": c.get("title")} for c in client.get_categories()]


def cmd_create_feed(client, args) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if args.category is not None:
        kwargs["category_id"] = args.category
    if getattr(args, "crawler", False):
        kwargs["crawler"] = True
    feed_id = client.create_feed(args.url, **kwargs)
    return {"created_feed_id": feed_id}


def cmd_delete_feed(client, args) -> dict[str, Any]:
    client.delete_feed(args.feed_id)
    return {"deleted_feed_id": args.feed_id}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestFeedCommands -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add feed and category raw commands (fhsk-8k8)`

---

## Task 4: Entry raw commands (get-entries, mark-read, toggle-star)

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestEntryCommands:
    def test_get_entries_passes_filters_and_projects(self):
        client = MagicMock()
        client.get_entries.return_value = {
            "total": 1,
            "entries": [
                {
                    "id": 5,
                    "title": "Hello",
                    "url": "https://ex.org/a",
                    "status": "unread",
                    "starred": False,
                    "published_at": "2026-06-13T00:00:00Z",
                    "feed": {"title": "Example", "category": {"title": "Tech"}},
                }
            ],
        }
        out = mfa.cmd_get_entries(
            client,
            _ns(status="unread", starred=None, search=None, category=None,
                feed=None, after=None, limit=20, order="published_at",
                direction="desc"),
        )
        client.get_entries.assert_called_once_with(
            status="unread", limit=20, order="published_at", direction="desc"
        )
        assert out["total"] == 1
        assert out["entries"][0] == {
            "id": 5,
            "title": "Hello",
            "url": "https://ex.org/a",
            "status": "unread",
            "starred": False,
            "published_at": "2026-06-13T00:00:00Z",
            "feed": "Example",
            "category": "Tech",
        }

    def test_mark_read(self):
        client = MagicMock()
        out = mfa.cmd_mark_read(client, _ns(ids=[1, 2, 3]))
        client.update_entries.assert_called_once_with([1, 2, 3], "read")
        assert out == {"marked_read": [1, 2, 3]}

    def test_toggle_star(self):
        client = MagicMock()
        out = mfa.cmd_toggle_star(client, _ns(entry_id=9))
        client.toggle_bookmark.assert_called_once_with(9)
        assert out == {"toggled_star": 9}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestEntryCommands -v`
Expected: FAIL — `AttributeError: ... 'cmd_get_entries'`

- [ ] **Step 3: Implement the entry handlers + shared entry projection**

Add to `miniflux_api.py`:

```python
def _project_entry(entry: dict[str, Any]) -> dict[str, Any]:
    feed = entry.get("feed") or {}
    cat = feed.get("category") or {}
    return {
        "id": entry["id"],
        "title": entry.get("title"),
        "url": entry.get("url"),
        "status": entry.get("status"),
        "starred": entry.get("starred"),
        "published_at": entry.get("published_at"),
        "feed": feed.get("title"),
        "category": cat.get("title"),
    }


def _entry_filters(args) -> dict[str, Any]:
    """Translate CLI args into get_entries kwargs, omitting unset ones."""
    mapping = {
        "status": getattr(args, "status", None),
        "starred": getattr(args, "starred", None),
        "search": getattr(args, "search", None),
        "category_id": getattr(args, "category", None),
        "feed_id": getattr(args, "feed", None),
        "after": getattr(args, "after", None),
        "limit": getattr(args, "limit", None),
        "order": getattr(args, "order", None),
        "direction": getattr(args, "direction", None),
    }
    return {k: v for k, v in mapping.items() if v is not None}


def cmd_get_entries(client, args) -> dict[str, Any]:
    result = client.get_entries(**_entry_filters(args))
    return {
        "total": result.get("total", 0),
        "entries": [_project_entry(e) for e in result.get("entries", [])],
    }


def cmd_mark_read(client, args) -> dict[str, Any]:
    client.update_entries(args.ids, "read")
    return {"marked_read": args.ids}


def cmd_toggle_star(client, args) -> dict[str, Any]:
    client.toggle_bookmark(args.entry_id)
    return {"toggled_star": args.entry_id}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestEntryCommands -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add entry read/triage raw commands (fhsk-8k8)`

---

## Task 5: OPML, discover, and refresh commands

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestOpmlAndMaintenance:
    def test_export_opml_returns_text(self):
        client = MagicMock()
        client.export_feeds.return_value = "<opml></opml>"
        out = mfa.cmd_export_opml(client, _ns())
        assert out == {"opml": "<opml></opml>"}

    def test_import_opml_reads_file(self, tmp_path):
        client = MagicMock()
        path = tmp_path / "feeds.opml"
        path.write_text("<opml>data</opml>")
        out = mfa.cmd_import_opml(client, _ns(path=str(path)))
        client.import_feeds.assert_called_once_with("<opml>data</opml>")
        assert out == {"imported_from": str(path)}

    def test_discover(self):
        client = MagicMock()
        client.discover.return_value = [{"url": "https://ex.org/feed", "title": "Ex"}]
        out = mfa.cmd_discover(client, _ns(url="https://ex.org"))
        client.discover.assert_called_once_with("https://ex.org")
        assert out == [{"url": "https://ex.org/feed", "title": "Ex"}]

    def test_refresh_feed(self):
        client = MagicMock()
        out = mfa.cmd_refresh_feed(client, _ns(feed_id=42))
        client.refresh_feed.assert_called_once_with(42)
        assert out == {"refreshed_feed_id": 42}

    def test_refresh_all(self):
        client = MagicMock()
        out = mfa.cmd_refresh_all(client, _ns())
        client.refresh_all_feeds.assert_called_once_with()
        assert out == {"refreshed": "all"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestOpmlAndMaintenance -v`
Expected: FAIL — `AttributeError: ... 'cmd_export_opml'`

- [ ] **Step 3: Implement the handlers**

Add to `miniflux_api.py`:

```python
def cmd_export_opml(client, args) -> dict[str, Any]:
    return {"opml": client.export_feeds()}


def cmd_import_opml(client, args) -> dict[str, Any]:
    opml = Path(args.path).read_text()
    client.import_feeds(opml)
    return {"imported_from": args.path}


def cmd_discover(client, args) -> list[dict[str, Any]]:
    return client.discover(args.url)


def cmd_refresh_feed(client, args) -> dict[str, Any]:
    client.refresh_feed(args.feed_id)
    return {"refreshed_feed_id": args.feed_id}


def cmd_refresh_all(client, args) -> dict[str, Any]:
    client.refresh_all_feeds()
    return {"refreshed": "all"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestOpmlAndMaintenance -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add OPML, discover, and refresh commands (fhsk-8k8)`

---

## Task 6: `digest` workflow

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestDigest:
    def test_excerpt_strips_html_and_truncates(self):
        html = "<p>Hello <b>world</b> &amp; friends.</p>" + ("x" * 400)
        out = mfa._excerpt(html, limit=20)
        assert out.startswith("Hello world & friends")
        assert len(out) <= 21  # 20 chars + ellipsis

    def test_digest_returns_candidates(self):
        client = MagicMock()
        client.get_entries.return_value = {
            "total": 1,
            "entries": [
                {
                    "id": 5,
                    "title": "Hello",
                    "url": "https://ex.org/a",
                    "content": "<p>Body text</p>",
                    "published_at": "2026-06-13T00:00:00Z",
                    "feed": {"title": "Example", "category": {"title": "Tech"}},
                }
            ],
        }
        out = mfa.cmd_digest(
            client,
            _ns(category=None, since=None, limit=50, mark_read=None, star=None),
        )
        client.get_entries.assert_called_once_with(
            status="unread", order="published_at", direction="desc", limit=50
        )
        assert out["count"] == 1
        cand = out["candidates"][0]
        assert cand["id"] == 5
        assert cand["feed"] == "Example"
        assert cand["category"] == "Tech"
        assert cand["excerpt"] == "Body text"

    def test_digest_since_filters_by_after(self):
        client = MagicMock()
        client.get_entries.return_value = {"total": 0, "entries": []}
        mfa.cmd_digest(
            client,
            _ns(category=3, since=1700000000, limit=10, mark_read=None, star=None),
        )
        client.get_entries.assert_called_once_with(
            status="unread", order="published_at", direction="desc",
            limit=10, category_id=3, after=1700000000,
        )

    def test_digest_applies_mark_read_and_star(self):
        client = MagicMock()
        client.get_entries.return_value = {"total": 0, "entries": []}
        out = mfa.cmd_digest(
            client,
            _ns(category=None, since=None, limit=50, mark_read=[1, 2], star=[3]),
        )
        client.update_entries.assert_called_once_with([1, 2], "read")
        client.toggle_bookmark.assert_called_once_with(3)
        assert out["marked_read"] == [1, 2]
        assert out["starred"] == [3]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestDigest -v`
Expected: FAIL — `AttributeError: ... '_excerpt'`

- [ ] **Step 3: Implement excerpt helper + digest**

Add imports near the top of `miniflux_api.py` (with the stdlib imports):

```python
import html
import re
```

Add to `miniflux_api.py`:

```python
_TAG_RE = re.compile(r"<[^>]+>")


def _excerpt(content: str | None, limit: int = 280) -> str:
    text = html.unescape(_TAG_RE.sub("", content or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def cmd_digest(client, args) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "status": "unread",
        "order": "published_at",
        "direction": "desc",
        "limit": args.limit,
    }
    if args.category is not None:
        kwargs["category_id"] = args.category
    if args.since is not None:
        kwargs["after"] = args.since
    result = client.get_entries(**kwargs)
    candidates = [
        {
            "id": e["id"],
            "title": e.get("title"),
            "url": e.get("url"),
            "feed": (e.get("feed") or {}).get("title"),
            "category": ((e.get("feed") or {}).get("category") or {}).get("title"),
            "published": e.get("published_at"),
            "excerpt": _excerpt(e.get("content")),
        }
        for e in result.get("entries", [])
    ]
    out: dict[str, Any] = {"count": len(candidates), "candidates": candidates}
    if getattr(args, "mark_read", None):
        client.update_entries(args.mark_read, "read")
        out["marked_read"] = args.mark_read
    if getattr(args, "star", None):
        for entry_id in args.star:
            client.toggle_bookmark(entry_id)
        out["starred"] = args.star
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestDigest -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add digest workflow (fhsk-8k8)`

---

## Task 7: `triage` workflow

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestTriage:
    def test_triage_summarizes_unread_per_feed(self):
        client = MagicMock()
        client.get_feed_counters.return_value = {
            "reads": {"42": 100},
            "unreads": {"42": 3, "7": 0},
        }
        client.get_feeds.return_value = [
            {"id": 42, "title": "Example", "category": {"title": "Tech"}},
            {"id": 7, "title": "Quiet", "category": {"title": "Tech"}},
        ]
        out = mfa.cmd_triage(
            client, _ns(mark_read_feed=None, mark_read_category=None)
        )
        # Only feeds with unread > 0 appear, sorted desc by count
        assert out["unread_by_feed"] == [
            {"feed_id": 42, "title": "Example", "category": "Tech", "unread": 3}
        ]
        assert out["total_unread"] == 3

    def test_triage_mark_read_feed(self):
        client = MagicMock()
        client.get_feed_counters.return_value = {"unreads": {}}
        client.get_feeds.return_value = []
        out = mfa.cmd_triage(
            client, _ns(mark_read_feed=42, mark_read_category=None)
        )
        client.mark_feed_entries_as_read.assert_called_once_with(42)
        assert out["marked_read_feed"] == 42

    def test_triage_mark_read_category(self):
        client = MagicMock()
        client.get_feed_counters.return_value = {"unreads": {}}
        client.get_feeds.return_value = []
        out = mfa.cmd_triage(
            client, _ns(mark_read_feed=None, mark_read_category=7)
        )
        client.mark_category_entries_as_read.assert_called_once_with(7)
        assert out["marked_read_category"] == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestTriage -v`
Expected: FAIL — `AttributeError: ... 'cmd_triage'`

- [ ] **Step 3: Implement triage**

Add to `miniflux_api.py`:

```python
def cmd_triage(client, args) -> dict[str, Any]:
    if getattr(args, "mark_read_feed", None) is not None:
        client.mark_feed_entries_as_read(args.mark_read_feed)
        return {"marked_read_feed": args.mark_read_feed}
    if getattr(args, "mark_read_category", None) is not None:
        client.mark_category_entries_as_read(args.mark_read_category)
        return {"marked_read_category": args.mark_read_category}

    counters = client.get_feed_counters().get("unreads", {})
    feeds_by_id = {f["id"]: f for f in client.get_feeds()}
    rows = []
    for feed_id_str, count in counters.items():
        if count <= 0:
            continue
        feed = feeds_by_id.get(int(feed_id_str), {})
        rows.append(
            {
                "feed_id": int(feed_id_str),
                "title": feed.get("title"),
                "category": (feed.get("category") or {}).get("title"),
                "unread": count,
            }
        )
    rows.sort(key=lambda r: r["unread"], reverse=True)
    return {"unread_by_feed": rows, "total_unread": sum(r["unread"] for r in rows)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestTriage -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add triage workflow (fhsk-8k8)`

---

## Task 8: `health-audit` workflow

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestHealthAudit:
    def test_flags_errored_disabled_and_stale(self):
        client = MagicMock()
        client.get_feeds.return_value = [
            {"id": 1, "title": "Errored", "parsing_error_count": 4, "disabled": False},
            {"id": 2, "title": "Disabled", "parsing_error_count": 0, "disabled": True},
            {"id": 3, "title": "Stale", "parsing_error_count": 0, "disabled": False},
            {"id": 4, "title": "Fresh", "parsing_error_count": 0, "disabled": False},
        ]

        # Latest entry published_at per feed: stale=old, fresh=recent.
        def feed_entries(feed_id, **kwargs):
            latest = {
                3: "2000-01-01T00:00:00Z",
                4: "2026-06-13T00:00:00Z",
            }.get(feed_id)
            entries = [{"published_at": latest}] if latest else []
            return {"total": len(entries), "entries": entries}

        client.get_feed_entries.side_effect = feed_entries

        out = mfa.cmd_health_audit(client, _ns(stale_days=30, now=1750000000))
        assert {f["id"] for f in out["errored"]} == {1}
        assert {f["id"] for f in out["disabled"]} == {2}
        assert {f["id"] for f in out["stale"]} == {3}

    def test_no_entries_counts_as_stale(self):
        client = MagicMock()
        client.get_feeds.return_value = [
            {"id": 9, "title": "Empty", "parsing_error_count": 0, "disabled": False}
        ]
        client.get_feed_entries.return_value = {"total": 0, "entries": []}
        out = mfa.cmd_health_audit(client, _ns(stale_days=30, now=1750000000))
        assert out["stale"][0]["id"] == 9
        assert out["stale"][0]["latest_entry"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestHealthAudit -v`
Expected: FAIL — `AttributeError: ... 'cmd_health_audit'`

- [ ] **Step 3: Implement health-audit**

Add imports near the top of `miniflux_api.py` (with the stdlib imports):

```python
import time
from datetime import datetime, timezone
```

Add to `miniflux_api.py`:

```python
def _parse_ts(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _latest_entry_ts(client, feed_id: int) -> tuple[float | None, str | None]:
    result = client.get_feed_entries(
        feed_id, order="published_at", direction="desc", limit=1
    )
    entries = result.get("entries", [])
    if not entries:
        return None, None
    raw = entries[0].get("published_at")
    return _parse_ts(raw), raw


def cmd_health_audit(client, args) -> dict[str, Any]:
    now = getattr(args, "now", None) or time.time()
    cutoff = now - args.stale_days * 86400
    errored, disabled, stale = [], [], []
    for f in client.get_feeds():
        summary = {"id": f["id"], "title": f.get("title")}
        if f.get("parsing_error_count", 0) > 0:
            errored.append({**summary, "errors": f["parsing_error_count"]})
        if f.get("disabled", False):
            disabled.append(summary)
            continue  # disabled feeds are not also flagged stale
        ts, raw = _latest_entry_ts(client, f["id"])
        if ts is None or ts < cutoff:
            stale.append({**summary, "latest_entry": raw})
    return {
        "errored": errored,
        "disabled": disabled,
        "stale": stale,
        "stale_days": args.stale_days,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestHealthAudit -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add health-audit workflow (fhsk-8k8)`

---

## Task 9: Curation — `suggest-rules` & `apply-rule`

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestCuration:
    def test_suggest_rules_dumps_titles_and_current_rules(self):
        client = MagicMock()
        client.get_feed.return_value = {
            "id": 42,
            "title": "Example",
            "blocklist_rules": "(?i)sponsored",
            "keeplist_rules": "",
        }
        client.get_feed_entries.return_value = {
            "total": 2,
            "entries": [
                {"id": 1, "title": "Real post"},
                {"id": 2, "title": "Sponsored: buy now"},
            ],
        }
        out = mfa.cmd_suggest_rules(client, _ns(feed=42, limit=50))
        client.get_feed_entries.assert_called_once_with(42, limit=50, direction="desc")
        assert out["feed_id"] == 42
        assert out["current"]["blocklist_rules"] == "(?i)sponsored"
        assert out["recent_titles"] == ["Real post", "Sponsored: buy now"]

    def test_apply_rule_blocklist(self):
        client = MagicMock()
        out = mfa.cmd_apply_rule(
            client, _ns(feed=42, blocklist="(?i)sponsored", keeplist=None)
        )
        client.update_feed.assert_called_once_with(42, blocklist_rules="(?i)sponsored")
        assert out == {"feed_id": 42, "applied": {"blocklist_rules": "(?i)sponsored"}}

    def test_apply_rule_keeplist(self):
        client = MagicMock()
        out = mfa.cmd_apply_rule(
            client, _ns(feed=7, blocklist=None, keeplist="(?i)python")
        )
        client.update_feed.assert_called_once_with(7, keeplist_rules="(?i)python")
        assert out == {"feed_id": 7, "applied": {"keeplist_rules": "(?i)python"}}

    def test_apply_rule_requires_one_rule(self):
        client = MagicMock()
        with pytest.raises(ValueError):
            mfa.cmd_apply_rule(client, _ns(feed=7, blocklist=None, keeplist=None))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestCuration -v`
Expected: FAIL — `AttributeError: ... 'cmd_suggest_rules'`

- [ ] **Step 3: Implement curation handlers**

Add to `miniflux_api.py`:

```python
def cmd_suggest_rules(client, args) -> dict[str, Any]:
    feed = client.get_feed(args.feed)
    result = client.get_feed_entries(args.feed, limit=args.limit, direction="desc")
    return {
        "feed_id": args.feed,
        "feed_title": feed.get("title"),
        "current": {
            "blocklist_rules": feed.get("blocklist_rules", ""),
            "keeplist_rules": feed.get("keeplist_rules", ""),
        },
        "recent_titles": [e.get("title") for e in result.get("entries", [])],
    }


def cmd_apply_rule(client, args) -> dict[str, Any]:
    applied: dict[str, str] = {}
    if getattr(args, "blocklist", None) is not None:
        applied["blocklist_rules"] = args.blocklist
    if getattr(args, "keeplist", None) is not None:
        applied["keeplist_rules"] = args.keeplist
    if not applied:
        raise ValueError("apply-rule requires --blocklist or --keeplist")
    client.update_feed(args.feed, **applied)
    return {"feed_id": args.feed, "applied": applied}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestCuration -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

`feat(miniflux): add curation suggest-rules and apply-rule commands (fhsk-8k8)`

---

## Task 10: argparse wiring & `main()` dispatch

**Files:**

- Modify: `homelab/skills/miniflux/scripts/miniflux_api.py`
- Modify: `homelab/skills/miniflux/tests/test_miniflux_api.py`
- [ ] **Step 1: Write the failing tests**

Append to `test_miniflux_api.py`:

```python
class TestMainDispatch:
    def test_list_commands_runs_without_client(self, capsys):
        rc = mfa.main(["--list-commands"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "digest" in out and "health-audit" in out

    def test_list_feeds_dispatches_through_client(self, capsys, monkeypatch):
        fake = MagicMock()
        fake.get_feeds.return_value = []
        monkeypatch.setattr(mfa, "resolve_config", lambda: {"url": "u", "api_key": "k"})
        monkeypatch.setattr(mfa, "make_client", lambda cfg: fake)
        rc = mfa.main(["list-feeds", "--format", "json"])
        out = capsys.readouterr().out
        assert rc == 0
        assert json.loads(out) == []
        fake.get_feeds.assert_called_once_with()

    def test_config_error_returns_2(self, capsys, monkeypatch):
        def boom():
            raise mfa.ConfigError("no config")

        monkeypatch.setattr(mfa, "resolve_config", boom)
        rc = mfa.main(["list-feeds"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "no config" in err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py::TestMainDispatch -v`
Expected: FAIL — `TypeError: main() takes 0 ...` or `AttributeError`

- [ ] **Step 3: Implement argparse + main**

Add `import argparse` to the stdlib imports. Add to `miniflux_api.py`:

```python
# command name -> handler. Handlers take (client, args) and return data.
COMMANDS = {
    "list-feeds": cmd_list_feeds,
    "list-categories": cmd_list_categories,
    "create-feed": cmd_create_feed,
    "delete-feed": cmd_delete_feed,
    "get-entries": cmd_get_entries,
    "mark-read": cmd_mark_read,
    "toggle-star": cmd_toggle_star,
    "export-opml": cmd_export_opml,
    "import-opml": cmd_import_opml,
    "discover": cmd_discover,
    "refresh-feed": cmd_refresh_feed,
    "refresh-all": cmd_refresh_all,
    "digest": cmd_digest,
    "triage": cmd_triage,
    "health-audit": cmd_health_audit,
    "suggest-rules": cmd_suggest_rules,
    "apply-rule": cmd_apply_rule,
}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=["yaml", "json"], default="yaml")

    parser = argparse.ArgumentParser(
        prog="miniflux_api.py", description="Manage and curate Miniflux RSS feeds."
    )
    parser.add_argument(
        "--list-commands", action="store_true", help="List available commands and exit"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-feeds", parents=[common], help="List feeds")
    sub.add_parser("list-categories", parents=[common], help="List categories")

    cf = sub.add_parser("create-feed", parents=[common], help="Subscribe to a feed")
    cf.add_argument("url")
    cf.add_argument("--category", type=int)
    cf.add_argument("--crawler", action="store_true")

    df = sub.add_parser("delete-feed", parents=[common], help="Delete a feed")
    df.add_argument("feed_id", type=int)

    ge = sub.add_parser("get-entries", parents=[common], help="List entries")
    ge.add_argument("--status", choices=["read", "unread", "removed"])
    ge.add_argument(
        "--starred", action=argparse.BooleanOptionalAction, default=None
    )
    ge.add_argument("--search")
    ge.add_argument("--category", type=int)
    ge.add_argument("--feed", type=int)
    ge.add_argument("--after", type=int)
    ge.add_argument("--limit", type=int, default=20)
    ge.add_argument("--order", default="published_at")
    ge.add_argument("--direction", default="desc", choices=["asc", "desc"])

    mr = sub.add_parser("mark-read", parents=[common], help="Mark entries read")
    mr.add_argument("ids", nargs="+", type=int)

    ts = sub.add_parser("toggle-star", parents=[common], help="Toggle entry star")
    ts.add_argument("entry_id", type=int)

    sub.add_parser("export-opml", parents=[common], help="Export OPML")
    io = sub.add_parser("import-opml", parents=[common], help="Import OPML")
    io.add_argument("path")

    dc = sub.add_parser("discover", parents=[common], help="Discover feeds at a URL")
    dc.add_argument("url")

    rf = sub.add_parser("refresh-feed", parents=[common], help="Refresh one feed")
    rf.add_argument("feed_id", type=int)
    sub.add_parser("refresh-all", parents=[common], help="Refresh all feeds")

    dg = sub.add_parser("digest", parents=[common], help="Unread digest candidates")
    dg.add_argument("--category", type=int)
    dg.add_argument("--since", type=int, help="Unix timestamp; only entries after")
    dg.add_argument("--limit", type=int, default=50)
    dg.add_argument("--mark-read", nargs="+", type=int, dest="mark_read")
    dg.add_argument("--star", nargs="+", type=int)

    tr = sub.add_parser("triage", parents=[common], help="Unread summary + bulk read")
    tr.add_argument("--mark-read-feed", type=int, dest="mark_read_feed")
    tr.add_argument("--mark-read-category", type=int, dest="mark_read_category")

    ha = sub.add_parser("health-audit", parents=[common], help="Audit feed health")
    ha.add_argument("--stale-days", type=int, default=30, dest="stale_days")

    sr = sub.add_parser("suggest-rules", parents=[common], help="Dump titles for rules")
    sr.add_argument("--feed", type=int, required=True)
    sr.add_argument("--limit", type=int, default=50)

    ar = sub.add_parser("apply-rule", parents=[common], help="Apply blocklist/keeplist")
    ar.add_argument("--feed", type=int, required=True)
    ar.add_argument("--blocklist")
    ar.add_argument("--keeplist")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_commands:
        print(format_output(sorted(COMMANDS), getattr(args, "format", "yaml")))
        return 0
    if not args.command:
        build_parser().print_help()
        return 2

    try:
        config = resolve_config()
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2

    client = make_client(config)
    handler = COMMANDS[args.command]
    return run_command(lambda: handler(client, args), args.format)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the full suite**

Run: `uv run --with pytest --with pyyaml --with miniflux pytest homelab/skills/miniflux/tests/test_miniflux_api.py -v`
Expected: PASS (all tests green)

- [ ] **Step 5: Smoke-test the CLI help**

Run: `homelab/skills/miniflux/scripts/miniflux_api.py --list-commands`
Expected: YAML list including `digest`, `health-audit`, `suggest-rules`, `triage`.

- [ ] **Step 6: Commit**

`feat(miniflux): wire argparse dispatch and main entrypoint (fhsk-8k8)`

---

## Task 11: SKILL.md and reference docs

**Files:**

- Create: `homelab/skills/miniflux/SKILL.md`
- Create: `homelab/skills/miniflux/references/feeds.md`
- Create: `homelab/skills/miniflux/references/entries.md`
- Create: `homelab/skills/miniflux/references/curation.md`
- Create: `homelab/skills/miniflux/references/digest.md`
- Create: `homelab/skills/miniflux/references/health.md`
- [ ] **Step 1: Write `SKILL.md`**

Create `homelab/skills/miniflux/SKILL.md` (mirror the grafana/terraform frontmatter shape). The outer fence below uses four backticks so the inner ```bash``` block nests correctly — write the SKILL.md with normal triple-backtick fences:

````markdown
---
name: miniflux
description: |
  Manage and curate a personal Miniflux RSS subscription set: feed management,
  reading & triage, AI curation, and health/maintenance. Wraps the official
  `miniflux` Python client via a uv-run gateway script (no MCP server required).
  Use when working with: (1) Feeds - subscribe/unsubscribe, organize into
  categories, OPML import/export, discover feeds at a URL; (2) Reading & triage -
  list/search unread entries, mark read, toggle stars, bulk-process the backlog;
  (3) Curation - generate a relevance-ranked digest of what's worth reading, and
  turn recurring noise into durable blocklist/keeplist regex rules; (4) Health -
  find errored, disabled, or stale feeds. This is a direct-client wrapper, not an
  MCP gateway.
allowed-tools:
  - "Bash(uv:*)"
  - "Bash(${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py:*)"
  - Read
  - Grep
  - Glob
  - Search
metadata:
  author: fzymgc-house
---

# Miniflux Operations

## Prerequisites

Set `MINIFLUX_URL` and `MINIFLUX_API_KEY`, or create
`~/.config/miniflux/config.yaml` with `url:` and `api_key:` keys. Create an API
key in Miniflux under Settings → API Keys.

Optional: `~/.config/miniflux/interests.md` describes your reading interests; the
digest workflow uses it to rank entries when present.

## Gateway Script

All operations run through
`${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py`.

```bash
# Discovery
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py --list-commands
${CLAUDE_PLUGIN_ROOT}/skills/miniflux/scripts/miniflux_api.py <command> --help

# Examples
.../miniflux_api.py list-feeds
.../miniflux_api.py get-entries --status unread --limit 50
.../miniflux_api.py digest --category 3 --limit 50
.../miniflux_api.py triage
.../miniflux_api.py health-audit --stale-days 45
.../miniflux_api.py suggest-rules --feed 42
```

`--format yaml` (default) or `--format json` on any command.

## Curation: rules + reasoning

Miniflux applies per-feed `blocklist_rules` / `keeplist_rules` (regex over entry
titles/URLs) deterministically on its side. Claude supplies judgment:

1. **Digest (reasoning):** run `digest`, rank candidates against the user's
   interests, write highlights, then apply decisions with
   `digest --mark-read <ids> --star <ids>` (or the `mark-read` / `toggle-star`
   commands).
2. **Soft → hard handoff (rules):** when you notice recurring noise, run
   `suggest-rules --feed <id>`, propose a regex, get user approval, then make it
   durable with `apply-rule --feed <id> --blocklist '<regex>'`.

See `references/` for per-domain detail: `feeds.md`, `entries.md`,
`curation.md`, `digest.md`, `health.md`.
````

- [ ] **Step 2: Write the five reference docs**

Create each file with command-focused content (no placeholders):

`references/feeds.md` — feed/category CRUD, OPML, discover. Document
`list-feeds`, `list-categories`, `create-feed <url> [--category N] [--crawler]`,
`delete-feed <id>`, `export-opml`, `import-opml <path>`, `discover <url>`,
`refresh-feed <id>`, `refresh-all`, with one example invocation each and the
fields each returns.

`references/entries.md` — `get-entries` with every filter
(`--status/--starred/--search/--category/--feed/--after/--limit/--order/--direction`),
`mark-read <ids...>`, `toggle-star <id>`. Note the projected entry fields
(`id, title, url, status, starred, published_at, feed, category`).

`references/curation.md` — explain `blocklist_rules`/`keeplist_rules`/`scraper_rules`/`rewrite_rules`
semantics (regex, case-insensitive via `(?i)`), the `suggest-rules` →
`apply-rule` flow, and that rules are applied feed-by-feed via `update_feed`.

`references/digest.md` — the digest workflow: pull unread candidates, rank
against `~/.config/miniflux/interests.md` or session context, write highlights,
apply `--mark-read`/`--star`. Document the candidate fields
(`id, title, url, feed, category, published, excerpt`).

`references/health.md` — `health-audit`: errored (`parsing_error_count > 0`),
disabled, and stale (no entry newer than `--stale-days`, default 30) feeds, and
how staleness is computed (latest entry `published_at` per feed).

- [ ] **Step 3: Lint the markdown**

Run: `task fmt && task lint`
Expected: PASS (rumdl picks up `homelab/skills/*/SKILL.md` automatically).

- [ ] **Step 4: Commit**

`docs(miniflux): add SKILL.md and reference docs (fhsk-8k8)`

---

## Task 12: Wire tests into the Taskfile

**Files:**

- Modify: `Taskfile.yaml`

- [ ] **Step 1: Add the test directory to `PYTEST_DIRS`**

In `Taskfile.yaml`, find the `PYTEST_DIRS` block (currently ends with
`homelab/skills/terraform/tests/`) and add the miniflux tests dir:

```yaml
    homelab/skills/terraform/tests/
    homelab/skills/miniflux/tests/
```

- [ ] **Step 2: Add `miniflux` to the test runner deps**

In the `test` task, update the pytest command to make the `miniflux` package
importable (the script imports it at module top):

```yaml
      - uv run --with pytest --with httpx --with pyyaml --with miniflux pytest {{.PYTEST_DIRS}}
```

- [ ] **Step 3: Run the full gate**

Run: `task test`
Expected: PASS — the miniflux suite runs alongside the existing suites.

- [ ] **Step 4: Run lint**

Run: `task lint`
Expected: PASS.

- [ ] **Step 5: Commit**

`test(miniflux): wire skill test suite into Taskfile gates (fhsk-8k8)`

---

## Done criteria

- `task test` and `task lint` pass with the new suite wired in.
- `miniflux_api.py --list-commands` lists all 17 commands.
- Every spec section (feed mgmt, reading/triage, AI curation incl. digest +
  rules, health/maintenance) maps to at least one task above.
<!-- adr-capture: sha256=ba9b7b1d6be17a53; session=cli; ts=2026-06-14T00:40:32Z; adrs=fhsk-pqw,fhsk-qs9,fhsk-0qz -->
