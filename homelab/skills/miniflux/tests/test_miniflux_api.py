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


def _ns(**kwargs):
    """Build a throwaway args namespace for handler tests."""
    from argparse import Namespace

    return Namespace(**kwargs)


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


class TestRunCommand:
    def test_success_prints_formatted(self, capsys):
        rc = mfa.run_command(lambda: {"ok": True}, "json")
        out = capsys.readouterr().out
        assert rc == 0
        assert json.loads(out) == {"ok": True}

    def test_unauthorized_maps_to_api_key_hint(self, capsys):
        import miniflux
        from unittest.mock import Mock

        def boom():
            resp = Mock()
            resp.status_code = 401
            resp.headers = {"Content-Type": "application/json"}
            resp.json.return_value = {"error_message": "unauthorized"}
            raise miniflux.AccessUnauthorized(resp)

        rc = mfa.run_command(boom, "yaml")
        err = capsys.readouterr().err
        assert rc == 1
        assert "MINIFLUX_API_KEY" in err

    def test_client_error_surfaces_message(self, capsys):
        import miniflux
        from unittest.mock import Mock

        def boom():
            resp = Mock()
            resp.status_code = 404
            resp.headers = {"Content-Type": "application/json"}
            resp.json.return_value = {"error_message": "feed not found"}
            raise miniflux.ResourceNotFound(resp)

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
        out = mfa.cmd_create_feed(
            client, _ns(url="https://x/feed", category=7, crawler=True)
        )
        client.create_feed.assert_called_once_with(
            "https://x/feed", category_id=7, crawler=True
        )
        assert out == {"created_feed_id": 99}

    def test_delete_feed(self):
        client = MagicMock()
        out = mfa.cmd_delete_feed(client, _ns(feed_id=42))
        client.delete_feed.assert_called_once_with(42)
        assert out == {"deleted_feed_id": 42}


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
            _ns(
                status="unread",
                starred=None,
                search=None,
                category=None,
                feed=None,
                after=None,
                limit=20,
                order="published_at",
                direction="desc",
            ),
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
