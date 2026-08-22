"""Project persistence — JSON payload + SQLite index (XPS-Deconv pattern)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.core.project import CompoundEntry, QuantaProject
from src.db.repositories import CompoundRepository
from src.utils.paths import DATA_DIR, ensure_runtime_dirs

PROJECTS_DIR = DATA_DIR / "projects"
PROJECT_DB_PATH = DATA_DIR / "projects_index.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE,
    n_entries INTEGER DEFAULT 0,
    notes TEXT
);
"""


def ensure_project_dirs() -> None:
    ensure_runtime_dirs()
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    ensure_project_dirs()
    path = db_path or PROJECT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def backup_db() -> Path | None:
    ensure_project_dirs()
    if not PROJECT_DB_PATH.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = PROJECT_DB_PATH.with_suffix(f".{stamp}.bak")
    dest.write_bytes(PROJECT_DB_PATH.read_bytes())
    return dest


def project_json_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"


def save_project(project: QuantaProject) -> Path:
    ensure_project_dirs()
    project.touch()
    path = project_json_path(project.id)
    path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, created_at, updated_at, json_path, n_entries, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              updated_at=excluded.updated_at,
              json_path=excluded.json_path,
              n_entries=excluded.n_entries,
              notes=excluded.notes
            """,
            (
                project.id,
                project.name,
                project.created_at,
                project.updated_at,
                str(path),
                len(project.entries),
                project.notes,
            ),
        )
    return path


def load_project(project_id: str) -> QuantaProject:
    path = project_json_path(project_id)
    if not path.exists():
        with connect() as conn:
            row = conn.execute(
                "SELECT json_path FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if not row:
                raise FileNotFoundError(f"Project not found: {project_id}")
            path = Path(row["json_path"])
    return QuantaProject.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_projects() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_project(project_id: str) -> None:
    backup_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT json_path FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row:
            path = Path(row["json_path"])
            if path.exists():
                path.unlink()
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


def create_project(name: str, notes: str = "") -> QuantaProject:
    project = QuantaProject(name=name.strip() or "Untitled project", notes=notes)
    save_project(project)
    return project


def add_compound_to_project(
    project: QuantaProject,
    compound_id: int,
    label: str | None = None,
) -> CompoundEntry:
    for entry in project.entries:
        if entry.compound_id == compound_id:
            if label:
                entry.label = label
            save_project(project)
            return entry
    compound = CompoundRepository().get(compound_id)
    entry = CompoundEntry(
        label=label or (compound.name if compound else f"Compound #{compound_id}"),
        compound_id=compound_id,
    )
    project.entries.append(entry)
    if project.active_entry_id is None:
        project.active_entry_id = entry.id
    save_project(project)
    return entry


def set_active_entry(project: QuantaProject, entry_id: str) -> CompoundEntry:
    for entry in project.entries:
        if entry.id == entry_id:
            project.active_entry_id = entry_id
            save_project(project)
            return entry
    raise KeyError(entry_id)


def remove_entry(project: QuantaProject, entry_id: str) -> None:
    project.entries = [e for e in project.entries if e.id != entry_id]
    if project.active_entry_id == entry_id:
        project.active_entry_id = project.entries[0].id if project.entries else None
    save_project(project)


def ensure_legacy_migration() -> QuantaProject | None:
    """If DB has compounds but no projects, wrap them in a default project."""
    if list_projects():
        return None
    compounds = CompoundRepository().list_all()
    if not compounds:
        return None
    project = create_project("Default project", notes="Auto-created from existing compounds.")
    for comp in compounds:
        if comp.id is not None:
            add_compound_to_project(project, comp.id, label=comp.name)
    return load_project(project.id)
