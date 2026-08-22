"""Tests for GitHub update helpers (offline)."""

from __future__ import annotations

import io
import json
import ssl
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.app_updater import apply_standalone_zip
from src.utils.github_updates import (
    ERR_HTTP_403,
    ERR_HTTP_404,
    ERR_NETWORK,
    ERR_SSL,
    ERR_TIMEOUT,
    ReleaseInfo,
    _normalize_repo,
    _pick_zip_asset,
    _save_disk_cache,
    check_for_update,
    classify_github_error,
    fetch_latest_release_outcome,
    is_newer,
    parse_semver,
    resolve_github_repo,
)


def test_parse_semver() -> None:
    assert parse_semver("v1.0.2") == (1, 0, 2)
    assert parse_semver("1.2.10") == (1, 2, 10)
    assert parse_semver("nope") == (0, 0, 0)


def test_is_newer() -> None:
    assert is_newer("1.0.3", "1.0.2")
    assert not is_newer("1.0.2", "1.0.2")
    assert not is_newer("1.0.1", "1.0.2")


def test_normalize_repo() -> None:
    assert _normalize_repo("acme/quanta") == "acme/quanta"
    assert _normalize_repo("https://github.com/acme/quanta.git") == "acme/quanta"
    assert _normalize_repo("# comment") is None


def test_resolve_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANTA_GITHUB_REPO", raising=False)
    (tmp_path / "GITHUB_REPO").write_text("acme/demo-app\n", encoding="utf-8")
    assert resolve_github_repo(tmp_path) == "acme/demo-app"


def test_resolve_skips_comment_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANTA_GITHUB_REPO", raising=False)
    (tmp_path / "GITHUB_REPO").write_text(
        "# comment\n# another\nacme/from-comments\n",
        encoding="utf-8",
    )
    assert resolve_github_repo(tmp_path) == "acme/from-comments"


def test_pick_zip_prefers_standalone() -> None:
    assets = [
        {"name": "source.zip", "browser_download_url": "https://example/a.zip"},
        {
            "name": "Quanta-standalone-1.0.3.zip",
            "browser_download_url": "https://example/b.zip",
        },
    ]
    url, name = _pick_zip_asset(assets)
    assert url == "https://example/b.zip"
    assert name and "standalone" in name.lower()


def test_apply_preserves_data(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "VERSION").write_text("1.0.2\n", encoding="utf-8")
    (app / "app.py").write_text("OLD\n", encoding="utf-8")
    data = app / "data" / "jobs"
    data.mkdir(parents=True)
    keep = data / "mine.json"
    keep.write_text('{"ok": true}\n', encoding="utf-8")

    payload = tmp_path / "upd.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Quanta/VERSION", "1.0.3\n")
        zf.writestr("Quanta/app.py", "NEW\n")
        zf.writestr("Quanta/src/marker.txt", "x\n")
    payload.write_bytes(buf.getvalue())

    apply_standalone_zip(payload, app_root=app)
    assert (app / "VERSION").read_text(encoding="utf-8").strip() == "1.0.3"
    assert (app / "app.py").read_text(encoding="utf-8").strip() == "NEW"
    assert keep.read_text(encoding="utf-8").startswith("{")
    assert (app / "src" / "marker.txt").is_file()


def test_classify_network_timeout_ssl_http() -> None:
    code, _ = classify_github_error(urllib.error.URLError("Name or service not known"))
    assert code == ERR_NETWORK
    code, _ = classify_github_error(TimeoutError("timed out"))
    assert code == ERR_TIMEOUT
    code, _ = classify_github_error(ssl.SSLError("CERTIFICATE_VERIFY_FAILED"))
    assert code == ERR_SSL
    http404 = urllib.error.HTTPError("https://api.github.com/x", 404, "Not Found", hdrs=None, fp=None)
    assert classify_github_error(http404)[0] == ERR_HTTP_404
    http403 = urllib.error.HTTPError("https://api.github.com/x", 403, "Forbidden", hdrs=None, fp=None)
    assert classify_github_error(http403)[0] == ERR_HTTP_403
    assert classify_github_error(json.JSONDecodeError("x", "", 0))[0] == "bad_response"


def test_check_for_update_keeps_typed_network_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANTA_GITHUB_REPO", raising=False)
    (tmp_path / "GITHUB_REPO").write_text("acme/demo-app\n", encoding="utf-8")
    with patch(
        "src.utils.github_updates.fetch_latest_release_outcome",
        return_value=(None, ERR_NETWORK, "Name or service not known"),
    ):
        status = check_for_update(local_version="1.0.6", root=tmp_path)
    assert status.configured is True
    assert status.update_available is False
    assert status.error_code == ERR_NETWORK
    assert "Name or service not known" in status.message


def test_check_for_update_not_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANTA_GITHUB_REPO", raising=False)
    status = check_for_update(local_version="1.0.6", root=tmp_path)
    assert status.configured is False
    assert status.error_code == "not_configured"


def test_disk_cache_avoids_repeat_fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "update_check_cache.json"
    monkeypatch.setattr("src.utils.github_updates.CACHE_PATH", cache)
    monkeypatch.setattr("src.utils.github_updates.DATA_DIR", tmp_path)
    release = ReleaseInfo(
        tag="v1.0.8",
        version="1.0.8",
        html_url="https://github.com/acme/quanta/releases/tag/v1.0.8",
        zip_url="https://example/standalone.zip",
        zip_name="standalone.zip",
    )
    _save_disk_cache("acme/quanta", release=release, error_code=None, detail="", ttl_s=3600.0)
    with patch("urllib.request.urlopen") as mock_open:
        got, err, detail = fetch_latest_release_outcome("acme/quanta", use_cache=True)
    mock_open.assert_not_called()
    assert err is None
    assert got is not None
    assert got.version == "1.0.8"


def test_fetch_picks_highest_semver_from_tags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("src.utils.github_updates.CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr("src.utils.github_updates.DATA_DIR", tmp_path)

    def fake_get(url: str):
        if "/releases?" in url:
            return (
                [
                    {
                        "tag_name": "v1.0.0",
                        "name": "old",
                        "draft": False,
                        "html_url": "https://github.com/acme/quanta/releases/tag/v1.0.0",
                        "assets": [],
                    }
                ],
                None,
                "",
            )
        if url.endswith("/releases/latest"):
            return (
                {
                    "tag_name": "v1.0.0",
                    "name": "old",
                    "html_url": "https://github.com/acme/quanta/releases/tag/v1.0.0",
                    "assets": [],
                },
                None,
                "",
            )
        if "/tags" in url:
            return (
                [{"name": "v1.0.8"}, {"name": "v1.0.7"}, {"name": "v1.0.0"}],
                None,
                "",
            )
        return None, "unexpected", url

    with patch("src.utils.github_updates._github_get_json", side_effect=fake_get):
        got, err, _ = fetch_latest_release_outcome("acme/quanta", use_cache=False)
    assert err is None
    assert got is not None
    assert got.version == "1.0.8"

