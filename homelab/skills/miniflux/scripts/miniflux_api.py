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

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime
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
        try:
            file_cfg = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {path}: {e}") from e

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
    except ValueError as e:
        print(f"Invalid usage: {e}", file=sys.stderr)
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


def cmd_get_feed(client, args) -> dict[str, Any]:
    return client.get_feed(args.feed_id)


def cmd_update_feed(client, args) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if getattr(args, "title", None) is not None:
        fields["title"] = args.title
    if getattr(args, "category", None) is not None:
        fields["category_id"] = args.category
    if getattr(args, "crawler", None) is not None:
        fields["crawler"] = args.crawler
    if getattr(args, "disabled", None) is not None:
        fields["disabled"] = args.disabled
    if not fields:
        raise ValueError(
            "update-feed requires at least one of "
            "--title / --category / --crawler / --disabled"
        )
    client.update_feed(args.feed_id, **fields)
    return {"updated_feed_id": args.feed_id, "updated": fields}


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
    path = Path(args.path)
    if not path.is_file():
        raise ValueError(f"OPML file not found: {args.path}")
    client.import_feeds(path.read_text())
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


# command name -> handler. Handlers take (client, args) and return data.
COMMANDS = {
    "list-feeds": cmd_list_feeds,
    "list-categories": cmd_list_categories,
    "get-feed": cmd_get_feed,
    "create-feed": cmd_create_feed,
    "update-feed": cmd_update_feed,
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

    gf = sub.add_parser("get-feed", parents=[common], help="Get one feed by id")
    gf.add_argument("feed_id", type=int)

    cf = sub.add_parser("create-feed", parents=[common], help="Subscribe to a feed")
    cf.add_argument("url")
    cf.add_argument("--category", type=int)
    cf.add_argument("--crawler", action="store_true")

    uf = sub.add_parser("update-feed", parents=[common], help="Update feed attributes")
    uf.add_argument("feed_id", type=int)
    uf.add_argument("--title")
    uf.add_argument("--category", type=int)
    uf.add_argument("--crawler", action=argparse.BooleanOptionalAction, default=None)
    uf.add_argument("--disabled", action=argparse.BooleanOptionalAction, default=None)

    df = sub.add_parser("delete-feed", parents=[common], help="Delete a feed")
    df.add_argument("feed_id", type=int)

    ge = sub.add_parser("get-entries", parents=[common], help="List entries")
    ge.add_argument("--status", choices=["read", "unread", "removed"])
    ge.add_argument("--starred", action=argparse.BooleanOptionalAction, default=None)
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
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_commands:
        print(format_output(sorted(COMMANDS), getattr(args, "format", "yaml")))
        return 0
    if not args.command:
        parser.print_help()
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
