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


class TestDigest:
    def test_excerpt_strips_html_and_truncates(self):
        html = "<p>Hello <b>world</b> &amp; friends.</p>" + ("x" * 400)
        out = mfa._excerpt(html, limit=21)
        assert out.startswith("Hello world & friends")
        assert len(out) <= 22  # 21 chars + ellipsis

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
            status="unread",
            order="published_at",
            direction="desc",
            limit=10,
            category_id=3,
            after=1700000000,
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
        out = mfa.cmd_triage(client, _ns(mark_read_feed=None, mark_read_category=None))
        # Only feeds with unread > 0 appear, sorted desc by count
        assert out["unread_by_feed"] == [
            {"feed_id": 42, "title": "Example", "category": "Tech", "unread": 3}
        ]
        assert out["total_unread"] == 3

    def test_triage_mark_read_feed(self):
        client = MagicMock()
        client.get_feed_counters.return_value = {"unreads": {}}
        client.get_feeds.return_value = []
        out = mfa.cmd_triage(client, _ns(mark_read_feed=42, mark_read_category=None))
        client.mark_feed_entries_as_read.assert_called_once_with(42)
        assert out["marked_read_feed"] == 42

    def test_triage_mark_read_category(self):
        client = MagicMock()
        client.get_feed_counters.return_value = {"unreads": {}}
        client.get_feeds.return_value = []
        out = mfa.cmd_triage(client, _ns(mark_read_feed=None, mark_read_category=7))
        client.mark_category_entries_as_read.assert_called_once_with(7)
        assert out["marked_read_category"] == 7


class TestHealthAudit:
    def test_flags_errored_disabled_and_stale(self):
        client = MagicMock()
        client.get_feeds.return_value = [
            {"id": 1, "title": "Errored", "parsing_error_count": 4, "disabled": False},
            {"id": 2, "title": "Disabled", "parsing_error_count": 0, "disabled": True},
            {"id": 3, "title": "Stale", "parsing_error_count": 0, "disabled": False},
            {"id": 4, "title": "Fresh", "parsing_error_count": 0, "disabled": False},
        ]

        # Latest entry published_at per feed. Feed 1 (Errored) gets a fresh entry
        # so it is flagged ONLY as errored, not incidentally stale (errored and
        # stale are independent conditions in the impl).
        def feed_entries(feed_id, **kwargs):
            latest = {
                1: "2026-06-13T00:00:00Z",
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


class TestGetUpdateFeed:
    def test_get_feed_returns_raw(self):
        client = MagicMock()
        client.get_feed.return_value = {"id": 42, "title": "Example"}
        out = mfa.cmd_get_feed(client, _ns(feed_id=42))
        client.get_feed.assert_called_once_with(42)
        assert out == {"id": 42, "title": "Example"}

    def test_update_feed_sets_fields(self):
        client = MagicMock()
        out = mfa.cmd_update_feed(
            client,
            _ns(feed_id=42, title="New", category=7, crawler=True, disabled=None),
        )
        client.update_feed.assert_called_once_with(
            42, title="New", category_id=7, crawler=True
        )
        assert out == {
            "updated_feed_id": 42,
            "updated": {"title": "New", "category_id": 7, "crawler": True},
        }

    def test_update_feed_requires_a_field(self):
        client = MagicMock()
        with pytest.raises(ValueError):
            mfa.cmd_update_feed(
                client,
                _ns(feed_id=42, title=None, category=None, crawler=None, disabled=None),
            )

    def test_get_feed_dispatches_in_command_list(self):
        assert "get-feed" in mfa.COMMANDS and "update-feed" in mfa.COMMANDS


class TestEntryFilterEdgeCases:
    def test_starred_false_passed_through(self):
        # --no-starred yields starred=False, which is meaningful (not None)
        # and must reach the API, not be dropped by the is-not-None guard.
        client = MagicMock()
        client.get_entries.return_value = {"total": 0, "entries": []}
        mfa.cmd_get_entries(
            client,
            _ns(
                status=None,
                starred=False,
                search=None,
                category=None,
                feed=None,
                after=None,
                limit=20,
                order="published_at",
                direction="desc",
            ),
        )
        _, kwargs = client.get_entries.call_args
        assert kwargs["starred"] is False


class TestErrorTranslation:
    def test_value_error_maps_to_invalid_usage(self, capsys):
        def boom():
            raise ValueError("apply-rule requires --blocklist or --keeplist")

        rc = mfa.run_command(boom, "yaml")
        err = capsys.readouterr().err
        assert rc == 1
        assert "Invalid usage" in err
        assert "apply-rule requires" in err

    def test_import_opml_missing_file_is_clean_error(self, tmp_path):
        client = MagicMock()
        missing = tmp_path / "nope.opml"
        with pytest.raises(ValueError) as exc:
            mfa.cmd_import_opml(client, _ns(path=str(missing)))
        assert "OPML file not found" in str(exc.value)
        client.import_feeds.assert_not_called()

    def test_invalid_config_yaml_raises_config_error(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MINIFLUX_URL", raising=False)
        monkeypatch.delenv("MINIFLUX_API_KEY", raising=False)
        path = tmp_path / "config.yaml"
        path.write_text("url: [unclosed\n")
        with pytest.raises(mfa.ConfigError) as exc:
            mfa.resolve_config(config_path=path)
        assert "Invalid YAML" in str(exc.value)
