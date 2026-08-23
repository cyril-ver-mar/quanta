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

# Top-level names that must survive an in-app update (case-insensitive match).
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

# Always snapshot/restore these files even if merge logic changes.
_CRITICAL_FILE_BACKUPS = frozenset({"SECRETS", ".env"})


def _preserve_keyset(names: Iterable[str]) -> set[str]:
    return {n.lower() for n in names}


def _is_preserved(name: str, keep_lower: set[str]) -> bool:
    return name.lower() in keep_lower


def _snapshot_critical_files(target: Path, keep_lower: set[str]) -> dict[str, bytes]:
    """Backup critical preserved files before merge (keyed by lowercased name)."""
    snaps: dict[str, bytes] = {}
    critical_lower = {n.lower() for n in _CRITICAL_FILE_BACKUPS}
    try:
        entries = list(target.iterdir())
    except OSError:
        entries = []
    for path in entries:
        if not path.is_file():
            continue
        key = path.name.lower()
        if key not in keep_lower or key not in critical_lower:
            continue
        try:
            snaps[key] = path.read_bytes()
        except OSError as exc:
            logger.warning("Could not backup %s before update: %s", path.name, exc)
    for canon in _CRITICAL_FILE_BACKUPS:
        path = target / canon
        if path.is_file() and canon.lower() not in snaps:
            try:
                snaps[canon.lower()] = path.read_bytes()
            except OSError as exc:
                logger.warning("Could not backup %s before update: %s", canon, exc)
    return snaps


def _restore_critical_files(target: Path, snaps: dict[str, bytes]) -> None:
    """Put SECRETS / .env back if missing or altered by a bad merge."""
    for key, payload in snaps.items():
        if key == "secrets":
            dest = target / "SECRETS"
        elif key == ".env":
            dest = target / ".env"
        else:
            dest = target / key
        try:
            if dest.is_file() and dest.read_bytes() == payload:
                continue
            dest.write_bytes(payload)
            logger.info("Restored preserved file after update: %s", dest.name)
        except OSError as exc:
            logger.error("Failed to restore %s after update: %s", dest, exc)


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
    """Unpack ``zip_path`` over ``app_root``, preserving local data/venv/SECRETS.

    Matching of preserved names is **case-insensitive** so a zip entry named
    ``secrets`` cannot delete ``SECRETS`` on Windows. Critical files are also
    snapshotted and restored after the merge.

    Returns the app root that was updated.
    """
    target = (app_root or ROOT).resolve()
    keep = set(preserve) if preserve is not None else set(PRESERVE_TOP_LEVEL)
    keep_lower = _preserve_keyset(keep)
    snaps = _snapshot_critical_files(target, keep_lower)

    with tempfile.TemporaryDirectory(prefix="quanta_upd_") as tmp:
        tmp_path = Path(tmp)
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        source = _find_app_root(extract_dir)

        for item in source.iterdir():
            name = item.name
            if _is_preserved(name, keep_lower):
                logger.debug("Skipping preserved top-level entry: %s", name)
                continue
            # Refuse to clobber a preserved local path under case-insensitive FS
            skip = False
            try:
                for local in target.iterdir():
                    if local.name.lower() != name.lower():
                        continue
                    if _is_preserved(local.name, keep_lower):
                        skip = True
                        break
            except OSError:
                pass
            if skip:
                logger.warning(
                    "Refusing to replace preserved local path with zip entry %r", name
                )
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

    _restore_critical_files(target, snaps)
    logger.info("Applied update zip into %s", target)
    return target


def download_and_apply(zip_url: str, *, app_root: Optional[Path] = None) -> Path:
    """Download release zip and apply over the app folder."""
    target = (app_root or ROOT).resolve()
    with tempfile.TemporaryDirectory(prefix="quanta_dl_") as tmp:
        zip_path = Path(tmp) / "update.zip"
        download_file(zip_url, zip_path)
        return apply_standalone_zip(zip_path, app_root=target)
