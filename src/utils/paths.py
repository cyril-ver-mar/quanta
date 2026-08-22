"""L1 — paths and runtime directories."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
GAUSSIAN_WORK_DIR = DATA_DIR / "gaussian_work"
EXPORTS_DIR = ROOT / "exports"
FIXTURES_DIR = ROOT / "fixtures"
DB_PATH = DATA_DIR / "quanta.db"
CONFIG_PATH = DATA_DIR / "settings.json"
CANCEL_FLAG = DATA_DIR / "cancel.flag"
HARD_STOP_FLAG = DATA_DIR / "hard_stop.flag"
LOG_DIR = DATA_DIR / "logs"


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, JOBS_DIR, GAUSSIAN_WORK_DIR, EXPORTS_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def job_dir(job_id: int | str) -> Path:
    path = JOBS_DIR / str(job_id)
    for sub in ("input", "raw", "curated", "logs"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path


def safe_fs_name(text: str, *, max_len: int = 60) -> str:
    """Filesystem-safe ASCII folder name."""
    s = (text or "unnamed").strip()
    for src, dst in (("·", "-"), ("Δ", "Delta"), (" ", "_"), ("/", "-"), ("\\", "-")):
        s = s.replace(src, dst)
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._-")
    return (s or "unnamed")[:max_len]


def gaussian_run_dir(
    *,
    work_dir: str,
    project_name: str,
    job_id: int,
    job_name: str,
) -> Path:
    """``{work_root}/{project}/{job_id}_{description}/`` for Gaussian I/O files."""
    root = Path(work_dir).expanduser() if (work_dir or "").strip() else GAUSSIAN_WORK_DIR
    path = root / safe_fs_name(project_name) / f"{job_id}_{safe_fs_name(job_name)}"
    path.mkdir(parents=True, exist_ok=True)
    return path
