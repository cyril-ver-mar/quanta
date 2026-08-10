"""L4 — portable job archives for Windows ↔ Mac transfer."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from src.db.connection import connect, init_db
from src.utils.logging_setup import get_logger
from src.utils.paths import DB_PATH, EXPORTS_DIR, JOBS_DIR, ensure_runtime_dirs, job_dir

logger = get_logger("quanta.archive")


class ArchiveService:
    def export_jobs(self, job_ids: list[int] | None = None) -> Path:
        """Zip selected jobs (or all) + a SQLite snapshot of related rows."""
        ensure_runtime_dirs()
        init_db()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = EXPORTS_DIR / f"quanta_archive_{stamp}.zip"
        ids = job_ids
        if ids is None:
            ids = [int(p.name) for p in JOBS_DIR.iterdir() if p.is_dir() and p.name.isdigit()]

        conn = connect()
        try:
            job_rows = []
            compound_ids: set[int] = set()
            for jid in ids:
                row = conn.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
                if row:
                    job_rows.append(dict(row))
                    compound_ids.add(int(row["compound_id"]))
            compounds = []
            for cid in compound_ids:
                crow = conn.execute("SELECT * FROM compounds WHERE id = ?", (cid,)).fetchone()
                if crow:
                    compounds.append(dict(crow))
        finally:
            conn.close()

        manifest = {"version": 1, "exported_at": stamp, "job_ids": ids, "jobs": job_rows, "compounds": compounds}
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            if DB_PATH.exists():
                zf.write(DB_PATH, arcname="quanta_snapshot.db")
            for jid in ids:
                jpath = JOBS_DIR / str(jid)
                if not jpath.exists():
                    continue
                for file in jpath.rglob("*"):
                    if file.is_file():
                        zf.write(file, arcname=f"jobs/{jid}/{file.relative_to(jpath).as_posix()}")
        logger.info("Exported archive %s (%d jobs)", out, len(ids))
        return out

    def import_archive(self, zip_path: Path) -> list[int]:
        """Import job folders + upsert compound/job metadata from manifest."""
        ensure_runtime_dirs()
        init_db()
        imported: list[int] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            # extract job files
            for name in zf.namelist():
                if name.startswith("jobs/") and not name.endswith("/"):
                    target = JOBS_DIR / name[len("jobs/") :]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

            conn = connect()
            try:
                id_map: dict[int, int] = {}
                for c in manifest.get("compounds", []):
                    old_id = int(c["id"])
                    cur = conn.execute(
                        """
                        INSERT INTO compounds (name, source_format, source_path, charge, multiplicity, formula, n_atoms, meta_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            c["name"],
                            c["source_format"],
                            c["source_path"],
                            c["charge"],
                            c["multiplicity"],
                            c["formula"],
                            c["n_atoms"],
                            c.get("meta_json") or "{}",
                        ),
                    )
                    id_map[old_id] = int(cur.lastrowid)
                for j in manifest.get("jobs", []):
                    old_cid = int(j["compound_id"])
                    new_cid = id_map.get(old_cid, old_cid)
                    cur = conn.execute(
                        """
                        INSERT INTO jobs (compound_id, name, status, route, nproc, mem_mb, work_path, error, progress, meta_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_cid,
                            j["name"],
                            j["status"],
                            j["route"],
                            j["nproc"],
                            j["mem_mb"],
                            j.get("work_path") or "",
                            j.get("error") or "",
                            j.get("progress") or 0,
                            j.get("meta_json") or "{}",
                        ),
                    )
                    new_jid = int(cur.lastrowid)
                    old_jid = int(j["id"])
                    # move extracted folder old_jid → new_jid if needed
                    old_dir = JOBS_DIR / str(old_jid)
                    new_dir = job_dir(new_jid)
                    if old_dir.exists() and old_dir.resolve() != new_dir.resolve():
                        for item in old_dir.rglob("*"):
                            if item.is_file():
                                dest = new_dir / item.relative_to(old_dir)
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(item, dest)
                    imported.append(new_jid)
                conn.commit()
            finally:
                conn.close()
        logger.info("Imported %d jobs from %s", len(imported), zip_path)
        return imported
