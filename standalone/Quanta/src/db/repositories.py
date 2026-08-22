"""L3 — compound / job repositories."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from src.core.models import Compound, Job, JobStatus
from src.db.connection import connect, init_db
from src.utils.paths import DB_PATH, ensure_runtime_dirs


def _backup_db() -> Path | None:
    ensure_runtime_dirs()
    if not DB_PATH.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DB_PATH.with_name(f"quanta_backup_{stamp}.db")
    shutil.copy2(DB_PATH, dest)
    return dest


class CompoundRepository:
    def __init__(self) -> None:
        init_db()

    def add(self, compound: Compound) -> int:
        conn = connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO compounds (name, source_format, source_path, charge, multiplicity, formula, n_atoms, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    compound.name,
                    compound.source_format,
                    compound.source_path,
                    compound.charge,
                    compound.multiplicity,
                    compound.formula,
                    compound.n_atoms,
                    json.dumps(compound.meta_json),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_all(self) -> list[Compound]:
        conn = connect()
        try:
            rows = conn.execute("SELECT * FROM compounds ORDER BY id DESC").fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, compound_id: int) -> Compound | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM compounds WHERE id = ?", (compound_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def update_charge_mult(self, compound_id: int, charge: int, multiplicity: int) -> None:
        conn = connect()
        try:
            conn.execute(
                "UPDATE compounds SET charge = ?, multiplicity = ? WHERE id = ?",
                (charge, multiplicity, compound_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row(row) -> Compound:
        return Compound(
            id=row["id"],
            name=row["name"],
            source_format=row["source_format"],
            source_path=row["source_path"],
            charge=row["charge"],
            multiplicity=row["multiplicity"],
            formula=row["formula"],
            n_atoms=row["n_atoms"],
            meta_json=json.loads(row["meta_json"] or "{}"),
        )


class JobRepository:
    def __init__(self) -> None:
        init_db()

    def add(self, job: Job) -> int:
        conn = connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO jobs (compound_id, name, status, route, nproc, mem_mb, work_path, error, progress, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.compound_id,
                    job.name,
                    job.status.value,
                    job.route,
                    job.nproc,
                    job.mem_mb,
                    job.work_path,
                    job.error,
                    job.progress,
                    json.dumps(job.meta_json),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_all(self) -> list[Job]:
        conn = connect()
        try:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def list_by_status(self, *statuses: JobStatus) -> list[Job]:
        conn = connect()
        try:
            qs = ",".join("?" for _ in statuses)
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status IN ({qs}) ORDER BY id ASC",
                tuple(s.value for s in statuses),
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def list_by_compound(self, compound_id: int) -> list[Job]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE compound_id = ? ORDER BY id DESC",
                (compound_id,),
            ).fetchall()
            return [self._row(r) for r in rows]
        finally:
            conn.close()

    def get(self, job_id: int) -> Job | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return self._row(row) if row else None
        finally:
            conn.close()

    def update(self, job: Job) -> None:
        assert job.id is not None
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE jobs SET status=?, work_path=?, error=?, progress=?, meta_json=?,
                updated_at=datetime('now') WHERE id=?
                """,
                (
                    job.status.value,
                    job.work_path,
                    job.error,
                    job.progress,
                    json.dumps(job.meta_json),
                    job.id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_pending(self, job_id: int) -> None:
        """Delete queued/draft/paused jobs only; backup DB first."""
        job = self.get(job_id)
        if job is None:
            return
        if job.status not in (JobStatus.QUEUED, JobStatus.DRAFT, JobStatus.PAUSED, JobStatus.CANCELLED):
            raise ValueError(f"Cannot delete job in status {job.status}")
        _backup_db()
        conn = connect()
        try:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row(row) -> Job:
        return Job(
            id=row["id"],
            compound_id=row["compound_id"],
            name=row["name"],
            status=JobStatus(row["status"]),
            route=row["route"],
            nproc=row["nproc"],
            mem_mb=row["mem_mb"],
            work_path=row["work_path"],
            error=row["error"],
            progress=row["progress"],
            meta_json=json.loads(row["meta_json"] or "{}"),
        )
