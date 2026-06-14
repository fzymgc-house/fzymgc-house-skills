#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "pyyaml", "miniflux"]
# ///
"""Tests for miniflux_api.py (handlers tested with a mocked client)."""

import json
import sys
from pathlib import Path

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
