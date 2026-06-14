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

import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import miniflux
import yaml
from miniflux import AccessUnauthorized, ClientError


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
