"""Tests for SECRETS file loading (no real tokens)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.secrets import (
    clear_secrets_cache,
    get_secret,
    github_token,
    parse_secrets_text,
    secrets_file_exists,
    secrets_status,
)


def test_parse_secrets_text() -> None:
    text = """
# comment
GITHUB_TOKEN=ghp_abc123
QUANTA_GITHUB_TOKEN="quoted"
EMPTY=
badline
KEY = spaced
"""
    parsed = parse_secrets_text(text)
    assert parsed["GITHUB_TOKEN"] == "ghp_abc123"
    assert parsed["QUANTA_GITHUB_TOKEN"] == "quoted"
    assert parsed["KEY"] == "spaced"
    assert "EMPTY" not in parsed


def test_github_token_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("QUANTA_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    (tmp_path / "SECRETS").write_text("GITHUB_TOKEN=ghp_from_file\n", encoding="utf-8")
    clear_secrets_cache()
    assert github_token(root=tmp_path) == "ghp_from_file"
    assert secrets_file_exists(tmp_path) is True
    st = secrets_status(root=tmp_path)
    assert st["exists"] is True
    assert st["github_token_from_file"] is True
    assert "GITHUB_TOKEN" in st["keys"]


def test_env_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "SECRETS").write_text("GITHUB_TOKEN=from_file\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "from_env")
    clear_secrets_cache()
    assert get_secret("GITHUB_TOKEN", root=tmp_path) == "from_env"


def test_missing_secrets_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("QUANTA_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    clear_secrets_cache()
    assert github_token(root=tmp_path) == ""
    assert secrets_file_exists(tmp_path) is False
