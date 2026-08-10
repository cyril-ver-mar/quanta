"""L4 — detect run vs analyze mode; launch Gaussian when available."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from src.core.models import JobStatus
from src.db.repositories import JobRepository
from src.services.gaussian_parser import estimate_eta_seconds, parse_gaussian_log
from src.services.results_service import ResultsService
from src.utils.cancel import clear_cancel_flags, hard_stop_requested, soft_cancel_requested
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.runner")


def gaussian_available(settings: AppSettings) -> bool:
    exe = (settings.gaussian_exe or "").strip()
    if exe and Path(exe).exists():
        return True
    return shutil.which("g09") is not None or shutil.which("g16") is not None


def resolve_gaussian_exe(settings: AppSettings) -> str | None:
    exe = (settings.gaussian_exe or "").strip()
    if exe and Path(exe).exists():
        return exe
    for name in ("g09", "g16"):
        found = shutil.which(name)
        if found:
            return found
    return None


class GaussianRunner:
    """Runs one queued job at a time. No-op when Gaussian is missing."""

    def __init__(self) -> None:
        self.repo = JobRepository()
        self.results = ResultsService()
        self._proc: subprocess.Popen | None = None

    def run_next(self, settings: AppSettings) -> int | None:
        exe = resolve_gaussian_exe(settings)
        if exe is None:
            logger.warning("Gaussian not available — analyze mode only")
            return None

        queued = self.repo.list_by_status(JobStatus.QUEUED)
        if not queued:
            return None
        job = queued[0]
        assert job.id is not None
        jdir = job_dir(job.id)
        gjf = Path(job.meta_json.get("gjf") or (jdir / "input" / f"job_{job.id}.gjf"))
        if not gjf.exists():
            job.status = JobStatus.FAILED
            job.error = f"Missing input {gjf}"
            self.repo.update(job)
            return job.id

        out_log = jdir / "raw" / f"job_{job.id}.log"
        clear_cancel_flags()
        job.status = JobStatus.RUNNING
        job.progress = 0.05
        self.repo.update(job)

        env = os.environ.copy()
        if settings.scratch_dir:
            env["GAUSS_SCRDIR"] = settings.scratch_dir
            Path(settings.scratch_dir).mkdir(parents=True, exist_ok=True)
        cwd = settings.work_dir or str(jdir / "raw")
        Path(cwd).mkdir(parents=True, exist_ok=True)

        # Copy gjf into cwd for Gaussian relative chk paths
        local_gjf = Path(cwd) / gjf.name
        local_gjf.write_text(gjf.read_text(encoding="utf-8"), encoding="utf-8")

        cmd = [exe, str(local_gjf.name)]
        logger.info("Starting job %s: %s", job.id, cmd)
        started = time.time()
        try:
            with open(out_log, "w", encoding="utf-8") as log_f:
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
                while True:
                    ret = self._proc.poll()
                    if out_log.exists() and out_log.stat().st_size > 0:
                        parsed = parse_gaussian_log(out_log)
                        job.progress = parsed.progress_estimate
                        eta = estimate_eta_seconds(parsed, time.time() - started)
                        job.meta_json["eta_s"] = eta
                        job.meta_json["opt_steps"] = parsed.opt_steps
                        job.meta_json["scf_last"] = parsed.scf_energies_ha[-1] if parsed.scf_energies_ha else None
                        self.repo.update(job)
                    if hard_stop_requested() and self._proc.poll() is None:
                        self._proc.terminate()
                        time.sleep(2)
                        if self._proc.poll() is None:
                            self._proc.kill()
                        job.status = JobStatus.CANCELLED
                        job.error = "Hard stop requested"
                        self.repo.update(job)
                        clear_cancel_flags()
                        return job.id
                    if soft_cancel_requested() and ret is None:
                        # soft: let current job finish; mark remaining queued as paused after
                        pass
                    if ret is not None:
                        break
                    time.sleep(2)

            # Collect outputs into raw/
            for pattern in ("*.chk", "*.log", "*.out"):
                for f in Path(cwd).glob(pattern):
                    dest = jdir / "raw" / f.name
                    if f.resolve() != dest.resolve():
                        shutil.copy2(f, dest)

            parsed = parse_gaussian_log(out_log)
            job.progress = parsed.progress_estimate
            if parsed.normal_termination:
                job.status = JobStatus.COMPLETED
                self.results.curate_job(job.id, settings)
            else:
                job.status = JobStatus.FAILED
                job.error = "; ".join(parsed.raw_errors) or "Gaussian did not terminate normally"
            self.repo.update(job)
            if soft_cancel_requested():
                for q in self.repo.list_by_status(JobStatus.QUEUED):
                    q.status = JobStatus.PAUSED
                    self.repo.update(q)
                clear_cancel_flags()
            return job.id
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job.status = JobStatus.FAILED
            job.error = str(exc)
            self.repo.update(job)
            return job.id
        finally:
            self._proc = None
