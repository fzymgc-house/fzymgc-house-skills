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
