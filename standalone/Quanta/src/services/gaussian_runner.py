"""L4 — detect run vs analyze mode; launch Gaussian when available."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from src.core.dscf import (
    StepKind,
    StepStatus,
    assign_core_orbitals,
    homo_orbital_index,
    is_dscf_workflow,
    list_xps_atoms,
    next_runnable_step,
)
from src.core.models import JobStatus
from src.db.repositories import JobRepository
from src.services.compound_service import CompoundService, mol_to_atoms
from src.services.gaussian_parser import estimate_eta_seconds, final_scf_energy_ha, parse_gaussian_log
from src.services.job_service import JobService
from src.services.results_service import ResultsService
from src.utils.cancel import clear_cancel_flags, hard_stop_requested, soft_cancel_requested
from src.utils.config import AppSettings
from src.utils.logging_setup import get_logger
from src.utils.paths import job_dir

logger = get_logger("quanta.runner")

# Windows Gaussian GUI launchers open an empty editor; CLI is g09.exe / g16.exe beside them.
_GUI_NAMES = frozenset({"g09w.exe", "g16w.exe", "g09w", "g16w"})


def _coerce_cli_exe(exe: str) -> str | None:
    """Prefer command-line Gaussian over the Windows GUI wrapper."""
    path = Path(exe)
    name = path.name.lower()
    if name.endswith(".app"):
        logger.warning("Gaussian.app cannot be driven from Quanta — set path to g09/g16 binary")
        return None
    if name in _GUI_NAMES:
        for cli_name in ("g09.exe", "g16.exe", "g09", "g16"):
            candidate = path.with_name(cli_name)
            if candidate.is_file():
                logger.info("Using CLI %s instead of GUI %s", candidate, path)
                return str(candidate)
        logger.warning(
            "Settings point to GUI %s but no g09.exe/g16.exe found next to it",
            path,
        )
        return None
    return str(path)


def gaussian_available(settings: AppSettings) -> bool:
    return resolve_gaussian_exe(settings) is not None


def resolve_gaussian_exe(settings: AppSettings) -> str | None:
    exe = (settings.gaussian_exe or "").strip()
    if exe and Path(exe).exists():
        return _coerce_cli_exe(exe)
    for name in ("g09", "g16"):
        found = shutil.which(name)
        if found:
            return found
    return None


class GaussianRunner:
    """Runs ΔSCF workflow steps one queued job at a time."""

    def __init__(self) -> None:
        self.repo = JobRepository()
        self.jobs = JobService()
        self.compounds = CompoundService()
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

        job = None
        for candidate in queued:
            steps = self.jobs.get_steps(candidate.id or 0)
            if is_dscf_workflow(steps):
                job = candidate
                break
            assert candidate.id is not None
            candidate.status = JobStatus.FAILED
            candidate.error = (
                "Not a ΔSCF workflow job — delete this job and create a new workflow on the Jobs page."
            )
            self.repo.update(candidate)

        if job is None:
            return None
        assert job.id is not None
        job.status = JobStatus.RUNNING
        self.repo.update(job)

        try:
            while True:
                steps = self.jobs.get_steps(job.id)
                step = next_runnable_step(steps)
                if step is None:
                    if steps and all(s.status == StepStatus.COMPLETED for s in steps):
                        job.status = JobStatus.COMPLETED
                        self.results.curate_job(job.id, settings)
                    else:
                        job.status = JobStatus.QUEUED
                    self.repo.update(job)
                    return job.id

                ok = self._run_step(job.id, step, settings, exe)
                steps = self.jobs.get_steps(job.id)
                if not ok:
                    job = self.repo.get(job.id)
                    assert job is not None
                    job.status = JobStatus.FAILED
                    self.repo.update(job)
                    return job.id

                self._prepare_following_steps(job.id, step.key, settings)
                steps = self.jobs.get_steps(job.id)
                if all(s.status == StepStatus.COMPLETED for s in steps):
                    job.status = JobStatus.COMPLETED
                    self.results.curate_job(job.id, settings)
                    self.repo.update(job)
                    if soft_cancel_requested():
                        for q in self.repo.list_by_status(JobStatus.QUEUED):
                            q.status = JobStatus.PAUSED
                            self.repo.update(q)
                        clear_cancel_flags()
                    return job.id
        except Exception as exc:
            logger.exception("Workflow job %s failed", job.id)
            job = self.repo.get(job.id)
            if job:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                self.repo.update(job)
            return job.id

    def _prepare_following_steps(self, job_id: int, completed_key: str, settings: AppSettings) -> None:
        steps = self.jobs.get_steps(job_id)
        job = self.repo.get(job_id)
        if job is None:
            return

        if completed_key == "opt":
            neutral = next(s for s in steps if s.kind == StepKind.NEUTRAL_SP)
            path = self.jobs.write_neutral_gjf(job_id, settings)
            neutral.status = StepStatus.QUEUED
            job.meta_json["current_gjf"] = str(path)
            self.jobs.save_steps(job_id, steps)
            return

        if completed_key == "neutral_sp":
            compound = self.compounds.get(job.compound_id)
            if compound is None:
                raise ValueError("compound missing")
            mol = self.compounds.load_molecule(compound)
            xps_atoms = list_xps_atoms(mol_to_atoms(mol))
            neutral_log = job_dir(job_id) / "raw" / next(
                s for s in steps if s.kind == StepKind.NEUTRAL_SP
            ).log_name
            parsed = parse_gaussian_log(neutral_log)
            orb_map = assign_core_orbitals(parsed.orbitals, xps_atoms)
            homo = homo_orbital_index(parsed.orbitals)
            for step in steps:
                if step.kind != StepKind.COREHOLE_SP or step.atom_index is None:
                    continue
                step.orbital_index = orb_map[step.atom_index]
                step.homo_index = homo
                self.jobs.write_corehole_gjf(job_id, step, settings)
                step.status = StepStatus.QUEUED
            self.jobs.save_steps(job_id, steps)
            return

    def _run_step(self, job_id: int, step, settings: AppSettings, exe: str) -> bool:
        jdir = job_dir(job_id)
        gjf = jdir / "input" / step.gjf_name
        if not gjf.exists():
            step.status = StepStatus.FAILED
            step.error = f"Missing input {gjf.name}"
            steps = self.jobs.get_steps(job_id)
            for i, s in enumerate(steps):
                if s.key == step.key:
                    steps[i] = step
            self.jobs.save_steps(job_id, steps)
            job = self.repo.get(job_id)
            if job:
                job.error = step.error
                self.repo.update(job)
            return False

        out_log = jdir / "raw" / step.log_name
        step.status = StepStatus.RUNNING
        steps = self.jobs.get_steps(job_id)
        for i, s in enumerate(steps):
            if s.key == step.key:
                steps[i] = step
        self.jobs.save_steps(job_id, steps)

        clear_cancel_flags()
        env = os.environ.copy()
        exe_path = Path(exe).resolve()
        env.setdefault("GAUSS_EXEDIR", str(exe_path.parent))
        if settings.scratch_dir:
            env["GAUSS_SCRDIR"] = settings.scratch_dir
            Path(settings.scratch_dir).mkdir(parents=True, exist_ok=True)
        cwd = settings.work_dir or str(jdir / "raw")
        Path(cwd).mkdir(parents=True, exist_ok=True)

        local_gjf = Path(cwd) / gjf.name
        local_gjf.write_text(gjf.read_text(encoding="utf-8"), encoding="utf-8")

        # Gaussian writes <stem>.log itself. Do not open that path as stdout — on Windows
        # the lock prevents the job from running (GUI may open idle).
        gauss_log = Path(cwd) / f"{local_gjf.stem}.log"
        stdout_capture = Path(cwd) / f"{local_gjf.stem}.stdout.txt"
        if gauss_log.exists():
            gauss_log.unlink()

        cmd = [str(exe_path), local_gjf.name]
        logger.info("Starting job %s step %s: %s (cwd=%s)", job_id, step.key, cmd, cwd)
        started = time.time()
        job = self.repo.get(job_id)
        assert job is not None
        job.meta_json["current_step"] = step.key
        job.meta_json["current_gjf"] = str(gjf)
        self.repo.update(job)

        try:
            with open(stdout_capture, "w", encoding="utf-8") as stdout_f:
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=stdout_f,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
                while True:
                    ret = self._proc.poll()
                    monitor_log = gauss_log if gauss_log.exists() and gauss_log.stat().st_size > 0 else None
                    if monitor_log is not None:
                        parsed = parse_gaussian_log(monitor_log)
                        job.progress = parsed.progress_estimate * (
                            sum(1 for s in self.jobs.get_steps(job_id) if s.status == StepStatus.COMPLETED)
                            + 0.5
                        ) / max(len(self.jobs.get_steps(job_id)), 1)
                        eta = estimate_eta_seconds(parsed, time.time() - started)
                        job.meta_json["eta_s"] = eta
                        job.meta_json["opt_steps"] = parsed.opt_steps
                        self.repo.update(job)
                    if hard_stop_requested() and self._proc.poll() is None:
                        self._proc.terminate()
                        time.sleep(2)
                        if self._proc.poll() is None:
                            self._proc.kill()
                        step.status = StepStatus.FAILED
                        step.error = "Hard stop requested"
                        steps = self.jobs.get_steps(job_id)
                        for i, s in enumerate(steps):
                            if s.key == step.key:
                                steps[i] = step
                        self.jobs.save_steps(job_id, steps)
                        clear_cancel_flags()
                        return False
                    if ret is not None:
                        break
                    time.sleep(2)

            for pattern in ("*.chk", "*.log", "*.out"):
                for f in Path(cwd).glob(pattern):
                    dest = jdir / "raw" / f.name
                    if f.resolve() != dest.resolve():
                        shutil.copy2(f, dest)

            if gauss_log.exists() and gauss_log.resolve() != out_log.resolve():
                shutil.copy2(gauss_log, out_log)
            elif not out_log.exists() and gauss_log.exists():
                shutil.copy2(gauss_log, out_log)

            if not out_log.exists() or out_log.stat().st_size == 0:
                step.status = StepStatus.FAILED
                step.error = (
                    "Gaussian produced no log. Use the CLI binary (g09.exe / g16.exe), "
                    "not the Windows GUI (g09w.exe)."
                )
                steps = self.jobs.get_steps(job_id)
                for i, s in enumerate(steps):
                    if s.key == step.key:
                        steps[i] = step
                self.jobs.save_steps(job_id, steps)
                job = self.repo.get(job_id)
                if job:
                    job.error = step.error
                    self.repo.update(job)
                return False

            parsed = parse_gaussian_log(out_log)
            steps = self.jobs.get_steps(job_id)
            for i, s in enumerate(steps):
                if s.key == step.key:
                    step = s
                    break

            if parsed.normal_termination:
                step.status = StepStatus.COMPLETED
                step.energy_ha = final_scf_energy_ha(parsed)
                step.error = ""
            else:
                step.status = StepStatus.FAILED
                step.error = "; ".join(parsed.raw_errors) or "Gaussian did not terminate normally"

            for i, s in enumerate(steps):
                if s.key == step.key:
                    steps[i] = step
            self.jobs.save_steps(job_id, steps)
            return step.status == StepStatus.COMPLETED
        except Exception as exc:
            logger.exception("Step %s failed", step.key)
            step.status = StepStatus.FAILED
            step.error = str(exc)
            steps = self.jobs.get_steps(job_id)
            for i, s in enumerate(steps):
                if s.key == step.key:
                    steps[i] = step
            self.jobs.save_steps(job_id, steps)
            return False
        finally:
            self._proc = None
