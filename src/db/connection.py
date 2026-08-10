"""L3 — SQLite connection and schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.utils.paths import DB_PATH, ensure_runtime_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS compounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_format TEXT NOT NULL,
    source_path TEXT NOT NULL,
    charge INTEGER NOT NULL DEFAULT 0,
    multiplicity INTEGER NOT NULL DEFAULT 1,
    formula TEXT NOT NULL DEFAULT '',
    n_atoms INTEGER NOT NULL DEFAULT 0,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compound_id INTEGER NOT NULL REFERENCES compounds(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    route TEXT NOT NULL,
    nproc INTEGER NOT NULL,
    mem_mb INTEGER NOT NULL,
    work_path TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    progress REAL NOT NULL DEFAULT 0,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_compound ON jobs(compound_id);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    ensure_runtime_dirs()
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
