"""Apply a standalone zip update from GitHub Releases (Layer 4)."""

from __future__ import annotations

import logging
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Optional

from src.utils.github_updates import USER_AGENT
from src.utils.paths import ROOT

logger = logging.getLogger(__name__)

PRESERVE_TOP_LEVEL = frozenset(
    {
        "data",
        "exports",
        "venv",
        ".venv",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "SECRETS",
        ".env",
    }
)


def _find_app_root(extracted: Path) -> Path:
    """Locate folder that contains ``app.py`` + ``VERSION`` under an extract tree."""
    direct = extracted / "app.py"
    if direct.is_file() and (extracted / "VERSION").is_file():
        return extracted
    candidates: list[Path] = []
    for path in extracted.rglob("app.py"):
        parent = path.parent
        if (parent / "VERSION").is_file():
            candidates.append(parent)
    if not candidates:
        raise FileNotFoundError("Update zip does not contain app.py + VERSION")
    candidates.sort(key=lambda p: len(p.parts))
    return candidates[0]


def download_file(url: str, dest: Path, timeout: float = 120.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def apply_standalone_zip(
    zip_path: Path,
    *,
    app_root: Optional[Path] = None,
    preserve: Optional[Iterable[str]] = None,
) -> Path:
    """Unpack ``zip_path`` over ``app_root``, preserving local data/venv.

    Returns the app root that was updated.
    """
    target = (app_root or ROOT).resolve()
    keep = set(preserve) if preserve is not None else set(PRESERVE_TOP_LEVEL)

    with tempfile.TemporaryDirectory(prefix="quanta_upd_") as tmp:
        tmp_path = Path(tmp)
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        source = _find_app_root(extract_dir)

        for item in source.iterdir():
            name = item.name
            if name in keep:
                continue
            dest = target / name
            if dest.exists() or dest.is_symlink():
                if dest.is_dir() and not dest.is_symlink():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    logger.info("Applied update zip into %s", target)
    return target


def download_and_apply(zip_url: str, *, app_root: Optional[Path] = None) -> Path:
    """Download release zip and apply over the app folder."""
    target = (app_root or ROOT).resolve()
    with tempfile.TemporaryDirectory(prefix="quanta_dl_") as tmp:
        zip_path = Path(tmp) / "update.zip"
        download_file(zip_url, zip_path)
        return apply_standalone_zip(zip_path, app_root=target)
