"""L1 — paths and runtime directories."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
EXPORTS_DIR = ROOT / "exports"
FIXTURES_DIR = ROOT / "fixtures"
DB_PATH = DATA_DIR / "quanta.db"
CONFIG_PATH = DATA_DIR / "settings.json"
CANCEL_FLAG = DATA_DIR / "cancel.flag"
HARD_STOP_FLAG = DATA_DIR / "hard_stop.flag"
LOG_DIR = DATA_DIR / "logs"


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, JOBS_DIR, EXPORTS_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def job_dir(job_id: int | str) -> Path:
    path = JOBS_DIR / str(job_id)
    for sub in ("input", "raw", "curated", "logs"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path
